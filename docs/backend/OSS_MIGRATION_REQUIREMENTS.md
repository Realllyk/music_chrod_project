# 文件上传/下载 OSS 迁移需求分析

> 文档版本：v1.2（重新核实版）
> 创建时间：2026-04-14
> 状态：**待审批**

---

## 一、背景说明

当前系统文件存储策略不一致，存在以下问题：

1. **全部依赖本地存储**：经逐个核实，6 个待确认接口**全部使用本地磁盘**，没有任何一个走 OSS。
2. **服务器磁盘压力**：音频/MIDI 文件体积较大，长期存本地会导致磁盘耗尽，且无冗余保护。
3. **路径不统一**：`audio_sources.file_path`、`songs.audio_path`、`capture_sessions.file_path` 等字段混用本地路径（`/api/uploads/...`）和 OSS URL（来自歌手头像、音源文件等已迁移部分），下游逻辑难以统一处理。
4. **横向扩展受限**：Flask 服务部署在多节点时，本地文件无法共享，扩展困难。

**迁移目标**：将所有用户上传的文件（录音、歌曲音频）以及系统生成的文件（MIDI 输出）统一存入阿里云 OSS，本地仅保留转录处理时的临时文件（处理完后立即清理）。

---

## 二、现状梳理（重新核实）

### 已完成 OSS 迁移（无需变更）

| 功能 | API | 说明 |
|------|-----|------|
| 歌手头像上传 | `POST /api/artists/add`、`PUT /api/artists/<id>`、`PUT /api/artists/<id>/avatar` | 通过 `_save_avatar_to_oss()` 上传，存 OSS URL ✅ |
| 音源文件上传 | `POST /api/audio-sources/upload` | 通过 `upload_file()` 上传到 `audio-sources/` ✅ |
| 列出 OSS 音源 | `GET /api/audio-sources/oss-files` | 直接列 OSS 目录 ✅ |
| 扒谱任务处理 | `POST /api/transcribe/start` | 从 OSS 下载音频处理，结果 MIDI 上传 OSS ✅ |

### 待迁移（本文档范围）

共 **6 处**，逐个核实结果如下：

---

## 三、需要变更的功能（逐个核实）

### 1. 音乐文件上传

- **文件**: `controllers/music_controller.py`
- **API**: `POST /api/music/upload`
- **核实结果**: ✅ 确认本地存储
  - 保存到 `backend/uploads/music/` 目录
  - 返回 `file_path`（本地绝对路径，如 `/home/realllyka/project/music_chrod_project/backend/uploads/music/xxx.mp3`）
  - **无任何 OSS 调用**
- **变更内容**: 不再写入本地磁盘；调用 `upload_file(audio_file, directory="music")` 上传至 OSS，返回 OSS 公网 URL 作为 `file_url`。
- **影响范围**: 后端；前端需将返回字段从 `file_path` 改为 `file_url`（详见第六章）。

---

### 2. MIDI 文件下载

- **文件**: `controllers/music_controller.py`
- **API**: `GET /api/music/download/midi/<filename>`
- **核实结果**: ✅ 确认本地存储
  - 在服务器本地 `outputs/` 和 `uploads/` 目录中查找文件
  - 通过 `send_file()` 直接返回二进制流
  - **无任何 OSS 调用**
- **变更内容**: MIDI 文件迁移到 OSS 后，此接口有两种处理方案：
  - **方案 A（推荐）**：接口改为返回 302 重定向到 OSS 签名 URL（适用于私有 Bucket）；
  - **方案 B**：若 Bucket 为公开读，直接让前端用 OSS URL 下载，废弃此接口。
  - 建议：先确认 Bucket 访问策略，再决定。
- **影响范围**: 后端；前端下载逻辑需同步调整。

---

### 3. 录音文件上传

- **文件**: `controllers/capture_controller.py`
- **API**: `POST /api/capture/upload-file`
- **核实结果**: ✅ 确认本地存储
  - 保存到 `backend/uploads/recordings/<date>/` 目录
  - 返回 `file_path`（本地路径）
  - `capture_sessions.file_path` 存本地路径
  - `AudioSourcesService.create_from_session()` 以本地路径创建音源记录
  - **无任何 OSS 调用**
