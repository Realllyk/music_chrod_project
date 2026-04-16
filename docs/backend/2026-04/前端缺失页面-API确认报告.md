# 前端缺失页面 - API 确认报告

**日期**：2026-04-16  
**范围**：对照《前端缺失页面清单》与后端当前 Flask controllers / services / mappers 实现，确认前端所需 API 的实际返回字段、缺失项与对接风险。  
**源码依据**：
- `backend/controllers/audio_sources_controller.py`
- `backend/controllers/capture_controller.py`
- `backend/controllers/transcribe_controller.py`
- `backend/controllers/songs_controller.py`
- `backend/controllers/health_controller.py`
- 辅助核对：`backend/services/*`、`backend/mappers/*`

---

## 一、结论摘要

### 1. 已有接口结论
- `/api/audio-sources/<audio_id>` `GET`：**接口已存在**，但字段名与前端需求**不完全一致**。
- `/api/audio-sources/<audio_id>` `DELETE`：**接口已存在**，成功仅返回 `{ok: true}`。
- `/api/capture/detail/<session_id>` `GET`：**接口已存在**，返回的是会话原始记录，字段名与前端需求**不完全一致**。
- `/api/capture/sessions/<session_id>` `PUT`：**接口已存在**，当前仅支持更新 `audio_name`。
- `/api/capture/sessions/<session_id>` `DELETE`：**接口已存在**，实现中包含“删文件 + 删 DB 记录”。
- `/api/transcribe/song/<song_id>` `GET`：**接口已存在**，返回结构为 `{ tasks: [...] }`，每个任务包含任务字段，但**不直接返回 `melody_url` / `chord_url`**。
- `/api/songs/<song_id>` `GET`：**接口已存在**，并且**明确返回 `melody_path`、`chord_path`，同时也返回 `melody_url`、`chord_url`**。
- `/api/status` `GET`：**接口已存在**，但当前只返回服务/数据库状态，**不返回歌曲数、歌手数、已完成转写数等统计字段**。

### 2. 重点结论：`/api/songs/<song_id>`
**明确结论：当前后端已经返回 `melody_path` 和 `chord_path` 字段。**  
同时还返回：
- `melody_url`
- `chord_url`

因此，歌曲详情页补全“转写结果”卡片时，前端**可直接使用 `melody_url` / `chord_url` 做下载链接**，`melody_path` / `chord_path` 可作为底层存储路径信息。

---

## 二、各 API 当前返回字段确认表

> **字段命名规则**：前端对接时以本报告"后端实际字段"列为准，不一致的字段在前端做映射处理。

## 1. `/api/audio-sources/<audio_id>` `GET`
**一句话说明：** 获取指定音源的详细信息，包括名称、格式、大小、时长、存储路径等。

### 当前实现
Controller：`audio_sources_controller.get_audio_source()`

### 实际返回字段
| 字段 | 当前是否返回 | 说明 |
|------|--------------|------|
| `id` | 是 | 音源 ID |
| `source_type` | 是 | 来源类型 |
| `source_id` | 是 | 来源业务 ID |
| `audio_name` | 是 | 音源名称；**对应前端需求中的 `name`** |
| `file_path` | 是 | 文件路径 / OSS URL |
| `file_size` | 是 | 文件大小；**对应前端需求中的 `size`** |
| `duration_sec` | 是 | 时长（秒） |
| `sample_rate` | 是 | 采样率 |
| `channels` | 是 | 声道数 |
| `format` | 是 | 文件格式 |
| `status` | 是 | 状态 |
| `created_at` | 是 | 创建时间；**可视作前端需求中的 `upload_time` 替代字段** |

### 与需求对比
| 需求字段 | 当前字段 | 结论 |
|----------|----------|------|
| `id` | `id` | 已满足 |
| `name` | `audio_name` | **字段名不一致** |
| `format` | `format` | 已满足 |
| `size` | `file_size` | **字段名不一致** |
| `upload_time` | `created_at` | **字段名不一致 / 语义近似** |

