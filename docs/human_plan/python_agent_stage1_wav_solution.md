# Windows 系统音频抓取方案（阶段一：Python Agent + WAV 持久化）

## 1. 文档目标

本方案用于实现一个 **Web 项目中的 Windows 系统音频采集链路**。当前阶段不追求完整桌面客户端，而是先通过一个 **本地 Python 脚本** 充当 Agent，完成以下闭环：

1. 用户在 Windows 电脑上播放音乐。
2. 本地 Python Agent 通过 **WASAPI loopback** 抓取系统正在播放的音频。
3. Agent 不直接把音频送入识别模块，而是**先保存为 WAV 文件**。
4. Flask 后端负责记录会话、接收文件信息、管理后续识别任务。
5. Web 前端只负责控制和展示，不直接采音。

本阶段的核心目标是：

- 先把 **采集 → 保存 → 管理** 这条链路跑通。
- 让采集到的音频具备可复用性，便于后续重跑识别算法。
- 让“音频采集”和“音频识别”两件事解耦。

---

## 2. 当前阶段的关键设计决策

### 2.1 为什么先做 Python Agent

原因如下：

- 你的现有后端是 Python / Flask，技术栈统一。
- WASAPI loopback 是 Windows 本地音频能力，需要本地程序调用。
- 网页本身不能直接无感调用系统级 loopback 采集。
- Python 脚本最容易快速验证采集是否稳定、音频是否可用、与后端是否能联通。

因此，当前阶段采用：

- **Windows 本地 Agent：Python 脚本**
- **用户启动方式：手动运行脚本**
- **音频输出：先保存为 WAV 文件，不直接进入识别**

---

### 2.2 为什么先保存，再识别

这是当前方案最重要的调整。

之前的思路是：

```text
采集 -> 立即上传 -> 立即识别
```

现在改成：

```text
采集 -> 保存为 WAV -> 注册到后端 -> 后续按需识别
```

这样做的好处：

- **复用性更高**：同一段音频可以多次重跑不同算法。
- **便于调试**：识别结果异常时，可以直接回放原始采集文件。
- **便于分阶段开发**：先验证采集，再验证识别，不把问题耦合在一起。
- **便于后续扩展**：以后可以增加离线批处理、切片重识别、缓存、数据集管理。

因此，本阶段建议把“采集层”和“识别层”彻底分开。

---

### 2.3 为什么保存成 WAV

当前阶段推荐把系统音频保存为 **WAV**，原因如下：

- WAV 是无损格式，适合后续基频提取和和弦识别。
- 结构简单，Python 处理方便。
- 调试最直接，几乎所有音频工具都能打开。
- 不会像 MP3 / AAC 那样因为有损压缩影响后续分析。

推荐保存参数：

- **容器格式**：WAV
- **编码**：PCM 16-bit
- **采样率**：保持采集设备原始采样率（通常 44100 Hz 或 48000 Hz）
- **声道数**：保持采集结果原始声道（通常 2 声道）

结论：

> 当前阶段统一采用 `WAV + PCM16` 作为持久化格式。

---

## 3. 核心概念

### 3.1 WASAPI loopback 的作用

WASAPI loopback 的作用不是录麦克风，而是：

> 让本地程序直接读取“电脑当前正在播放到扬声器/耳机的音频数据”。

也就是说：

- 它抓的是系统输出音频。
- 不是环境声音。
- 不是麦克风输入。
- 适合做音乐分析、频谱分析、基频提取、和弦识别。

---

### 3.2 本方案中的 Agent 是什么

本方案中的 Agent 是一个运行在 Windows 本机上的 Python 脚本，它负责：

- 调用 WASAPI loopback
- 读取 PCM 音频流
- 按规则保存为 WAV 文件
- 把文件元信息通知 Flask 后端
- 供网页间接控制采集流程

因此，Agent 不是网页的一部分，也不是 Flask 的一部分，而是第三个组件。

---

## 4. 总体架构