- **变更内容**: 文件上传后立即调用 `upload_file(file, directory="recordings")` 传至 OSS；`file_path` 改存 OSS URL；音源创建同步改为 OSS URL。
- **影响范围**: 后端；数据库 `capture_sessions.file_path`、`audio_sources.file_path` 字段语义变更（详见第四章）。

---

### 4. 录音文件回放

- **文件**: `controllers/capture_controller.py`
- **API**: `GET /api/capture/uploads/recordings/<filename>`
- **核实结果**: ✅ 确认本地存储
  - 从 `backend/uploads/recordings/` 目录读取文件
  - 通过 `send_file()` 返回
  - **无任何 OSS 调用**
- **变更内容**: 录音文件已迁移 OSS（功能 3）后，前端播放录音时直接使用 `capture_sessions.file_path` 中的 OSS URL。此接口作为兼容层，前端仍通过此路径访问，但后端改为从 OSS 下载后返回（降级方案）。待前端确认已全面切换到 OSS URL 后，可废弃此接口。
- **影响范围**: 后端（兼容降级）；前端需逐步切换到 OSS URL。

---

### 5. 歌曲音频文件上传

- **文件**: `controllers/songs_controller.py`
- **API**: `POST /api/songs/add`（multipart/form-data 分支）
- **核实结果**: ✅ 确认本地存储
  - 接收 `audio_file`，保存到 `backend/uploads/audio/`
  - `audio_path` 存为 `/api/uploads/audio/<filename>`（本地访问路径）
  - **无任何 OSS 调用**
  - 注意：JSON 分支（引用录音/音源）会使用 capture_sessions 或 audio_sources 中已存在的路径，这些路径目前也可能是本地路径。
- **变更内容**: 上传至 OSS `songs/` 目录，`audio_path` 存 OSS URL。
- **影响范围**: 后端；数据库 `songs.audio_path` 字段语义变更；前端播放音频链接需适配 OSS URL。

---

### 6. 歌曲音频文件回放

- **文件**: `controllers/songs_controller.py`
- **API**: `GET /api/songs/uploads/audio/<filename>`
- **核实结果**: ✅ 确认本地存储
  - 从 `backend/uploads/audio/` 读取音频文件
  - 通过 `send_file()` 返回
  - **无任何 OSS 调用**
- **变更内容**: 歌曲音频已迁移 OSS（功能 5）后，前端播放歌曲时直接使用 `songs.audio_path` 中的 OSS URL。此接口作为兼容层，前端仍通过此路径访问，但后端改为从 OSS 下载后返回（降级方案）。待前端确认已全面切换到 OSS URL 后，可废弃此接口。
- **影响范围**: 后端（兼容降级）；前端需逐步切换到 OSS URL。

---

### 7. 采集转录接口（⚠️ 已废弃，前端零调用，可删除）

- **文件**: `controllers/capture_controller.py`
- **API**: `PUT /api/capture/transcribe`
- **当前行为**: 通过 `song.get('audio_path')` 或 `session.get('file_path')` 获取本地路径，直接检查 `os.path.exists(file_path)` 并传入 transcriber。若 `audio_path` 已改为 OSS URL，此处会直接报 `Audio file not found`。
- **变更内容**: **此接口已废弃，前端零调用，无需迁移，可直接删除。**
- **影响范围**: 后端（删除接口）。

---

## 四、涉及的数据库字段变更

| 表名 | 字段 | 当前存储 | 迁移后存储 | 备注 |
|------|------|----------|------------|------|
| `songs` | `audio_path` | 本地绝对路径 或 `/api/uploads/audio/...` | OSS 公网 URL | 已有历史数据需迁移或兼容 |
| `songs` | `melody_path` | 本地绝对路径（`backend/outputs/...`）| OSS 公网 URL | |
| `songs` | `chord_path` | 本地绝对路径（`backend/outputs/...`）| OSS 公网 URL | |
| `capture_sessions` | `file_path` | 本地绝对路径 或 `/api/uploads/recordings/...` | OSS 公网 URL | |
| `audio_sources` | `file_path` | 混用：本地路径（来自录音）/ OSS URL（来自直传）| 统一为 OSS URL | 当前字段语义不一致，需清理 |
| `song_analysis` | `midi_path` | 本地绝对路径 | OSS 公网 URL | |
| `transcribe_tasks` | `result_path` | OSS URL | OSS URL | ✅ 已完成，无需变更 |

