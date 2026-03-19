# 📚 模块文档和输入/输出格式说明

## 快速索引

- [Melody 扒谱](#melody-扒谱)
- [Polyphonic 扒谱](#polyphonic-扒谱)
- [Spotify 音乐源](#spotify-音乐源)
- [本地文件源](#本地文件源)

---

## Melody 扒谱

**文件：** `backend/transcriber/melody.py`

**用途：** 提取单条主旋律

### 输入

| 参数 | 类型 | 说明 | 例子 |
|------|------|------|------|
| `audio_path` | str | 音频文件路径 | `/path/to/song.mp3` |
| `sr` | int | 采样率（Hz） | 22050（默认） |
| `hop_length` | int | STFT 跳跃大小 | 512（默认） |

### 支持的音频格式

```
.mp3, .wav, .flac, .ogg, .m4a, .wma
```

### 输出格式

#### 方法：`transcribe(audio_path: str) -> Dict`

```json
{
  "notes": [
    {
      "start_frame": 0,
      "end_frame": 512,
      "midi": 60,              // C4 音符
      "freq": 261.63,          // Hz
      "duration": 0.5,         // 秒
      "confidence": 0.95       // 0-1
    },
    {
      "start_frame": 512,
      "end_frame": 1024,
      "midi": 62,
      "freq": 293.66,
      "duration": 0.5,
      "confidence": 0.93
    }
  ],
  "total_notes": 42,
  "duration_sec": 10.5
}
```

#### 方法：`save_midi(output_path: str) -> None`

生成标准 MIDI 文件（`.mid`）：
- **轨道数：** 1
- **乐器：** 长笛（Flute, Program 73）
- **时值：** 根据音符时长自动计算

#### 方法：`get_visualization_data() -> Dict`

```json
{
  "pitch_curve": [0, 261.63, 293.66, 0, ...],  // 基频曲线
  "midi_curve": [null, 60, 62, null, ...],     // MIDI 序列
  "confidence": [0, 0.95, 0.92, 0, ...],       // 置信度
  "notes": [...]                                // 同 transcribe 输出
}
```

### 使用示例

```python
from transcriber import MelodyTranscriber

# 创建提取器
transcriber = MelodyTranscriber()

# 执行扒谱
result = transcriber.transcribe('song.mp3')
print(f"识别 {result['total_notes']} 个音符")

# 保存 MIDI
transcriber.save_midi('output.mid')

# 获取可视化数据
viz_data = transcriber.get_visualization_data()
```

### 参数调优

**识别不到音符？**
- 检查 `fmin` 和 `fmax`：
  ```python
  transcriber.extract_pitch_pyin()  # 默认 80-400 Hz
  ```
- 调整范围（女性人声）：
  ```python
  # 在 melody.py 修改 fmin=150, fmax=600
  ```

**基频抖动？**
- 增加平滑窗口：
  ```python
  transcriber.smooth_pitch(window_size=11)  # 默认 7
  ```

---

## Polyphonic 扒谱

**文件：** `backend/transcriber/polyphonic.py`

**用途：** 分离和识别多个声部

### 输入

| 参数 | 类型 | 说明 | 例子 |
|------|------|------|------|
| `audio_path` | str | 音频文件路径 | `/path/to/song.mp3` |
| `n_voices` | int | 预期声部数 | 2（默认） |
| `sr` | int | 采样率 | 22050（默认） |
| `hop_length` | int | STFT 跳跃 | 512（默认） |

### 输出格式

#### 方法：`transcribe(audio_path: str, n_voices: int = 2) -> Dict`

```json
{
  "voices": [
    [  // 声部 1
      {
        "start_frame": 0,
        "end_frame": 512,
        "midi": 60,
        "freq": 261.63,
        "duration": 0.5
      },
      ...
    ],
    [  // 声部 2
      {
        "start_frame": 100,
        "end_frame": 612,
        "midi": 72,
        "freq": 392.00,
        "duration": 0.5
      },
      ...
    ]
  ],
  "total_voices": 2,
  "duration_sec": 10.5
}
```

#### 方法：`save_midi_multitrack(output_path: str) -> None`

生成多轨 MIDI 文件：
- **轨道数：** N（等于 `n_voices`）
- **乐器分配：**
  1. 长笛（Flute）
  2. 小提琴（Violin）
  3. 大提琴（Cello）
  4. 低音提琴（Contrabass）
- **时值：** 自动计算

#### 方法：`get_visualization_data() -> Dict`

```json
{
  "voices": [...],                    // 同 transcribe 输出
  "harmonic_spectrogram": [...],      // 2D 频谱图
  "percussive_spectrogram": [...]     // 打击分量
}
```

### 使用示例

```python
from transcriber import PolyphonicTranscriber

# 创建分离器
transcriber = PolyphonicTranscriber()

# 执行多声部分离
result = transcriber.transcribe('song.mp3', n_voices=2)
print(f"分离出 {result['total_voices']} 个声部")

# 保存多轨 MIDI
transcriber.save_midi_multitrack('output.mid')
```

### 参数调优

**声部分离不清楚？**
- 增加 HPSS margin（更激进分离）：
  ```python
  # 在 config.json 中修改
  "hpss_margin": 6.0  # 默认 4.0
  ```

**需要识别更多声部？**
```python
result = transcriber.transcribe('song.mp3', n_voices=4)
```

---

## Spotify 音乐源

**文件：** `backend/sources/spotify.py`

**用途：** 从 Spotify 搜索和下载音乐预览

### 配置

**文件：** `backend/config.json`

```json
{
  "spotify": {
    "auth_url": "https://accounts.spotify.com/api/token",
    "api_url": "https://api.spotify.com/v1",
    "search_limit": 50,
    "preview_timeout": 10
  }
}
```

### 输入

#### 方法：`authenticate(client_id: str, client_secret: str) -> bool`

```python
source = SpotifySource({
    'client_id': 'YOUR_CLIENT_ID',
    'client_secret': 'YOUR_CLIENT_SECRET'
})

if source.authenticate():
    print("认证成功")
```

#### 方法：`search(query: str, limit: int = 10) -> List[Dict]`

```python
results = source.search('Imagine John Lennon', limit=5)
```

### 输出格式

#### 搜索结果

```json
[
  {
    "id": "7qiZfU4dY1lsylvNEprXGy",
    "title": "Imagine",
    "artist": "John Lennon",
    "duration": 183000,           // 毫秒
    "preview_url": "https://p.scdn.co/...",
    "source": "spotify",
    "url": "https://open.spotify.com/track/..."
  }
]
```

#### 方法：`get_audio_file(music_id: str, save_path: str) -> str`

下载 30 秒预览音频：
```python
filepath = source.get_audio_file(
    'track_id',
    '/path/to/preview.mp3'
)
# 返回：'/path/to/preview.mp3'
```

### 限制

- ⏱️ 预览：30 秒（API 限制）
- 📁 格式：MP3
- 🔐 需要：Client ID + Secret
- 🌐 需要网络连接

### 使用示例

```python
from sources import SourceFactory

# 切换到 Spotify 源
SourceFactory.set_current('spotify', {
    'client_id': 'xxx',
    'client_secret': 'xxx'
})

source = SourceFactory.get_current()

# 搜索
results = source.search('Beatles', limit=10)

# 下载
for track in results[:1]:
    source.get_audio_file(track['id'], 'preview.mp3')
```

---

## 本地文件源

**文件：** `backend/sources/local_file.py`

**用途：** 从本地文件夹搜索音乐文件

### 配置

**文件：** `backend/config.json`

```json
{
  "audio": {
    "allowed_formats": [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma"]
  }
}
```

### 输入

#### 方法：`search(query: str, limit: int = 10) -> List[Dict]`

搜索文件名包含关键词的文件：

```python
source = LocalFileSource({
    'music_dir': '~/Music',
    'recursive': True
})

results = source.search('love', limit=5)
```

### 输出格式

#### 搜索结果

```json
[
  {
    "id": "/home/user/Music/love_song.mp3",
    "title": "love_song",
    "artist": "Local",
    "duration": 0,
    "format": ".mp3",
    "source": "local_file",
    "path": "/home/user/Music/love_song.mp3"
  }
]
```

#### 方法：`get_audio_file(music_id: str, save_path: str) -> str`

复制文件到指定位置：
```python
source.get_audio_file(
    '/home/user/Music/song.mp3',
    '/tmp/work/song.mp3'
)
# 返回：'/tmp/work/song.mp3'
```

#### 方法：`list_available_music() -> List[Dict]`

列出所有可用音乐：
```python
all_music = source.list_available_music()
print(f"找到 {len(all_music)} 首音乐")
```

### 使用示例

```python
from sources import SourceFactory

# 切换到本地文件源
SourceFactory.set_current('local_file', {
    'music_dir': '~/Music',
    'recursive': True
})

source = SourceFactory.get_current()

# 搜索
results = source.search('song', limit=10)

# 使用
for track in results:
    print(f"{track['title']} ({track['format']})")
    path = source.get_audio_file(track['id'], f'/tmp/{track["title"]}.mp3')
```

---

## 📊 完整工作流

### Spotify → 扒谱 → MIDI

```python
from sources import SourceFactory
from transcriber import MelodyTranscriber

# 1. 搜索
SourceFactory.set_current('spotify', config)
source = SourceFactory.get_current()
results = source.search('Yesterday Beatles')

# 2. 下载预览
track = results[0]
source.get_audio_file(track['id'], 'preview.mp3')

# 3. 扒谱
transcriber = MelodyTranscriber()
result = transcriber.transcribe('preview.mp3')

# 4. 保存
transcriber.save_midi('output.mid')
```

---

**更多帮助：** 查看 `BACKEND_SETUP.md` 和 `USAGE_EXAMPLES.md`
