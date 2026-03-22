# 🎵 项目架构文档

## 📐 系统设计

### 核心理念：可切换的音乐源架构

```
┌─────────────────────────────────────┐
│        Flask Web 应用 (API)          │
├─────────────────────────────────────┤
│       SourceFactory 管理层           │
│   (负责源的创建、切换、管理)          │
├─────────────────────────────────────┤
│         Audio Source Layer           │
├────────┬────────┬────────┬──────────┤
│Spotify │ Local  │YouTube │  其他    │
│        │ File   │        │（可扩展）│
└────────┴────────┴────────┴──────────┘
         ↓
┌─────────────────────────────────────┐
│   Transcriber (扒谱引擎)             │
├─────────────────────────────────────┤
│  ├─ Melody (单旋律提取)             │
│  └─ Polyphonic (多声部分离)         │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│        Output (输出)                 │
├─────────────────────────────────────┤
│  ├─ MIDI File                       │
│  ├─ Visualization (JSON)            │
│  └─ Metadata                        │
└─────────────────────────────────────┘
```

## 🔌 音乐源组件

### 1. AudioSource 基类

**位置：** `backend/sources/base.py`

**接口：**
```python
class AudioSource(ABC):
    def authenticate() -> bool        # 认证
    def search(query, limit) -> list  # 搜索
    def get_audio_stream(id) -> BytesIO  # 获取流
    def get_audio_file(id, path) -> str  # 下载文件
```

### 2. 内置实现

#### Spotify 源
**文件：** `backend/sources/spotify.py`

**特点：**
- ✅ 支持搜索百万级音乐库
- ⚠️ 只提供 30 秒预览（API 限制）
- 🔑 需要 Client ID + Client Secret
- 📍 可获取歌曲元数据

**使用：**
```python
source = SpotifySource({
    'client_id': '...',
    'client_secret': '...'
})
source.authenticate()
results = source.search('song name', limit=10)
```

#### 本地文件源
**文件：** `backend/sources/local_file.py`

**特点：**
- ✅ 完整音频文件
- ✅ 无需认证
- 📁 支持递归搜索
- 🎵 支持多种格式（MP3、WAV、FLAC、OGG 等）

**使用：**
```python
source = LocalFileSource({
    'music_dir': '~/Music',
    'recursive': True
})
results = source.search('song name', limit=10)
```

### 3. SourceFactory 管理器

**文件：** `backend/sources/__init__.py`

**功能：**
- 创建音乐源实例
- 切换音乐源
- 注册新源
- 获取可用源列表

**API：**
```python
# 创建源
source = SourceFactory.create('spotify', config)

# 切换源
SourceFactory.set_current('local_file', config)

# 获取当前源
current = SourceFactory.get_current()

# 列出可用源
sources = SourceFactory.get_available_sources()

# 注册新源
SourceFactory.register_source('youtube', YouTubeSource)
```

## 🎼 扒谱引擎

### 单旋律提取（Melody）

**预期实现：** `backend/transcriber/melody.py`

```python
class MelodyTranscriber:
    def extract_pitch(audio) -> array  # 基频提取
    def smooth_pitch(pitch) -> array   # 平滑处理
    def note_segmentation() -> list    # 音符分割
    def to_music21() -> Score          # 转换为 music21
    def to_midi() -> MidiFile          # 生成 MIDI
```

**算法步骤：**
1. 加载音频文件
2. 计算频谱图（STFT）
3. 基频提取（Harmonic-Percussive 分离）
4. 音高平滑和量化
5. 音符识别和分割
6. 生成 MIDI/五线谱

### 多声部分离（Polyphonic）

**预期实现：** `backend/transcriber/polyphonic.py`

```python
class PolyphonicTranscriber:
    def separate_sources(audio) -> dict  # 声源分离
    def extract_harmonies() -> list      # 和弦识别
    def voice_leading() -> list          # 声部走向
    def to_multitrack_midi()             # 多轨 MIDI
```

**算法步骤：**
1. 声源分离（Source Separation）
2. 和弦识别
3. 声部识别
4. 多轨输出

## 📊 前端界面

### 页面结构

```
┌─────────────────────────────────────┐
│     Header (导航/源切换)             │
├─────────────────────────────────────┤
│  Left Panel     │    Main Content    │
│  - 音乐源选择    │  - 上传/搜索      │
│  - 搜索结果     │  - 波形显示      │
│  - 播放列表     │  - 频谱显示      │
│                 │  - 五线谱显示     │
│                 │  - MIDI 下载按钮  │
├─────────────────────────────────────┤
│  Tabs: 单旋律 | 多声部 | 设置        │
└─────────────────────────────────────┘
```

### 交互流程

```
1. 选择音乐源
   ↓
2. 搜索或上传音乐
   ↓
3. 选择曲目
   ↓
4. 点击"开始扒谱"
   ↓
5. 显示结果
   - 波形
   - 频谱
   - 识别的旋律/和弦
   - 五线谱
   ↓
6. 导出 MIDI
```

## 🔄 数据流

### 单曲处理流程

```
用户请求
  ↓
选择音乐源 (SourceFactory)
  ↓
搜索/获取音乐 (AudioSource.search/get_audio_stream)
  ↓
加载音频到内存 (librosa.load)
  ↓
预处理 (重采样、归一化)
  ↓
特征提取 (STFT、频谱图、基频等)
  ↓
音乐分析
  ├─ MelodyTranscriber (单旋律)
  └─ PolyphonicTranscriber (多声部)
  ↓
结果生成
  ├─ MIDI 文件
  ├─ JSON 可视化数据
  └─ 元数据
  ↓
返回前端显示和下载
```

## 📦 依赖管理

**主要库：**
- `librosa` - 音乐信号处理
- `music21` - 乐理和符号
- `numpy/scipy` - 数值计算
- `Flask` - Web 框架
- `requests` - HTTP 请求

## 🚀 扩展点

### 添加新音乐源

1. 创建 `sources/xxx.py`
2. 继承 `AudioSource`
3. 实现 4 个抽象方法
4. 在 `__init__.py` 注册

### 改进扒谱算法

1. 编辑 `transcriber/melody.py` 或 `polyphonic.py`
2. 调整参数或算法
3. 测试精度

### 新增可视化方式

1. 编辑 `frontend/js/visualizer.js`
2. 添加新的 Canvas 或 SVG 渲染
3. 连接后端数据

## 📋 Next Steps

- [ ] 实现 Flask app.py 和 API 路由
- [ ] 实现 MelodyTranscriber
- [ ] 实现 PolyphonicTranscriber
- [ ] 前端页面设计
- [ ] 集成测试
- [ ] 性能优化
- [ ] 错误处理和日志
- [ ] 部署脚本

---

**Architecture designed for extensibility and maintainability.**
