# 接口规范化 - 阶段 C2 capture 接口设计

## 1. 文档目标

本阶段面向 `backend/controllers/capture_controller.py` 做存量接口设计收敛，输出 `capture_controller` 的 DTO / VO / Result 规范文档，**本次仅定义接口契约，不落地实现代码**。

覆盖接口共 14 个：

### 1.1 Session 管理

1. `POST /api/capture/start`
2. `GET /api/capture/active`
3. `PUT /api/capture/stop`
4. `GET /api/capture/list`
5. `GET /api/capture/detail/<session_id>`
6. `DELETE /api/capture/sessions/<session_id>`
7. `PUT /api/capture/sessions/<session_id>`

### 1.2 Recording 控制

8. `PUT /api/capture/request-recording`
9. `POST /api/capture/start-recording`
10. `PUT /api/capture/stop-recording`
11. `PUT /api/capture/save`
12. `PUT /api/capture/register-file`
13. `POST /api/capture/upload-file`

### 1.3 录音回放

14. `GET /api/capture/recordings`
15. `GET /api/capture/uploads/recordings/<filename>`

> 说明：需求描述写“共 14 个”，但按实际列举为 **15 个端点**。本文档按用户给出的完整列表全部覆盖。

设计依据：

- DTO 层统一使用 `BaseDTO + use_dto`
- 响应层统一使用 `Result.success(...)`
- 列表分页接口使用 `PageVO`
- 路径参数同样收敛为 Path DTO
- **文件流接口成功时直接返回 `send_file()`，不包装 `Result`；失败时返回 `Result.xxx(...).to_response()`**

---

## 2. 现状梳理

当前 `capture_controller.py` 存在以下共性问题：

1. 大量接口仍使用 `request.get_json()` / `request.args` / `request.form` 手写解析
2. 成功响应均为裸 JSON，未统一 `Result` 三段式
3. 错误响应风格不统一：有的返回 `{error: ...}, 400`，有的返回裸对象，且部分成功响应包含 `ok` / `message` 等历史字段
4. `session_id`、`filename` 等路径 / query / body 参数未统一收敛为 DTO
5. 会话类接口与录音类接口有明显复用入参，但当前未做归类建模
6. 文件流接口需单独明确成功/失败响应规则，避免与 JSON API 混用

---

## 3. DTO 设计

## 3.1 文件建议

建议新增文件：

- `backend/pojo/dto/capture_dto.py`

建议按“入参相似性”而不是“每接口一个 DTO”进行归类，包含：

- `StartSessionDTO`
- `SessionIdDTO`
- `SessionIdPathDTO`
- `ListSessionsQueryDTO`
- `UpdateSessionDTO`
- `RequestRecordingDTO`
- `StartRecordingDTO`
- `StopRecordingDTO`
- `SaveRecordingDTO`
- `RegisterFileDTO`
- `UploadFileDTO`
- `RecordingFilePathDTO`
- `ListRecordingsQueryDTO`

---

## 3.2 Session 管理 DTO

### 3.2.1 `POST /api/capture/start`

#### DTO 类名

`StartSessionDTO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `source` | `str` | 否 | 采集来源 | `min_length=1`；默认 `system_loopback` |

#### 推荐定义

```python
class StartSessionDTO(BaseDTO):
    source: str = Field('system_loopback', min_length=1, description='采集来源')
```

### 3.2.2 `PUT /api/capture/stop`

#### DTO 类名

`SessionIdDTO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `session_id` | `str` | 是 | 会话 ID | `min_length=1` |

#### 推荐定义

```python
class SessionIdDTO(BaseDTO):
    session_id: str = Field(..., min_length=1, description='会话 ID')
```

### 3.2.3 `GET /api/capture/list`

#### DTO 类名

`ListSessionsQueryDTO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `limit` | `int` | 否 | 分页大小 | `ge=1`、`le=100`，默认 `50` |
| `offset` | `int` | 否 | 分页偏移量 | `ge=0`，默认 `0` |
| `status` | `str \| None` | 否 | 状态过滤 | 非空时 `min_length=1` |
| `source` | `str \| None` | 否 | 来源过滤（可选扩展） | 非空时 `min_length=1` |

#### 推荐定义

```python
class ListSessionsQueryDTO(BaseDTO):
    limit: int = Field(50, ge=1, le=100, description='分页大小')
    offset: int = Field(0, ge=0, description='分页偏移量')
    status: str | None = Field(None, min_length=1, description='状态过滤')
    source: str | None = Field(None, min_length=1, description='来源过滤')
