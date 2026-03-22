# Windows 系统音频抓取 + Web 项目识别方案（清洁版）

## 1. 目标

项目目标是实现这条链路：

- 用户在 Windows 电脑上播放音频
- 本机采集当前系统播放音频
- 将音频分片上传到 Flask 后端
- 后端执行预处理、单旋律提取、和弦识别
- 前端网页展示识别状态与结果

该方案不依赖商业音乐平台提供整首音频下载接口。

---

## 2. 推荐架构

采用三段式结构：

1. **网页前端**
   - 控制开始/停止识别
   - 展示会话状态和结果

2. **Windows 本地采集代理（Agent）**
   - 使用 WASAPI loopback 抓取系统音频
   - 切成固定时长分片
   - 上传到 Flask 后端

3. **Flask 后端**
   - 创建识别会话
   - 接收音频分片
   - 统一转码与预处理
   - 调用 pYIN 与和弦识别算法
   - 返回中间结果和最终结果

---

## 3. 为什么不建议把“抓系统音频”放在浏览器主流程里

浏览器可以通过屏幕共享配合音频采集实现录制，但它不适合作为主方案，原因有三点：

1. 依赖用户手动授权
2. 浏览器兼容性和系统音频支持不稳定
3. 交互流程重，不利于长期维护

因此：

- **主方案**：本地 Agent 负责采集
- **备选方案**：浏览器采集仅用于演示或兜底

---

## 4. Windows 本地采集方案

### 4.1 核心能力

Windows 推荐使用 **WASAPI loopback** 抓取系统正在播放到默认输出设备的音频。

### 4.2 第一版实现建议

优先采用 Python 实现本地 Agent，原因：

- 你的后端已是 Python / Flask
- 实现成本低
- 方便快速联调

推荐库：

- `pyaudiowpatch`
- `requests`
- `fastapi` 或 `flask`（用于本地 Agent 暴露本机 HTTP 接口）

### 4.3 后续增强方案

如果后面追求更强的稳定性和 Windows 集成体验，可以改成：

- C# + NAudio

---

## 5. 整体数据流

### 5.1 开始识别

1. 用户打开网页前端
2. 前端请求后端创建会话：`POST /api/sessions`
3. 后端返回：
   - `session_id`
   - `upload_token`
   - `backend_upload_url`
4. 前端再请求本机 Agent：`POST http://127.0.0.1:18765/capture/start`
5. 前端把后端返回的信息传给本机 Agent

### 5.2 采集上传

1. Agent 抓取系统音频
2. 按 5 秒切片
3. 每个分片上传到 Flask：`POST /api/audio/chunk`
4. Flask 处理后更新会话状态
5. 前端轮询状态和结果

### 5.3 停止识别

1. 前端调用本机 Agent：`POST /capture/stop`
2. Agent 停止采集并上传最后一片
3. Flask 结束聚合并输出最终结果

---

## 6. 音频格式建议

### 6.1 采集端

采集端尽量使用系统默认输出设备的原生参数，不要强行指定与设备不匹配的采样率。

### 6.2 后端统一标准化

上传后统一转成：

- WAV
- PCM 16-bit
- Mono
- 22050 Hz 或 44100 Hz

如果你的 pYIN 和和弦识别模块对采样率有固定要求，就按模型要求统一。

### 6.3 分片长度

第一版推荐：

- **5 秒一片**

这样延迟和实现复杂度比较平衡。

---

## 7. Flask 后端接口设计

### 7.1 创建识别会话

`POST /api/sessions`

请求示例：

```json
{
  "mode": "system_audio",
  "source": "windows_loopback"
}
```

响应示例：

```json
{
  "session_id": "sess_xxx",
  "upload_token": "token_xxx",
  "backend_upload_url": "http://your-backend-host:5000/api/audio/chunk",
  "status_url": "http://your-backend-host:5000/api/sessions/sess_xxx"
}
```

### 7.2 上传音频分片

`POST /api/audio/chunk`

请求头：

```text
Authorization: Bearer <upload_token>
```

表单字段：

- `session_id`
- `chunk_index`
- `is_last`
- `audio_file`

### 7.3 查询会话状态

`GET /api/sessions/<session_id>`

响应示例：

```json
{
  "session_id": "sess_xxx",
  "status": "running",
  "received_chunks": 4,
  "processed_chunks": 3,
  "partial_result": {
    "melody": [],
    "chords": []
  }
}
```

### 7.4 获取最终结果

`GET /api/results/<session_id>`

---

## 8. 本机 Agent 接口设计

本机 Agent 仅监听：

- `127.0.0.1:18765`

### 8.1 健康检查

`GET /health`

响应：

```json
{
  "ok": true,
  "capturing": false,
  "version": "0.1.0"
}
```

### 8.2 开始采集

`POST /capture/start`

请求示例：

```json
{
  "session_id": "sess_xxx",
  "upload_token": "token_xxx",
  "backend_upload_url": "http://your-backend-host:5000/api/audio/chunk",
  "chunk_seconds": 5
}
```

### 8.3 停止采集

`POST /capture/stop`

### 8.4 查询采集状态

`GET /capture/status`

---

## 9. Agent 模块划分建议

```text
agent/
├─ main.py
├─ capture.py
├─ chunker.py
├─ uploader.py
├─ state.py
├─ config.py
└─ temp/
```

