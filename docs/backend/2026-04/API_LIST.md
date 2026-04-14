# 后端 API 清单

> 基于 `backend/app.py` 当前注册的 Flask Blueprint 与路由整理。
> 
> 说明：
> - 主要业务接口统一走 `/api/...`
> - 文档中同时保留了少量“兼容接口”和“非 /api 文件访问接口”，方便前端排查历史调用

## 健康检查模块

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/health` | 健康检查，确认服务是否运行 |
| GET | `/api/status` | 获取系统运行状态与数据库连接状态 |
| POST | `/api/db/test` | 测试数据库连接 |

## 音乐源模块（Provider / 搜索）

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/sources` | 获取可用音乐源列表及当前激活源 |
| PUT | `/api/sources/switch` | 切换当前音乐源（如 local_file / spotify） |
| GET | `/api/sources/search` | 使用当前激活音乐源搜索歌曲 |

## 音源资源模块（Audio Sources）

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/audio-sources/list` | 获取音源列表 |
| GET | `/api/audio-sources/oss-files` | 获取 OSS `audio-sources/` 目录文件列表 |
| GET | `/api/audio-sources/<audio_id>` | 获取单个音源详情 |
| DELETE | `/api/audio-sources/<audio_id>` | 删除指定音源 |
| POST | `/api/audio-sources/upload` | 上传音频文件并创建音源记录 |

## 录音采集模块（Capture）

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/capture/start` | 创建采集会话 |
| GET | `/api/capture/active` | 获取当前活跃采集会话 |
| PUT | `/api/capture/request-recording` | 请求开始录制（更新会话状态） |
| PUT | `/api/capture/register-file` | 注册已保存的录音文件 |
| POST | `/api/capture/upload-file` | 上传 WAV 录音文件到 OSS，并自动创建音源 |
| PUT | `/api/capture/stop` | 停止采集会话 |
| GET | `/api/capture/list` | 获取采集会话列表 |
| GET | `/api/capture/detail/<session_id>` | 获取采集会话详情 |
| POST | `/api/capture/start-recording` | 兼容接口：直接开始录音（创建会话并置为 recording） |
| PUT | `/api/capture/stop-recording` | 兼容接口：停止录音 |
| PUT | `/api/capture/save` | 保存录音名称 |
| GET | `/api/capture/recordings` | 获取可用于建歌的录音列表 |
| DELETE | `/api/capture/sessions/<session_id>` | 删除录音会话 |
| PUT | `/api/capture/sessions/<session_id>` | 更新录音会话信息（如文件名） |
| GET | `/api/capture/uploads/recordings/<filename>` | 获取录音文件（本地或 OSS 回源） |

## 歌手模块（Artists）

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/artists/list` | 获取歌手列表 |
| GET | `/api/artists/<artist_id>` | 获取单个歌手详情 |
| POST | `/api/artists/add` | 新增歌手（支持 JSON 或 multipart/form-data） |
| PUT | `/api/artists/<artist_id>` | 更新歌手信息（支持 JSON 或 multipart/form-data） |
| DELETE | `/api/artists/<artist_id>` | 删除歌手 |
| PUT | `/api/artists/<artist_id>/avatar` | 单独上传/更新歌手头像 |

## 歌曲模块（Songs）

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/songs/list` | 获取歌曲列表，支持关键词搜索 |
| GET | `/api/songs/<song_id>` | 获取单个歌曲详情 |
| POST | `/api/songs/add` | 新增歌曲（支持上传文件，或通过 `session_id` / `audio_source_id` 引用音频） |
| PUT | `/api/songs/<song_id>` | 更新歌曲信息 |
| DELETE | `/api/songs/<song_id>` | 删除歌曲 |
| GET | `/api/songs/uploads/audio/<filename>` | 兼容接口：获取歌曲音频文件，建议优先使用 `audio_url` |

## 转谱模块（Transcribe）

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/transcribe/start` | 启动转谱/提取任务（melody 或 chord） |
| GET | `/api/transcribe/status/<task_id>` | 查询转谱任务状态 |
| GET | `/api/transcribe/song/<song_id>` | 查询某首歌曲下的全部转谱任务 |

## 音乐文件模块（Music）

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/music/upload` | 上传音乐文件到 OSS |
| GET | `/api/music/download/midi/<filename>` | 下载 MIDI 文件 |

## 文件查询模块（Files）

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/files/oss-url` | 根据 `song_id` / `session_id` / `audio_source_id` 查询 OSS 文件 URL |

## 非 `/api` 文件访问接口

> 以下接口也由后端提供，但不在 `/api` 命名空间内。若前端仅对齐业务 API，可视情况忽略。

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/outputs/<filename>` | 获取输出目录下文件 |

## 汇总

- `/api` 业务接口总数：**36 个**
- 非 `/api` 文件接口：**1 个**
- 后端暴露端点总数：**37 个**

## 备注

1. `capture`、`songs` 中存在若干兼容层接口，前端新调用时建议优先采用更明确的新接口与返回字段。  
2. 文件访问类接口较多已经返回 OSS 公网地址，前端若已拿到 `audio_url` / `melody_url` / `chord_url` / `recording_url`，优先直接使用 URL。  
3. `transcribe` 当前 `mode` 仅支持：`melody`、`chord`。  
4. `files/oss-url` 要求 `song_id`、`session_id`、`audio_source_id` 三者必须且只能传一个。  
