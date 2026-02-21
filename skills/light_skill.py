import time
import random
import tts

"""
@Author: DuoDuoJuZi
@Date: 2026-02-21
"""

def execute(parameters, mqtt_client, mqtt_topic):
    """
    执行灯光控制技能。

    Args:
        parameters: 包含动作指令的字典，例如 {"action": "ON"}.
        mqtt_client: MQTT 客户端实例。
        mqtt_topic: 控制指令发布的 MQTT 主题。
    """
    action = parameters.get("action")
    
    if action in ["ON", "OFF"]:
        file_num = random.choice([1, 2])
        audio_file = f"template/{action.lower()}_{file_num}.wav" 
        
        print(f"播放预设语音: {audio_file}")
        tts.play_local_file(audio_file)

        time.sleep(1) 
        
        mqtt_client.publish(mqtt_topic, action)
        print(f"已发送 MQTT 指令: {action}")
    else:
        print("动作参数错误")
