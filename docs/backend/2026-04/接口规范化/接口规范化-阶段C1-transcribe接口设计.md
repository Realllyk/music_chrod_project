# 接口规范化 - 阶段 C1 transcribe 接口设计

## 1. 文档目标

本阶段面向 `backend/controllers/transcribe_controller.py` 做存量接口设计收敛，先输出 DTO / VO / Result 规范文档，**本次仅定义接口契约，不落地实现代码**。

覆盖接口：

1. `POST /api/transcribe/start`
2. `GET /api/transcribe/status/<task_id>`
3. `GET /api/transcribe/song/<song_id>`

设计依据：

- DTO 层统一使用 `BaseDTO + use_dto`
- 响应层统一使用 `Result.success(...)`
- 列表接口无分页时，直接返回 `list[TranscribeTaskVO]`，**不使用 `PageVO`**
- 路径参数也收敛为 Path DTO

---

## 2. 现状梳理

当前 `transcribe_controller.py` 的接口现状如下：

### 2.1 `POST /api/transcribe/start`

当前入参来源：
- `request.get_json()`
- 字段：`song_id`、`mode`

当前成功响应：

```json
{
  "ok": true,
  "task_id": "task_xxx",
  "message": "Task submitted"
}
```

问题：
- 未使用统一 `Result` 外层结构
- `status` 未返回，和目标接口约定不一致
- 参数校验为 controller 手写 if 分支

### 2.2 `GET /api/transcribe/status/<task_id>`

当前入参来源：
- 路径参数 `task_id`

当前成功响应：
- 直接返回 `_serialize_task(task)` 的裸对象

当前字段包括：
- `task_id`
- `song_id`
- `mode`
- `status`
- `result_path`
- `error`
- `created_at`
- `updated_at`
- 条件字段：`vocal_stem_path`

问题：
- 未使用统一 `Result`
- 路径参数未收敛为 DTO
- `progress` 当前 controller 未实际返回，需要在设计层明确兼容策略

### 2.3 `GET /api/transcribe/song/<song_id>`

当前入参来源：
- 路径参数 `song_id`

当前成功响应：

```json
{
  "tasks": [ ... ]
}
```

异常时响应：

```json
{
  "tasks": [],
  "error": "..."
}
```

问题：
- 成功与失败结构不统一
- 未使用 `Result`
- 路径参数未收敛为 DTO
- 返回列表应定义为 `list[TranscribeTaskVO]`

---

## 3. DTO 设计

## 3.1 文件建议

建议新增文件：

- `backend/pojo/dto/transcribe_dto.py`

建议包含以下 DTO：

- `StartTranscribeDTO`
- `TranscribeTaskIdPathDTO`
- `TranscribeSongIdPathDTO`

---

## 3.2 `POST /api/transcribe/start` DTO

### DTO 类名

`StartTranscribeDTO`

### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `song_id` | `int` | 是 | 目标歌曲 ID | `gt=0` |
| `mode` | `Literal['melody', 'chord']` | 是 | 提取模式 | 仅允许 `melody` / `chord` |

### 推荐定义

```python
class StartTranscribeDTO(BaseDTO):
    song_id: int = Field(..., gt=0, description='目标歌曲 ID')
    mode: Literal['melody', 'chord'] = Field(..., description='提取模式')
```

### 说明

- 文档层建议将 `mode` 设为**必填**，避免前后端对默认值理解不一致。
- 如果实现阶段要兼容旧前端，也可以临时保留默认值 `melody`，但规范接口仍建议前端显式传值。

---

## 3.3 `GET /api/transcribe/status/<task_id>` DTO

### DTO 类名

`TranscribeTaskIdPathDTO`

### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `task_id` | `str` | 是 | 转写任务 ID | 非空；`min_length=1`；建议以 `task_` 开头 |

### 推荐定义

```python
class TranscribeTaskIdPathDTO(BaseDTO):
    task_id: str = Field(..., min_length=1, description='转写任务 ID')
```

### 说明

- 当前系统 `task_id` 由 `task_{uuid12}` 生成。
- DTO 层可先做非空校验；若后续希望更严格，可增加正则：`^task_[a-z0-9]{12}$`。
- 鉴于历史数据兼容性，阶段 C1 文档先不强制正则。

---

## 3.4 `GET /api/transcribe/song/<song_id>` DTO

### DTO 类名

`TranscribeSongIdPathDTO`

### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `song_id` | `int` | 是 | 歌曲 ID | `gt=0` |

