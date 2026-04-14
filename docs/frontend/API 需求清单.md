# 前端 API 需求清单

> 整理时间：2026-04-11
> 整理依据：`docs/frontend/前端代码整理报告.md` + 前端代码实际 API 调用扫描

---

## 一、概览

| 分类 | 模块 | 前端页面数 | API 端点数 |
|------|------|------------|------------|
| 歌曲管理 | songs | 4 页 | 4 |
| 歌手管理 | artists | 3 页 | 4 |
| 录音采集 | capture | 1 页 | 4 |
| 录音文件 | recordings | 1 页 | 3 |
| 扒谱 | transcribe | 1 页 | 3 |
| 音源 | audio-sources | 1 页 | 2 |
| **合计** | | **11 页** | **20** |

---

## 二、模块详细清单

### 2.1 歌曲模块（songs）

#### 2.1.1 歌曲列表/搜索
- **端点**：`GET /api/songs/list`
- **参数**：`keyword`（可选，URL query）
- **响应**：歌曲列表（id, title, artist_id, category, audio_path, status）
- **已有/缺失**：**需新增**（前端已调用，但后端无此端点）

#### 2.1.2 歌曲详情
- **端点**：`GET /api/songs/{id}`
- **参数**：路径参数 `id`
- **响应**：歌曲详情对象
- **已有/缺失**：**需新增**

#### 2.1.3 创建歌曲
- **端点**：`POST /api/songs/add`
- **参数（JSON）**：`{title, artist_id?, category, audio_source_id?}`
- **参数（FormData）**：当上传文件时，包含 file 字段
- **响应**：`{ok: bool, song_id: int}`
- **已有/缺失**：**需新增**

#### 2.1.4 更新歌曲
- **端点**：`PUT /api/songs/{id}`
- **参数（JSON）**：`{title, artist_id?, category}`
- **响应**：更新结果
- **已有/缺失**：**需新增**

#### 2.1.5 删除歌曲
- **端点**：`DELETE /api/songs/{id}`
- **参数**：路径参数 `id`
- **响应**：删除结果
- **已有/缺失**：**需新增**

---

### 2.2 歌手模块（artists）

#### 2.2.1 歌手列表
- **端点**：`GET /api/songs/artists/list`
- **参数**：无
- **响应**：歌手列表（id, name, bio, avatar_path）
- **已有/缺失**：**需新增**

#### 2.2.2 歌手详情
- **端点**：`GET /api/songs/artists/{id}`
- **参数**：路径参数 `id`
- **响应**：歌手详情对象
- **已有/缺失**：**需新增**

#### 2.2.3 新增歌手
- **端点**：`POST /api/songs/artists/add`
- **参数**：FormData（name, bio, avatar_file）
- **响应**：`{ok: bool, artist_id: int}`
- **已有/缺失**：**需新增**

#### 2.2.4 更新歌手
- **端点**：`PUT /api/songs/artists/{id}`
- **参数**：FormData 或 JSON（name, bio, avatar_file?）
- **响应**：更新结果
- **已有/缺失**：**需新增**

#### 2.2.5 删除歌手
- **端点**：`DELETE /api/songs/artists/{id}`
- **参数**：路径参数 `id`
- **响应**：删除结果
- **已有/缺失**：**需新增**

---

### 2.3 录音采集模块（capture）

#### 2.3.1 开始录音
- **端点**：`POST /api/capture/start-recording`
- **参数**：无（空 JSON `{}`）
- **响应**：`{ok, session_id, ...}`
- **已有/缺失**：**需新增**

#### 2.3.2 停止录音
- **端点**：`PUT /api/capture/stop-recording`
- **参数**：`{session_id, file_name?}`
- **响应**：停止结果
- **已有/缺失**：**需新增**

#### 2.3.3 录音文件列表
- **端点**：`GET /api/capture/list`
- **参数**：`limit`（可选，默认 20）
- **响应**：录音文件列表（session_id, file_name, created_at 等）
- **已有/缺失**：**需新增**

#### 2.3.4 删除录音会话
- **端点**：`DELETE /api/capture/sessions/{sessionId}`
- **参数**：路径参数 `sessionId`
- **响应**：删除结果
- **已有/缺失**：**需新增**

#### 2.3.5 更新录音会话（元数据编辑）
- **端点**：`PUT /api/capture/sessions/{sessionId}`
- **参数（JSON）**：`{file_name}`
- **响应**：更新结果
- **已有/缺失**：**需新增**

---

### 2.4 扒谱模块（transcribe）

#### 2.4.1 提交扒谱任务
- **端点**：`POST /api/transcribe/start`
- **参数（JSON）**：`{song_id, mode}`（mode: melody / polyphonic）
- **响应**：`{ok, task_id}`
- **已有/缺失**：**需新增**（现有 API `/api/transcribe/melody` 和 `/api/transcribe/polyphonic` 是旧设计）

#### 2.4.2 查询扒谱状态
- **端点**：`GET /api/transcribe/status/{taskId}`
- **参数**：路径参数 `taskId`
- **响应**：`{status, progress?, result?, midi_file?, error?}`
- **已有/缺失**：**需新增**

#### 2.4.3 歌曲列表（扒谱页）
- **端点**：`GET /api/songs/list`
- **参数**：`keyword`（可选）
- **说明**：与 songs 模块复用同一端点

---

### 2.5 音源模块（audio-sources）

#### 2.5.1 音源列表
- **端点**：`GET /api/audio-sources/list`
- **参数**：`status`（可选，如 `active`）
- **响应**：音源列表（id, name, file_path, type, status 等）
- **已有/缺失**：**需新增**

