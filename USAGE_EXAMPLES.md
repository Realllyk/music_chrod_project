# 💡 使用示例

## Python 脚本示例

### 示例 1: 基本的单旋律提取

```python
from backend.transcriber import MelodyTranscriber

# 创建提取器
transcriber = MelodyTranscriber(sr=22050)

# 执行完整的扒谱流程
result = transcriber.transcribe('path/to/music.mp3')

# 查看结果
print(f"识别的音符数: {result['total_notes']}")
print(f"音乐时长: {result['duration_sec']:.2f}秒")
print(f"首个音符: {result['notes'][0]}")

# 保存 MIDI
transcriber.save_midi('output.mid')

# 获取可视化数据
viz_data = transcriber.get_visualization_data()
```

### 示例 2: 多声部分离

```python
from backend.transcriber import PolyphonicTranscriber

# 创建多声部提取器
transcriber = PolyphonicTranscriber(sr=22050)

# 执行多声部分离
result = transcriber.transcribe('path/to/music.mp3', n_voices=2)

# 查看结果
print(f"声部数: {result['total_voices']}")
for i, voice_notes in enumerate(result['voices']):
    print(f"第 {i+1} 声部: {len(voice_notes)} 个音符")

# 保存多轨 MIDI
transcriber.save_midi_multitrack('output_multitrack.mid')
```

### 示例 3: 切换音乐源搜索

```python
from backend.sources import SourceFactory

# 使用本地文件源
SourceFactory.set_current('local_file', {
    'music_dir': '~/Music',
    'recursive': True
})

source = SourceFactory.get_current()
results = source.search('imagine', limit=5)

for result in results:
    print(f"标题: {result['title']}")
    print(f"路径: {result['path']}")
    print()

# 切换到 Spotify
SourceFactory.set_current('spotify', {
    'client_id': 'YOUR_CLIENT_ID',
    'client_secret': 'YOUR_CLIENT_SECRET'
})

source = SourceFactory.get_current()
results = source.search('imagine john lennon', limit=5)

for result in results:
    print(f"标题: {result['title']}")
    print(f"艺术家: {result['artist']}")
    print(f"预览链接: {result.get('preview_url')}")
    print()
```

### 示例 4: 完整流程 - 从 Spotify 搜索到扒谱

```python
from backend.sources import SourceFactory
from backend.transcriber import MelodyTranscriber

# 1. 切换到 Spotify
SourceFactory.set_current('spotify', {
    'client_id': 'YOUR_CLIENT_ID',
    'client_secret': 'YOUR_CLIENT_SECRET'
})

# 2. 搜索音乐
source = SourceFactory.get_current()
results = source.search('Yesterday Beatles', limit=1)

if results:
    track = results[0]
    print(f"找到: {track['title']} - {track['artist']}")
    
    # 3. 下载音乐
    music_id = track['id']
    local_path = f"downloads/{music_id}.mp3"
    source.get_audio_file(music_id, local_path)
    print(f"已下载到: {local_path}")
    
    # 4. 执行扒谱
    transcriber = MelodyTranscriber()
    result = transcriber.transcribe(local_path)
    print(f"扒谱结果: {result['total_notes']} 个音符")
    
    # 5. 保存 MIDI
    transcriber.save_midi(f"outputs/{music_id}.mid")
    print("MIDI 文件已保存")
```

---

## REST API 示例

### 示例 1: 使用 curl 上传和扒谱

```bash
# 1. 上传音乐文件
UPLOAD_RESULT=$(curl -X POST http://localhost:5000/api/music/upload \
  -F "file=@~/Music/mymusic.mp3")

# 提取文件名
FILENAME=$(echo $UPLOAD_RESULT | jq -r '.filename')
echo "上传成功: $FILENAME"

# 2. 执行单旋律提取
curl -X POST http://localhost:5000/api/transcribe/melody \
  -H "Content-Type: application/json" \
  -d "{\"audio_file\": \"$FILENAME\"}"

# 3. 下载 MIDI 文件
curl http://localhost:5000/api/download/midi/melody_mymusic.mid \
  -o ~/Music/mymusic.mid
```

### 示例 2: 使用 Python requests

```python
import requests
import json

BASE_URL = 'http://localhost:5000'

# 1. 获取可用音乐源
response = requests.get(f'{BASE_URL}/api/sources')
sources = response.json()['available_sources']
print(f"可用源: {sources}")

# 2. 切换到本地文件源
response = requests.post(f'{BASE_URL}/api/sources/switch', json={
    'source_name': 'local_file',
    'config': {
        'music_dir': '~/Music',
        'recursive': True
    }
})
print(response.json())

# 3. 搜索音乐
response = requests.get(f'{BASE_URL}/api/search', params={
    'q': 'love',
    'limit': 10
})
results = response.json()['results']

for track in results:
    print(f"- {track['title']}")

# 4. 上传文件
with open('~/Music/mymusic.mp3', 'rb') as f:
    files = {'file': f}
    response = requests.post(f'{BASE_URL}/api/music/upload', files=files)
    filename = response.json()['filename']

# 5. 执行扒谱
response = requests.post(f'{BASE_URL}/api/transcribe/melody', json={
    'audio_file': filename
})

result = response.json()
print(f"识别的音符: {result['result']['total_notes']}")
print(f"MIDI 文件: {result['midi_file']}")

# 6. 下载输出
midi_filename = result['midi_file']
response = requests.get(f'{BASE_URL}/api/download/midi/{midi_filename}')

with open(f'~/outputs/{midi_filename}', 'wb') as f:
    f.write(response.content)
```

