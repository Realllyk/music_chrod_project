# Agent 接手说明

本文档面向即将接手本项目的另一个 agent。目标是让接手者快速理解项目在做什么、代码怎么分层、核心流程如何运转，以及继续开发时应该优先看哪些文件。

## 1. 项目目的

本项目是一个音乐音频管理与自动分析工具，围绕“音频来源 -> 歌曲/录音入库 -> 旋律或和弦转写 -> MIDI/结果文件输出”这条链路构建。

当前系统主要支持：

- 管理歌手、歌曲、音频源、系统录音会话。
- 上传或登记音频文件，并将文件保存到阿里云 OSS。
- 对歌曲音频发起异步转写任务，支持 `melody` 和 `chord` 两种模式。
- 使用 `librosa`、`spleeter`、`demucs` 等音频算法模块提取旋律/和弦，并生成 MIDI 文件。
- 通过 Windows 本地 agent 使用 WASAPI loopback 录制系统声音，再回传到 Flask 后端。
- 提供静态前端页面调用后端 API，完成上传、列表、详情、录音、转写等操作。

需要注意：仓库里很多旧文档和源码注释在当前环境显示为乱码，但实际目录、函数名、API 路径和业务结构仍然清晰。接手时请优先相信代码，其次参考本文档。

## 2. 技术栈与运行形态

- 后端：Python + Flask + Flask-CORS。
- 数据库：MySQL，通过 `PyMySQL` 直接访问。
- 对象存储：阿里云 OSS，工具封装在 `backend/utils/aliyun_oss.py`。
- 音频分析：`librosa`、`music21`、`pretty_midi`、`spleeter`、`demucs` 相关依赖。
- 前端：纯 HTML/CSS/JavaScript 静态页面，`fetch` 调 API。
- 本地录音 agent：Windows Python 程序，依赖 `pyaudiowpatch` 和 `requests`。

默认后端入口：

```bash
cd backend
python app.py
```

默认服务地址：

```text
http://localhost:5000
```

前端不是独立构建项目，页面文件在 `frontend/` 下，通常由 Flask 静态路由或本地静态服务访问。

## 3. 顶层目录结构

```text
music_chrod_project/
├── backend/                 # Flask 后端、业务服务、数据库 mapper、音频转写算法
├── frontend/                # 静态前端页面、公共 CSS 和 API JS 封装
├── agent/                   # Windows 系统音频录制 agent
├── docs/                    # 项目文档、历史规划、接口说明、修复记录
├── uploads/                 # 本地上传/缓存目录
├── outputs/                 # 本地输出目录，转写 MIDI 临时生成在这里
├── memory/                  # 历史记忆/记录
├── test_api.sh              # API 测试脚本
└── INDEX.md                 # 旧文档索引，当前环境可能乱码
```

## 4. 后端结构

后端入口是 `backend/app.py`。它完成以下工作：

- 读取 `backend/config.json`。
- 创建 Flask app 并开启 CORS。
- 根据配置创建 `uploads/`、`outputs/` 目录。
- 注册所有 controller blueprint。
- 在 `__main__` 中启动 Flask。

主要子目录：

```text
backend/
├── app.py                   # Flask 应用入口
├── config.json              # API、音频、转写、OSS、数据库配置
├── controllers/             # HTTP API 层
├── services/                # 业务服务层
├── mappers/                 # MySQL 表访问层
├── database/                # 数据库连接封装
├── transcriber/             # 转写算法抽象与实现
├── sources/                 # 音频来源抽象，如本地文件、Spotify
├── utils/aliyun_oss.py      # OSS 上传、下载、删除、列表、URL 解析
└── constants/               # 枚举常量
```

### Controller 分组

`backend/app.py` 当前注册了这些 blueprint：

- `health_controller`：健康检查、状态、数据库测试。
- `artists_controller`：歌手列表、详情、新增、更新、删除、头像更新。
- `songs_controller`：歌曲列表、详情、新增、更新、删除、音频文件访问。
- `audio_sources_controller`：音频源列表、OSS 文件列表、上传、详情、删除。
- `capture_controller`：录音会话启动、停止、保存、上传、列表、详情。
- `transcribe_controller`：创建转写任务、查询任务状态、查询歌曲任务。
- `sources_controller`：切换音频来源、搜索来源。
- `music_controller`：旧式音乐上传和 MIDI 下载接口。
- `files_controller`：按业务 ID 查询 OSS 文件 URL。
- `home_controller`：输出文件访问。