### 推荐定义

```python
class TranscribeSongIdPathDTO(BaseDTO):
    song_id: int = Field(..., gt=0, description='歌曲 ID')
```

---

## 4. VO 设计

## 4.1 文件建议

建议新增文件：

- `backend/pojo/vo/transcribe_vo.py`

建议包含以下 VO：

- `StartTranscribeVO`
- `TranscribeTaskVO`
- `SongTranscribeTasksVO`

其中：
- 单任务查询接口直接返回 `TranscribeTaskVO`
- 歌曲任务列表接口返回 `SongTranscribeTasksVO`
- `SongTranscribeTasksVO.tasks` 类型为 `list[TranscribeTaskVO]`

---

## 4.2 通用任务 VO

### VO 类名

`TranscribeTaskVO`

### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `task_id` | `str` | 是 | 任务 ID |
| `song_id` | `int` | 是 | 关联歌曲 ID |
| `mode` | `str` | 是 | 提取模式，当前取值 `melody` / `chord` |
| `status` | `str` | 是 | 任务状态，如 `pending` / `processing` / `completed` / `failed` |
| `progress` | `int \| None` | 否 | 任务进度百分比，0~100；当前存量实现暂无精确进度，可为空 |
| `result_path` | `str \| None` | 否 | 结果文件存储路径（OSS 或相对路径） |
| `error` | `str \| None` | 否 | 失败原因 |
| `vocal_stem_path` | `str \| None` | 否 | 人声分离文件路径，仅 melody 模式可能返回 |
| `created_at` | `str \| None` | 否 | 创建时间，ISO 8601 字符串 |
| `updated_at` | `str \| None` | 否 | 更新时间，ISO 8601 字符串 |

### 推荐定义

```python
class TranscribeTaskVO(BaseVO):
    task_id: str
    song_id: int
    mode: str
    status: str
    progress: int | None = None
    result_path: str | None = None
    error: str | None = None
    vocal_stem_path: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
```

### 字段来源说明

- `task_id` / `song_id` / `mode` / `status` / `result_path` / `error` / `created_at` / `updated_at`
  - 与当前 `_serialize_task(task)` 已有字段保持一致
- `vocal_stem_path`
  - 当前 controller 中仅在 `task.get('vocal_stem_path')` 存在时输出
- `progress`
  - 当前库表与 controller 未体现实际进度计算
  - 设计阶段先预留字段，规范允许返回 `null`
  - 后续如增加进度落库或线程内阶段映射，可直接填充，无需改前端契约

---

## 4.3 启动任务成功响应 VO

### VO 类名

`StartTranscribeVO`

### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `task_id` | `str` | 是 | 新创建的任务 ID |
| `status` | `str` | 是 | 初始任务状态，建议返回 `pending` |

### 推荐定义

```python
class StartTranscribeVO(BaseVO):
    task_id: str
    status: str
```

### 说明

- 当前实现成功后只返回 `task_id` 和 `message`。
- 规范化后应去掉 `ok` / `message` 这类非统一字段，改为：

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "task_id": "task_xxx",
    "status": "pending"
  }
}
```

---

## 4.4 歌曲任务列表响应 VO

### VO 类名

`SongTranscribeTasksVO`

### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `song_id` | `int` | 是 | 歌曲 ID |
| `tasks` | `list[TranscribeTaskVO]` | 是 | 当前歌曲下全部转写任务列表，按 `created_at desc` 排序 |

### 推荐定义

```python
class SongTranscribeTasksVO(BaseVO):
    song_id: int
    tasks: list[TranscribeTaskVO]
```

### 说明

- 这里使用 `tasks: list[TranscribeTaskVO]`。
- **明确不使用 `PageVO`**，因为当前接口无分页语义。
- 这样前端仍可以在 `result.tasks` 下获得稳定列表结构，同时补齐 `song_id` 方便页面上下文绑定。

---

## 5. 接口响应设计

## 5.1 `POST /api/transcribe/start`

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "task_id": "task_123abc456def",
    "status": "pending"
  }
}
```

### 失败响应示例

参数错误：

```json
{
  "code": 400,
  "description": "参数校验失败: song_id Field required",
  "result": {
    "errors": [ ... ]
  }
}
```

任务创建失败：

```json
{
  "code": 500,
  "description": "Failed to create task",
  "result": null
}
```

---