```

### 3.2.4 `GET /api/capture/detail/<session_id>` / `DELETE /api/capture/sessions/<session_id>`

#### DTO 类名

`SessionIdPathDTO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `session_id` | `str` | 是 | 路径中的会话 ID | `min_length=1` |

#### 推荐定义

```python
class SessionIdPathDTO(BaseDTO):
    session_id: str = Field(..., min_length=1, description='路径中的会话 ID')
```

### 3.2.5 `PUT /api/capture/sessions/<session_id>`

#### DTO 类名

`UpdateSessionDTO`

#### 适用方式

- 路径参数：`session_id` 仍由 `SessionIdPathDTO` 承载
- 请求体：由 `UpdateSessionDTO` 承载

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `audio_name` | `str \| None` | 否 | 录音文件名 | 非空时 `min_length=1` |
| `source` | `str \| None` | 否 | 采集来源 | 非空时 `min_length=1` |
| `status` | `str \| None` | 否 | 会话状态 | 非空时 `min_length=1` |

#### 推荐定义

```python
class UpdateSessionDTO(BaseDTO):
    audio_name: str | None = Field(None, min_length=1, description='录音文件名')
    source: str | None = Field(None, min_length=1, description='采集来源')
    status: str | None = Field(None, min_length=1, description='会话状态')

    @model_validator(mode='after')
    def _validate_non_empty_update(self) -> 'UpdateSessionDTO':
        if self.audio_name is None and self.source is None and self.status is None:
            raise ValueError('至少提供一个可更新字段')
        return self
```

### 3.2.6 `GET /api/capture/active`

该接口无业务入参，**不强制定义 DTO**。实现阶段可直接返回当前活跃会话 VO。

如实现风格需要统一，也可定义空 DTO：

```python
class EmptyQueryDTO(BaseDTO):
    pass
```

但本文档不要求为无入参接口额外引入 DTO。

---

## 3.3 Recording 控制 DTO

### 3.3.1 `PUT /api/capture/request-recording`

#### DTO 类名

`RequestRecordingDTO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `session_id` | `str` | 是 | 目标会话 ID | `min_length=1` |

#### 推荐定义

```python
class RequestRecordingDTO(BaseDTO):
    session_id: str = Field(..., min_length=1, description='目标会话 ID')
```

> 说明：虽然它与 `SessionIdDTO` 字段相同，但该接口属于“录音控制语义”，实现阶段可二选一：
> - 若强调精简：直接复用 `SessionIdDTO`
> - 若强调语义可读性：单独保留 `RequestRecordingDTO`
>
> 本文档保留 `RequestRecordingDTO` 命名，方便 controller 代码语义表达。

### 3.3.2 `POST /api/capture/start-recording`

#### DTO 类名

`StartRecordingDTO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `source` | `str` | 否 | 采集来源 | `min_length=1`；默认 `system_loopback` |

#### 推荐定义

```python
class StartRecordingDTO(BaseDTO):
    source: str = Field('system_loopback', min_length=1, description='采集来源')
```

### 3.3.3 `PUT /api/capture/stop-recording`

#### DTO 类名

`StopRecordingDTO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `session_id` | `str \| None` | 否 | 会话 ID | 非空时 `min_length=1` |
| `audio_name` | `str \| None` | 否 | 录音文件名 | 非空时 `min_length=1` |

#### 推荐定义

```python
class StopRecordingDTO(BaseDTO):
    session_id: str | None = Field(None, min_length=1, description='会话 ID')
    audio_name: str | None = Field(None, min_length=1, description='录音文件名')
```

#### 说明

- 当前存量逻辑允许 `session_id` 为空，并自动回退到活跃会话。
- 因此设计阶段不强制 `session_id` 必填，但 service 层需明确：
  - 若 DTO 未传 `session_id` 且系统无活跃会话，返回 `400`。

### 3.3.4 `PUT /api/capture/save`

#### DTO 类名

`SaveRecordingDTO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `session_id` | `str` | 是 | 会话 ID | `min_length=1` |
| `audio_name` | `str` | 是 | 录音文件名 | `min_length=1` |

#### 推荐定义

```python
class SaveRecordingDTO(BaseDTO):
    session_id: str = Field(..., min_length=1, description='会话 ID')
    audio_name: str = Field(..., min_length=1, description='录音文件名')
```

#### 说明

