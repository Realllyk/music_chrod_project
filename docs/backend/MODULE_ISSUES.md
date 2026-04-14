# 后端 API 问题清单（按模块）

## 一、模块清单

### 1. 录音模块
- **功能**：
  - `POST /api/capture/start`：创建采集会话
  - `GET /api/capture/active`：获取当前活跃会话
  - `PUT /api/capture/request-recording`：请求进入录制状态
  - `PUT /api/capture/register-file`：登记已录制文件信息
  - `POST /api/capture/upload-file`：上传录音到 OSS，并自动创建音源记录
  - `PUT /api/capture/stop`：停止采集会话
  - `GET /api/capture/list`：获取录音会话列表
  - `GET /api/capture/detail/<session_id>`：获取录音会话详情
  - `POST /api/capture/start-recording`：简化版开始录音
  - `PUT /api/capture/stop-recording`：简化版停止录音
  - `PUT /api/capture/save`：保存录音文件名
  - `GET /api/capture/recordings`：获取可供创建歌曲的录音列表
  - `POST /api/capture/upload-wav`：上传 WAV/MP3 到本地目录
  - `DELETE /api/capture/sessions/<session_id>`：删除录音会话
  - `PUT /api/capture/sessions/<session_id>`：更新录音文件名等信息
  - `GET /api/capture/uploads/recordings/<filename>`：读取录音文件
  - `PUT /api/capture/transcribe`：直接对录音/歌曲音频执行识别
- **问题**：
  - 问题1：录音流程存在两套接口体系（`/start + /request-recording + /stop` 与 `/start-recording + /stop-recording`），语义重复，前端难以判断标准流程。
  - 问题2：录音上传存在两条路径：`/upload-file` 走 OSS 且自动创建音源，`/upload-wav` 走本地存储且不自动入库，副作用完全不同。
  - 问题3：`/api/capture/transcribe` 把提取逻辑放在录音模块内，造成职责越界。
  - 问题4：`CaptureSessionsMapper.update()` 只支持更新 `status/audio_name/file_path/duration_sec/ended_at`，但 `register_file()` 和自动建音源逻辑传入了 `sample_rate/channels/device_name`，这些字段实际不会落库。
  - 问题5：删除录音时用 `os.path.exists(file_path)` 处理文件，但 `file_path` 大多为 OSS URL，导致远端文件无法清理且逻辑判断失真。
  - 问题6：`transcribe_session()` 对 `session_id` 场景只读取 `file_path`，却仍会调用 `SongsService.update_song(song_id, ...)` 和 `SongsService.add_analysis(song_id, ...)`，当未传 `song_id` 时存在空 ID 写入风险。
- **解决方案**：
  - 方案1：统一录音流程，对外只保留一套正式 API；另一套标记为内部协作接口或兼容接口。
  - 方案2：统一录音上传策略，明确“正式上传”只走 OSS；本地上传接口若保留，应改名为临时调试接口并补充文档。
  - 方案3：将提取能力收敛到 `/api/transcribe/*`，录音模块只负责会话和文件管理。
  - 方案4：补齐 `CaptureSessionsMapper.update()` 可更新字段，确保 `sample_rate/channels/device_name` 等元数据真正入库。
  - 方案5：引入统一文件删除策略：本地路径走本地删除，OSS URL/object key 走 OSS 删除接口。
  - 方案6：重构 `capture/transcribe` 的输入约束：要么强制 `song_id`，要么支持纯 session 识别但禁止回写 songs 表。
- **HTTP 方法规范问题**：
  - 问题：会话状态与元数据更新接口已经切换为 `PUT`，但历史文档仍残留旧的 `POST` 描述，容易导致前端或测试脚本继续按过期方法调用。当前应以 `PUT /api/capture/request-recording`、`PUT /api/capture/register-file`、`PUT /api/capture/stop`、`PUT /api/capture/stop-recording`、`PUT /api/capture/save` 为准。另有 `PUT /api/capture/transcribe` 仍属于“触发识别任务”语义，更接近创建处理任务/触发动作，后续可评估是否改为 `POST`。
  - 解决方案：
    - 新增数据 → POST
    - 更新数据 → PUT
    - 删除数据 → DELETE
    - 同步清理所有旧的 `POST /api/capture/*` 方法描述，统一以当前代码实现为准；后续如继续收敛接口，可将会话状态、文件名等资源更新统一收敛到 `PUT /api/capture/sessions/<session_id>` 或等价更新接口。

