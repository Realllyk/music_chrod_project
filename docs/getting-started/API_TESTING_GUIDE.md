# 🧪 后端 API 测试指南

## 项目位置
```
~/project/music_project/
```

---

## 🚀 启动后端

### 第 1 步：进入项目目录
```bash
cd ~/project/music_project/backend
```

### 第 2 步：安装依赖（首次）
```bash
pip install -r requirements.txt
```

### 第 3 步：启动 Flask 应用
```bash
python app.py
```

**预期输出：**
```
============================================================
🎵 音乐扒谱应用 - 后端服务启动
============================================================
上传文件夹: .../uploads
输出文件夹: .../outputs
访问 http://localhost:5000 查看 API 文档
============================================================
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

---

## 🌐 访问 API 文档

### 打开浏览器
访问：**`http://localhost:5000`**

你会看到完整的 API 文档和所有端点列表

---

## 📋 完整 API 列表

### 1️⃣ 音乐源管理

#### 获取所有可用源
```
GET http://localhost:5000/api/sources
```

**响应示例：**
```json
{
  "status": "success",
  "available_sources": ["spotify", "local_file"],
  "current_source": null,
  "total": 2
}
```

**测试命令：**
```bash
curl http://localhost:5000/api/sources
```

---

#### 切换音乐源
```
POST http://localhost:5000/api/sources/switch
```

**请求体（本地文件源）：**
```json
{
  "source_name": "local_file",
  "config": {
    "music_dir": "~/Music",
    "recursive": true
  }
}
```

**请求体（Spotify 源）：**
```json
{
  "source_name": "spotify",
  "config": {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET"
  }
}
```

**测试命令（本地文件）：**
```bash
curl -X POST http://localhost:5000/api/sources/switch \
  -H "Content-Type: application/json" \
  -d '{
    "source_name": "local_file",
    "config": {
      "music_dir": "~/Music",
      "recursive": true
    }
  }'
```

**响应示例：**
```json
{
  "status": "success",
  "message": "已切换到 local_file",
  "source": "local_file"
}
```

---

### 2️⃣ 搜索音乐

#### 搜索
```
GET http://localhost:5000/api/search?q=QUERY&limit=LIMIT
```

**参数：**
- `q` - 搜索关键词（必需）
- `limit` - 返回结果数（可选，默认 10）

**测试命令：**
```bash
# 搜索本地"love"相关的文件
curl "http://localhost:5000/api/search?q=love&limit=5"
```

**响应示例：**
```json
{
  "status": "success",
  "query": "love",
  "results": [
    {
      "id": "/home/user/Music/love_song.mp3",
      "title": "love_song",
      "artist": "Local",
      "duration": 0,
      "format": ".mp3",
      "source": "local_file",
      "path": "/home/user/Music/love_song.mp3"
    }
  ],
  "total": 1
}
```

---

### 3️⃣ 文件上传

#### 上传音乐文件
```
POST http://localhost:5000/api/music/upload
```

**参数：**
- `file` - 音乐文件（multipart form data）

**支持格式：** `.mp3, .wav, .flac, .ogg, .m4a, .wma`

**测试命令：**
```bash
curl -X POST http://localhost:5000/api/music/upload \
  -F "file=@~/Music/song.mp3"
```

**响应示例：**
```json
{
  "status": "success",
  "filename": "upload_20260321_123456_song.mp3",
  "filepath": ".../uploads/upload_20260321_123456_song.mp3",
  "size_bytes": 5242880
}
```

**⚠️ 保存 filename，后续使用需要用到！**

---

### 4️⃣ 扒谱 - 单旋律提取

#### 单旋律提取（PYIN 算法）
```
POST http://localhost:5000/api/transcribe/melody
```

**请求体：**
```json
{
  "audio_file": "upload_20260321_123456_song.mp3"
}
```

**测试命令：**
```bash
curl -X POST http://localhost:5000/api/transcribe/melody \
  -H "Content-Type: application/json" \
  -d '{
    "audio_file": "upload_20260321_123456_song.mp3"
  }'
```

**响应示例：**
```json
{
  "status": "success",
  "mode": "melody",
  "audio_file": "upload_20260321_123456_song.mp3",
  "result": {
    "notes": [
      {
        "start_frame": 0,
        "end_frame": 512,
        "midi": 60,
        "freq": 261.63,
        "duration": 0.5,
        "confidence": 0.95
      }
    ],
    "total_notes": 42,
    "duration_sec": 10.5
  },
  "midi_file": "melody_song.mid",
  "midi_path": ".../outputs/melody_song.mid"
}
```