### 结论
- 接口存在。
- 前端需要的核心信息基本都能拿到。
- 但若前端按 `name / size / upload_time` 直接读取，**当前会拿不到，需要做字段映射或后端补齐别名字段**。

---

## 2. `/api/audio-sources/<audio_id>` `DELETE`
**一句话说明：** 删除指定音源，包括 OSS 文件和数据库记录，被歌曲引用时禁止删除。

### 当前实现
Controller：`audio_sources_controller.delete_audio_source()`  
Service：`AudioSourcesService.delete_audio_source()`

### 当前行为
1. 先查询音源是否存在。
2. 若不存在：返回 `404` / 业务失败（Controller 最终表现为 400 或 404 取决于调用路径，本接口这里实际是 service 返回失败后 controller 返回 `400`）。
3. 若该音源被歌曲表 `songs.audio_path` 引用：**禁止删除**，返回错误 `Audio source is referenced by songs and cannot be deleted`。
4. 若可删：
   - 先删除 OSS 文件（`delete_file(source_path)`）
   - 再删除 `audio_sources` 表记录
5. 删除成功返回：

```json
{
  "ok": true
}
```

### 删除后前端行为确认
| 项目 | 当前情况 |
|------|----------|
| 是否返回 `ok` | 是 |
| 是否返回删除后的跳转信息 | 否 |
| 是否返回剩余列表 / redirect URL | 否 |
| 是否可能删除失败 | 是，尤其是被歌曲引用时 |
| 前端是否需要自行跳回列表 | 是 |

### 结论
- 接口已存在。
- 前端删除成功后应：`alert/提示成功 → 跳回列表页 → 刷新列表`。
- 前端删除失败时要特别处理“已被歌曲引用，不可删除”的提示。

---

## 3. `/api/capture/detail/<session_id>` `GET`
**一句话说明：** 获取指定录音采集会话的完整详情，包括文件名、时长、采样率、文件路径、状态等。

### 当前实现
Controller：`capture_controller.get_session_detail()`  
Service：`CaptureService.get_session()`  
Mapper：`CaptureSessionsMapper.find_by_session_id()`

### 实际返回结构
该接口直接：
```python
return jsonify(session)
```
即直接返回数据库会话记录字典。

### 根据 controller / mapper 可确认的现有字段
| 字段 | 当前是否返回 | 说明 |
|------|--------------|------|
| `session_id` | 是 | 会话 ID |
| `source` | 是 | 采集来源 |
| `status` | 是 | 状态 |
| `audio_name` | 是 | 文件名；**对应前端需求中的 `filename`** |
| `file_path` | 是 | 录音路径 / OSS URL |
| `sample_rate` | 是 | 采样率 |
| `channels` | 是 | 声道数 |
| `duration_sec` | 是 | 时长（秒）；**对应前端需求中的 `duration`** |
| `device_name` | 可能返回 | 若保存过设备名 |
| `ended_at` | 可能返回 | 结束时间 |
| `created_at` | 是 | 创建时间（mapper 查询/排序已使用该字段） |

### 与需求对比
| 需求字段 | 当前字段 | 结论 |
|----------|----------|------|
| `session_id` | `session_id` | 已满足 |
| `filename` | `audio_name` | **字段名不一致** |
| `duration` | `duration_sec` | **字段名不一致** |
| `sample_rate` | `sample_rate` | 已满足 |
| `status` | `status` | 已满足 |
| `created_at` | `created_at` | 已满足 |

### 结论
- 接口存在。
- 前端详情页所需数据大部分可拿到。
- 但 `filename` / `duration` 当前并不是这个名字，前端需映射 `audio_name` / `duration_sec`。

---

## 4. `/api/capture/sessions/<session_id>` `PUT`
**一句话说明：** 更新录音会话的文件名（audio_name）。

### 当前实现
Controller：`capture_controller.update_session_info()`

### 请求要求
请求体读取：
- `audio_name`

若缺少则返回：
```json
{ "error": "audio_name is required" }
```