### 2. 歌曲模块
- **功能**：
  - `GET /api/songs/list`：歌曲列表/关键词搜索
  - `GET /api/songs/<song_id>`：歌曲详情
  - `POST /api/songs/add`：创建歌曲，支持 multipart 上传、`session_id`、`audio_source_id`
  - `PUT /api/songs/<song_id>`：更新歌曲信息
  - `DELETE /api/songs/<song_id>`：删除歌曲
  - `GET /api/songs/uploads/audio/<filename>`：读取歌曲音频文件
- **问题**：
  - 问题1：创建歌曲同时兼容 multipart 上传、录音会话引用、音源引用三种模式，输入模型过于混杂。
  - 问题2：`SongsMapper.update()` 不支持更新 `audio_path/source/source_id/session_id`，但创建与提取流程又依赖这些字段，导致后续维护能力不足。
  - 问题3：`serve_audio()` 通过路径参数接收 `filename`，但实际保存的 `audio_path` 往往是完整 OSS URL，接口设计与数据形态不一致。
  - 问题4：删除歌曲只删数据库记录，不处理关联的 `song_analysis`、OSS 音频、MIDI 文件，容易留下脏数据。
  - 问题5：歌曲列表接口没有统一返回字段规范，搜索与普通列表虽都返回 `songs/total`，但内部字段依赖数据库原始结果，稳定性不足。
- **解决方案**：
  - 方案1：拆分歌曲创建场景，明确“上传新音频创建歌曲”和“基于已有音源创建歌曲”两种标准输入模型。
  - 方案2：扩展 `SongsMapper.update()` 支持完整业务字段，避免服务层能传、Mapper 层不能存。
  - 方案3：统一歌曲音频字段规范：数据库中明确保存 OSS URL 或 object key，文件访问接口按该规范设计。
  - 方案4：删除歌曲时补充级联清理策略，至少处理分析结果和关联文件引用。
  - 方案5：增加 DTO/序列化层，统一 songs 接口返回结构，避免直接暴露数据库字段细节。

### 3. 歌手模块
- **功能**：
  - `GET /api/artists/list`：歌手列表
  - `GET /api/artists/<artist_id>`：歌手详情
  - `POST /api/artists/add`：创建歌手，支持头像上传
  - `PUT /api/artists/<artist_id>`：更新歌手资料
  - `DELETE /api/artists/<artist_id>`：软删除歌手
  - `PUT /api/artists/<artist_id>/avatar`：单独更新头像
- **问题**：
  - 问题1：创建、更新、单独更新头像三处都在处理头像上传，逻辑重复。
  - 问题2：删除歌手采用软删除，但没有检查 songs 表中的关联歌曲，业务约束不明确。
  - 问题3：接口未做重名校验，可能出现重复歌手数据。
  - 问题4：软删除后未提供恢复能力，也未定义前端如何处理已绑定歌曲的歌手展示。
- **解决方案**：
  - 方案1：抽出统一的头像上传与参数校验逻辑，减少重复分支。
  - 方案2：补充删除前校验策略：若歌手已被歌曲引用，需阻止删除或改为“停用”状态。
  - 方案3：在 Service/Mapper 层增加名称唯一性校验，必要时增加数据库唯一索引。
  - 方案4：明确软删除后的展示和恢复规则，并补充相应接口或管理策略。

### 4. 音源模块
- **功能**：
  - `GET /api/audio-sources/list`：音源资产列表
  - `GET /api/audio-sources/oss-files`：列出 OSS 音源目录文件
  - `GET /api/audio-sources/<audio_id>`：音源详情
  - `DELETE /api/audio-sources/<audio_id>`：逻辑删除音源
  - `POST /api/audio-sources/upload`：上传音频并创建音源记录
  - `GET /api/sources`：获取可用音乐提供方列表
  - `PUT /api/sources/switch`：切换当前音乐提供方
  - `GET /api/sources/search`：使用当前提供方搜索音乐
