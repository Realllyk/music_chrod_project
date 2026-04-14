# 前端 API 对齐分析

## 一、页面清单

| # | 页面 | 路由 | 调用 API |
|---|------|------|----------|
| 1 | 首页 | `/` | 无 |
| 2 | 录音采集 | `/capture` | `POST /api/capture/start-recording`、`PUT /api/capture/stop-recording`、`GET /api/capture/list?limit=20`、`DELETE /api/capture/sessions/{session_id}` |
| 3 | 录音文件管理 | `/recordings` | `GET /api/capture/list?limit=100`、`PUT /api/capture/sessions/{session_id}`、`DELETE /api/capture/sessions/{session_id}` |
| 4 | 歌曲列表 | `/songs` | `GET /api/songs/list?keyword=...`、`GET /api/songs/{id}` |
| 5 | 创建歌曲 | `/songs/add` | `GET /api/audio-sources/list?status=active`、`GET /api/artists/list`、`POST /api/songs/add` |
| 6 | 歌曲详情 | `/songs/details?id={id}` | `GET /api/songs/{id}`、`GET /api/artists/list`、`PUT /api/songs/{id}`、`DELETE /api/songs/{id}` |
| 7 | 歌手列表 | `/artists` | `GET /api/artists/list`、`GET /api/artists/{id}` |
| 8 | 新增歌手 | `/artists/add` | `POST /api/artists/add` |
| 9 | 歌手详情 | `/artists/details?id={id}` | `GET /api/artists/{id}`、`PUT /api/artists/{id}`、`DELETE /api/artists/{id}` |
| 10 | 音源管理 | `/audio-sources` | `GET /api/audio-sources/list` |
| 11 | 上传音源 | `/audio-sources/upload` | `POST /api/audio-sources/upload` |
| 12 | 歌曲提取 | `/transcribe` | `GET /api/songs/list?keyword=...`、`POST /api/transcribe/start`、`GET /api/transcribe/status/{task_id}` |

## 二、按模块分类

### 录音模块

- 页面：`/capture`
  - `POST /api/capture/start-recording`
  - `PUT /api/capture/stop-recording`
  - `GET /api/capture/list?limit=20`
  - `DELETE /api/capture/sessions/{session_id}`
- 页面：`/recordings`
  - `GET /api/capture/list?limit=100`
  - `PUT /api/capture/sessions/{session_id}`
  - `DELETE /api/capture/sessions/{session_id}`

**模块判断**
- 页面调用均落在 `/api/capture` 下，模块归属基本正确。
- 但接口方法、请求字段与后端存在不一致，详见第三部分。

### 歌曲模块

- 页面：`/songs`
  - `GET /api/songs/list?keyword=...`
  - `GET /api/songs/{id}`
- 页面：`/songs/add`
  - `POST /api/songs/add`
  - 依赖跨模块数据：`GET /api/audio-sources/list?status=active`、`GET /api/artists/list`
- 页面：`/songs/details?id={id}`
  - `GET /api/songs/{id}`
  - `PUT /api/songs/{id}`
  - `DELETE /api/songs/{id}`
  - 依赖跨模块数据：`GET /api/artists/list`

**模块判断**
- 核心 CRUD 均与 `/api/songs` 匹配。
- 歌曲创建/编辑依赖歌手、音源数据，属于合理跨模块调用。

### 歌手模块

- 页面：`/artists`
  - `GET /api/artists/list`
  - `GET /api/artists/{id}`
- 页面：`/artists/add`
  - `POST /api/artists/add`
- 页面：`/artists/details?id={id}`
  - `GET /api/artists/{id}`
  - `PUT /api/artists/{id}`
  - `DELETE /api/artists/{id}`

**模块判断**
- 页面调用与 `/api/artists` 模块一致。
- 未发现异常跨模块调用。

### 音源模块

- 页面：`/audio-sources`
  - `GET /api/audio-sources/list`
- 页面：`/audio-sources/upload`
  - `POST /api/audio-sources/upload`
- 被其他页面依赖：`/songs/add` 调用 `GET /api/audio-sources/list?status=active`