## 5. 核心 API 速查

健康检查：

```text
GET  /api/health
GET  /api/status
POST /api/db/test
```

歌手：

```text
GET    /api/artists/list
GET    /api/artists/<artist_id>
POST   /api/artists/add
PUT    /api/artists/<artist_id>
DELETE /api/artists/<artist_id>
PUT    /api/artists/<artist_id>/avatar
```

歌曲：

```text
GET    /api/songs/list
GET    /api/songs/<song_id>
POST   /api/songs/add
PUT    /api/songs/<song_id>
DELETE /api/songs/<song_id>
GET    /api/songs/uploads/audio/<filename>
```

音频源：

```text
GET    /api/audio-sources/list
GET    /api/audio-sources/oss-files
GET    /api/audio-sources/<audio_id>
POST   /api/audio-sources/upload
DELETE /api/audio-sources/<audio_id>
```

录音：

```text
POST   /api/capture/start
GET    /api/capture/active
PUT    /api/capture/request-recording
PUT    /api/capture/register-file
POST   /api/capture/upload-file
PUT    /api/capture/stop
GET    /api/capture/list
GET    /api/capture/detail/<session_id>
POST   /api/capture/start-recording
PUT    /api/capture/stop-recording
PUT    /api/capture/save
GET    /api/capture/recordings
DELETE /api/capture/sessions/<session_id>
PUT    /api/capture/sessions/<session_id>
GET    /api/capture/uploads/recordings/<filename>
```

转写：

```text
POST /api/transcribe/start
GET  /api/transcribe/status/<task_id>
GET  /api/transcribe/song/<song_id>
```

`POST /api/transcribe/start` 请求体示例：

```json
{
  "song_id": 1,
  "mode": "melody"
}
```

`mode` 可选值：

- `melody`：旋律提取。
- `chord`：和弦/复调提取。

## 6. 数据模型和持久化

数据库连接配置在 `backend/config.json` 的 `database` 节点，连接封装在 `backend/database/__init__.py`。

代码里可见的主要表：

- `artists`：歌手信息，支持软删除字段 `deleted_at`。
- `songs`：歌曲主表，包含音频路径、状态、session 关联、melody/chord 输出路径。
- `audio_sources`：上传或登记的音频源。
- `capture_sessions`：系统录音会话。
- `song_analysis`：歌曲分析结果。
- `transcribe_tasks`：异步转写任务状态。

主要 mapper：

- `backend/mappers/artists_mapper.py`
- `backend/mappers/songs_mapper.py`
- `backend/mappers/audio_sources_mapper.py`
- `backend/mappers/capture_mapper.py`
- `backend/mappers/song_analysis_mapper.py`

接手数据库相关问题时，建议从对应 service 读起，再下钻 mapper。服务层基本承担校验、状态转换和文件清理，mapper 只负责 SQL。

## 7. 文件与 OSS 流程

OSS 工具在 `backend/utils/aliyun_oss.py`，核心函数：

- `upload_file(file_obj, directory, object_name=None)`：上传本地文件或 Flask FileStorage 到 OSS。
- `download_file(path_or_url)`：把 OSS object 或 URL 下载到本地缓存。
- `get_oss_url(object_name)`：拼出公开 URL。
- `extract_object_name(path_or_url)`：从 URL 或 key 中提取 OSS object key。
- `delete_file(path_or_url)`：删除 OSS 文件。
- `list_files_with_prefix(prefix)`：列出某个 prefix 下的 OSS 文件。

运行涉及两个环境变量：

```text
OSS_ACCESS_KEY_ID
OSS_ACCESS_KEY_SECRET
```

如果没有这两个变量，上传、下载、列表、删除等 OSS 操作会失败。

常用 OSS 路径约定：