### 当前可修改字段
| 字段 | 是否可修改 | 说明 |
|------|------------|------|
| `audio_name` | 是 | 当前唯一明确支持的可修改字段 |
| `filename` | 否 | 不是接口字段名 |
| `status` | 否 | 本接口不处理 |
| `file_path` | 否 | 本接口不处理 |
| `sample_rate` | 否 | 本接口不处理 |

### 成功返回
```json
{
  "ok": true,
  "audio_name": "新的文件名"
}
```

### 结论
- 接口存在。
- **当前只支持修改文件名，字段名为 `audio_name`。**
- 若前端按需求文档中的“修改文件名”理解为传 `filename`，则会失败。

---

## 5. `/api/capture/sessions/<session_id>` `DELETE`
**一句话说明：** 删除指定录音会话，同时删除 OSS 文件和数据库记录。

### 当前实现
Controller：`capture_controller.delete_session()`

### 实际行为
1. 查询会话是否存在。
2. 若存在，读取 `file_path`。
3. 调用 `FileService.delete_path(file_path)` 删除文件（本地或 OSS）。
4. 调用 `CaptureService.delete_session(session_id)` 删除数据库记录。
5. 返回：

```json
{
  "ok": true
}
```

### 结论
| 确认项 | 结果 |
|--------|------|
| 删除录音文件 | 已实现 |
| 删除 DB 记录 | 已实现 |
| 删除成功返回 | `{ok: true}` |
| 删除后返回剩余资源信息 | 未提供 |

### 备注
- 文件删除异常被 `try/except` 吞掉，随后仍继续删 DB 记录。
- 这意味着“DB 删除成功但文件删失败”的情况，当前接口层不会暴露详细错误。

---

## 6. `/api/transcribe/song/<song_id>` `GET`
**一句话说明：** 查询指定歌曲下所有转写任务的列表及其状态/结果。

### 当前实现
Controller：`transcribe_controller.get_song_tasks()`

### 实际返回结构
返回格式不是单个任务对象，而是：

```json
{
  "tasks": [
    {
      "task_id": "...",
      "song_id": 1,
      "mode": "melody|chord",
      "status": "pending|processing|completed|failed",
      "result_path": "...",
      "error": "...",
      "created_at": "...",
      "updated_at": "...",
      "vocal_stem_path": "..."   // 仅部分 melody 任务可能有
    }
  ]
}
```

### 每个 task 当前可确认字段
| 字段 | 当前是否返回 | 说明 |
|------|--------------|------|
| `task_id` | 是 | 任务 ID |
| `song_id` | 是 | 歌曲 ID |
| `mode` | 是 | `melody` / `chord` |
| `status` | 是 | 任务状态 |
| `result_path` | 是 | 结果文件路径 / OSS URL |
| `error` | 是 | 失败时错误信息 |
| `created_at` | 是 | 创建时间 |
| `updated_at` | 是 | 更新时间 |
| `vocal_stem_path` | 条件返回 | 仅 melody 且存在人声分离结果时返回 |

### 与需求对比
| 需求项 | 当前情况 | 结论 |
|--------|----------|------|
| `task_id` | 有 | 已满足 |
| `mode` | 有 | 已满足 |
| `status` | 有 | 已满足 |
| `created_at` | 有 | 已满足 |
| `result_path` | 有 | 已满足 |
| `melody_url` | 无 | **未直接返回** |
| `chord_url` | 无 | **未直接返回** |

### 结论
- 接口存在。
- 当前适合历史页展示“任务列表”。
- 但**结果字段统一是 `result_path`，并不会按模式拆成 `melody_url` / `chord_url`**。
- 前端历史页若想展示下载按钮，应直接使用 `result_path`。

---

## 7. `/api/songs/<song_id>` `GET`
**一句话说明：** 获取指定歌曲的完整信息，包含音频路径、转写结果路径和公网访问 URL。

### 当前实现
Controller：`songs_controller.get_song()`  
序列化函数：`_serialize_song()`

