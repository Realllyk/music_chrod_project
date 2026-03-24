# 🎙️ Windows 系统音频采集 Agent

## 简介

这是一个运行在 Windows 上的 Python 脚本，用于抓取系统正在播放的音频（WASAPI Loopback）。

## 工作原理

```
[用户在 Windows 播放音乐]
          ↓
[Agent 通过 WASAPI Loopback 抓取]
          ↓
[保存为 WAV 文件]
          ↓
[上报给 Flask 后端]
          ↓
[后续进行扒谱识别]
```

## 安装

### 1. 确保 Python 已安装

需要 Python 3.8+，在 Windows 上运行。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

或者手动安装：

```bash
pip install pyaudiowpatch requests
```

## 使用方法

### 方式 1：连接后端模式（推荐）

```bash
# 默认连接 http://127.0.0.1:5000
python agent.py

# 指定后端地址
python agent.py --backend http://192.168.5.129:5000

# 指定录音保存目录
python agent.py --output D:/recordings
```

**流程：**
1. 启动 Agent，等待后端任务
2. 在网页上点击「开始采集」
3. 播放音乐
4. 在网页上点击「停止采集」
5. Agent 自动保存 WAV 并上报后端

### 方式 2：独立模式（不需要后端）

```bash
python agent.py --standalone
```

**流程：**
1. 按 Enter 开始录制
2. 播放音乐
3. 按 Enter 停止录制
4. WAV 文件保存到本地

### 方式 3：列出可用设备

```bash
python agent.py --list-devices
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--backend`, `-b` | Flask 后端地址 | `http://127.0.0.1:5000` |
| `--output`, `-o` | 录音保存目录 | `./recordings` |
| `--standalone`, `-s` | 独立模式 | - |
| `--list-devices`, `-l` | 列出设备 | - |

## 输出文件

### WAV 文件

```
recordings/
└── 20260323/
    ├── sess_20260323_143025.wav
    └── sess_20260323_143025.json
```

### 元数据文件（JSON）

```json
{
  "session_id": "sess_20260323_143025",
  "source": "wasapi_loopback",
  "file_name": "sess_20260323_143025.wav",
  "file_path": "C:/project/agent/recordings/20260323/sess_20260323_143025.wav",
  "sample_rate": 48000,
  "channels": 2,
  "duration_sec": 37.2,
  "device_name": "Speakers (Realtek Audio)",
  "status": "recorded"
}
```

## 常见问题

### Q: 报错 "No module named 'pyaudiowpatch'"

A: 安装依赖：
```bash
pip install pyaudiowpatch
```

### Q: 报错 "找不到 loopback 设备"

A: 
1. 确保你在 Windows 上运行
2. 确保有音频输出设备（扬声器/耳机）
3. 尝试 `python agent.py --list-devices` 查看可用设备

### Q: 录制的音频没有声音

A:
1. 确保在录制时有音频正在播放
2. 检查系统音量是否静音
3. 某些软件（如 Discord）可能使用独占模式

### Q: 连接后端失败

A:
1. 确保 Flask 后端已启动
2. 检查后端地址是否正确
3. 检查防火墙设置

## 技术细节

- **采集方式**: WASAPI Loopback
- **音频格式**: WAV (PCM 16-bit)
- **采样率**: 使用设备默认（通常 44100 或 48000 Hz）
- **声道数**: 使用设备默认（通常 2 声道）

## 后续扩展

- [ ] 打包成 exe 可执行文件
- [ ] 添加系统托盘图标
- [ ] 支持选择特定设备
- [ ] 支持实时流式传输