**模块判断**
- 页面调用与 `/api/audio-sources` 模块一致。
- 被歌曲模块依赖属于正常业务关联。

### 提取模块

- 页面：`/transcribe`
  - `POST /api/transcribe/start`
  - `GET /api/transcribe/status/{task_id}`
  - 依赖跨模块数据：`GET /api/songs/list?keyword=...`

**模块判断**
- 提取任务接口与 `/api/transcribe` 匹配。
- 通过歌曲列表选择待提取对象，属于合理跨模块调用。

## 三、对齐检查

| 问题 | 描述 | 建议 |
|------|------|------|
| `stop-recording` 请求方法不一致 | 旧文档曾记为 `POST /api/capture/stop-recording`，但后端当前实际定义为 `PUT /api/capture/stop-recording`。若仍按旧方法调用，会直接导致停止录音失败或 405。 | 前后端统一按 `PUT /api/capture/stop-recording` 对接，并清理所有旧的 `POST` 描述。 |
| 录音编辑字段名不一致 | `/recordings` 页面保存时提交 `{ file_name }` 到 `PUT /api/capture/sessions/{id}`；后端接口实际读取的是 `audio_name`。当前会触发 `audio_name is required`。 | 前端改为提交 `{ audio_name }`；同时页面展示字段命名也应统一。 |
| 录音列表字段使用不一致 | `/capture` 页面列表使用 `audio_name`；`/recordings` 页面列表使用 `file_name`。后端 `GET /api/capture/list` 返回字段若以 `audio_name` 为主，则 `/recordings` 页面会出现空值或展示异常。 | 统一录音会话 DTO 字段，建议前后端都使用 `audio_name`。如需保留 `file_name`，需后端显式兼容返回。 |
| 歌曲列表到详情存在冗余请求 | `/songs` 页面点击某首歌曲时先调用 `GET /api/songs/{id}`，跳转到详情页后 `/songs/details` 又再次调用 `GET /api/songs/{id}`。`sessionStorage` 中缓存的数据未真正减少请求。 | 二选一：1）列表页直接跳转，由详情页独立拉取；2）详情页优先读取 `sessionStorage`，仅在缺失时请求接口。 |
| 歌手列表到详情存在冗余请求 | `/artists` 页面点击歌手时先请求 `GET /api/artists/{id}`，详情页初始化后再次请求同一接口。 | 处理方式同上，去掉一次重复请求。 |
| 模块内存在历史接口并行，前端未统一使用 | 后端 `capture` 模块同时存在 `/start`、`/stop`、`/start-recording`、`/stop-recording`、`/save`、`/recordings` 等多套接口；前端目前只使用其中一部分。虽然不影响当前页面梳理，但会提高后续维护和对齐成本。 | 建议后端明确“当前正式接口集”，文档中标记废弃接口；前端只对接一套稳定接口。 |
| 跨模块调用存在但总体合理 | `/songs/add` 调用歌手、音源接口；`/songs/details` 调用歌手接口；`/transcribe` 调用歌曲列表接口。这些都属于业务依赖，不属于异常跨模块。 | 保持现状，但建议在接口文档中明确这些依赖关系，避免后续改动时漏改。 |

## 四、待确认项

1. `PUT /api/capture/stop-recording` 已是后端当前标准接口；前端与测试文档都应统一按 `PUT` 调用。
2. 录音会话统一字段名是否确定为 `audio_name`？当前前端页面内部已经出现 `audio_name` / `file_name` 两套命名。
3. `GET /api/capture/list` 的返回结构是否已有正式约定？建议明确会话列表返回字段，避免两个录音页面各自猜测字段名。
4. 列表页进入详情页时，是否保留“先预取详情再跳转”的交互方案？若无明确需要，建议删除预取请求。
5. 后端 `capture` 模块历史接口是否需要清理或标记废弃？否则后续文档和联调容易继续混用。

---

## 结论

- [x] 所有页面已列出
- [x] 按模块分类完成
- [x] 对齐问题已标记
- [x] 等待审批