### 实际返回字段
| 字段 | 当前是否返回 | 说明 |
|------|--------------|------|
| `id` | 是 | 歌曲 ID |
| `title` | 是 | 标题 |
| `artist_id` | 是 | 歌手 ID |
| `artist_name` | 可能返回 | 取决于查询结果是否带出该字段 |
| `category` | 是 | 分类 |
| `duration` | 是 | 时长 |
| `source` | 是 | 来源 |
| `source_id` | 是 | 来源 ID |
| `session_id` | 是 | 录音会话 ID |
| `audio_path` | 是 | 音频底层路径 |
| `audio_url` | 是 | 音频公网 URL |
| `melody_path` | 是 | **已返回** |
| `melody_url` | 是 | **已返回** |
| `chord_path` | 是 | **已返回** |
| `chord_url` | 是 | **已返回** |
| `status` | 是 | 状态 |
| `created_at` | 是 | 创建时间 |
| `updated_at` | 是 | 更新时间 |

### 重点确认：`melody_path` / `chord_path`
**结论：当前接口明确返回 `melody_path` 和 `chord_path`。不是待实现。**

### 是否有替代字段
有，且更适合前端直接使用：
- `melody_url`
- `chord_url`

### 前端建议
| 使用场景 | 推荐字段 |
|----------|----------|
| 展示“是否已有结果” | `melody_path` / `chord_path` 是否为空 |
| 下载链接 / 跳转链接 | `melody_url` / `chord_url` |

---

## 8. `/api/status` `GET`
**一句话说明：** 获取服务运行状态和数据库连接状态，不包含业务统计数字。

### 当前实现
Controller：`health_controller.status()`

### 实际返回字段
```json
{
  "status": "running",
  "timestamp": "2026-...",
  "database": {
    "enabled": true,
    "connected": true
  }
}
```

### 字段表
| 字段 | 当前是否返回 | 说明 |
|------|--------------|------|
| `status` | 是 | 服务运行状态 |
| `timestamp` | 是 | 当前时间 |
| `database.enabled` | 是 | 数据库是否启用 |
| `database.connected` | 是 | 数据库是否连接成功 |

### 与首页需求对比
| 需求项 | 当前情况 | 结论 |
|--------|----------|------|
| 歌曲数 | 无 | **待实现** |
| 歌手数 | 无 | **待实现** |
| 已完成转写数 | 无 | **待实现** |
| 其他统计数字 | 无 | **待实现** |

### 结论
- `/api/status` 当前不是“统计接口”，只是“健康状态接口”。
- 首页如果要展示统计卡片，当前后端**不能直接满足**。

---

## 三、已有字段清单 / 缺失字段清单

## 1. 已有字段清单

### `/api/audio-sources/<audio_id>`
已有：
- `id`
- `audio_name`
- `format`
- `file_size`
- `created_at`
- `file_path`
- `duration_sec`
- `sample_rate`
- `channels`
- `status`

### `/api/capture/detail/<session_id>`
已有：
- `session_id`
- `audio_name`
- `duration_sec`
- `sample_rate`
- `status`
- `created_at`
- `file_path`
- `source`
- `channels`
- `device_name`（条件）
- `ended_at`（条件）

### `/api/capture/sessions/<session_id>` `PUT`
已有能力：
- 可更新 `audio_name`

### `/api/capture/sessions/<session_id>` `DELETE`
已有能力：
- 删除录音文件
- 删除 DB 记录
- 返回 `{ok: true}`

### `/api/transcribe/song/<song_id>`
已有：
- `tasks[]`
- `task_id`
- `song_id`
- `mode`
- `status`
- `result_path`
- `error`
- `created_at`
- `updated_at`
- `vocal_stem_path`（条件）

### `/api/songs/<song_id>`
已有：
- `id`
- `title`
- `artist_id`
- `artist_name`
- `category`
- `duration`
- `source`
- `source_id`
- `session_id`
- `audio_path`
- `audio_url`
- `melody_path`
- `melody_url`
- `chord_path`
- `chord_url`
- `status`
- `created_at`
- `updated_at`