- 当前实现会自动补 `.wav` 后缀。
- 设计层建议保留该兼容行为，但响应中应返回最终规范化后的 `audio_name`。

### 3.3.5 `PUT /api/capture/register-file`

#### DTO 类名

`RegisterFileDTO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `session_id` | `str` | 是 | 会话 ID | `min_length=1` |
| `audio_name` | `str \| None` | 否 | 文件名 | 非空时 `min_length=1` |
| `file_path` | `str \| None` | 否 | 文件存储路径 | 非空时 `min_length=1` |
| `duration_sec` | `float \| None` | 否 | 时长（秒） | `ge=0` |
| `sample_rate` | `int \| None` | 否 | 采样率 | `gt=0` |
| `channels` | `int \| None` | 否 | 声道数 | `ge=1` |

#### 推荐定义

```python
class RegisterFileDTO(BaseDTO):
    session_id: str = Field(..., min_length=1, description='会话 ID')
    audio_name: str | None = Field(None, min_length=1, description='文件名')
    file_path: str | None = Field(None, min_length=1, description='文件存储路径')
    duration_sec: float | None = Field(None, ge=0, description='时长（秒）')
    sample_rate: int | None = Field(None, gt=0, description='采样率')
    channels: int | None = Field(None, ge=1, description='声道数')
```

#### 说明

- 当前 controller 把 `data` 整体传入 `CaptureService.register_file(session_id, data)`。
- 规范化后建议显式声明常用字段，避免无约束 dict 透传。
- `extra='ignore'` 允许后续兼容新增元数据字段。

### 3.3.6 `POST /api/capture/upload-file`

#### DTO 类名

`UploadFileDTO`

#### 入参来源

- 默认 `multipart/form-data`
- 通过 `@use_dto(UploadFileDTO)` 走 `from_form`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `session_id` | `str` | 是 | 会话 ID | `min_length=1` |
| `audio_file` | `Any` | 是 | 上传的音频文件对象 | `FileStorage`，不能为空 |
| `audio_name` | `str \| None` | 否 | 自定义音频名称 | 非空时 `min_length=1` |

#### 推荐定义

```python
class UploadFileDTO(BaseDTO):
    session_id: str = Field(..., min_length=1, description='会话 ID')
    audio_file: Any = Field(..., description='上传的音频文件对象')
    audio_name: str | None = Field(None, min_length=1, description='自定义音频名称')

    @model_validator(mode='after')
    def _validate_file(self) -> 'UploadFileDTO':
        if self.audio_file is None:
            raise ValueError('audio_file is required')
        filename = getattr(self.audio_file, 'filename', '') or ''
        if not filename.strip():
            raise ValueError('audio_file filename is empty')
        return self
```

#### 说明

- 该接口属于**文件流接口**，成功时不走 `Result` 包装，详见第 6 节。
- 虽然当前存量实现成功后返回 JSON，但本阶段按任务要求收敛为“成功返回文件流”。

---

## 3.4 录音回放 DTO

### 3.4.1 `GET /api/capture/recordings`

#### DTO 类名

`ListRecordingsQueryDTO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `limit` | `int` | 否 | 返回条数 | `ge=1`、`le=200`，默认 `100` |
| `offset` | `int` | 否 | 偏移量 | `ge=0`，默认 `0` |
| `session_id` | `str \| None` | 否 | 会话过滤 | 非空时 `min_length=1` |
| `audio_name` | `str \| None` | 否 | 文件名模糊过滤 | 非空时 `min_length=1` |

#### 推荐定义

```python
class ListRecordingsQueryDTO(BaseDTO):
    limit: int = Field(100, ge=1, le=200, description='返回条数')
    offset: int = Field(0, ge=0, description='偏移量')
    session_id: str | None = Field(None, min_length=1, description='会话过滤')
    audio_name: str | None = Field(None, min_length=1, description='文件名过滤')
```

#### 说明

- 当前存量接口未显式支持分页，但查询语义是列表接口，设计阶段建议同步引入 `limit/offset`，便于后续统一。
- 若实现阶段为了兼容旧前端，也可先保留默认 `100` 的行为。

### 3.4.2 `GET /api/capture/uploads/recordings/<filename>`

#### DTO 类名

