# 后端 API 对齐分析

## 一、Controller 清单
| # | Controller | 模块 | API 端点 |
|---|------------|------|----------|
| 1 | `capture_controller` | 录音模块 | `POST /api/capture/start`<br>`GET /api/capture/active`<br>`PUT /api/capture/request-recording`<br>`PUT /api/capture/register-file`<br>`POST /api/capture/upload-file`<br>`PUT /api/capture/stop`<br>`GET /api/capture/list`<br>`GET /api/capture/detail/<session_id>`<br>`PUT /api/capture/transcribe`<br>`POST /api/capture/start-recording`<br>`PUT /api/capture/stop-recording`<br>`PUT /api/capture/save`<br>`GET /api/capture/recordings`<br>`POST /api/capture/upload-wav`<br>`DELETE /api/capture/sessions/<session_id>`<br>`PUT /api/capture/sessions/<session_id>`<br>`GET /api/capture/uploads/recordings/<filename>` |
| 2 | `songs_controller` | 歌曲模块 | `GET /api/songs/list`<br>`GET /api/songs/<song_id>`<br>`POST /api/songs/add`<br>`PUT /api/songs/<song_id>`<br>`DELETE /api/songs/<song_id>`<br>`GET /api/songs/uploads/audio/<filename>` |
| 3 | `artists_controller` | 歌手模块 | `GET /api/artists/list`<br>`GET /api/artists/<artist_id>`<br>`POST /api/artists/add`<br>`PUT /api/artists/<artist_id>`<br>`DELETE /api/artists/<artist_id>`<br>`PUT /api/artists/<artist_id>/avatar` |
| 4 | `audio_sources_controller` | 音源模块 | `GET /api/audio-sources/list`<br>`GET /api/audio-sources/oss-files`<br>`GET /api/audio-sources/<audio_id>`<br>`DELETE /api/audio-sources/<audio_id>`<br>`POST /api/audio-sources/upload` |
| 5 | `sources_controller` | 音源模块 | `GET /api/sources`<br>`PUT /api/sources/switch`<br>`GET /api/sources/search` |
| 6 | `transcribe_controller` | 提取模块 | `POST /api/transcribe/start`<br>`GET /api/transcribe/status/<task_id>`<br>`GET /api/transcribe/song/<song_id>` |
| 7 | `music_controller` | 跨模块/文件 | `POST /api/music/upload`<br>`GET /api/music/download/midi/<filename>` |
| 8 | `files_controller` | 跨模块/文件 | `GET /api/files/oss-url` |
| 9 | `health_controller` | 系统/运维 | `GET /api/health`<br>`GET /api/status`<br>`POST /api/db/test` |
| 10 | `home_controller` | 系统/静态文件 | `GET /health`<br>`GET /outputs/<filename>` |

> 说明：以上以 `app.py` 中实际注册的 Blueprint 为准。`health_controller` 与 `home_controller` 都提供健康检查，且路径不同。

## 二、按模块分类

### 录音模块
- `POST /api/capture/start`：创建采集会话
- `GET /api/capture/active`：获取当前活跃会话
- `PUT /api/capture/request-recording`：请求开始录制
- `PUT /api/capture/register-file`：登记已保存录音文件
- `POST /api/capture/upload-file`：上传录音文件到 OSS，并自动创建音源
- `PUT /api/capture/stop`：停止采集会话
- `GET /api/capture/list`：录音会话列表
- `GET /api/capture/detail/<session_id>`：录音会话详情
- `POST /api/capture/start-recording`：简化版开始录音
- `PUT /api/capture/stop-recording`：简化版停止录音
- `PUT /api/capture/save`：保存录音文件名
- `GET /api/capture/recordings`：获取可用于创建歌曲的录音列表
- `POST /api/capture/upload-wav`：上传 WAV/MP3 到本地 uploads
- `DELETE /api/capture/sessions/<session_id>`：删除录音会话
- `PUT /api/capture/sessions/<session_id>`：更新录音会话信息
- `GET /api/capture/uploads/recordings/<filename>`：读取录音文件

### 歌曲模块
- `GET /api/songs/list`：歌曲列表/搜索
- `GET /api/songs/<song_id>`：歌曲详情
- `POST /api/songs/add`：创建歌曲，支持上传文件、引用录音会话、引用音源
- `PUT /api/songs/<song_id>`：更新歌曲
- `DELETE /api/songs/<song_id>`：删除歌曲
- `GET /api/songs/uploads/audio/<filename>`：读取歌曲音频

### 歌手模块
- `GET /api/artists/list`：歌手列表
- `GET /api/artists/<artist_id>`：歌手详情
- `POST /api/artists/add`：创建歌手
- `PUT /api/artists/<artist_id>`：更新歌手
- `DELETE /api/artists/<artist_id>`：删除歌手
- `PUT /api/artists/<artist_id>/avatar`：单独更新头像

### 音源模块
#### A. 音源资产管理（`audio_sources_controller`）
- `GET /api/audio-sources/list`：音源列表
- `GET /api/audio-sources/oss-files`：列出 OSS 中的音源文件
- `GET /api/audio-sources/<audio_id>`：音源详情
- `DELETE /api/audio-sources/<audio_id>`：删除音源
- `POST /api/audio-sources/upload`：上传音源并创建记录

#### B. 音乐来源切换/搜索（`sources_controller`）
- `GET /api/sources`：可用音乐源列表（如 `local_file` / `spotify`）
- `PUT /api/sources/switch`：切换当前音乐源
- `GET /api/sources/search`：使用当前音乐源搜索音乐

### 提取模块
- `POST /api/transcribe/start`：启动提取任务（后台线程）
- `GET /api/transcribe/status/<task_id>`：查询任务状态
- `GET /api/transcribe/song/<song_id>`：查询歌曲相关提取任务
- `PUT /api/capture/transcribe`：对采集音频直接发起识别并回写歌曲结果