- **问题**：
  - 问题1：`audio-sources` 与 `sources` 都被称为“音源”，一个是音频资产库，一个是搜索提供方，概念冲突严重。
  - 问题2：`AudioSourcesService.create_from_session()` 用 `os.path.exists(session['file_path'])` 取文件大小，但 `file_path` 常为 OSS URL，导致文件大小经常取不到。
  - 问题3：`AudioSourcesMapper.find_all()` 在 DictCursor 模式下返回 `len(results)` 作为 total，不是全量总数，分页总数不准确。
  - 问题4：`audio_sources_controller` 里混用了 Service 和 Mapper，层级不统一，例如上传直接调用 `AudioSourcesMapper.insert()`。
  - 问题5：删除音源仅改状态，不清理 OSS 文件，也未处理被歌曲引用的场景。
  - 问题6：`sources_controller.search_music()` 注释写 `GET /api/search`，但实际路径是 `/api/sources/search`，文档与实现不一致。
- **解决方案**：
  - 方案1：术语拆分，建议把 `sources_controller` 重命名为 `providers` 或 `music-providers`。
  - 方案2：统一音源文件元数据获取方式，不再依赖本地路径；文件大小、格式、时长应在上传后显式解析并存储。
  - 方案3：修正分页总数统计 SQL，确保返回真实 total。
  - 方案4：统一分层约束，Controller 只调 Service，禁止直接跨到 Mapper。
  - 方案5：补充引用校验和文件清理策略，防止“记录删了但文件还在/歌曲还在引用”。
  - 方案6：同步修正文档、注释和前端调用路径，避免继续沿用错误接口地址。
- **HTTP 方法规范问题**：
  - 问题：代码已经使用 `PUT /api/sources/switch` 更新当前激活的音乐提供方配置/状态，但历史文档仍有旧的 `POST` 写法，容易造成调用失败或对接误解。
  - 解决方案：
    - 新增数据 → POST
    - 更新数据 → PUT
    - 删除数据 → DELETE
    - 统一以 `PUT /api/sources/switch` 为正式接口，并同步修正文档、测试示例与调用方说明。

### 5. 提取模块
- **功能**：
  - `POST /api/transcribe/start`：创建提取任务并启动后台线程
  - `GET /api/transcribe/status/<task_id>`：查询任务状态
  - `GET /api/transcribe/song/<song_id>`：查询歌曲相关任务列表
  - 依赖 `SongsService`、`transcribe_tasks` 表、OSS 下载/上传、Librosa/Spleeter/Demucs 提取器
- **问题**：
  - 问题1：提取模块对外使用 `mode=melody/chord`，但录音模块 `capture/transcribe` 使用 `mode=melody/polyphonic`，枚举不一致。
  - 问题2：后台任务采用 Flask 进程内线程，服务重启后任务状态不可恢复，也缺少任务队列和并发控制。
  - 问题3：`run_transcription()` 调用 `SongsService.update_song(song_id, {'melody_path': ...})` 或 `{'chord_path': ...}`，虽然字段受支持，但不会更新歌曲状态为 processing/completed，任务状态与歌曲状态可能脱节。
  - 问题4：`get_song_tasks()` 直接返回数据库原始结果，缺少统一序列化，接口稳定性不足。
  - 问题5：算法选择分支没有兜底校验，若配置值异常，`transcriber` 变量可能未定义。
- **解决方案**：
  - 方案1：统一提取枚举，只保留 `melody` / `chord` 两种对外模式。
  - 方案2：把异步任务迁移到可持久化的任务系统（如 Celery/RQ/独立 worker），至少补充重试和状态恢复设计。
  - 方案3：建立任务状态与歌曲状态联动规则，例如提交任务时置为 `processing`，成功后置为 `completed`，失败时置为 `failed`。
  - 方案4：为任务查询接口增加固定返回结构和字段白名单。
  - 方案5：对配置算法做白名单校验，非法值直接返回明确错误而不是运行期异常。