### `/api/status`
已有：
- `status`
- `timestamp`
- `database.enabled`
- `database.connected`

---

## 2. 缺失字段 / 待实现清单

## A. 字段名不一致（建议后端补齐别名或前端做映射）

| 接口 | 前端期望 | 后端当前 | 结论 |
|------|----------|----------|------|
| `/api/audio-sources/<audio_id>` | `name` | `audio_name` | 字段名不一致 |
| `/api/audio-sources/<audio_id>` | `size` | `file_size` | 字段名不一致 |
| `/api/audio-sources/<audio_id>` | `upload_time` | `created_at` | 字段名不一致 |
| `/api/capture/detail/<session_id>` | `filename` | `audio_name` | 字段名不一致 |
| `/api/capture/detail/<session_id>` | `duration` | `duration_sec` | 字段名不一致 |
| `/api/capture/sessions/<session_id>` `PUT` | `filename` | `audio_name` | 入参字段名不一致 |

## B. 字段缺失 / 需后端新增

| 接口 | 需求字段 | 当前情况 | 结论 |
|------|----------|----------|------|
| `/api/transcribe/song/<song_id>` | `melody_url` | 无 | 可不新增，前端可直接用 `result_path`；若想统一语义可后端补充 |
| `/api/transcribe/song/<song_id>` | `chord_url` | 无 | 可不新增，前端可直接用 `result_path`；若想统一语义可后端补充 |
| `/api/status` | `song_count` 等统计字段 | 无 | **待实现** |
| `/api/status` | `artist_count` | 无 | **待实现** |
| `/api/status` | `completed_transcribe_count` | 无 | **待实现** |

---

## 四、风险点与建议

## 1. 风险点

### 风险 1：前端按文档字段名直连会取不到值
最明显的有：
- `name` vs `audio_name`
- `size` vs `file_size`
- `upload_time` vs `created_at`
- `filename` vs `audio_name`
- `duration` vs `duration_sec`

如果前端不做字段映射，详情页会出现空值。

### 风险 2：`/api/transcribe/song/<song_id>` 是任务列表接口，不是“歌曲结果聚合接口”
它返回的是：
- `tasks[]`
- 每条任务一个 `result_path`

并不是：
- `melody_url`
- `chord_url`

因此历史页展示逻辑要按“任务维度”实现，而不能按歌曲详情接口的字段结构复用。

### 风险 3：`/api/status` 不能支撑首页统计卡片
当前只有健康检查信息，没有业务统计数字。  
首页若强依赖统计卡片，需要后端补接口或扩展 `/api/status`。

### 风险 4：音源删除存在引用约束
`DELETE /api/audio-sources/<audio_id>` 在音源被歌曲引用时会失败。  
前端不能默认“点删除必成功”，需要给出失败提示。

### 风险 5：录音删除的文件异常不会反馈给前端
`DELETE /api/capture/sessions/<session_id>` 中，文件删除异常被吞掉，随后仍会删除数据库记录。  
这会带来“数据库删了、对象存储残留文件”的潜在脏数据风险。

## 2. 建议

### 建议 1：短期由前端做字段映射，保证页面可先对接
建议映射关系：
- `audio_name -> name/filename`
- `file_size -> size`
- `created_at -> upload_time`
- `duration_sec -> duration`

### 建议 2：中期由后端统一补齐前端友好字段
例如：
- 音源详情接口同时返回 `name`、`size`、`upload_time`
- 录音详情接口同时返回 `filename`、`duration`
- 更新录音接口兼容 `filename` 入参

这样前端页面实现会更直接，也更符合需求文档。

### 建议 3：为首页新增统计接口，或扩展 `/api/status`
建议至少补齐：
- `song_count`
- `artist_count`
- `audio_source_count`
- `transcribe_task_count`
- `completed_transcribe_count`