---

### 5️⃣ 扒谱 - 多声部分离

#### 多声部分离（HPSS 算法）
```
POST http://localhost:5000/api/transcribe/polyphonic
```

**请求体：**
```json
{
  "audio_file": "upload_20260321_123456_song.mp3"
}
```

**测试命令：**
```bash
curl -X POST http://localhost:5000/api/transcribe/polyphonic \
  -H "Content-Type: application/json" \
  -d '{
    "audio_file": "upload_20260321_123456_song.mp3"
  }'
```

**响应示例：**
```json
{
  "status": "success",
  "mode": "polyphonic",
  "audio_file": "upload_20260321_123456_song.mp3",
  "result": {
    "voices": [
      [
        {
          "start_frame": 0,
          "end_frame": 512,
          "midi": 60,
          "freq": 261.63,
          "duration": 0.5
        }
      ],
      [
        {
          "start_frame": 100,
          "end_frame": 612,
          "midi": 72,
          "freq": 392.00,
          "duration": 0.5
        }
      ]
    ],
    "total_voices": 2,
    "duration_sec": 10.5
  },
  "midi_file": "polyphonic_song.mid",
  "midi_path": ".../outputs/polyphonic_song.mid"
}
```

---

### 6️⃣ 下载文件

#### 下载 MIDI 文件
```
GET http://localhost:5000/api/download/midi/FILENAME
```

**参数：**
- `FILENAME` - MIDI 文件名（从扒谱响应中获取）

**测试命令：**
```bash
curl http://localhost:5000/api/download/midi/melody_song.mid \
  -o ~/Downloads/melody_song.mid
```

---

### 7️⃣ 状态检查

#### 应用状态
```
GET http://localhost:5000/api/status
```

**响应示例：**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-21T12:37:00.123456",
  "upload_folder": ".../uploads",
  "output_folder": ".../outputs",
  "current_source": null
}
```

**测试命令：**
```bash
curl http://localhost:5000/api/status
```

---

#### 健康检查
```
GET http://localhost:5000/api/health
```

**响应：**
```json
{
  "status": "ok"
}
```

**测试命令：**
```bash
curl http://localhost:5000/api/health
```

---

## 📋 完整测试工作流

### 场景 1：本地音乐 → 单旋律提取 → MIDI

```bash
# 1. 确认后端运行
curl http://localhost:5000/api/health

# 2. 切换到本地文件源
curl -X POST http://localhost:5000/api/sources/switch \
  -H "Content-Type: application/json" \
  -d '{
    "source_name": "local_file",
    "config": {"music_dir": "~/Music", "recursive": true}
  }'

# 3. 上传音乐文件
RESPONSE=$(curl -s -X POST http://localhost:5000/api/music/upload \
  -F "file=@~/Music/test.mp3")
FILENAME=$(echo $RESPONSE | jq -r '.filename')
echo "上传的文件名：$FILENAME"

# 4. 执行单旋律提取
curl -X POST http://localhost:5000/api/transcribe/melody \
  -H "Content-Type: application/json" \
  -d "{\"audio_file\": \"$FILENAME\"}"

# 5. 从响应获取 midi_file，然后下载
# (假设 midi_file 是 "melody_test.mid")
curl http://localhost:5000/api/download/midi/melody_test.mid \
  -o ~/Downloads/melody_test.mid
```

---

## 🛠️ 使用工具测试

### 选项 1：curl（命令行）
```bash
curl http://localhost:5000/api/sources
```

### 选项 2：Postman（图形界面）
1. 下载 Postman
2. 导入 API 文档
3. 点击测试

### 选项 3：Thunder Client（VS Code 插件）
1. 安装插件
2. 创建请求
3. 点击发送

### 选项 4：Python requests（编程）
```python
import requests

# 获取源列表
response = requests.get('http://localhost:5000/api/sources')
print(response.json())