### 示例 3: 使用 JavaScript/Fetch

```javascript
const BASE_URL = 'http://localhost:5000';

// 1. 获取状态
async function getStatus() {
    const response = await fetch(`${BASE_URL}/api/status`);
    const data = await response.json();
    console.log('应用状态:', data);
}

// 2. 上传文件
async function uploadFile(fileInput) {
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    const response = await fetch(`${BASE_URL}/api/music/upload`, {
        method: 'POST',
        body: formData
    });
    
    const data = await response.json();
    return data.filename;
}

// 3. 执行单旋律提取
async function transcribeMelody(filename) {
    const response = await fetch(`${BASE_URL}/api/transcribe/melody`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({audio_file: filename})
    });
    
    const data = await response.json();
    console.log(`识别 ${data.result.total_notes} 个音符`);
    return data.midi_file;
}

// 4. 下载 MIDI
async function downloadMidi(filename) {
    const response = await fetch(`${BASE_URL}/api/download/midi/${filename}`);
    const blob = await response.blob();
    
    // 创建下载链接
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
}

// 完整流程
async function fullWorkflow(fileInput) {
    try {
        // 上传
        const filename = await uploadFile(fileInput);
        console.log('上传成功:', filename);
        
        // 扒谱
        const midiFile = await transcribeMelody(filename);
        console.log('扒谱完成:', midiFile);
        
        // 下载
        await downloadMidi(midiFile);
        console.log('下载完成');
    } catch (error) {
        console.error('出错:', error);
    }
}
```

### 示例 4: 高级 - 自定义扒谱参数

```bash
# 调整基频提取的频率范围（适合不同人声/乐器）

# 女性人声（高频）
curl -X POST http://localhost:5000/api/transcribe/melody \
  -H "Content-Type: application/json" \
  -d '{
    "audio_file": "song.mp3",
    "fmin": 150,
    "fmax": 600
  }'

# 男性人声（低频）
curl -X POST http://localhost:5000/api/transcribe/melody \
  -H "Content-Type: application/json" \
  -d '{
    "audio_file": "song.mp3",
    "fmin": 80,
    "fmax": 300
  }'

# 小提琴（中高频）
curl -X POST http://localhost:5000/api/transcribe/melody \
  -H "Content-Type: application/json" \
  -d '{
    "audio_file": "song.mp3",
    "fmin": 200,
    "fmax": 800
  }'
```

---

## 常见工作流

### 工作流 1: 本地音乐 → 扒谱 → MIDI

```bash
# 1. 启动服务
cd ~/music_learning_project/backend
python app.py &

# 2. 使用本地文件
curl -X POST http://localhost:5000/api/sources/switch \
  -H "Content-Type: application/json" \
  -d '{"source_name": "local_file", "config": {"music_dir": "~/Music"}}'

# 3. 搜索
curl "http://localhost:5000/api/search?q=imagine&limit=3"

# 4. 上传
curl -X POST http://localhost:5000/api/music/upload \
  -F "file=@~/Music/imagine.mp3" > upload.json

FILENAME=$(jq -r '.filename' upload.json)

# 5. 扒谱
curl -X POST http://localhost:5000/api/transcribe/melody \
  -H "Content-Type: application/json" \
  -d "{\"audio_file\": \"$FILENAME\"}" > result.json

MIDIFILE=$(jq -r '.midi_file' result.json)

# 6. 下载
curl http://localhost:5000/api/download/midi/$MIDIFILE -o output.mid
```

### 工作流 2: Spotify 搜索 → 下载预览 → 快速扒谱

```bash
# 1. 切换到 Spotify
curl -X POST http://localhost:5000/api/sources/switch \
  -H "Content-Type: application/json" \
  -d '{
    "source_name": "spotify",
    "config": {
      "client_id": "YOUR_ID",
      "client_secret": "YOUR_SECRET"
    }
  }'

# 2. 搜索
curl "http://localhost:5000/api/search?q=Bohemian%20Rhapsody&limit=1" > search.json

MUSICID=$(jq -r '.results[0].id' search.json)

# 3. 下载预览
curl "http://localhost:5000/api/music/download/spotify/$MUSICID" > download.json

FILENAME=$(jq -r '.filename' download.json)

# 4. 扒谱（多声部）
curl -X POST http://localhost:5000/api/transcribe/polyphonic \
  -H "Content-Type: application/json" \
  -d "{\"audio_file\": \"$FILENAME\"}" > result.json

MIDIFILE=$(jq -r '.midi_file' result.json)

# 5. 下载结果
curl http://localhost:5000/api/download/midi/$MIDIFILE -o bohemian.mid
```

---

**更多示例敬请期待！** 📚