#### 2.5.2 音源上传
- **端点**：`POST /api/audio-sources/upload`
- **参数**：FormData（name, file）
- **响应**：`{ok, audio_source_id, file_path}`
- **已有/缺失**：**需新增**

---

### 2.6 通用基础 API（已有）

#### 2.6.1 健康检查
- **端点**：`GET /api/health`
- **状态**：✅ **已有**

#### 2.6.2 应用状态
- **端点**：`GET /api/status`
- **状态**：✅ **已有**

#### 2.6.3 获取音乐源
- **端点**：`GET /api/sources`
- **状态**：✅ **已有**

#### 2.6.4 切换音乐源
- **端点**：`PUT /api/sources/switch`
- **状态**：✅ **已有**

#### 2.6.5 搜索音乐
- **端点**：`GET /api/search`
- **参数**：`q`, `limit`
- **状态**：✅ **已有**

#### 2.6.6 上传音乐文件
- **端点**：`POST /api/music/upload`
- **状态**：✅ **已有**

#### 2.6.7 单旋律提取（旧）
- **端点**：`POST /api/transcribe/melody`
- **参数**：`{audio_file}`
- **状态**：⚠️ **已存在，但前端未使用（旧设计）**

#### 2.6.8 多声部分离（旧）
- **端点**：`POST /api/transcribe/polyphonic`
- **参数**：`{audio_file}`
- **状态**：⚠️ **已存在，但前端未使用（旧设计）**

#### 2.6.9 下载 MIDI
- **端点**：`GET /api/download/midi/{file}`
- **状态**：✅ **已有**

---

## 三、汇总对照表

| # | 模块 | 端点 | 方法 | 状态 |
|---|------|------|------|------|
| 1 | 通用 | `/api/health` | GET | ✅ 已有 |
| 2 | 通用 | `/api/status` | GET | ✅ 已有 |
| 3 | 通用 | `/api/sources` | GET | ✅ 已有 |
| 4 | 通用 | `/api/sources/switch` | PUT | ✅ 已有 |
| 5 | 通用 | `/api/search` | GET | ✅ 已有 |
| 6 | 通用 | `/api/music/upload` | POST | ✅ 已有 |
| 7 | 通用 | `/api/transcribe/melody` | POST | ⚠️ 已有（前端未用，旧设计） |
| 8 | 通用 | `/api/transcribe/polyphonic` | POST | ⚠️ 已有（前端未用，旧设计） |
| 9 | 通用 | `/api/download/midi/{file}` | GET | ✅ 已有 |
| 10 | 歌曲 | `/api/songs/list` | GET | ❌ **需新增** |
| 11 | 歌曲 | `/api/songs/{id}` | GET | ❌ **需新增** |
| 12 | 歌曲 | `/api/songs/add` | POST | ❌ **需新增** |
| 13 | 歌曲 | `/api/songs/{id}` | PUT | ❌ **需新增** |
| 14 | 歌曲 | `/api/songs/{id}` | DELETE | ❌ **需新增** |
| 15 | 歌手 | `/api/songs/artists/list` | GET | ❌ **需新增** |
| 16 | 歌手 | `/api/songs/artists/{id}` | GET | ❌ **需新增** |
| 17 | 歌手 | `/api/songs/artists/add` | POST | ❌ **需新增** |
| 18 | 歌手 | `/api/songs/artists/{id}` | PUT | ❌ **需新增** |
| 19 | 歌手 | `/api/songs/artists/{id}` | DELETE | ❌ **需新增** |
| 20 | 录音 | `/api/capture/start-recording` | POST | ❌ **需新增** |
| 21 | 录音 | `/api/capture/stop-recording` | PUT | ❌ **需新增** |
| 22 | 录音 | `/api/capture/list` | GET | ❌ **需新增** |
| 23 | 录音 | `/api/capture/sessions/{id}` | PUT | ❌ **需新增** |
| 24 | 录音 | `/api/capture/sessions/{id}` | DELETE | ❌ **需新增** |
| 25 | 扒谱 | `/api/transcribe/start` | POST | ❌ **需新增** |
| 26 | 扒谱 | `/api/transcribe/status/{taskId}` | GET | ❌ **需新增** |
| 27 | 音源 | `/api/audio-sources/list` | GET | ❌ **需新增** |
| 28 | 音源 | `/api/audio-sources/upload` | POST | ❌ **需新增** |

---

## 四、说明

### 4.1 旧扒谱 API 与新设计的区别

现有 API 设计以 `audio_file` 为参数（文件名），前端新设计改为：
- `POST /api/transcribe/start` + `song_id`（以歌曲ID为主键）
- `GET /api/transcribe/status/{taskId}`（轮询任务状态）

这是**需要废弃旧 API 还是并行新设计**，待后端确认。

### 4.2 前端页面覆盖情况

本清单已覆盖全部 11 个前端页面（不计 index.html）的所有 API 调用：
- `pages/songs/index.html`、`add.html`、`details.html`
- `pages/artists/index.html`、`add.html`、`details.html`
- `pages/capture.html`
- `pages/recordings/index.html`
- `pages/transcribe/index.html`
- `pages/audio-sources/upload.html`

### 4.3 统一说明

- 所有 API 基础路径为 `/api/`（经 Nginx 反向代理）
- 前端 `API_BASE` 为空字符串，调用时直接拼接
- 数据库需同步新建 songs、artists、audio_sources、capture_sessions 等表

---

*本清单由前端整理报告 + 代码扫描生成，供后端 agent 参考。*
