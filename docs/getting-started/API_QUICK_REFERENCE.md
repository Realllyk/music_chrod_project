# 🚀 API 快速参考

## 项目位置
```
~/project/music_project/
```

---

## 🎯 最常用的 API

### 1. 启动后端
```bash
cd ~/project/music_project/backend
python app.py
```

访问 API 文档：`http://localhost:5000`

---

### 2. 健康检查
```bash
curl http://localhost:5000/api/health
```

**预期响应：** `{"status":"ok"}`

---

### 3. 获取可用音乐源
```bash
curl http://localhost:5000/api/sources
```

---

### 4. 切换到本地文件源
```bash
curl -X POST http://localhost:5000/api/sources/switch \
  -H "Content-Type: application/json" \
  -d '{"source_name":"local_file","config":{"music_dir":"~/Music","recursive":true}}'
```

---

### 5. 搜索本地音乐
```bash
curl "http://localhost:5000/api/search?q=love&limit=5"
```

---

### 6. 上传音乐文件
```bash
curl -X POST http://localhost:5000/api/music/upload \
  -F "file=@~/Music/song.mp3"
```

**获取返回的 `filename` 备用**

---

### 7. 单旋律提取
```bash
curl -X POST http://localhost:5000/api/transcribe/melody \
  -H "Content-Type: application/json" \
  -d '{"audio_file":"FILENAME_FROM_UPLOAD"}'
```

---

### 8. 多声部分离
```bash
curl -X POST http://localhost:5000/api/transcribe/polyphonic \
  -H "Content-Type: application/json" \
  -d '{"audio_file":"FILENAME_FROM_UPLOAD"}'
```

---

### 9. 下载 MIDI
```bash
curl http://localhost:5000/api/download/midi/MIDI_FILENAME \
  -o ~/Downloads/result.mid
```

---

## 📋 所有 API 端点

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/status` | 应用状态 |
| GET | `/api/sources` | 获取音乐源列表 |
| POST | `/api/sources/switch` | 切换音乐源 |
| GET | `/api/search` | 搜索音乐 |
| POST | `/api/music/upload` | 上传文件 |
| POST | `/api/transcribe/melody` | 单旋律提取 |
| POST | `/api/transcribe/polyphonic` | 多声部分离 |
| GET | `/api/download/midi/{file}` | 下载 MIDI |

---

## 🧪 自动测试脚本

```bash
bash ~/project/music_project/test_api.sh
```

---

## 📚 详细文档

- **完整测试指南：** `API_TESTING_GUIDE.md`
- **使用代码示例：** `USAGE_EXAMPLES.md`
- **配置说明：** `CONFIG_GUIDE.md`
- **模块文档：** `backend/MODULE_DOCS.md`

---

## ⚡ 一键完整工作流

### Python 脚本
```python
import requests
import json

BASE_URL = 'http://localhost:5000'

# 1. 健康检查
print("1️⃣  健康检查...")
print(requests.get(f'{BASE_URL}/api/health').json())

# 2. 切换源
print("2️⃣  切换到本地文件源...")
print(requests.post(f'{BASE_URL}/api/sources/switch', json={
    'source_name': 'local_file',
    'config': {'music_dir': '~/Music', 'recursive': True}
}).json())

# 3. 搜索
print("3️⃣  搜索音乐...")
print(requests.get(f'{BASE_URL}/api/search?q=song&limit=3').json())

# 4. 上传
print("4️⃣  上传文件...")
with open('~/Music/test.mp3', 'rb') as f:
    response = requests.post(f'{BASE_URL}/api/music/upload', 
                           files={'file': f}).json()
    filename = response['filename']
    print(f"上传成功: {filename}")

# 5. 单旋律提取
print("5️⃣  执行单旋律提取...")
result = requests.post(f'{BASE_URL}/api/transcribe/melody',
                      json={'audio_file': filename}).json()
if result['status'] == 'success':
    print(f"✅ 提取成功，识别 {result['result']['total_notes']} 个音符")
    print(f"MIDI 文件: {result['midi_file']}")

print("\n✅ 完成！")
```

---

## 🔍 常见参数

### 音乐源配置

**本地文件：**
```json
{
  "source_name": "local_file",
  "config": {
    "music_dir": "~/Music",
    "recursive": true
  }
}
```

**Spotify：**
```json
{
  "source_name": "spotify",
  "config": {
    "client_id": "YOUR_ID",
    "client_secret": "YOUR_SECRET"
  }
}
```

---

### 搜索参数

```
GET /api/search?q=QUERY&limit=LIMIT
```

- `q` - 搜索关键词（必需）
- `limit` - 返回数量，范围 1-50（默认 10）

---

### 扒谱参数

```json
POST /api/transcribe/melody
{
  "audio_file": "FILENAME"
}

POST /api/transcribe/polyphonic
{
  "audio_file": "FILENAME"
}
```

---

## 💾 保存这个文档

建议打印或保存此文件以便快速查阅！

---

**现在就开始测试吧！** 🚀
