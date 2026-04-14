# 后端问题修复报告（2026-04）

基于 `docs/backend/MODULE_ISSUES.md` 对后端已实现问题进行本轮修复收口。

## 本轮已完成

### 1. 录音模块
- 已明确 `POST /api/capture/start-recording`、`PUT /api/capture/stop-recording` 为**兼容接口**，正式流程仍为：
  - `POST /api/capture/start`
  - `PUT /api/capture/request-recording`
  - `PUT /api/capture/register-file`
  - `PUT /api/capture/stop`
- 修复 `CaptureSessionsMapper.update()` 字段缺失问题，已支持：
  - `sample_rate`
  - `channels`
  - `device_name`
  - 以及原有 `status/audio_name/file_path/duration_sec/ended_at`
- 删除录音时改为统一文件删除策略：
  - 本地路径 → 本地删除
  - OSS URL / object key → OSS 删除

### 2. 歌曲模块
- 修复 `SongsMapper.update()` 字段支持不完整问题，已补齐：
  - `source`
  - `source_id`
  - `audio_path`
  - `session_id`
- 歌曲列表/详情新增统一序列化输出，避免直接暴露不稳定数据库原始结构。
- `POST /api/songs/add` 的 JSON 引用创建分支已收紧输入：
  - `session_id` 与 `audio_source_id` 必须二选一
  - 禁止同时传或都不传
- 删除歌曲时增加关联清理：
  - 删除 `song_analysis`
  - 尝试清理 `audio_path / melody_path / chord_path` 对应文件
- `/api/songs/uploads/audio/<filename>` 明确为兼容层；正式消费建议直接使用返回的 `audio_url`。

### 3. 歌手模块
- 保留统一头像上传辅助函数，继续复用在：
  - 创建歌手
  - 更新歌手
  - 单独更新头像
- 新增歌手重名校验：
  - 创建重名返回 `409`
  - 更新为已存在名称返回 `409`
- 删除歌手前新增引用校验：
  - 若已有歌曲引用该歌手，阻止删除并返回错误

### 4. 音频资产模块（audio-sources）
- 修复 `AudioSourcesMapper.find_all()` 分页总数统计错误，`total` 现在返回真实总数而非分页结果长度。
- `audio_sources_controller` 上传分支已统一改为通过 `AudioSourcesService` 创建记录，不再直接写 Mapper。
- `AudioSourcesService.create_from_session()` 不再错误依赖 `os.path.exists(OSS URL)` 获取文件大小。
- 删除音频资产时新增：
  - 歌曲引用校验
  - 文件清理尝试

### 5. 提取模块
- 增加算法白名单校验，避免配置异常导致 `transcriber` 未定义。
- 任务状态与歌曲状态增加联动：
  - 任务开始 → `songs.status=processing`
  - 任务成功 → `songs.status=completed`
  - 任务失败 → `songs.status=failed`
- `GET /api/transcribe/status/<task_id>` 与 `GET /api/transcribe/song/<song_id>` 已改为统一序列化返回。
- MIDI 下载路径已兼容优先从 `transcribe/` 获取，回退旧 `outputs/`。

### 6. 健康检查与文件服务
- 修复 `/api/status` 中 `DatabaseConnection.config.enabled` 读取问题。
- 修复 `/api/db/test` 与 `database.test_connection()` 的签名不匹配问题。
- `/api/files/oss-url` 已补充接口约束：
  - `song_id / session_id / audio_source_id` 必须且只能传一个
  - `type` 仅允许：`audio / melody / chord / recording / source`
  - 返回统一包裹为 `{ resource, requested_type, data }`
- 新增统一文件服务 `services/file_service.py`，用于：
  - 公网 URL 解析
  - 本地/OSS 文件读取
  - 本地/OSS 文件删除

### 7. 文档/注释修正
- 修正 `sources_controller.search_music()` 注释路径为 `GET /api/sources/search`。

## 暂未在本轮彻底重构但已做收口说明
以下问题属于架构级优化，当前未做破坏性重构，只完成了风险收敛或兼容标注：

1. `capture/transcribe` 职责越界：当前代码库里本轮未发现对应有效路由实现，未新增该能力；后续应继续统一到 `/api/transcribe/*`。
2. 录音正式上传与本地调试上传双轨：本轮先保留兼容思路，未新增新的本地正式上传路径。
3. `audio-sources` 与 `sources` 术语冲突：本轮先修正文档/注释，路由未做破坏性改名。
4. 进程内线程任务模型：本轮只补状态联动与防御性校验，未迁移到独立任务系统。
5. 文件服务仍存在历史兼容入口：本轮新增统一 FileService，但外部路由暂未完全合并，以避免影响现有调用方。

## 涉及代码文件
- `backend/utils/aliyun_oss.py`
- `backend/services/file_service.py`
- `backend/mappers/capture_mapper.py`
- `backend/mappers/songs_mapper.py`
- `backend/mappers/audio_sources_mapper.py`
- `backend/database/__init__.py`
- `backend/services/audio_sources_service.py`
- `backend/services/songs_service.py`
- `backend/services/artists_service.py`
- `backend/controllers/artists_controller.py`
- `backend/controllers/audio_sources_controller.py`
- `backend/controllers/health_controller.py`
- `backend/controllers/files_controller.py`
- `backend/controllers/music_controller.py`
- `backend/controllers/songs_controller.py`
- `backend/controllers/capture_controller.py`
- `backend/controllers/transcribe_controller.py`
- `backend/controllers/sources_controller.py`

## 建议后续验证
1. 用真实 OSS 配置验证上传/删除/下载链路。
2. 回归测试以下接口：
   - `/api/files/oss-url`
   - `/api/transcribe/start`
   - `/api/music/download/midi/<filename>`
   - `/api/songs/add`
   - `/api/artists/add` / `PUT /api/artists/<id>` / `DELETE /api/artists/<id>`
   - `/api/audio-sources/delete`
3. 若准备进一步收敛架构，建议下一轮处理：
   - 文件访问统一路由
   - 提取任务系统外置
   - provider 术语改名
   - 历史兼容接口下线计划