## 5.2 `GET /api/transcribe/status/<task_id>`

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "task_id": "task_123abc456def",
    "song_id": 12,
    "mode": "melody",
    "status": "processing",
    "progress": null,
    "result_path": null,
    "error": null,
    "vocal_stem_path": null,
    "created_at": "2026-04-21T21:00:00",
    "updated_at": "2026-04-21T21:01:00"
  }
}
```

### 失败响应示例

任务不存在：

```json
{
  "code": 404,
  "description": "Task not found",
  "result": null
}
```

---

## 5.3 `GET /api/transcribe/song/<song_id>`

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "song_id": 12,
    "tasks": [
      {
        "task_id": "task_a1",
        "song_id": 12,
        "mode": "melody",
        "status": "completed",
        "progress": 100,
        "result_path": "transcribe/12_melody_task_a1.mid",
        "error": null,
        "vocal_stem_path": "transcribe/vocals/12_task_a1.wav",
        "created_at": "2026-04-21T20:00:00",
        "updated_at": "2026-04-21T20:03:00"
      },
      {
        "task_id": "task_a2",
        "song_id": 12,
        "mode": "chord",
        "status": "failed",
        "progress": null,
        "result_path": null,
        "error": "Audio file not found",
        "vocal_stem_path": null,
        "created_at": "2026-04-21T19:00:00",
        "updated_at": "2026-04-21T19:01:00"
      }
    ]
  }
}
```

### 失败响应示例

参数错误：

```json
{
  "code": 400,
  "description": "参数校验失败: song_id Input should be greater than 0",
  "result": {
    "errors": [ ... ]
  }
}
```

数据库异常：

```json
{
  "code": 500,
  "description": "Internal server error",
  "result": null
}
```

---

## 6. API 对接表

| 方法 | 路径 | DTO | 成功响应 VO | 错误 code |
|---|---|---|---|---|
| `POST` | `/api/transcribe/start` | `StartTranscribeDTO` | `StartTranscribeVO` | `400` / `404` / `500` |
| `GET` | `/api/transcribe/status/<task_id>` | `TranscribeTaskIdPathDTO` | `TranscribeTaskVO` | `400` / `404` / `500` |
| `GET` | `/api/transcribe/song/<song_id>` | `TranscribeSongIdPathDTO` | `SongTranscribeTasksVO` | `400` / `500` |

### 错误码补充说明

#### `POST /api/transcribe/start`
- `400`：DTO 校验失败（如 `song_id` 缺失、`mode` 非法）
- `404`：若实现阶段补充歌曲存在性校验，可在歌曲不存在时返回
- `500`：任务创建失败、线程启动异常、数据库异常

#### `GET /api/transcribe/status/<task_id>`
- `400`：`task_id` 非法
- `404`：任务不存在
- `500`：数据库异常或系统异常

#### `GET /api/transcribe/song/<song_id>`
- `400`：`song_id` 非法
- `500`：数据库异常或系统异常

---

## 7. 字段对齐说明

本节用于明确前端如何从统一 `Result` 中读取字段，避免继续按旧裸结构访问。

## 7.1 通用规则

规范化后，所有接口都遵循：

```json
{
  "code": 200,
  "description": "success",
  "result": ...
}
```

因此前端读取规则统一为：

- 业务状态码：`resp.code`
- 描述信息：`resp.description`
- 业务数据：`resp.result`

**不要再直接访问旧结构顶层字段**，例如：
- 不要再用 `resp.task_id`
- 不要再用 `resp.tasks`
- 不要再用 `resp.ok`
- 不要再用 `resp.message`

---

## 7.2 启动任务接口字段路径

接口：`POST /api/transcribe/start`

前端应访问：

- 任务 ID：`resp.result.task_id`
- 初始状态：`resp.result.status`

示例：

```js
const taskId = resp.result.task_id;
const status = resp.result.status;
```

而不是：

```js
resp.task_id      // 旧结构，废弃
resp.message      // 旧结构，废弃
resp.ok           // 旧结构，废弃
```

---

## 7.3 查询任务状态接口字段路径

接口：`GET /api/transcribe/status/<task_id>`

前端应访问：

- 任务 ID：`resp.result.task_id`
- 歌曲 ID：`resp.result.song_id`
- 模式：`resp.result.mode`
- 状态：`resp.result.status`
- 进度：`resp.result.progress`
- 结果文件路径：`resp.result.result_path`
- 错误信息：`resp.result.error`
- 人声路径：`resp.result.vocal_stem_path`
- 创建时间：`resp.result.created_at`
- 更新时间：`resp.result.updated_at`