- **HTTP 方法规范问题**：
  - 问题：`POST /api/transcribe/start` 用于创建提取任务，方法选择基本合理；但当前系统还存在 `PUT /api/capture/transcribe` 这种跨模块的识别触发接口，与本模块“创建任务用 POST”的规范不一致，容易让前后端误解“识别到底是更新资源还是发起任务”。本模块内未发现“应使用 PUT 却用了 POST”的更新类接口。
  - 解决方案：
    - 新增数据 → POST
    - 更新数据 → PUT
    - 删除数据 → DELETE
    - 建议统一把“发起识别/提取”定义为任务创建行为，全部收敛到 `POST /api/transcribe/*`；不要再用 `PUT` 表示启动识别，统一按 RESTful 规范对外暴露。

### 6. 其他（健康检查、文件服务、通用文件上传等）
- **功能**：
  - `GET /api/health`：服务健康检查
  - `GET /api/status`：应用状态和数据库状态
  - `POST /api/db/test`：测试数据库连接
  - `GET /health`：额外健康检查接口（来自 `home_controller`）
  - `GET /outputs/<filename>`：读取本地输出文件
  - `GET /api/files/oss-url`：按 song/session/audio_source 查询 OSS URL
  - `POST /api/music/upload`：通用音乐文件上传
  - `GET /api/music/download/midi/<filename>`：下载 MIDI 文件
- **问题**：
  - 问题1：健康检查存在 `/api/health` 与 `/health` 两套入口，职责重复。
  - 问题2：`health_controller.test_db()` 调用 `test_connection(data if data else None)`，但 `database.test_connection()` 不接收参数，实际签名不匹配。
  - 问题3：`DatabaseConnection` 只有静态 `get_connection()`，但 `status()` 中使用了 `db.config.enabled`，会触发属性不存在问题。
  - 问题4：文件服务分散在 capture、songs、music、files、home 多个 controller，消费者要自行判断路径规则。
  - 问题5：`music/download/midi` 从 `outputs/` 目录取文件，但提取模块上传 MIDI 到 OSS `transcribe/` 目录，下载路径和实际产物目录不一致。
  - 问题6：`/api/files/oss-url` 是聚合接口，但没有明确组合传参规则、优先级和标准返回结构。
- **解决方案**：
  - 方案1：对外只保留一个正式健康检查入口，另一条作为内部兼容接口并标注明确用途。
  - 方案2：修正数据库测试接口调用签名，统一为无参测试或支持显式传入临时配置。
  - 方案3：修复 `DatabaseConnection` 与 `status()` 的调用方式，避免运行期属性错误。
  - 方案4：收敛文件服务入口，统一文件解析、下载、预览规则。
  - 方案5：统一 MIDI 结果的存储目录和下载规则，避免“上传到 A、下载从 B” 的断链问题。
  - 方案6：补充 `/api/files/oss-url` 的接口契约文档，明确允许参数组合和返回字段。

## 二、待审批事项

1. **录音流程是否统一为单一标准接口**：确认保留“agent 协作流”还是“前端简化流”，或两者分别标记用途。
2. **录音文件是否统一使用 OSS 作为正式存储**：若确认，则 `upload-wav` 应降级为调试接口或废弃。
3. **提取能力是否全部收敛到 `/api/transcribe/*`**：若确认，则 `capture/transcribe` 需改为兼容层或移除。
4. **“音源模块”是否拆分术语**：`audio-sources` 作为音频资产，`sources` 改为 provider/provider-search。
5. **歌曲创建入口是否统一输入模型**：是否废弃 `session_id` 与 `audio_source_id` 双轨并存，改为单一 `audio_asset_id`。
6. **删除策略是否补充引用校验与文件清理**：涉及歌曲、录音、音源、分析结果的级联规则需要统一。
7. **异步提取是否升级为独立任务系统**：若短期不做，也需至少明确线程模型的风险接受范围。
8. **健康检查与文件服务是否做统一收口**：需要确认正式对外入口，避免前端继续依赖历史路径。