- `audio-sources/`：音频源文件。
- `recordings/`：录音文件。
- `transcribe/`：转写结果 MIDI。
- `transcribe/vocals/`：旋律提取时可能产生的人声分离结果。
- `avatars/`：歌手头像。

## 8. 转写核心流程

主要入口：`backend/controllers/transcribe_controller.py`。

流程如下：

1. 前端或调用方请求 `POST /api/transcribe/start`，传入 `song_id` 和 `mode`。
2. 后端创建 `transcribe_tasks` 记录，状态为 `pending`。
3. 后端启动后台线程 `run_transcription(task_id, song_id, mode)`。
4. 线程将任务状态更新为 `processing`，并将歌曲状态更新为 `processing`。
5. 通过 `SongsService.get_song_by_id(song_id)` 找到歌曲。
6. 从歌曲 `audio_path` 下载 OSS 音频到本地缓存。
7. 根据 `mode` 选择转写器：
   - `melody`：按配置优先使用 `demucs`，失败后可 fallback 到 `spleeter`、`librosa`。
   - `chord`：按 `config.json` 中 `transcription.algorithm.chord` 选择，当前默认 `librosa`。
8. 调用转写器提取结果。
9. 调用 `transcriber.save_midi(midi_path)` 生成 MIDI。
10. 上传 MIDI 到 OSS 的 `transcribe/`。
11. 更新 `songs.melody_path` 或 `songs.chord_path`，并将歌曲和任务状态置为 `completed`。
12. 清理本地临时音频、MIDI、人声分离文件。

关键抽象：

- `TranscriberBase`
- `MelodyTranscriberBase`
- `ChordTranscriberBase`

算法实现目录：

```text
backend/transcriber/librosa/
backend/transcriber/spleeter/
backend/transcriber/demucs/
```

## 9. Windows 录音 Agent

本地录音 agent 位于 `agent/agent.py`，目的不是替代后端，而是帮助后端拿到 Windows 系统声音。

核心机制：

- 使用 `pyaudiowpatch` 访问 WASAPI loopback 设备。
- 轮询后端 `/api/capture/active`。
- 当后端存在可录制 session 时，开始录制默认系统输出设备。
- 停止后写出 WAV 和 JSON 元数据。
- 调用 `/api/capture/register-file` 登记本地文件。
- 如后端要求上传，则调用 `/api/capture/upload-file` 上传 WAV。

常用命令：

```bash
cd agent
python agent.py --backend http://127.0.0.1:5000
python agent.py --list-devices
python agent.py --standalone
```

注意：当前 `agent/agent.py` 在部分位置可能存在乱码导致的字符串/变量问题，接手时建议先运行 `python -m py_compile agent/agent.py` 检查语法，再修复。

## 10. 前端结构

前端在 `frontend/`，没有复杂构建链路。

```text
frontend/
├── index.html
├── css/base.css
├── js/api.js              # fetch 封装：apiGet/apiPost/apiPostForm/apiPut/apiPutForm/apiDelete
├── js/menu.js             # 菜单/导航
└── pages/
    ├── artists/
    ├── songs/
    ├── audio-sources/
    ├── recordings/
    ├── transcribe/
    └── capture.html
```

`frontend/js/api.js` 中 `API_BASE = ''`，表示前端默认和后端同源。如果改成独立前端服务，需要同步设置 API base URL 或配置反向代理。

## 11. 配置重点

`backend/config.json` 是主要配置文件：

- `api.host`、`api.port`、`api.debug`：Flask 启动配置。
- `audio.sample_rate`、`audio.hop_length`、`audio.max_file_size`、`audio.allowed_formats`：音频处理配置。
- `transcription.melody`：旋律提取参数。
- `transcription.polyphonic`：复调/和弦相关参数。
- `transcription.algorithm.chord`：和弦算法选择，当前为 `librosa`。
- `transcription.vocal_separation`：人声分离 provider 和 fallback 顺序。
- `paths.uploads`、`paths.outputs`：本地目录。
- `aliyunoss.endpoint`、`aliyunoss.bucket`：OSS bucket 配置。
- `database`：MySQL 连接配置。

安全提醒：当前 `config.json` 中包含数据库连接信息。若项目要公开或交给外部 agent，应先迁移到环境变量或本地私有配置文件。

