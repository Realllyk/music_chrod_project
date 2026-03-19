# 🎵 音乐扒谱应用 - Music Transcription App

用 AI 自动提取和显示音乐旋律。

## ✨ 功能

- 🎼 **单旋律提取** - 自动识别主旋律
- 🎹 **多声部分离** - 识别和分离不同声部
- 🔌 **可切换音乐源** - 支持 Spotify、本地文件等
- 📊 **可视化** - 波形、频谱、五线谱显示
- 💾 **MIDI 输出** - 导出为标准 MIDI 格式

## 🏗️ 项目结构

```
music-transcription-app/
├── backend/
│   ├── app.py                 # Flask 主应用
│   ├── requirements.txt       # Python 依赖
│   │
│   ├── sources/               # 📌 可切换的音乐源组件
│   │   ├── __init__.py       # SourceFactory 管理器
│   │   ├── base.py           # 基类（抽象接口）
│   │   ├── spotify.py        # Spotify 实现
│   │   └── local_file.py     # 本地文件实现
│   │
│   ├── transcriber/           # 扒谱引擎
│   │   ├── __init__.py
│   │   ├── melody.py         # 单旋律提取
│   │   └── polyphonic.py     # 多声部分离
│   │
│   └── utils/
│       ├── audio_processor.py
│       └── midi_generator.py
│
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── main.js
│       ├── visualizer.js
│       └── api.js
│
└── README.md
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd music-transcription-app/backend
pip install -r requirements.txt
```

### 2. 配置音乐源

#### 方案 A：使用 Spotify（推荐）

1. 前往 [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. 创建应用，获取 `Client ID` 和 `Client Secret`
3. 在 Flask 应用中配置：

```python
from sources import SourceFactory

# 切换到 Spotify 源
SourceFactory.set_current('spotify', {
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret'
})
```

#### 方案 B：使用本地文件

```python
from sources import SourceFactory

# 切换到本地文件源
SourceFactory.set_current('local_file', {
    'music_dir': '~/Music',
    'recursive': True
})
```

### 3. 运行应用

```bash
python app.py
```

访问 `http://localhost:5000`

## 🔌 可切换音乐源架构

### 添加新的音乐源

1. 创建新文件 `sources/youtube.py`
2. 继承 `AudioSource` 基类
3. 实现所有抽象方法

```python
from sources.base import AudioSource

class YouTubeSource(AudioSource):
    def authenticate(self):
        # 实现认证逻辑
        pass
    
    def search(self, query, limit=10):
        # 实现搜索逻辑
        pass
    
    # ... 其他方法
```

4. 在 `sources/__init__.py` 中注册：

```python
SourceFactory.register_source('youtube', YouTubeSource)
```

### 切换音乐源

```python
from sources import SourceFactory

# 列出所有可用源
print(SourceFactory.get_available_sources())
# 输出: ['spotify', 'local_file', 'youtube']

# 切换源
SourceFactory.set_current('youtube', config={'api_key': '...'})

# 使用当前源
source = SourceFactory.get_current()
results = source.search('Imagine - John Lennon')
```

## 🎯 下一步

- [ ] 实现 Flask 后端 API
- [ ] 创建前端 HTML/JS 界面
- [ ] 实现单旋律提取（librosa）
- [ ] 实现多声部分离
- [ ] 可视化显示（波形、频谱、五线谱）
- [ ] MIDI 生成和导出
- [ ] YouTube 音乐源支持
- [ ] 服务器部署

## 📝 技术栈

- **后端：** Python + Flask
- **音乐处理：** librosa（信号处理）、music21（乐理）
- **前端：** HTML + CSS + JavaScript
- **音乐源：** Spotify API、本地文件、YouTube（未来）

## ⚠️ 注意事项

- Spotify API 只提供 30 秒预览（需要 Premium 账户获取完整音频）
- 某些音乐可能没有预览链接
- 扒谱精度取决于音乐复杂度和清晰度

---

**Status:** 🚧 开发中...
