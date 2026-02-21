import os
import re
import json
import time
import random
import paho.mqtt.client as mqtt
from openai import OpenAI
from funasr import AutoModel
import speech_recognition as sr
from pypinyin import lazy_pinyin
import soundfile as sf
from dotenv import load_dotenv
import tts
from skills import light_skill

"""
@Author: DuoDuoJuZi
@Date: 2026-02-21
"""

load_dotenv()

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

WAKE_WORDS_PINYIN = [['miu', 'er', 'sai', 'si'], ['miu', 'er'], ['sai', 'si'], ['miu', 'miu']]

def levenshtein_distance(s1, s2):
    """
    计算两个序列（字符串或列表）之间的编辑距离。

    Args:
        s1: 第一个序列。
        s2: 第二个序列。

    Returns:
        两个序列之间的 Levenshtein 距离。
    """
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
    """
    检测输入文本中是否包含唤醒词，支持拼音模糊匹配。

    Args:
        text: 语音识别后的文本。

    Returns:
        一个元组 (is_wake, cleaned_text)，其中 is_wake 为布尔值，cleaned_text 为去除唤醒词后的文本。
    """
    if "muelsyse" in text.lower():
        cleaned_text = re.sub(r'(?i)muelsyse', '', text).strip(" ，。！？,.!?")
        return True, cleaned_text

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

                before = text[:i]
                after = text[i+n:]
                
                cleaned_text = (before + after).strip(" ，。！？,.!?")

                if not cleaned_text:
                    cleaned_text = text 
                
                return True, cleaned_text
                
    return False, text

def get_ai_decision(text):
    """
    调用大模型分析用户文本意图并生成回复。

    Args:
        text: 用户输入的自然语言文本。

    Returns:
        包含意图、参数和回复消息的字典。
    """
    prompt = f"""
    你是游戏《明日方舟》中的角色缪尔赛思（Mulsyse）。
    你的身份是莱茵生命生态科主任，一位能操纵水分子、制造“流形”水分身的精灵。
    你的性格俏皮、聪慧、有些小恶魔，你对面前的“博士”有着极深的感情和绝对的信任。

    【核心任务：意图识别】
    请根据博士的语音转录文本，判断他的核心意图，并提取相关参数。
    目前支持的意图有：
    1. "light_control": 博士想开灯或关灯。
    2. "chat": 博士在和你闲聊、问问题，或者指令不明确。作为生态科主任，你拥有渊博的学识。当博士询问百科知识、常识或专业问题时，请精准调用你的知识库进行解答，将科普与你的俏皮语气完美融合。
    （未来会加入闹钟等，目前仅限这两种）

    【语音容错】
    博士的话是通过语音转录的，可能把“缪尔赛思”识别成“约尔赛斯”，把“开灯”识别成“开登”等。请聪慧地忽略错别字，理解真实意图！你永远只能自称“缪尔赛思”或“我”。

    【严格要求】
    1. 必须严格返回 JSON 格式数据。
    2. message 字段是你对博士的回复，必须以“博士，...” 或 “Doctor，...” 开头！请根据内容自动判断字数：如果是日常闲聊，长度严格控制在20字以内；如果是回答科普知识或专业问题，则不做字数限制。

    【返回 JSON 字段规范】
    - intent: 必须是 "light_control" 或 "chat"
    - parameters: 一个字典。如果是 light_control，则包含 {{"action": "ON" 或 "OFF"}}；如果是 chat，则为空字典 {{}}。
    - message: 你的回复文本，当 intent 是 light_control 时，不需要返回字段。
    - time: "{time.strftime('%Y-%m-%d %H:%M:%S')}"

    当前博士的语音转录内容为: "{text}"
    请聪慧地滤除杂音，给出你的JSON回复：
    """
    
    response = ai_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def clean_sensevoice_output(text):
    """
    清理 SenseVoice 输出文本中的特殊标签。

    Args:
        text: 包含标签的原始文本。

    Returns:
        清理后的纯文本。
    """
    cleaned = re.sub(r'<\|.*?\|>', '', text)
    return cleaned.strip()

def listen_and_talk():
    """
    主循环函数，负责监听语音、识别、理解意图并执行相应操作。
    """
    recognizer = sr.Recognizer()

    recognizer.pause_threshold = 1.8
    recognizer.non_speaking_duration = 0.5

    with sr.Microphone(sample_rate=16000) as source:
        print("\n[听取中...] 请下达指令 (例如: 请把灯打开)")
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
        audio = recognizer.listen(source, phrase_time_limit=15)

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
        
        is_wake, clean_text = check_wake_word(user_text)
        if not is_wake:
            print("未检测到唤醒词")
            return
            
        print(clean_text)

        decision = get_ai_decision(clean_text)
        
        intent = decision.get("intent", "chat")
        parameters = decision.get("parameters", {})
        message = decision.get("message", "")
        
        print(f"PRTS 解析意图: {intent}, 参数: {parameters}, 消息: {message}")
        
        if intent == "light_control":
            light_skill.execute(parameters, mqtt_client, MQTT_TOPIC)
            
        elif intent == "alarm_set":
            pass
            
        elif intent == "chat":
            if len(message) > 40:
                file_num = random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13 ,14, 15, 16, 17, 18])
                tts.play_local_file(f"template/wait/wait_{file_num}.wav")

                tts.mulsyse_speak(message)
            else:
                tts.mulsyse_speak(message)
            
        else:
            tts.mulsyse_speak(message)

    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    while True:
        listen_and_talk()