```text
[用户在 Windows 播放音乐]
          |
          v
[Windows 本地 Python Agent]
  - 调用 WASAPI loopback
  - 读取系统音频流
  - 保存为 WAV 文件
  - 上报文件信息给 Flask
          |
          v
[Flask Backend]
  - 创建采集会话
  - 记录 WAV 文件路径/元数据
  - 提供任务管理接口
  - 后续触发识别任务
          |
          v
[识别模块]
  - 读取 WAV
  - 预处理
  - pYIN
  - 和弦识别
          |
          v
[Web Frontend]
  - 开始采集
  - 停止采集
  - 查看会话
  - 触发识别
  - 展示结果
```

---

## 5. 组件职责划分

### 5.1 Windows 本地 Python Agent

职责：

- 调用 WASAPI loopback 抓系统音频
- 维护本地采集状态
- 把音频保存为 WAV 文件
- 记录采集参数
- 把文件元数据发送到 Flask

当前阶段建议形态：

- 文件名：`agent.py`
- 启动方式：命令行手动启动
- 运行方式：常驻进程

---

### 5.2 Flask 后端

职责：

- 创建会话
- 接收 Agent 上报的文件信息
- 管理会话状态
- 保存音频元数据
- 后续读取 WAV 文件并触发识别

当前阶段不要求：

- 实时流式识别
- 复杂任务队列
- 自动转码服务

---

### 5.3 Web 前端

职责：

- 提示用户先启动本地 Agent
- 点击“开始采集”
- 点击“停止采集”
- 查看采集历史
- 对某个 WAV 发起识别
- 展示识别结果

当前阶段网页不直接采音。

---

## 6. 推荐的数据流

### 6.1 当前阶段的数据流

```text
用户点击开始采集
    -> Flask 创建 session
    -> Agent 检测到 session 开始
    -> Agent 开始抓系统音频
    -> Agent 本地保存 WAV
    -> Agent 停止后上报文件信息
    -> Flask 记录 session 与文件关系
    -> 用户稍后点击“开始识别”
    -> Flask 读取 WAV 并调用识别模块
```

这意味着：

- 采集和识别不是同一步。
- 采集完成后，WAV 文件先落盘。
- 识别可以是手动触发，也可以后续再做自动触发。

---

### 6.2 推荐不要直接边采边识别

当前阶段不推荐主流程采用边采边识别，原因：

- 调试复杂度会明显上升。
- 出现识别错误时不容易定位问题是采集问题还是算法问题。
- 没有稳定的原始音频缓存，不利于复现。

因此建议：

> 先把 WAV 保存下来，再做识别。

---

## 7. 音频保存策略

## 7.1 保存粒度

当前阶段推荐 **一段采集会话对应一个完整 WAV 文件**。

例如：

- 用户点击开始采集
- 播放一段音乐
- 用户点击停止采集
- Agent 输出一个完整 WAV 文件

这是最简单、最稳妥的方式。

---

### 7.2 不建议当前阶段只保存小 chunk

chunk 适合实时识别，但你当前目标是复用和调试。若直接保存很多小分片，会带来：

- 管理更复杂
- 回放不方便
- 后续再合并增加步骤

因此建议当前阶段：

- **内存中按帧缓存**
- 停止时一次性写出完整 WAV

后续如果要做实时识别，再增加 chunk 机制。

---

### 7.3 WAV 文件参数建议

推荐参数如下：

- `format`: WAV
- `encoding`: PCM 16-bit
- `sample_rate`: 使用采集设备原始采样率（44100 或 48000）
- `channels`: 2
- `channel_layout`: stereo

说明：

- 采集阶段不急着转 mono。
- 采集阶段不急着重采样。
- 这些动作放到识别前处理阶段更合理。

即：

> 先保存最接近原始采集结果的 WAV，再在识别时做标准化处理。

---

## 8. 目录结构设计

推荐目录结构如下：

```text
project_root/
├─ backend/
│  ├─ app.py
│  ├─ services/
│  ├─ uploads/
│  └─ sessions/
├─ agent/
│  ├─ agent.py
│  ├─ config.yaml
│  └─ recordings/
│     ├─ 20260323/
│     │  ├─ sess_20260323_001.wav
│     │  ├─ sess_20260323_001.json
│     │  ├─ sess_20260323_002.wav
│     │  └─ sess_20260323_002.json
├─ frontend/
└─ docs/
```