示例：

```js
const task = resp.result;
const status = task.status;
const progress = task.progress;
const resultPath = task.result_path;
const errorMsg = task.error;
```

### 关于 `progress`

- 阶段 C1 设计中保留 `progress` 字段。
- 在当前存量实现未支持精确进度前，前端必须允许它为 `null`。
- 前端展示建议：
  - `status === 'pending'`：显示“排队中”
  - `status === 'processing' && progress == null`：显示“处理中”
  - `status === 'completed'`：可视为 100%
  - `status === 'failed'`：显示失败与 `error`

---

## 7.4 查询歌曲任务列表接口字段路径

接口：`GET /api/transcribe/song/<song_id>`

前端应访问：

- 当前歌曲 ID：`resp.result.song_id`
- 任务列表：`resp.result.tasks`
- 单项任务状态：`resp.result.tasks[i].status`
- 单项任务结果路径：`resp.result.tasks[i].result_path`

示例：

```js
const songId = resp.result.song_id;
const tasks = resp.result.tasks || [];
const latestStatus = tasks[0]?.status;
```

而不是：

```js
resp.tasks        // 旧结构，废弃
resp.error        // 旧结构，废弃
```

---

## 7.5 `result_path` 字段含义对齐

`result_path` 在本阶段仍定义为**后端存储路径字段**，与 `songs_controller` 中 `audio_url / melody_url / chord_url` 的“公共可访问 URL”语义不同。

因此这里需要明确：

- `resp.result.result_path` 或 `resp.result.tasks[i].result_path`
  - 当前语义是后端记录的结果文件路径
  - 可能是 OSS object path，也可能是系统内部可解析路径
- 前端**不要默认把它当成可直接浏览器打开的 URL**
- 如果页面需要可下载地址，建议在后续阶段新增显式 URL 字段，例如：
  - `result_url`
  - 或由后端统一转换为公共访问地址

### 当前前端使用建议

- 列表展示：可直接显示 `status` / `mode` / `updated_at`
- 下载入口：在未新增 `result_url` 前，不应直接拼接 `result_path` 作为 href

该点属于 **待后续阶段确认**。

---

## 8. 实施建议（供后续阶段使用）

本节不是实现要求，只用于给后续阶段提供收敛方向。

### 8.1 建议新增 DTO

```python
class StartTranscribeDTO(BaseDTO):
    song_id: int = Field(..., gt=0)
    mode: Literal['melody', 'chord'] = Field(...)


class TranscribeTaskIdPathDTO(BaseDTO):
    task_id: str = Field(..., min_length=1)


class TranscribeSongIdPathDTO(BaseDTO):
    song_id: int = Field(..., gt=0)
```

### 8.2 建议新增 VO

```python
class StartTranscribeVO(BaseVO):
    task_id: str
    status: str


class TranscribeTaskVO(BaseVO):
    task_id: str
    song_id: int
    mode: str
    status: str
    progress: int | None = None
    result_path: str | None = None
    error: str | None = None
    vocal_stem_path: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class SongTranscribeTasksVO(BaseVO):
    song_id: int
    tasks: list[TranscribeTaskVO]
```

### 8.3 建议 controller 目标形态

- `POST /start`
  - `@use_dto(StartTranscribeDTO)`
  - 返回 `Result.success(StartTranscribeVO(...)).to_response()`
- `GET /status/<task_id>`
  - `@use_dto(TranscribeTaskIdPathDTO, source='path')`
  - 返回 `Result.success(TranscribeTaskVO.from_domain(...)).to_response()`
- `GET /song/<song_id>`
  - `@use_dto(TranscribeSongIdPathDTO, source='path')`
  - 返回 `Result.success(SongTranscribeTasksVO(...)).to_response()`

---

## 9. 结论

阶段 C1 对 `transcribe_controller` 的接口设计收敛结果如下：

1. 三个接口均已明确 DTO 命名、字段、校验规则
2. 三个接口均已明确统一 `Result` 包装下的成功响应 VO
3. 歌曲任务列表接口已明确采用 `list[TranscribeTaskVO]`，**不使用 `PageVO`**
4. 已明确前端字段访问路径均从 `result` 下读取
5. 已明确 `result_path` 当前是“路径”而非“可直接访问 URL”，该点需后续实现阶段继续对齐

本设计文档可作为阶段 C1 审批与后续阶段实现输入。