`RecordingFilePathDTO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 | 校验规则 |
|---|---|---:|---|---|
| `filename` | `str` | 是 | 录音文件名 | `min_length=1`；不得包含路径穿越片段 |

#### 推荐定义

```python
class RecordingFilePathDTO(BaseDTO):
    filename: str = Field(..., min_length=1, description='录音文件名')

    @field_validator('filename')
    @classmethod
    def _validate_filename(cls, value: str) -> str:
        if '..' in value or '/' in value or '\\' in value:
            raise ValueError('filename 非法，禁止路径穿越')
        return value
```

#### 说明

- 该接口属于**文件流接口**，成功时直接 `send_file()`。
- 路径参数必须做路径穿越防护。

---

## 4. VO 设计

## 4.1 文件建议

建议新增文件：

- `backend/pojo/vo/capture_vo.py`

建议包含以下 VO：

- `CaptureSessionVO`
- `ActiveCaptureSessionVO`
- `StartSessionVO`
- `RecordingActionVO`
- `SaveRecordingVO`
- `RegisterFileVO`
- `DeleteSessionVO`
- `UpdateSessionVO`
- `RecordingVO`
- `RecordingListVO`

其中：

- 会话详情 / 会话列表项统一使用 `CaptureSessionVO`
- 获取活跃会话可使用精简版 `ActiveCaptureSessionVO`
- 通用状态变更类接口可复用 `RecordingActionVO`
- 录音列表接口返回 `PageVO[RecordingVO]` 或 `RecordingListVO`

本文档优先推荐：
- `list sessions` 使用 `PageVO[CaptureSessionVO]`
- `recordings` 使用 `PageVO[RecordingVO]`

---

## 4.2 会话相关 VO

### 4.2.1 `CaptureSessionVO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `session_id` | `str` | 是 | 会话 ID |
| `source` | `str \| None` | 否 | 采集来源 |
| `status` | `str \| None` | 否 | 会话状态 |
| `audio_name` | `str \| None` | 否 | 录音文件名 |
| `file_path` | `str \| None` | 否 | 存储路径 |
| `duration_sec` | `float \| None` | 否 | 时长（秒） |
| `sample_rate` | `int \| None` | 否 | 采样率 |
| `channels` | `int \| None` | 否 | 声道数 |
| `created_at` | `str \| None` | 否 | 创建时间，ISO 8601 |
| `updated_at` | `str \| None` | 否 | 更新时间，ISO 8601 |

#### 推荐定义

```python
class CaptureSessionVO(BaseVO):
    session_id: str
    source: str | None = None
    status: str | None = None
    audio_name: str | None = None
    file_path: str | None = None
    duration_sec: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
```

#### 说明

- 该 VO 同时用于：
  - 会话详情
  - 会话列表项
  - 更新后返回的会话对象（如实现阶段希望增强返回信息）

### 4.2.2 `ActiveCaptureSessionVO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `session_id` | `str \| None` | 否 | 当前活跃会话 ID，无活跃会话时为 `null` |
| `status` | `str \| None` | 否 | 活跃会话状态，无活跃会话时为 `null` |
| `source` | `str \| None` | 否 | 采集来源 |

#### 推荐定义

```python
class ActiveCaptureSessionVO(BaseVO):
    session_id: str | None = None
    status: str | None = None
    source: str | None = None
```

#### 说明

- 当前实现“无活跃会话”时返回 200 而不是 404，此行为建议保留。
- 若后续前端需要更多上下文，也可直接改为返回 `CaptureSessionVO | None`，但本阶段保留精简结构更贴合现状。

### 4.2.3 `StartSessionVO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `session_id` | `str` | 是 | 新建会话 ID |
| `status` | `str` | 是 | 初始状态 |
| `source` | `str` | 是 | 采集来源 |
| `created_at` | `str \| None` | 否 | 创建时间 |

#### 推荐定义

```python
class StartSessionVO(BaseVO):
    session_id: str
    status: str
    source: str
    created_at: str | None = None
```

### 4.2.4 `DeleteSessionVO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `session_id` | `str` | 是 | 已删除会话 ID |
| `deleted` | `bool` | 是 | 是否删除成功 |

#### 推荐定义

```python
class DeleteSessionVO(BaseVO):
    session_id: str
    deleted: bool
```

### 4.2.5 `UpdateSessionResultVO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `session_id` | `str` | 是 | 会话 ID |
| `audio_name` | `str \| None` | 否 | 更新后的文件名 |
| `source` | `str \| None` | 否 | 更新后的采集来源 |
| `status` | `str \| None` | 否 | 更新后的状态 |

#### 推荐定义

