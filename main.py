import os
import re
import json
import time
import paho.mqtt.client as mqtt
from openai import OpenAI
from funasr import AutoModel
import speech_recognition as sr
from pypinyin import lazy_pinyin
import soundfile as sf

MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_TOPIC = os.getenv("MQTT_TOPIC")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set("mqtt", "mqtt") 
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.loop_start()

ai_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

print("正在加载 SenseVoice 模型 (iic/SenseVoiceSmall)...")
stt_model = AutoModel(
    model="iic/SenseVoiceSmall",
    trust_remote_code=True,
    device="cpu",
)

WAKE_WORDS_PINYIN = [
    ['miu', 'er', 'sai', 'si'], # 缪尔赛斯
    ['miu', 'er'],              # 缪尔
    ['sai', 'si'],              # 赛斯
    ['miu', 'miu'],             # 缪缪
]

def levenshtein_distance(s1, s2):
    """计算两个拼音列表或字符串之间的编辑距离"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def check_wake_word(text):
    """基于拼音编辑距离的模糊唤醒词检测"""
    if "muelsyse" in text.lower():
        return True

    text_pinyin = lazy_pinyin(text)
    
    for wake_pinyin in WAKE_WORDS_PINYIN:
        n = len(wake_pinyin)
        for i in range(len(text_pinyin) - n + 1):
            window = text_pinyin[i:i+n]
            
            window_str = "".join(window)
            wake_str = "".join(wake_pinyin)
            
            dist = levenshtein_distance(window_str, wake_str)

            threshold = len(wake_str) * 0.35 
            if dist <= threshold:
                print(f"检测到唤醒词: {''.join(window)} (匹配: {wake_str}, 距离: {dist})")
                return True
                
    return False

def get_ai_decision(text):
    """把文字发给 DeepSeek，让它决定执行什么动作"""
    prompt = f"""
    你是一个智能管家。请根据用户的话，判断是否需要开灯或关灯。
    必须返回 JSON 格式，包含以下字段：
    - action: "ON" (如果是开灯), "OFF" (如果是关灯), "NONE" (其他)
    - message: 你回复用户的话
    - time: "{time.strftime('%Y-%m-%d %H:%M:%S')}"

    用户说: "{text}"
    """
    
    response = ai_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def clean_sensevoice_output(text):
    """
    SenseVoice 可能输出包含标签的文本，例如 <|zh|><|NEUTRAL|><|Speech|>你好
    这里使用正则去掉所有 <|...|> 格式的标签
    """
    cleaned = re.sub(r'<\|.*?\|>', '', text)
    return cleaned.strip()

def listen_and_talk():
    recognizer = sr.Recognizer()
    with sr.Microphone(sample_rate=16000) as source:
        print("\n[听取中...] 请下达指令 (例如: 请把灯打开)")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        with open("voice.wav", "wb") as f:
            f.write(audio.get_wav_data())

        audio_data, sample_rate = sf.read("voice.wav")

        res = stt_model.generate(
            input=audio_data,
            cache={},
            language="zh", 
            use_itn=True,
            batch_size_s=60, 
            merge_vad=True,
            merge_length_s=15,
        )

        raw_text = res[0]['text']
        user_text = clean_sensevoice_output(raw_text)
        
        print(f"我说: {user_text}")

        if not check_wake_word(user_text):
            print("未检测到唤醒词")
            return

        decision = get_ai_decision(user_text)
        print(f"机器人: {decision['message']}")

        if decision['action'] in ["ON", "OFF"]:
            mqtt_client.publish(MQTT_TOPIC, decision['action'])
            print(f"已发送 MQTT 指令: {decision['action']}")

    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    while True:
        listen_and_talk()