说明：

- `agent/recordings/` 用于保存本机采集到的 WAV 文件
- 同名 `.json` 文件保存元数据
- 按日期分目录，便于管理

---

## 9. 文件命名规则

推荐文件命名：

```text
sess_YYYYMMDD_NNN.wav
```

例如：

```text
sess_20260323_001.wav
sess_20260323_002.wav
```

如果希望更稳妥，可以加入时间戳：

```text
sess_20260323_143025.wav
```

推荐同时生成配套元数据文件：

```text
sess_20260323_143025.json
```

---

## 10. 元数据文件设计

每个 WAV 对应一个 JSON 元数据文件。

示例：

```json
{
  "session_id": "sess_20260323_143025",
  "source": "wasapi_loopback",
  "file_name": "sess_20260323_143025.wav",
  "file_path": "agent/recordings/20260323/sess_20260323_143025.wav",
  "sample_rate": 48000,
  "channels": 2,
  "sample_width_bytes": 2,
  "encoding": "pcm16",
  "device_name": "Speakers (Realtek Audio)",
  "start_time": "2026-03-23T14:30:25",
  "end_time": "2026-03-23T14:31:02",
  "duration_sec": 37.2,
  "status": "recorded"
}
```

作用：

- 便于后续读取文件参数
- 便于 Flask 建立会话记录
- 便于回溯来源和采集设备

---

## 11. Flask 接口设计

当前阶段建议 Flask 提供以下接口。

### 11.1 创建采集会话

`POST /api/capture/start`

请求：

```json
{
  "source": "system_loopback"
}
```

响应：

```json
{
  "session_id": "sess_20260323_143025",
  "status": "ready"
}
```

说明：

- 网页点击“开始采集”后先调用这个接口。
- Flask 创建 session。
- Agent 可以轮询获取当前待采集会话，或通过本地配置读取目标 session。

---

### 11.2 获取当前待采集会话

`GET /api/capture/active`

响应：

```json
{
  "session_id": "sess_20260323_143025",
  "status": "recording_requested"
}
```

说明：

- Agent 轮询这个接口。
- 若存在待开始会话，则启动采集。

---

### 11.3 上报已保存音频文件

`PUT /api/capture/register-file`

请求：

```json
{
  "session_id": "sess_20260323_143025",
  "file_name": "sess_20260323_143025.wav",
  "file_path": "C:/project/agent/recordings/20260323/sess_20260323_143025.wav",
  "sample_rate": 48000,
  "channels": 2,
  "duration_sec": 37.2,
  "meta": {
    "encoding": "pcm16",
    "device_name": "Speakers (Realtek Audio)"
  }
}
```

响应：

```json
{
  "ok": true,
  "status": "recorded"
}
```

说明：

- Agent 完成采集并写出 WAV 后，调用该接口。
- Flask 不一定要立即接收整个文件本体，可以先只记录元信息。
- 若后端与 Agent 不在同一台机器上，可后续增加文件上传接口。

---

### 11.4 上传 WAV 文件（可选）

`POST /api/capture/upload-file`

说明：

- 当你希望把 WAV 从 Windows 主机同步到 Ubuntu 后端时使用。
- 当前阶段可选，不一定一开始就做。

上传方式建议：

- `multipart/form-data`
- 字段：`session_id`, `audio_file`

---

### 11.5 结束采集会话

`PUT /api/capture/stop`

请求：

```json
{
  "session_id": "sess_20260323_143025"
}
```

响应：

```json
{
  "ok": true,
  "status": "stopped"
}
```

---

### 11.6 发起识别任务

`POST /api/transcription/start`

请求：

```json
{
  "session_id": "sess_20260323_143025"
}
```

说明：

- Flask 根据 session 找到对应 WAV 文件。
- 后续再读取 WAV，进入预处理与识别流程。

这一步与采集解耦。

---

## 12. Agent 运行逻辑设计

推荐 Agent 主循环逻辑如下：