```python
class UpdateSessionResultVO(BaseVO):
    session_id: str
    audio_name: str | None = None
    source: str | None = None
    status: str | None = None
```

---

## 4.3 录音控制相关 VO

### 4.3.1 `RecordingActionVO`

用于以下接口复用：

- `PUT /api/capture/request-recording`
- `POST /api/capture/start-recording`
- `PUT /api/capture/stop-recording`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `session_id` | `str` | 是 | 会话 ID |
| `status` | `str` | 是 | 操作后的状态 |
| `message` | `str \| None` | 否 | 提示信息；规范化后建议尽量少用 |

#### 推荐定义

```python
class RecordingActionVO(BaseVO):
    session_id: str
    status: str
    message: str | None = None
```

#### 说明

- 若实现阶段希望进一步统一，可去掉 `message`，仅保留 `session_id + status`。
- 但考虑前端兼容与历史接口文案，设计层允许 `message` 作为可选字段。

### 4.3.2 `SaveRecordingVO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `session_id` | `str` | 是 | 会话 ID |
| `audio_name` | `str` | 是 | 最终保存的文件名 |

#### 推荐定义

```python
class SaveRecordingVO(BaseVO):
    session_id: str
    audio_name: str
```

### 4.3.3 `RegisterFileVO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `session_id` | `str` | 是 | 会话 ID |
| `status` | `str` | 是 | 注册后的状态，建议 `recorded` |
| `audio_name` | `str \| None` | 否 | 文件名 |
| `file_path` | `str \| None` | 否 | 存储路径 |

#### 推荐定义

```python
class RegisterFileVO(BaseVO):
    session_id: str
    status: str
    audio_name: str | None = None
    file_path: str | None = None
```

---

## 4.4 录音回放相关 VO

### 4.4.1 `RecordingVO`

#### 字段定义

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `session_id` | `str` | 是 | 会话 ID |
| `audio_name` | `str \| None` | 否 | 录音文件名 |
| `file_path` | `str \| None` | 否 | 文件存储路径 |
| `duration_sec` | `float \| None` | 否 | 时长 |
| `created_at` | `str \| None` | 否 | 创建时间 |

#### 推荐定义

```python
class RecordingVO(BaseVO):
    session_id: str
    audio_name: str | None = None
    file_path: str | None = None
    duration_sec: float | None = None
    created_at: str | None = None
```

#### 说明

- 该 VO 面向“可供回放 / 选择音源”的录音列表场景。
- 当前 controller 未返回 `created_at`，但建议在规范接口中补齐，提升排序与展示一致性。

---

## 5. 接口响应设计

## 5.1 Session 管理

### 5.1.1 `POST /api/capture/start`

成功响应：

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "session_id": "cap_123abc",
    "status": "created",
    "source": "system_loopback",
    "created_at": "2026-04-22T00:00:00"
  }
}
```

### 5.1.2 `GET /api/capture/active`

有活跃会话：

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "session_id": "cap_123abc",
    "status": "recording",
    "source": "system_loopback"
  }
}
```

无活跃会话：

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "session_id": null,
    "status": null,
    "source": null
  }
}
```

### 5.1.3 `PUT /api/capture/stop`

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "session_id": "cap_123abc",
    "status": "stopped"
  }
}
```

### 5.1.4 `GET /api/capture/list`

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "items": [
      {
        "session_id": "cap_1",
        "source": "system_loopback",
        "status": "uploaded",
        "audio_name": "demo.wav",
        "duration_sec": 15.2,
        "created_at": "2026-04-22T00:00:00",
        "updated_at": "2026-04-22T00:01:00"
      }
    ],
    "total": 23,
    "limit": 50,
    "offset": 0
  }
}
```

### 5.1.5 `GET /api/capture/detail/<session_id>`

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "session_id": "cap_1",
    "source": "system_loopback",
    "status": "uploaded",
    "audio_name": "demo.wav",
    "file_path": "recordings/demo.wav",
    "duration_sec": 15.2,
    "sample_rate": 48000,
    "channels": 2,
    "created_at": "2026-04-22T00:00:00",
    "updated_at": "2026-04-22T00:01:00"
  }
}
```

### 5.1.6 `DELETE /api/capture/sessions/<session_id>`

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "session_id": "cap_1",
    "deleted": true
  }
}
```

### 5.1.7 `PUT /api/capture/sessions/<session_id>`

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "session_id": "cap_1",
    "audio_name": "new_name.wav",
    "source": "system_loopback",
    "status": "stopped"
  }
}
```

