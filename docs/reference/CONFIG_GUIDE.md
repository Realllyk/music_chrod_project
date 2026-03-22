# ⚙️ 配置文件指南

## 配置文件位置

```
~/music_learning_project/backend/config.json
```

## 配置文件内容说明

### 1. API 配置

```json
{
  "api": {
    "host": "0.0.0.0",      // 监听地址（0.0.0.0 = 所有接口）
    "port": 5000,            // 监听端口
    "debug": true            // 调试模式（生产环境改为 false）
  }
}
```

**修改场景：**
- `port`：如果 5000 被占用
- `host`：如果只在本地访问，改为 "127.0.0.1"
- `debug`：生产环境改为 false

---

### 2. Spotify API 配置

```json
{
  "spotify": {
    "auth_url": "https://accounts.spotify.com/api/token",
    "api_url": "https://api.spotify.com/v1",
    "search_limit": 50,       // 搜索结果数上限
    "preview_timeout": 10     // 下载预览音频超时（秒）
  }
}
```

**注意：**
- `auth_url` 和 `api_url` 从代码硬编码迁移到配置文件
- 使用 Client Credentials Flow（无用户授权）
- 预览音频仅 30 秒（API 限制）

**不包含的敏感信息：**
- `client_id` 和 `client_secret` 应该在运行时通过环境变量或 API 参数传入
- 不要在配置文件中存储这些凭证（安全风险）

---

### 3. 音频处理配置

```json
{
  "audio": {
    "sample_rate": 22050,                    // 采样率（Hz）
    "hop_length": 512,                       // STFT 跳跃大小
    "max_file_size": 536870912,              // 最大文件大小（500MB）
    "allowed_formats": [".mp3", ".wav", ...] // 允许的音频格式
  }
}
```

**参数说明：**

- `sample_rate`：
  - 22050 Hz：标准，足以捕捉人声
  - 44100 Hz：更高精度，处理较慢
  - 范围：8000-48000 Hz

- `hop_length`：
  - 512：默认，约 23ms 帧间隔（推荐）
  - 256：更高时间分辨率，处理更慢
  - 1024：较低时间分辨率，处理更快

- `max_file_size`：
  - 536870912 = 500MB
  - 增加值：`1000 * 1024 * 1024` = 1GB

- `allowed_formats`：支持的音频格式
  - 修改此列表可以限制上传格式

---

### 4. 扒谱配置

```json
{
  "transcription": {
    "melody": {
      "fmin": 80,              // 最小基频（Hz）
      "fmax": 400,             // 最大基频（Hz）
      "hop_length": 512,       // 跳跃大小
      "window_size": 7         // 基频平滑窗口
    },
    "polyphonic": {
      "n_voices": 2,           // 预期声部数
      "hpss_margin": 4.0       // HPSS 分离程度
    }
  }
}
```

**单旋律参数：**

`fmin` 和 `fmax` 的推荐值：
- 女性人声：`"fmin": 150, "fmax": 600`
- 男性人声：`"fmin": 80, "fmax": 300`
- 小提琴：`"fmin": 200, "fmax": 800`
- 笛子：`"fmin": 250, "fmax": 1000`

`window_size`：
- 更大的窗口：更平滑，但可能丢失细节
- 7：平衡值（推荐）
- 范围：3-15

**多声部参数：**

`n_voices`：
- 1：单旋律
- 2：双声部（默认）
- 3：三声部
- 4：四声部

`hpss_margin`：
- 2.0：温和分离
- 4.0：平衡（默认，推荐）
- 8.0：激进分离

---

### 5. 文件路径配置

```json
{
  "paths": {
    "uploads": "./uploads",  // 用户上传文件夹
    "outputs": "./outputs",  // 扒谱输出文件夹
    "logs": "./logs"         // 日志文件夹
  }
}
```

**注意：**
- 路径相对于项目根目录
- 这些文件夹会自动创建

---

## 🔧 常见修改场景

### 场景 1：只处理女性人声

修改 `config.json`：
```json
{
  "transcription": {
    "melody": {
      "fmin": 150,
      "fmax": 600,
      "window_size": 7
    }
  }
}
```

### 场景 2：提高处理速度

```json
{
  "audio": {
    "sample_rate": 16000,    // 降低采样率
    "hop_length": 1024       // 增加跳跃大小
  }
}
```

### 场景 3：提高精度

```json
{
  "audio": {
    "sample_rate": 44100,    // 提高采样率
    "hop_length": 256        // 减小跳跃大小
  },
  "transcription": {
    "melody": {
      "window_size": 11      // 增加平滑窗口
    }
  }
}
```

### 场景 4：提取四声部

```json
{
  "transcription": {
    "polyphonic": {
      "n_voices": 4,
      "hpss_margin": 5.0
    }
  }
}
```

### 场景 5：处理大文件

```json
{
  "audio": {
    "max_file_size": 2147483648  // 2GB
  }
}
```

---

## 📝 环境变量覆盖（可选）

虽然主要配置在 JSON 中，但可以通过环境变量覆盖：

```bash
# 修改端口
export API_PORT=8000

# 修改上传文件夹
export UPLOAD_FOLDER=/var/uploads

# Spotify 凭证（敏感信息）
export SPOTIFY_CLIENT_ID="xxx"
export SPOTIFY_CLIENT_SECRET="xxx"
```

在 `app.py` 中读取：
```python
API_PORT = os.getenv('API_PORT', config['api']['port'])
```

---

## ⚠️ 安全提示

**不要在配置文件中存储：**
- ❌ Spotify `client_id` / `client_secret`
- ❌ API keys 或令牌
- ❌ 数据库密码
- ❌ 私钥或证书

**应该存储在：**
- ✅ 环境变量
- ✅ `.env` 文件（不要提交到版本控制）
- ✅ 密钥管理服务（AWS Secrets, HashiCorp Vault 等）

---

## 📋 配置检查清单

部署前检查：

- [ ] `sample_rate` 和 `hop_length` 根据需求调整
- [ ] `max_file_size` 足以处理目标文件
- [ ] `fmin` / `fmax` 适合音频类型
- [ ] 文件路径正确
- [ ] API 端口未被占用
- [ ] 生产环境 `debug` 设为 false
- [ ] 敏感信息通过环境变量注入

---

## 🔄 重新加载配置

修改 `config.json` 后，需要重启 Flask 应用：

```bash
# 停止应用
Ctrl+C

# 重新启动
python app.py
```

---

## 📚 更多信息

- 音乐源配置：`BACKEND_SETUP.md`
- API 使用示例：`USAGE_EXAMPLES.md`
- 完整文档：`PROJECT_STRUCTURE.md`