```text
启动 Agent
   -> 初始化音频设备
   -> 循环轮询 Flask active session
   -> 如果发现待采集 session
      -> 开始录制系统音频
      -> 持续缓存 PCM 帧
      -> 直到收到 stop 指令
      -> 写出 WAV 文件
      -> 生成 metadata JSON
      -> 调用 register-file
   -> 回到等待状态
```

---

## 13. Agent 模块划分

建议把 `agent.py` 拆成以下模块概念。

### 13.1 `audio_capture`

职责：

- 枚举 WASAPI loopback 设备
- 打开输入流
- 读取 PCM 帧

### 13.2 `session_manager`

职责：

- 管理当前是否正在录制
- 保存 session_id
- 处理 start / stop 状态

### 13.3 `wav_writer`

职责：

- 将缓存中的 PCM 帧写成 WAV 文件
- 生成文件名
- 返回文件路径

### 13.4 `api_client`

职责：

- 调用 Flask 接口
- 轮询 active session
- 上报 register-file

### 13.5 `metadata_writer`

职责：

- 生成 `.json` 元数据文件

当前阶段可以先写在一个文件里，后面再拆模块。

---

## 14. Python Agent 骨架设计

下面给出的是结构骨架，不是最终可直接运行的完整版本，但足够作为实现起点。

```python
import os
import time
import json
import wave
import requests
from datetime import datetime

import pyaudiowpatch as pyaudio

BACKEND_BASE = "http://127.0.0.1:5000"
RECORDINGS_DIR = "./recordings"
POLL_INTERVAL = 2
CHUNK = 1024
FORMAT = pyaudio.paInt16


class LoopbackRecorder:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.sample_rate = None
        self.channels = None
        self.device_name = None

    def open_default_loopback(self):
        default_speakers = self.p.get_default_wasapi_loopback()
        self.sample_rate = int(default_speakers["defaultSampleRate"])
        self.channels = int(default_speakers["maxInputChannels"])
        self.device_name = default_speakers["name"]

        self.stream = self.p.open(
            format=FORMAT,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=default_speakers["index"],
            frames_per_buffer=CHUNK,
        )

    def start(self):
        self.frames = []
        if self.stream is None:
            self.open_default_loopback()

    def read_once(self):
        data = self.stream.read(CHUNK, exception_on_overflow=False)
        self.frames.append(data)

    def stop(self):
        pass

    def close(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def build_session_paths(session_id):
    date_part = datetime.now().strftime("%Y%m%d")
    dir_path = os.path.join(RECORDINGS_DIR, date_part)
    ensure_dir(dir_path)
    wav_path = os.path.join(dir_path, f"{session_id}.wav")
    meta_path = os.path.join(dir_path, f"{session_id}.json")
    return wav_path, meta_path


def write_wav(wav_path, frames, channels, sample_rate):
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))


def write_metadata(meta_path, payload):
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def get_active_session():
    try:
        resp = requests.get(f"{BACKEND_BASE}/api/capture/active", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        return None
    return None


def register_file(payload):
    try:
        requests.post(
            f"{BACKEND_BASE}/api/capture/register-file",
            json=payload,
            timeout=10,
        )
    except Exception:
        pass


def should_stop(session_id):
    try:
        resp = requests.get(f"{BACKEND_BASE}/api/capture/active", timeout=5)
        if resp.status_code != 200:
            return True
        data = resp.json()
        return data.get("session_id") != session_id
    except Exception:
        return False


def main():
    recorder = LoopbackRecorder()

    try:
        while True:
            session = get_active_session()
            if not session or session.get("status") != "recording_requested":
                time.sleep(POLL_INTERVAL)
                continue

            session_id = session["session_id"]
            start_time = datetime.now()
            recorder.start()

            while True:
                recorder.read_once()
                if should_stop(session_id):
                    break

            end_time = datetime.now()
            wav_path, meta_path = build_session_paths(session_id)
            write_wav(wav_path, recorder.frames, recorder.channels, recorder.sample_rate)

            duration_sec = len(recorder.frames) * CHUNK / recorder.sample_rate
            meta = {
                "session_id": session_id,
                "source": "wasapi_loopback",
                "file_name": os.path.basename(wav_path),
                "file_path": os.path.abspath(wav_path),
                "sample_rate": recorder.sample_rate,
                "channels": recorder.channels,
                "sample_width_bytes": 2,
                "encoding": "pcm16",
                "device_name": recorder.device_name,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_sec": duration_sec,
                "status": "recorded",
            }
            write_metadata(meta_path, meta)
            register_file(meta)

    finally:
        recorder.close()


if __name__ == "__main__":
    main()
```