---

## 5.2 Recording 控制

### 5.2.1 `PUT /api/capture/request-recording`

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "session_id": "cap_1",
    "status": "recording_requested"
  }
}
```

### 5.2.2 `POST /api/capture/start-recording`

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "session_id": "cap_1",
    "status": "recording"
  }
}
```

### 5.2.3 `PUT /api/capture/stop-recording`

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "session_id": "cap_1",
    "status": "stopped"
  }
}
```

### 5.2.4 `PUT /api/capture/save`

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "session_id": "cap_1",
    "audio_name": "demo.wav"
  }
}
```

### 5.2.5 `PUT /api/capture/register-file`

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "session_id": "cap_1",
    "status": "recorded",
    "audio_name": "demo.wav",
    "file_path": "recordings/demo.wav"
  }
}
```

### 5.2.6 `POST /api/capture/upload-file`

> **注意**：该接口保持返回 JSON，不改为文件流。

成功时返回 `Result.success({ok, session_id, file_path})`：

```python
return send_file(local_path_or_downloaded_path)
```

失败示例：

```json
{
  "code": 404,
  "description": "Session not found",
  "result": null
}
```

---

## 5.3 录音回放

### 5.3.1 `GET /api/capture/recordings`

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "items": [
      {
        "session_id": "cap_1",
        "audio_name": "demo.wav",
        "file_path": "recordings/demo.wav",
        "duration_sec": 15.2,
        "created_at": "2026-04-22T00:00:00"
      }
    ],
    "total": 8,
    "limit": 100,
    "offset": 0
  }
}
```

### 5.3.2 `GET /api/capture/uploads/recordings/<filename>`

该接口为**文件流接口**：

- 成功：直接返回 `send_file(...)`
- 失败：返回 `Result.not_found(...).to_response()`

失败示例：

```json
{
  "code": 404,
  "description": "File not found",
  "result": null
}
```

---

## 6. 文件流接口说明

本阶段明确以下接口为**文件流接口**：

1. `GET /api/capture/uploads/recordings/<filename>`

> **说明**：`POST /api/capture/upload-file` 本质是"上传文件 + 返回结果"，不是下载，**保持返回 JSON**（`{ok, session_id, file_path}`），不改为文件流。

### 6.1 统一规则

#### 入参

- `serve_recording` 使用路径参数 DTO

#### 成功响应

- **直接返回 `send_file()`**
- **不包装 `Result.success(...)`**

#### 失败响应

- 使用统一错误结构：
  - `Result.bad_request(...).to_response()`
  - `Result.not_found(...).to_response()`
  - `Result.server_error(...).to_response()`

### 6.2 为什么文件流接口不包装 Result

原因与下载类 / 预览类接口一致：

1. `send_file()` 返回的是文件流 / 二进制响应，不是 JSON
2. 若外层再包 `Result`，前端无法直接消费音频流
3. 因此该类接口采用“成功直接流式返回，失败统一 JSON 错误”的混合模式

### 6.3 实现阶段约束

建议实现形态（`upload-file` — 返回 JSON）：

```python
@capture_controller.route('/upload-file', methods=['POST'])
@use_dto(UploadFileDTO)
def upload_file(dto: UploadFileDTO):
    session = CaptureService.get_session(dto.session_id)
    if not session:
        return Result.not_found('Session not found').to_response()

    # 处理上传、OSS 存储、创建音源等逻辑
    # ...
    return Result.success({
        'ok': True,
        'session_id': dto.session_id,
        'file_path': oss_url
    }).to_response()
```

建议实现形态（`serve_recording` — 文件流）：

```python
@capture_controller.route('/uploads/recordings/<filename>', methods=['GET'])
@use_dto(RecordingFilePathDTO, source='path')
def serve_recording(dto: RecordingFilePathDTO):
    local_path = ...
    if not local_path:
        return Result.not_found('File not found').to_response()
    return send_file(local_path)
```

---

## 7. API 对接表