> 说明：`/api/capture/transcribe` 语义上属于提取模块，但实现放在录音模块中。

### 非本次五大业务模块，但会影响 API 对齐
- `POST /api/music/upload`：通用音乐文件上传
- `GET /api/music/download/midi/<filename>`：MIDI 下载
- `GET /api/files/oss-url`：跨歌曲/录音/音源的 OSS URL 查询
- `GET /api/health`、`GET /api/status`、`POST /api/db/test`：系统运维接口
- `GET /health`、`GET /outputs/<filename>`：系统/静态文件接口

## 三、语义歧义检查
| 问题 | 描述 | 建议 |
|------|------|------|
| 提取能力分散在两个模块 | `transcribe_controller` 负责异步任务式提取；`capture_controller` 里又有 `PUT /api/capture/transcribe` 负责同步提取并直接写歌曲。一个能力被拆成两套入口，调用方式和处理模式不同。 | 统一收敛到提取模块，保留一种主路径：建议以 `/api/transcribe/*` 为标准；录音模块只负责生成可提取的音频资源。 |
| “音源”概念被拆成两类 controller | `audio_sources_controller` 管理音频资产；`sources_controller` 管理“搜索来源/Provider 切换”。两者中文都叫“音源/音乐源”，容易混淆。 | 明确术语：`audio-sources` 表示“音频资产库”，`sources` 建议改名为 `providers` / `music-providers`。文档和前端文案同步调整。 |
| 文件上传入口重复 | 已存在 `POST /api/music/upload`、`POST /api/audio-sources/upload`、`POST /api/capture/upload-file`、`POST /api/capture/upload-wav`、`POST /api/songs/add`(multipart) 多种上传入口，职责有重叠。 | 按业务对象统一：歌曲上传归 songs，录音上传归 capture，资产上传归 audio-sources；若保留 `music/upload`，需明确它只是底层通用文件服务。 |
| 录音上传存在两套存储路径 | `/api/capture/upload-file` 上传到 OSS，并自动创建音源；`/api/capture/upload-wav` 保存到本地 uploads，且不自动创建音源。语义接近但副作用完全不同。 | 明确废弃其中一种，或拆成“本地临时上传”和“正式入库上传”两个清晰命名的 API。 |
| 录音流程 API 命名重复 | 同时存在 `/start` + `/request-recording` + `/stop`，又存在 `/start-recording` + `/stop-recording` 简化接口。功能相近但命名体系不一致。 | 选择一种流程模型。若保留两套，应在文档明确：一套是 agent 协作协议，一套是前端简化接口。 |
| 健康检查重复 | `GET /api/health` 与 `GET /health` 都返回健康检查，但归属不同、路径不同。 | 对外只保留一个正式健康检查入口；另一个标记为内部或兼容接口。 |
| 文件访问能力分散 | 录音文件读取在 `/api/capture/uploads/recordings/*`，歌曲音频读取在 `/api/songs/uploads/audio/*`，MIDI 下载在 `/api/music/download/midi/*`，OSS URL 查询在 `/api/files/oss-url`。 | 引入统一文件域设计：例如 `/api/files/audio/...`、`/api/files/midi/...`、`/api/files/resolve`，减少消费者判断成本。 |
| 歌曲创建跨录音/音源模块取数据 | `POST /api/songs/add` 可通过 `session_id` 从录音模块取文件，也可通过 `audio_source_id` 从音源模块取文件。歌曲创建逻辑依赖其他模块内部结构。 | 将“选择已有音频资产创建歌曲”沉淀为统一输入模型，例如只接受 `audio_asset_id`；避免 `session_id` 与 `audio_source_id` 双轨并存。 |
| 搜索接口路径与注释不一致 | `sources_controller.search_music` 注释写的是 `GET /api/search`，但实际注册路径是 `GET /api/sources/search`。 | 立即修正文档与注释，避免前端按旧路径对接。 |
| 提取 mode 命名不一致 | `transcribe_controller` 使用 `mode=melody/chord`；`capture_controller` 使用 `mode=melody/polyphonic`，内部再映射到 chord。 | 统一对外枚举值，建议只保留 `melody` / `chord`。 |
| 文件 URL 解析接口是跨模块聚合 | `GET /api/files/oss-url` 同时接受 `song_id`、`session_id`、`audio_source_id`，本质是跨模块文件解析层。虽实用，但会掩盖上游模块边界不清。 | 保留聚合接口，但需要明确它是“文件聚合服务”，并补充优先级、组合传参规则、返回字段规范。 |

## 四、待确认项
1. `capture_controller` 中的 `PUT /api/capture/transcribe` 是否计划保留？若保留，需要明确与 `/api/transcribe/start` 的边界。
2. “音源模块”是否要拆成两个正式模块：
   - 音频资产（audio assets）
   - 音乐提供方/搜索源（providers）
3. `POST /api/music/upload` 是否仍是前端正式依赖接口，还是历史遗留/通用工具接口？
4. 录音上传是否以 OSS 为唯一正式存储方案？若是，`/api/capture/upload-wav` 可考虑标记废弃。
5. 歌曲创建是否继续兼容 `session_id` 与 `audio_source_id` 双入口，还是统一为单一音频资产引用模型？
6. 对外标准健康检查路径是否确定为 `/api/health`？若确定，应将 `/health` 标记为内部兼容。
7. 提取模块对外标准术语是否统一为：`melody`（旋律）/`chord`（和弦）？若确定，应清理 `polyphonic` 命名。

---

## 完成状态
- [x] 所有 controller 已列出
- [x] 按模块分类完成
- [x] 语义歧义已标记
- [x] 等待审批