> ⚠️ **历史数据处理**：已存在的本地路径记录，需要编写数据迁移脚本：
> 1. 将本地文件上传 OSS；
> 2. 更新数据库中对应字段为 OSS URL；
> 3. 视情况保留或删除本地文件。
> 此部分为高风险操作，建议单独排期处理，不阻塞功能迁移。

---

## 五、前端配合事项

| 事项 | 涉及页面 | 说明 |
|------|----------|------|
| **统一通过 API 获取 OSS URL** | 全局（所有页面）| **新增**：前端获取任何文件的 OSS URL，统一调用 `GET /api/files/oss-url`，传入对应文件标识（song_id / session_id / audio_source_id 等）。禁止自行拼接 OSS 路径格式 |
| 音乐上传返回字段变更 | 音乐上传相关页面 | `POST /api/music/upload` 返回字段由 `file_path`（本地路径）改为 `file_url`（OSS URL），前端需适配 |
| 音频播放链接适配 | 歌曲列表/详情页 | `songs.audio_path` 改为 OSS URL，前端 `<audio>` 标签 src 直接使用该 URL，移除对 `/api/songs/uploads/audio/` 的拼接 |
| 录音回放链接适配 | `pages/recordings/` | `capture_sessions.file_path` 改为 OSS URL，前端直接使用该 URL，移除对 `/api/capture/uploads/recordings/` 的依赖 |
| MIDI 下载链接适配 | `pages/transcribe/` | 根据后端采用方案 A（302 重定向）或方案 B（直接 OSS URL），前端下载逻辑对应调整 |
| 移除废弃接口调用 | 全局 | `/api/capture/uploads/recordings/<filename>` 和 `/api/songs/uploads/audio/<filename>` 废弃后，前端不得再直接调用 |

---

## 六、API 变更

### 6.1 `POST /api/music/upload`

**请求**：无变化（multipart/form-data）

**响应变更**：

| 字段 | 旧 | 新 | 说明 |
|------|----|----|------|
| `file_path` | 本地绝对路径（如 `/home/.../uploads/music/abc.mp3`）| 废弃 | 移除 |
| `file_url` | 不存在 | OSS 公网 URL | 新增 |

### 6.2 `POST /api/capture/upload-file`

**响应变更**：

| 字段 | 旧 | 新 |
|------|----|----|
| `file_path` | 本地路径 | OSS 公网 URL |

### 6.3 `POST /api/songs/add`（multipart 分支）

**响应变更**：

| 字段 | 旧 | 新 |
|------|----|----|
| `audio_path` | `/api/uploads/audio/<filename>` | OSS 公网 URL |

### 6.4 `GET /api/music/download/midi/<filename>`

待定：方案 A 改为返回 `302 Location: <OSS 签名 URL>`；方案 B 接口废弃。需确认 Bucket 访问策略后决定。

### 6.5 `PUT /api/capture/transcribe`（⚠️ 已废弃，前端零调用，可删除）

**无需变更，接口直接删除。**

### 6.6 `GET /api/files/oss-url`（新增）

**功能**：前端通过文件标识查询对应的 OSS URL，无需自行拼接 OSS 路径格式。

**请求参数**（Query Parameters）：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `song_id` | int | 否 | 歌曲 ID，查询 `songs.audio_path` |
| `session_id` | int | 否 | 采集会话 ID，查询 `capture_sessions.file_path` |
| `audio_source_id` | int | 否 | 音源记录 ID，查询 `audio_sources.file_path` |
| `melody_path` | string | 否 | 查询 `songs.melody_path` |
| `chord_path` | string | 否 | 查询 `songs.chord_path` |

> **说明**：以上参数至少传入一个，后端根据传入的参数类型查询对应字段的 OSS URL。

**成功响应**（200）：

```json
{
  "url": "https://bucket.endpoint/audio-sources/xxx.mp3"
}
```

**异常响应**：

| 状态码 | 响应 | 说明 |
|--------|------|------|
| 400 | `{"error": "缺少文件标识参数"}` | 未传入任何查询参数 |
| 404 | `{"error": "文件不存在"}` | 对应记录不存在或路径为空 |
| 500 | `{"error": "查询失败"}` | 数据库或 OSS 查询异常 |