| 方法 | 路径 | DTO | 成功响应 VO / 类型 | 备注 |
|---|---|---|---|---|
| `POST` | `/api/capture/start` | `StartSessionDTO` | `StartSessionVO` | 创建新会话 |
| `GET` | `/api/capture/active` | 无 | `ActiveCaptureSessionVO` | 无活跃会话时返回空对象，不报 404 |
| `PUT` | `/api/capture/stop` | `SessionIdDTO` | `RecordingActionVO` | 停止会话 |
| `GET` | `/api/capture/list` | `ListSessionsQueryDTO` | `PageVO[CaptureSessionVO]` | 分页列表 |
| `GET` | `/api/capture/detail/<session_id>` | `SessionIdPathDTO` | `CaptureSessionVO` | 会话详情 |
| `DELETE` | `/api/capture/sessions/<session_id>` | `SessionIdPathDTO` | `DeleteSessionVO` | 删除会话 |
| `PUT` | `/api/capture/sessions/<session_id>` | `SessionIdPathDTO` + `UpdateSessionDTO` | `UpdateSessionResultVO` | 更新会话信息 |
| `PUT` | `/api/capture/request-recording` | `RequestRecordingDTO` | `RecordingActionVO` | 请求录音权限 |
| `POST` | `/api/capture/start-recording` | `StartRecordingDTO` | `RecordingActionVO` | 兼容启动录音 |
| `PUT` | `/api/capture/stop-recording` | `StopRecordingDTO` | `RecordingActionVO` | 兼容停止录音 |
| `PUT` | `/api/capture/save` | `SaveRecordingDTO` | `SaveRecordingVO` | 保存录音文件名 |
| `PUT` | `/api/capture/register-file` | `RegisterFileDTO` | `RegisterFileVO` | 注册已保存文件 |
| `POST` | `/api/capture/upload-file` | `UploadFileDTO` | `{ok, session_id, file_path}` | `400 / 404 / 500` |
| `GET` | `/api/capture/recordings` | `ListRecordingsQueryDTO` | `PageVO[RecordingVO]` | 录音列表 |
| `GET` | `/api/capture/uploads/recordings/<filename>` | `RecordingFilePathDTO` | `send_file()` | **文件流接口** |

---

## 8. 错误码约定

## 8.1 通用错误码

| code | 含义 | 典型场景 |
|---|---|---|
| `200` | 成功 | 正常查询 / 更新 / 删除 / 返回文件流前的校验通过 |
| `400` | 参数错误 / 业务前置条件不满足 | `session_id` 缺失、`audio_name` 为空、无活跃会话、文件名非法 |
| `404` | 资源不存在 | 会话不存在、录音文件不存在 |
| `409` | 状态冲突 | 会话状态不允许当前操作，如重复开始录音 |
| `500` | 服务内部异常 | OSS 上传失败、下载失败、数据库异常、未知异常 |

## 8.2 各接口错误码建议

### Session 管理

| 接口 | 错误 code | 说明 |
|---|---|---|
| `POST /api/capture/start` | `400` / `500` | source 非法 / 创建会话失败 |
| `GET /api/capture/active` | `500` | 查询异常；无活跃会话不算错误 |
| `PUT /api/capture/stop` | `400` / `404` / `409` / `500` | `session_id` 缺失；会话不存在；状态冲突；系统异常 |
| `GET /api/capture/list` | `400` / `500` | 分页参数非法 / 查询失败 |
| `GET /api/capture/detail/<session_id>` | `400` / `404` / `500` | 路径参数非法 / 会话不存在 / 查询异常 |
| `DELETE /api/capture/sessions/<session_id>` | `400` / `404` / `500` | 路径参数非法 / 会话不存在 / 删除失败 |
| `PUT /api/capture/sessions/<session_id>` | `400` / `404` / `500` | 无可更新字段 / 会话不存在 / 更新失败 |

### Recording 控制

| 接口 | 错误 code | 说明 |
|---|---|---|
| `PUT /api/capture/request-recording` | `400` / `404` / `409` / `500` | session 不合法 / 会话不存在 / 状态不允许 / 系统异常 |
| `POST /api/capture/start-recording` | `400` / `409` / `500` | source 非法 / 已存在进行中录音 / 创建失败 |
| `PUT /api/capture/stop-recording` | `400` / `404` / `409` / `500` | 无可停止会话 / 会话不存在 / 状态冲突 / 系统异常 |
| `PUT /api/capture/save` | `400` / `404` / `500` | 参数缺失 / session 不存在 / 保存失败 |
| `PUT /api/capture/register-file` | `400` / `404` / `500` | 参数错误 / session 不存在 / 注册失败 |
| `POST /api/capture/upload-file` | `400` / `404` / `500` | multipart 不合法 / session 不存在 / 上传或回传文件失败 |

### 录音回放