职责划分：

- `main.py`：启动本机 HTTP 服务
- `capture.py`：系统音频抓取
- `chunker.py`：按固定时长切分片
- `uploader.py`：将分片上传后端
- `state.py`：记录采集状态、错误、chunk 序号

---

## 10. Python 采集骨架

下面给的是实现骨架，便于你开始写 Agent。

```python
import io
import wave
import threading
import requests
import pyaudiowpatch as pyaudio

class LoopbackCaptureService:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.running = False
        self.worker_thread = None
        self.session_id = None
        self.upload_token = None
        self.backend_upload_url = None
        self.chunk_seconds = 5
        self.chunk_index = 0

    def start(self, session_id, upload_token, backend_upload_url, chunk_seconds=5):
        if self.running:
            return

        self.session_id = session_id
        self.upload_token = upload_token
        self.backend_upload_url = backend_upload_url
        self.chunk_seconds = chunk_seconds
        self.chunk_index = 0
        self.running = True

        device_info = self.audio.get_default_wasapi_loopback()
        rate = int(device_info["defaultSampleRate"])
        channels = int(device_info["maxInputChannels"])
        sample_format = pyaudio.paInt16
        frames_per_buffer = 1024

        self.stream = self.audio.open(
            format=sample_format,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=device_info["index"],
            frames_per_buffer=frames_per_buffer,
        )

        self.worker_thread = threading.Thread(
            target=self._capture_loop,
            args=(rate, channels, frames_per_buffer),
            daemon=True,
        )
        self.worker_thread.start()

    def stop(self):
        self.running = False
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def _capture_loop(self, rate, channels, frames_per_buffer):
        bytes_per_sample = 2
        target_bytes = rate * channels * bytes_per_sample * self.chunk_seconds
        buffer = bytearray()

        while self.running:
            data = self.stream.read(frames_per_buffer, exception_on_overflow=False)
            buffer.extend(data)

            while len(buffer) >= target_bytes:
                chunk = bytes(buffer[:target_bytes])
                buffer = buffer[target_bytes:]
                wav_bytes = self._to_wav_bytes(chunk, rate, channels)
                self._upload_chunk(wav_bytes, is_last=False)
                self.chunk_index += 1

        if buffer:
            wav_bytes = self._to_wav_bytes(bytes(buffer), rate, channels)
            self._upload_chunk(wav_bytes, is_last=True)

    def _to_wav_bytes(self, raw_pcm, rate, channels):
        bio = io.BytesIO()
        with wave.open(bio, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(raw_pcm)
        bio.seek(0)
        return bio.read()

    def _upload_chunk(self, wav_bytes, is_last=False):
        headers = {
            "Authorization": f"Bearer {self.upload_token}"
        }
        files = {
            "audio_file": (f"chunk_{self.chunk_index}.wav", wav_bytes, "audio/wav")
        }
        data = {
            "session_id": self.session_id,
            "chunk_index": self.chunk_index,
            "is_last": str(is_last).lower(),
        }
        requests.post(self.backend_upload_url, headers=headers, data=data, files=files, timeout=30)
```

---

## 11. Flask 后端处理流程建议

后端收到 chunk 后执行：

1. 校验 `upload_token`
2. 保存原始 chunk
3. 统一转码
4. 执行预处理
5. 调用 pYIN 提取旋律
6. 调用和弦识别模块
7. 将结果写入会话状态

建议把识别过程设计成异步任务，避免上传接口阻塞太久。

---

## 12. 前端页面建议

第一版前端只需要极简功能：

1. 检查本机 Agent 是否在线
2. 点击“开始识别”
3. 点击“停止识别”
4. 轮询查看状态
5. 展示旋律和和弦结果

### 12.1 前端流程建议

- 页面加载后先请求：`http://127.0.0.1:18765/health`
- Agent 在线时允许开始识别
- 点击开始后：
  1. 请求 Flask 创建会话
  2. 请求 Agent 启动采集
  3. 启动定时轮询会话状态
- 点击停止后：
  1. 请求 Agent 停止采集
  2. 继续轮询直到后端状态变成 `finished`

---

## 13. 部署建议

结合你当前环境：

- Windows：运行浏览器前端 + 本机 Agent
- Ubuntu：运行 Flask 后端

注意两点：

1. Windows 必须能访问 Ubuntu 后端的 IP 和端口
2. Flask 不能只绑定 `127.0.0.1`，应绑定到局域网可访问地址，例如：

```python
app.run(host="0.0.0.0", port=5000)
```

---

## 14. 第一阶段落地顺序

建议按这个顺序实现：

### 第一步
先单独验证 Windows 上能否抓到系统音频，并导出一个 5 秒 WAV 文件。

### 第二步
把这个 5 秒 WAV 手工上传到 Flask，验证后端预处理和算法链路。

### 第三步
把 Agent 的自动上传接上，形成完整数据流。

### 第四步
补上网页前端的开始/停止与状态展示。

---

## 15. 最终结论

对于你的 Web 项目，最稳的实现方案是：

- **网页前端负责控制和展示**
- **Windows 本地 Agent 负责抓系统音频**
- **Flask 后端负责识别**

不要把主流程建立在浏览器直接抓系统音频上，也不要把项目依赖在商业音乐平台的整曲下载能力上。