**前端调用示例**：

```javascript
// 通过 song_id 获取歌曲音频 OSS URL
const songResp = await fetch('/api/files/oss-url?song_id=123');
const { url: songUrl } = await songResp.json();

// 通过 session_id 获取录音 OSS URL
const sessResp = await fetch('/api/files/oss-url?session_id=456');
const { url: recUrl } = await sessResp.json();
```

**影响范围**：
- **新增**：后端在 `controllers/files_controller.py`（新建）中实现此接口。
- 前端所有需要播放/下载文件的地方，统一调用此接口获取 OSS URL，不再自行拼接路径。
- 配合第五章前端适配工作，统一替换所有本地文件访问路径。

---

## 七、实施计划

建议按以下顺序实施，风险从低到高：

| 优先级 | 步骤 | 说明 | 风险 |
|--------|------|------|------|
| 1 | 统一 `audio_sources.file_path` | 录音上传走 OSS（功能 3），audio_sources 创建改用 OSS URL | 低：仅影响新上传，历史数据不动 |
| 2 | 歌曲音频上传走 OSS（功能 5）| `songs.audio_path` 改存 OSS URL；前端播放链接适配 | 低 |
| 3 | 废弃本地文件服务接口（功能 4、6）| 确认前端不再依赖后，接口下线 | 低（需前端配合） |
| 4 | 音乐上传接口迁移 OSS（功能 1）| 返回字段变更，前端适配 | 低 |
| 5 | MIDI 下载接口重构（功能 2）| 确认 Bucket 策略后重构 | 中 |
| 6 | 历史数据迁移脚本 | 批量将历史本地文件上传 OSS，更新数据库字段 | 高：不可逆，须备份 |
| — | 删除废弃接口（功能 7）| `PUT /api/capture/transcribe` 前端零调用，直接删除 | 低 |

> **前置条件**：
> - OSS Bucket 已创建，`config.json` 中 `aliyunoss.endpoint` / `aliyunoss.bucket` 已配置；
> - `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` 环境变量已注入；
> - `oss2` 库已安装（`pip install oss2`）。

---

## 八、附：`aliyun_oss.py` 工具现有能力

| 函数 | 说明 |
|------|------|
| `upload_file(file_obj, directory, object_name)` | 上传文件（FileStorage 或本地路径）到指定目录，返回公网 URL |
| `download_file(object_name)` | 从 OSS 下载到 `uploads/oss_cache/`，返回本地临时路径 |
| `get_oss_url(object_name)` | 根据 object_name 生成公网 URL（不实际上传） |
| `file_exists(object_name)` | 检查 OSS 文件是否存在 |
| `list_files(directory)` | 列出 OSS 目录下所有文件 |

---

## 九、核实结论汇总

| # | 功能 | API | 核实结果 | 存储位置 |
|---|------|-----|----------|----------|
| 1 | 音乐文件上传 | `POST /api/music/upload` | ❌ 本地（未迁移） | `backend/uploads/music/` |
| 2 | MIDI 下载 | `GET /api/music/download/midi/...` | ❌ 本地（未迁移） | `outputs/` + `uploads/` |
| 3 | 采集录音上传 | `POST /api/capture/upload-file` | ❌ 本地（未迁移） | `backend/uploads/recordings/<date>/` |
| 4 | 采集录音回放 | `GET /api/capture/uploads/recordings/...` | ❌ 本地（未迁移） | `backend/uploads/recordings/` |
| 5 | 歌曲音频上传 | `POST /api/songs/add`（multipart） | ❌ 本地（未迁移） | `backend/uploads/audio/` |
| 6 | 歌曲音频回放 | `GET /api/songs/uploads/audio/...` | ❌ 本地（未迁移） | `backend/uploads/audio/` |

**结论**：之前文档中描述的"混用"情况不准确——实际上这 6 个接口**全部为本地存储**，没有任何 OSS 调用。OSS 工具类（`aliyun_oss.py`）存在且可用，但没有任何一个接口使用它。

---

> **状态**：本文档待技术协调负责人（Aemeath Manager）审核后提交 Edward 审批，批准前不进入实现阶段。