### 建议 4：删除接口补充更明确的错误码 / 错误信息
尤其是：
- 音源被引用不可删除
- 录音文件删除失败但 DB 已删除

建议前后端统一错误响应约定。

---

## 五、前端对接注意事项

## 1. 音源详情页
- 不要直接读 `name`，当前应读 `audio_name`。
- 不要直接读 `size`，当前应读 `file_size`。
- 不要直接读 `upload_time`，当前应读 `created_at`。
- 音频预览建议使用 `file_path`（当前看起来就是 OSS URL / 可访问路径）。

## 2. 音源删除
- 成功只返回 `{ok: true}`，前端需自行返回列表页。
- 删除失败时注意展示后端返回的 `error`，尤其是“已被歌曲引用，不可删除”。

## 3. 录音详情页
- `filename` 当前应映射到 `audio_name`。
- `duration` 当前应映射到 `duration_sec`。
- 音频预览优先使用 `file_path`；若页面设计坚持走兼容播放路径，可拼 `/api/capture/uploads/recordings/<filename>`，但前提是本地/OSS对象名可对应。

## 4. 录音重命名
- 更新接口必须传：

```json
{
  "audio_name": "xxx.wav"
}
```

- 直接传 `filename` 当前不会生效。

## 5. 转写历史页
- 接口返回结构是：`{ tasks: [...] }`。
- 结果下载字段当前应使用 `task.result_path`。
- 如果要区分旋律/和弦，直接看 `mode`。

## 6. 歌曲详情页转写结果
- `melody_path` / `chord_path` 已可直接判断是否存在转写结果。
- 下载按钮建议使用 `melody_url` / `chord_url`，不要直接拼接下载地址。

## 7. 首页统计卡片
- 当前 `/api/status` 不能满足统计需求。
- 若前端暂时必须上线，可考虑先隐藏统计卡片，或临时改用多个 list 接口的 `total` 聚合，但会增加请求数。

---

## 六、后端验收清单

## P0：必须确认
- [x] `/api/songs/<song_id>` 已明确返回 `melody_path`
- [x] `/api/songs/<song_id>` 已明确返回 `chord_path`
- [x] `/api/songs/<song_id>` 已明确返回 `melody_url`
- [x] `/api/songs/<song_id>` 已明确返回 `chord_url`
- [x] `/api/transcribe/song/<song_id>` 已确认为任务列表结构 `{tasks: [...]}`
- [x] `/api/capture/sessions/<session_id>` `DELETE` 已确认删除文件 + 删除 DB 记录
- [x] `/api/capture/sessions/<session_id>` `PUT` 已确认仅支持 `audio_name`

## P1：建议后端补齐
- [ ] `/api/audio-sources/<audio_id>` 增加别名字段：`name`、`size`、`upload_time`
- [ ] `/api/capture/detail/<session_id>` 增加别名字段：`filename`、`duration`
- [ ] `/api/capture/sessions/<session_id>` `PUT` 兼容 `filename` 入参
- [ ] `/api/status` 增加业务统计字段：歌曲数、歌手数、转写任务数、已完成转写数

## P2：稳定性建议
- [ ] 录音删除接口补充文件删除失败的可观测错误信息
- [ ] 统一各模块字段命名风格，减少前端页面层映射成本
- [ ] 明确下载 / 预览优先使用 `*_url` 还是 `*_path`

---

## 七、最终结论

1. 本次核对的 8 个接口 / 能力点，**接口本身均已存在**。  
2. 真正的主要问题不是“接口不存在”，而是：
   - **字段名与前端需求文档不一致**
   - `/api/status` **缺少首页统计能力**
   - `/api/transcribe/song/<song_id>` 返回的是**任务列表结构**，不是聚合结果结构
3. **重点结论**：`/api/songs/<song_id>` 当前已经返回：
   - `melody_path`
   - `chord_path`
   - `melody_url`
   - `chord_url`
4. 因此歌曲详情页补全“转写结果”卡片，**后端无需新增该接口字段**；前端可以直接对接。