| 接口 | 错误 code | 说明 |
|---|---|---|
| `GET /api/capture/recordings` | `400` / `500` | 分页参数非法 / 查询失败 |
| `GET /api/capture/uploads/recordings/<filename>` | `400` / `404` / `500` | 文件名非法 / 文件不存在 / OSS 下载异常 |

## 8.3 错误描述建议

建议错误描述保持稳定、短句、可读：

- `Session not found`
- `Invalid session_id`
- `audio_name is required`
- `No active session`
- `filename 非法，禁止路径穿越`
- `OSS upload failed`
- `File not found`

避免：

- 暴露底层堆栈
- 拼接过长英文异常全文
- 返回前端难以消费的 Python 原始异常结构

---

## 9. 字段对齐说明

## 9.1 前端统一读取规则

规范化后，除文件流接口外，其余接口统一返回：

```json
{
  "code": 200,
  "description": "success",
  "result": ...
}
```

前端应统一从 `result` 读取业务数据：

- 不再读取 `resp.ok`
- 不再读取 `resp.message` 作为核心状态字段
- 不再读取裸顶层 `session_id` / `sessions` / `recordings`

## 9.2 会话列表字段路径

前端应访问：

- 列表：`resp.result.items`
- 总数：`resp.result.total`
- 单项会话 ID：`resp.result.items[i].session_id`
- 单项状态：`resp.result.items[i].status`

## 9.3 录音列表字段路径

前端应访问：

- 列表：`resp.result.items`
- 文件名：`resp.result.items[i].audio_name`
- 存储路径：`resp.result.items[i].file_path`
- 时长：`resp.result.items[i].duration_sec`

## 9.4 文件流接口处理方式

对于以下接口：

- `POST /api/capture/upload-file`
- `GET /api/capture/uploads/recordings/<filename>`

前端必须按“文件响应”处理，而不是按 JSON 读取 `resp.result`：

- 成功：读取二进制 / blob / audio stream
- 失败：按 JSON `Result` 结构处理

这意味着前端调用层需要根据 `content-type` 或 HTTP 状态分支处理响应。

---

## 10. 实施建议（供后续阶段使用）

> 本节不是实现要求，只作为后续阶段的落地参考。

### 10.1 建议 DTO 归类

```python
class StartSessionDTO(BaseDTO):
    ...

class SessionIdDTO(BaseDTO):
    ...

class ListSessionsQueryDTO(BaseDTO):
    ...

class SessionIdPathDTO(BaseDTO):
    ...

class UpdateSessionDTO(BaseDTO):
    ...

class RequestRecordingDTO(BaseDTO):
    ...

class StartRecordingDTO(BaseDTO):
    ...

class StopRecordingDTO(BaseDTO):
    ...

class SaveRecordingDTO(BaseDTO):
    ...

class RegisterFileDTO(BaseDTO):
    ...

class UploadFileDTO(BaseDTO):
    ...

class ListRecordingsQueryDTO(BaseDTO):
    ...

class RecordingFilePathDTO(BaseDTO):
    ...
```

### 10.2 建议 VO 归类

```python
class CaptureSessionVO(BaseVO):
    ...

class ActiveCaptureSessionVO(BaseVO):
    ...

class StartSessionVO(BaseVO):
    ...

class RecordingActionVO(BaseVO):
    ...

class SaveRecordingVO(BaseVO):
    ...

class RegisterFileVO(BaseVO):
    ...

class DeleteSessionVO(BaseVO):
    ...

class UpdateSessionResultVO(BaseVO):
    ...

class RecordingVO(BaseVO):
    ...
```

### 10.3 controller 目标形态

- JSON / query 接口：统一 `@use_dto(...) + Result.success(...).to_response()`
- 路径参数接口：使用 Path DTO
- 文件流接口：`@use_dto(...)` 做参数校验，成功 `send_file()`，失败 `Result.xxx(...).to_response()`

---

## 11. 结论

阶段 C2 对 `capture_controller` 的接口设计收敛结果如下：

1. 已按“入参相似性”完成 DTO 分组，而非为每个接口机械定义独立 DTO
2. 已定义 `CaptureSessionVO`、`RecordingVO` 等核心响应对象
3. 已完成 15 个 capture 相关端点的 API 对接表整理
4. 已明确 `upload-file` 与 `serve_recording` 为文件流接口：**成功不包装 Result，失败统一走 Result 错误结构**
5. 已补充分页、路径安全、状态冲突、错误码约定等后续实现必须遵循的边界

本设计文档可作为阶段 C2 审批与后续实现输入。