# 切换源
response = requests.post(
    'http://localhost:5000/api/sources/switch',
    json={
        'source_name': 'local_file',
        'config': {'music_dir': '~/Music', 'recursive': True}
    }
)
print(response.json())
```

---

## 📊 API 端点速查表

| 方法 | 路由 | 说明 | 测试命令 |
|------|------|------|---------|
| GET | `/api/sources` | 获取源列表 | `curl http://localhost:5000/api/sources` |
| POST | `/api/sources/switch` | 切换源 | 见上文 |
| GET | `/api/search?q=xxx` | 搜索 | `curl "http://localhost:5000/api/search?q=love"` |
| POST | `/api/music/upload` | 上传 | 见上文 |
| POST | `/api/transcribe/melody` | 单旋律 | 见上文 |
| POST | `/api/transcribe/polyphonic` | 多声部 | 见上文 |
| GET | `/api/download/midi/{file}` | 下载 MIDI | 见上文 |
| GET | `/api/status` | 状态 | `curl http://localhost:5000/api/status` |
| GET | `/api/health` | 健康检查 | `curl http://localhost:5000/api/health` |

---

## ⚠️ 常见错误和解决方案

### 错误 1：连接被拒绝
**错误：** `Connection refused`

**原因：** 后端未启动

**解决：**
```bash
cd ~/project/music_project/backend
python app.py
```

---

### 错误 2：404 Not Found
**错误：** `404 Not Found`

**原因：** API 路由错误

**解决：** 检查 URL 拼写，确保完全正确

---

### 错误 3：文件上传失败
**错误：** `Failed to upload`

**原因：** 文件格式不支持或超过大小限制

**解决：**
- 支持格式：`.mp3, .wav, .flac, .ogg, .m4a, .wma`
- 默认限制：500MB
- 修改 `config.json` 中的 `max_file_size`

---

### 错误 4：音频文件未找到
**错误：** `File not found`

**原因：** `audio_file` 参数错误

**解决：** 确保 `filename` 来自上传响应中的 `filename` 字段

---

### 错误 5：Spotify 认证失败
**错误：** `Authentication failed`

**原因：** Client ID 或 Secret 错误

**解决：**
1. 访问 https://developer.spotify.com/dashboard
2. 创建应用，获取正确的 ID 和 Secret
3. 确保复制时没有多余空格

---

## 🔍 调试技巧

### 1. 查看 Flask 日志
```
运行后端时查看终端输出
每个请求会显示详细日志
```

### 2. 使用 -v 参数查看详细信息
```bash
curl -v http://localhost:5000/api/sources
```

### 3. 保存响应到文件
```bash
curl http://localhost:5000/api/sources > response.json
cat response.json
```

### 4. 检查文件夹权限
```bash
ls -la ~/project/music_project/uploads/
ls -la ~/project/music_project/outputs/
```

---

## 📝 快速参考

### 完整的请求-响应示例

**请求：**
```bash
curl -X POST http://localhost:5000/api/transcribe/melody \
  -H "Content-Type: application/json" \
  -d '{"audio_file": "upload_20260321_120000_test.mp3"}'
```

**响应（成功）：**
```json
{
  "status": "success",
  "mode": "melody",
  "audio_file": "upload_20260321_120000_test.mp3",
  "result": {
    "notes": [...],
    "total_notes": 42,
    "duration_sec": 10.5
  },
  "midi_file": "melody_test.mid",
  "midi_path": ".../outputs/melody_test.mid"
}
```

**响应（错误）：**
```json
{
  "error": "提取失败",
  "message": "文件不存在"
}
```

---

## ✅ 测试清单

完整测试前，确保已完成：

- [ ] 后端正在运行（`python app.py`）
- [ ] 访问 `http://localhost:5000` 可以看到 API 文档
- [ ] `/api/health` 返回 `{"status": "ok"}`
- [ ] `/api/sources` 返回可用源列表
- [ ] 可以成功切换音乐源
- [ ] 可以上传音乐文件
- [ ] 可以执行单旋律提取
- [ ] 可以执行多声部分离
- [ ] 可以下载生成的 MIDI 文件

---

## 🎯 下一步

1. ✅ **测试所有 API** - 使用上面的命令
2. ⬜ **实现前端** - HTML/CSS/JavaScript
3. ⬜ **集成前后端** - 前端调用后端 API
4. ⬜ **部署上线** - 生产环境配置

---

## 📚 更多信息

- 配置说明：`CONFIG_GUIDE.md`
- 模块文档：`backend/MODULE_DOCS.md`
- 使用示例：`USAGE_EXAMPLES.md`
- 项目结构：`PROJECT_STRUCTURE.md`

---

**准备好了吗？开始测试吧！** 🚀
