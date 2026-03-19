# 🚀 后端设置和启动指南

## 📍 项目位置
```
~/music_learning_project/
```

## 📦 安装依赖

### 方案 1: 使用虚拟环境（推荐）

```bash
cd ~/music_learning_project/backend

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 方案 2: 使用 conda

```bash
cd ~/music_learning_project/backend

# 创建 conda 环境
conda create -n music-transcription python=3.9

# 激活环境
conda activate music-transcription

# 安装依赖
pip install -r requirements.txt
```

## 🔧 配置

### 1. Spotify API（可选）

如果要使用 Spotify 作为音乐源：

1. 前往 [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. 创建应用，获取：
   - `Client ID`
   - `Client Secret`
3. 保存到某个地方（后续会用到）

### 2. 创建文件夹

```bash
cd ~/project
mkdir -p uploads outputs logs
```

## 🎬 启动服务

### 基本启动

```bash
cd ~/music_learning_project/backend

# 激活虚拟环境（如果使用）
source venv/bin/activate

# 启动 Flask 应用
python app.py
```

**输出示例：**
```
============================================================
🎵 音乐扒谱应用 - 后端服务启动
============================================================
上传文件夹: ~/music_learning_project/uploads
输出文件夹: ~/music_learning_project/outputs
访问 http://localhost:5000 查看 API 文档
============================================================
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

### 访问 API

打开浏览器，访问：
```
http://localhost:5000
```

你会看到完整的 API 文档。

## 🧪 测试 API

### 1. 获取状态

```bash
curl http://localhost:5000/api/status
```

### 2. 查看可用音乐源

```bash
curl http://localhost:5000/api/sources
```

### 3. 切换到本地文件源

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

### 4. 搜索音乐

```bash
curl "http://localhost:5000/api/search?q=love&limit=5"
```

### 5. 上传音乐文件

```bash
curl -X POST http://localhost:5000/api/music/upload \
  -F "file=@/path/to/music.mp3"
```

### 6. 单旋律提取

```bash
curl -X POST http://localhost:5000/api/transcribe/melody \
  -H "Content-Type: application/json" \
  -d '{
    "audio_file": "upload_20260316_150000_mymusic.mp3"
  }'
```

### 7. 多声部分离

```bash
curl -X POST http://localhost:5000/api/transcribe/polyphonic \
  -H "Content-Type: application/json" \
  -d '{
    "audio_file": "upload_20260316_150000_mymusic.mp3"
  }'
```

### 8. 下载 MIDI 文件

```bash
curl http://localhost:5000/api/download/midi/melody_mymusic.mid \
  -o output.mid
```

## 📊 API 端点列表

### 音乐源管理
| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/sources` | 获取所有可用源 |
| POST | `/api/sources/switch` | 切换音乐源 |

### 搜索
| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/search?q=xxx&limit=10` | 搜索音乐 |

### 文件管理
| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/music/upload` | 上传音乐文件 |
| GET | `/api/music/download/<source>/<music_id>` | 下载音乐 |

### 扒谱
| 方法 | 路由 | 说明 |
|------|------|------|
| POST | `/api/transcribe/melody` | 单旋律提取 |
| POST | `/api/transcribe/polyphonic` | 多声部分离 |

### 输出
| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/download/<file_type>/<filename>` | 下载输出文件 |

### 状态
| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/status` | 获取应用状态 |
| GET | `/api/health` | 健康检查 |

## 🐛 常见问题

### Q: librosa 安装失败

**A:** 需要先安装 ffmpeg
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 从 https://ffmpeg.org/download.html 下载
```

### Q: music21 找不到 MIDI 生成器

**A:** 首次使用时，music21 会要求配置。运行：
```python
from music21 import environment
environment.set('musicxmlPath', '/path/to/musescore')  # 或其他软件
```

### Q: 上传大文件时超时

**A:** 修改 `app.py` 中的 `MAX_CONTENT_LENGTH`：
```python
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 改为 1GB
```

### Q: 基频提取效果不好

**A:** 调整 `melody.py` 中的参数：
```python
f0, voiced_flag, voiced_probs = librosa.pyin(
    self.audio,
    fmin=60,    # 降低最小频率
    fmax=500,   # 提高最大频率
    sr=self.sr
)
```

## 📝 生产部署

### 使用 Gunicorn

```bash
pip install gunicorn

cd ~/music_learning_project/backend

# 用 Gunicorn 启动（支持多进程）
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /uploads {
        alias ~/music_learning_project/uploads;
    }

    location /outputs {
        alias ~/music_learning_project/outputs;
    }
}
```

### 使用 systemd 服务

创建 `/etc/systemd/system/music-transcription.service`:

```ini
[Unit]
Description=Music Transcription App
After=network.target

[Service]
Type=simple
User=realllyka
WorkingDirectory=/home/realllyka/music_learning_project/backend
Environment="PATH=/home/realllyka/music_learning_project/backend/venv/bin"
ExecStart=/home/realllyka/music_learning_project/backend/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl start music-transcription
sudo systemctl enable music-transcription
```

## 📚 更多信息

- **项目结构:** 查看 `PROJECT_STRUCTURE.md`
- **快速开始:** 查看 `QUICKSTART.md`
- **音乐源:** 查看 `sources/__init__.py`

---

**后端已就绪！** 🎉
