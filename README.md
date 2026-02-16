# Myurujisu

一个基于 Python 的轻量级智能家居语音控制终端

## 核心功能

- **精准语音识别**: 使用阿里达摩院开源的 `SenseVoiceSmall` 模型，支持中英混合识别，抗噪能力强。
- **模糊唤醒词**: 支持拼音模糊匹配唤醒词（如“缪尔赛斯”、“缪缪”），即使发音不准也能识别。
- **智能意图理解**: 集成 DeepSeek 大模型，不仅能听懂“把灯打开”，还能理解“太黑了”、“我不喜欢光”等自然表达。
- **MQTT 联动**: 标准 MQTT 协议输出控制指令 (`ON`/`OFF`)，易于接入各类开发板（ESP32/ESP8266）。

## 环境要求

- Python 3.8+
- 麦克风设备
- 网络连接（用于访问 DeepSeek API 和 MQTT Broker）

## 安装依赖

推荐使用 Python 虚拟环境：

```bash
# 1. 克隆项目
git clone https://github.com/DuoDuoJuZi/Myurujisu.git
cd Myurujisu

# 2. 安装 Python 依赖
pip install -r requirements.txt
```

> **注意**: `funasr` 和 `SenseVoice` 模型首次运行时会自动下载约 1GB 的模型文件。

## 配置

1.  **环境变量配置**:
    将 `.env.example` 复制为 `.env`，并根据实际情况修改配置：

    ```ini
    MQTT_BROKER=192.168.1.100
    MQTT_TOPIC=home/livingroom/light/set
    DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    ```

    或者在 `main.py` 中直接修改相关变量（不推荐）。

## 运行

```bash
python main.py
```

程序启动后会显示 `[听取中...]`，直接对着麦克风说出指令即可，例如：

- “缪尔赛斯，帮我把灯打开。”
- “缪缪，关灯。”
