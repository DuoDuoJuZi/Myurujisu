import requests
import pygame
import io
import os
from dotenv import load_dotenv

"""
@Author: DuoDuoJuZi
@Date: 2026-02-21
"""

load_dotenv()

TTS_API_URL = os.getenv("TTS_API_URL")
REF_AUDIO_PATH = os.getenv("TTS_REF_AUDIO_PATH")
PROMPT_TEXT = os.getenv("TTS_PROMPT_TEXT")
PROMPT_LANG = os.getenv("TTS_PROMPT_LANG")

def play_audio(audio_bytes):
    """
    播放内存中的音频数据。

    Args:
        audio_bytes: 音频文件的二进制数据。
    """
    pygame.mixer.init()
    audio_stream = io.BytesIO(audio_bytes)
    pygame.mixer.music.load(audio_stream)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

def mulsyse_speak(text):
    """
    调用 TTS API 生成语音并播放。

    Args:
        text: 需要转换成语音的文本。
    """
    
    params = {
        "text": text,
        "text_language": "zh",               
        "refer_wav_path": REF_AUDIO_PATH,    
        "prompt_text": PROMPT_TEXT,
        "prompt_language": PROMPT_LANG       
    }
    
    try:
        response = requests.get(TTS_API_URL, params=params, timeout=30)
        
        if response.status_code == 200:
            play_audio(response.content)
        else:
            print(f"TTS 请求失败，错误码: {response.status_code}, 详情: {response.text}")
    except Exception as e:
        print(f"调用 TTS 出错: {e}")

def play_local_file(file_path):
    """
    播放本地音频文件。

    Args:
        file_path: 音频文件的本地路径。
    """
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"播放本地文件 {file_path} 失败: {e}")