---

## 15. 推荐的状态机设计

建议后端为每个会话维护状态：

- `ready`
- `recording_requested`
- `recording`
- `recorded`
- `transcribing`
- `done`
- `failed`

作用：

- 网页可以明确展示当前阶段。
- Agent 可以根据状态决定是否开始录制。
- Flask 可以根据状态决定是否允许发起识别。

---

## 16. 识别模块如何接入

当 WAV 已经保存后，识别流程建议单独设计成：

```text
读取 WAV
 -> 重采样
 -> 转 mono
 -> 音量标准化
 -> pYIN 基频提取
 -> 和弦识别
 -> 保存结果
```

这里的重点是：

- 识别模块不关心音频来自哪里。
- 它只关心输入是一个标准 WAV 文件。

这样以后不论音频来源是：

- WASAPI loopback
- 用户上传文件
- 第三方来源

都可以复用同一套识别入口。

---

## 17. 部署建议

你的环境是：

- Windows 主机
- Ubuntu 服务器

因此当前阶段推荐两种部署方式。

### 17.1 本机联调模式

- Flask 暂时跑在 Windows 本机
- Agent 也跑在 Windows 本机
- 前端本地访问 Flask

优点：

- 最简单
- 最容易调试

---

### 17.2 实际项目模式

- Agent 跑在 Windows 主机
- Flask 跑在 Ubuntu 服务器
- Agent 通过 HTTP 调 Ubuntu 的接口
- WAV 文件可选择：
  - 仅保留在 Windows 本地，后续按路径同步
  - 或直接上传到 Ubuntu

建议当前阶段先做：

> 本机联调模式

等链路稳定后，再迁移到 Windows + Ubuntu 分离部署。

---

## 18. 当前阶段的最小可行实现顺序

建议按这个顺序落地。

### 第一步：验证 loopback 采集

目标：

- 在 Windows 上抓到系统音频
- 成功写出一个 WAV 文件
- 能用播放器正常播放

验收标准：

- 录制 5~10 秒系统播放音频
- 生成 WAV
- 回放无明显异常

---

### 第二步：加入 Flask 会话管理

目标：

- 网页点击“开始采集”后，Flask 创建 session
- Agent 能轮询到 session
- 网页点击“停止采集”后，Agent 能结束并保存 WAV

---

### 第三步：加入文件注册

目标：

- Agent 录制结束后，把元数据提交给 Flask
- Flask 能查询到采集历史

---

### 第四步：将识别模块改为读取 WAV

目标：

- Flask 能从 session 找到 WAV
- 识别模块从 WAV 文件启动
- 输出旋律与和弦结果

---

## 19. 后续扩展方向

当前阶段稳定后，可以按以下方向扩展：

1. 把 Agent 从 Python 脚本打包成 exe
2. 增加托盘程序
3. 增加自动启动能力
4. 增加 WAV 上传到服务器
5. 增加 chunk + 实时识别
6. 增加 FLAC 归档
7. 增加历史会话管理页面

---

## 20. 本阶段最终结论

本阶段推荐方案如下：

- **采集方式**：Windows 本地 Python Agent
- **底层能力**：WASAPI loopback
- **保存格式**：WAV（PCM 16-bit）
- **当前链路**：采集 -> 保存 -> 注册 -> 后续识别
- **系统定位**：网页负责控制，Agent 负责采集，Flask 负责管理和识别

一句话概括：

> 当前阶段先把 Windows 系统音频稳定采集为 WAV 文件，并与 Flask 会话系统打通；识别放在采集完成之后再触发。