## 12. 接手建议

优先阅读顺序：

1. `backend/app.py`：确认应用入口和注册的模块。
2. `backend/config.json`：确认运行参数、数据库、OSS、算法策略。
3. `backend/controllers/transcribe_controller.py`：理解最核心的转写链路。
4. `backend/services/songs_service.py`、`backend/services/capture_service.py`、`backend/services/audio_sources_service.py`：理解业务状态流。
5. `backend/mappers/*.py`：确认实际 SQL 和表字段。
6. `backend/utils/aliyun_oss.py`：确认文件如何在本地与 OSS 之间流转。
7. `frontend/js/api.js` 和 `frontend/pages/*`：确认页面调用了哪些 API。
8. `agent/agent.py`：如果任务涉及系统录音，再深入这里。

开发时建议先做这些检查：

```bash
python -m py_compile backend/app.py
python -m py_compile backend/controllers/transcribe_controller.py
python -m py_compile agent/agent.py
```

然后启动后端并检查：

```bash
cd backend
python app.py
```

```bash
curl http://127.0.0.1:5000/api/health
curl http://127.0.0.1:5000/api/status
```

如果涉及 OSS，先确认环境变量和网络；如果涉及数据库，先调用 `/api/db/test` 或直接检查 `backend/database/__init__.py`。

## 13. 已知风险和容易踩坑

- 乱码问题：仓库中不少中文注释、文档、页面文本在当前环境里显示异常。修改业务逻辑时不要依赖乱码注释判断含义，优先读函数名、参数、SQL、API 路由。
- OSS 强依赖：转写流程会下载原音频、上传 MIDI。没有 OSS 凭证时核心流程会中断。
- 数据库强依赖：很多 API 直接依赖 MySQL。`database.enabled` 为 true 时，数据库不可达会导致列表、任务创建、状态更新失败。
- 后台线程：转写任务使用 Flask 进程内线程，不是 Celery/RQ。生产环境如果多进程部署或进程重启，任务状态可能不可靠。
- 本地临时文件：转写流程会在 `uploads/oss_cache` 和 `outputs/transcribe` 生成临时文件，finally 中会尝试清理。
- agent 仅适合 Windows：`pyaudiowpatch` 和 WASAPI loopback 是 Windows 场景，非 Windows 环境不要期望它工作。
- 依赖较重：`spleeter`、`tensorflow`、`demucs`、`torch` 相关依赖可能安装慢或平台敏感。Windows 另有 `requirements_windows_conda.txt` 和 `requirements_pytorch.txt` 可参考。
- 前端同源假设：`API_BASE = ''`，页面脱离 Flask 或反代后可能请求不到 API。

## 14. 常见任务落点

- 新增或修改 API：从 `backend/controllers/` 找对应 controller，再进入 `services/` 和 `mappers/`。
- 修歌曲字段或状态：看 `SongsService`、`SongsMapper`、`constants`。
- 修转写算法：看 `backend/transcriber/base.py` 和对应 provider 目录。
- 修 OSS 文件访问：看 `backend/utils/aliyun_oss.py`、`files_controller.py`。
- 修系统录音：看 `agent/agent.py` 和 `capture_controller.py`。
- 修前端页面：看 `frontend/pages/<module>/`、`frontend/js/api.js`、`frontend/css/base.css`。

## 15. 最小业务闭环

一个完整闭环大致是：

1. 上传音频或通过录音 agent 生成音频。
2. 音频保存到 OSS，并在数据库中产生 `audio_sources`、`capture_sessions` 或 `songs` 记录。
3. 创建或选择一首 `songs` 记录。
4. 调用 `/api/transcribe/start` 发起 `melody` 或 `chord` 转写。
5. 轮询 `/api/transcribe/status/<task_id>`。
6. 任务完成后，`songs.melody_path` 或 `songs.chord_path` 指向 OSS 上的 MIDI。
7. 前端展示状态，并通过 OSS URL 或下载接口拿到结果。

如果接手任务不明确，优先确认它属于“数据管理、文件/OSS、转写算法、录音 agent、前端页面”中的哪一类，再从上面的对应模块切入。
