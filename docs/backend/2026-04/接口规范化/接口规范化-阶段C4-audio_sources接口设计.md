# 接口规范化 - 阶段 C4 audio_sources 接口设计

## 1. 目标与范围

本阶段针对 `backend/controllers/audio_sources_controller.py` 做接口契约收敛，**仅产出 DTO / VO / API 对接文档，不进入实现代码阶段**。

覆盖接口共 5 个：

1. `GET /api/audio-sources/list`
2. `GET /api/audio-sources/oss-files`
3. `GET /api/audio-sources/<id>`
4. `DELETE /api/audio-sources/<id>`
5. `POST /api/audio-sources/upload`

设计基线：
- 入参遵循《DTO层设计》：Controller 使用 DTO 承接 query / form / path 入参
- 出参遵循《VO层与Result设计》：统一返回 `Result{code, description, result}`
- 列表接口使用 `PageVO`
- 本模块无文件下载流接口，上传接口成功返回 JSON 结果

---

## 2. 现状梳理

当前 `audio_sources_controller` 主要特点：

- `list` 返回裸 JSON：`{sources, total}`
- `oss-files` 直接返回 `{files, total}`，异常时返回 `{error}`
- `detail` 兼容 service 返回 dict / tuple，两套序列化逻辑并存
- `delete` 成功返回 `{ok: true}`，失败返回 `{error}`
- `upload` 使用 `multipart/form-data`，校验 `audio_name` 和 `audio_file`，上传 OSS 后写入 `audio_sources`
- 模块内存在 tuple 下标访问，说明需要通过 VO 层屏蔽底层结构差异

因此阶段 C4 的设计目标是：
- 将音源列表 / 详情统一收敛为 `AudioSourceVO`
- 将 OSS 文件列表统一为轻量结果对象
- 将上传、删除成功结果统一为轻量业务 result，再包入 `Result`
- 将错误响应统一到 `400 / 404 / 500`

---

## 3. DTO 定义

> 本节按“查询类 / 路径类 / 文件上传类”归类，避免重复。

## 3.1 查询类 DTO

### ListAudioSourcesQueryDTO

用于 `GET /api/audio-sources/list`。

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| limit | int | 否 | 每页条数 | `Field(100, ge=1, le=200)` |
| offset | int | 否 | 分页偏移量 | `Field(0, ge=0)` |

建议声明：

```python
class ListAudioSourcesQueryDTO(BaseDTO):
    limit: int = Field(100, ge=1, le=200)
    offset: int = Field(0, ge=0)
```

### ListOssAudioFilesQueryDTO

用于 `GET /api/audio-sources/oss-files`。

当前接口无业务入参，原则上可不单独定义 DTO；若实现阶段希望保持统一，也可定义空 DTO：

```python
class ListOssAudioFilesQueryDTO(BaseDTO):
    pass
```

---

## 3.2 路径参数 DTO

### AudioSourceIdPathDTO

用于以下接口：
- `GET /api/audio-sources/<id>`
- `DELETE /api/audio-sources/<id>`

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| audio_id | int | 是 | 音源 ID | `Field(..., gt=0)` |

建议声明：

```python
class AudioSourceIdPathDTO(BaseDTO):
    audio_id: int = Field(..., gt=0)
```

---

## 3.3 文件上传类 DTO

### UploadAudioSourceDTO

用于 `POST /api/audio-sources/upload`。

请求体：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| audio_name | str | 是 | 音源显示名称 | `Field(..., min_length=1, max_length=255)` |
| audio_file | Any | 是 | 上传音频文件对象（`FileStorage`） | 必填，文件名非空 |

建议声明：

```python
class UploadAudioSourceDTO(BaseDTO):
    audio_name: str = Field(..., min_length=1, max_length=255)
    audio_file: Any = Field(...)

    @model_validator(mode='after')
    def _validate_file(self) -> 'UploadAudioSourceDTO':
        if self.audio_file is None:
            raise ValueError('audio_file is required')
        filename = getattr(self.audio_file, 'filename', '') or ''
        if not filename.strip():
            raise ValueError('audio_file filename is empty')
        return self
```

### 业务补充规则

1. `audio_name` 必填，空白字符串视为无效
2. `audio_file` 必须存在且文件名非空
3. 文件扩展名当前 controller 未限制；规范化阶段建议：
   - 若继续放开，需至少在文档中声明“由 OSS / 后续解析链路兜底”
   - 更推荐在实现阶段补充白名单：`mp3 / wav / flac / ogg / m4a / wma`
4. `file_size` 允许由服务端从上传对象读取，不要求前端传入

---

## 4. VO 定义

## 4.1 AudioSourceVO

用于：
- `GET /api/audio-sources/list` 列表项
- `GET /api/audio-sources/<id>` 详情

### 字段定义

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 音源 ID |
| source_type | str \| None | 音源来源类型，如 `upload` |
| source_id | str \| None | 外部来源标识 |
| audio_name | str \| None | 音源名称 |
| file_path | str \| None | 存储路径 / OSS URL |
| file_size | int \| None | 文件大小（字节） |
| duration_sec | float \| None | 时长（秒） |
| sample_rate | int \| None | 采样率 |
| channels | int \| None | 声道数 |
| format | str \| None | 文件格式扩展名 |
| status | str \| None | 状态 |
| created_at | str \| None | 创建时间，ISO 8601 |

建议声明：

```python
class AudioSourceVO(BaseVO):
    id: int
    source_type: str | None = None
    source_id: str | None = None
    audio_name: str | None = None
    file_path: str | None = None
    file_size: int | None = None
    duration_sec: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    format: str | None = None
    status: str | None = None
    created_at: str | None = None
```

### 映射说明

由于现状 service 可能返回 dict 或 tuple，建议 `from_domain` 中兼容两种结构，统一对外暴露同一字段集，彻底消除 controller 内的 tuple 下标映射。

---

## 4.2 OSSFIleVO（轻量列表项）

用于 `GET /api/audio-sources/oss-files` 的 `items`。

| 字段 | 类型 | 说明 |
|------|------|------|
| key | str | OSS 对象 key |
| url | str | 公网访问地址 |
| name | str \| None | 文件名 |

> 说明：`list_files("audio-sources/")` 当前返回结构未在 controller 内二次约束。规范化时建议统一成轻量 VO 列表；若底层已直接返回字符串 URL，也可在实现阶段退化为 `list[str]`，但推荐标准化为对象数组，便于前端展示。

---

## 4.3 辅助结果对象

### DeleteAudioSourceResult

用于 `DELETE /api/audio-sources/<id>` 成功结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | bool | 固定为 `true` |
| audio_source_id | int | 已删除音源 ID |

### UploadAudioSourceResult

用于 `POST /api/audio-sources/upload` 成功结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | bool | 固定为 `true` |
| audio_source_id | int | 新建音源记录 ID |
| audio_name | str | 音源名称 |
| file_path | str | 上传后的 OSS 地址 |
| format | str \| None | 文件格式 |

---

## 5. API 对接表

> 外层统一使用 `Result`：`{code, description, result}`。

| 方法 | 路径 | DTO | 成功 result | 失败码 |
|------|------|-----|-------------|--------|
| GET | `/api/audio-sources/list` | `ListAudioSourcesQueryDTO` | `PageVO[AudioSourceVO]` | `400 / 500` |
| GET | `/api/audio-sources/oss-files` | `ListOssAudioFilesQueryDTO`（可选） | `{items, total}` 或 `list[OSSFileVO]` 包装对象 | `500` |
| GET | `/api/audio-sources/<id>` | `AudioSourceIdPathDTO` | `AudioSourceVO` | `400 / 404 / 500` |
| DELETE | `/api/audio-sources/<id>` | `AudioSourceIdPathDTO` | `{ok, audio_source_id}` | `400 / 404 / 500` |
| POST | `/api/audio-sources/upload` | `UploadAudioSourceDTO` | `{ok, audio_source_id, audio_name, file_path, format}` | `400 / 500` |

---

## 6. 各接口响应设计

## 6.1 GET /api/audio-sources/list

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "items": [
      {
        "id": 1,
        "source_type": "upload",
        "source_id": null,
        "audio_name": "demo piano",
        "file_path": "https://oss.example.com/audio-sources/demo.wav",
        "file_size": 123456,
        "duration_sec": null,
        "sample_rate": null,
        "channels": null,
        "format": "wav",
        "status": "active",
        "created_at": "2026-04-22T00:00:00"
      }
    ],
    "total": 1,
    "limit": 100,
    "offset": 0
  }
}
```

### 说明

- 将现有 `{sources, total}` 收敛为 `PageVO[AudioSourceVO]`
- `items` 对应原 `sources`

---

## 6.2 GET /api/audio-sources/oss-files

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "items": [
      {
        "key": "audio-sources/demo.wav",
        "name": "demo.wav",
        "url": "https://oss.example.com/audio-sources/demo.wav"
      }
    ],
    "total": 1
  }
}
```

### 说明

- 现状接口返回 `{files, total}`
- 规范化后建议稳定为 `{items, total}`，降低前后端字段分裂
- 若底层 `list_files` 已稳定输出对象结构，可直接映射为 `items`

---

## 6.3 GET /api/audio-sources/<id>

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "id": 1,
    "source_type": "upload",
    "source_id": null,
    "audio_name": "demo piano",
    "file_path": "https://oss.example.com/audio-sources/demo.wav",
    "file_size": 123456,
    "duration_sec": null,
    "sample_rate": null,
    "channels": null,
    "format": "wav",
    "status": "active",
    "created_at": "2026-04-22T00:00:00"
  }
}
```

### 不存在响应

```json
{
  "code": 404,
  "description": "Audio source not found",
  "result": null
}
```

---

## 6.4 DELETE /api/audio-sources/<id>

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "ok": true,
    "audio_source_id": 1
  }
}
```

### 说明

- 现状只返回 `{ok: true}`
- 规范化后建议带回被删除 ID，便于前端直接更新列表
- 当 service 能区分“目标不存在”和“删除失败”时，优先返回 `404` 而不是统一 `400`

---

## 6.5 POST /api/audio-sources/upload

### content-type

- `multipart/form-data`

### 请求字段

- `audio_name=demo piano`
- `audio_file=<file>`

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "ok": true,
    "audio_source_id": 12,
    "audio_name": "demo piano",
    "file_path": "https://oss.example.com/audio-sources/demo.wav",
    "format": "wav"
  }
}
```

### 说明

- 该接口是上传接口，不是文件流接口
- 成功时保持 JSON 返回，不使用 `send_file`
- `file_size`、时长、采样率等元数据如需补齐，可由后续异步解析或 service 层同步计算

---

## 7. 错误码约定

## 7.1 通用错误码

| code | 场景 | 说明 |
|------|------|------|
| 200 | 成功 | 请求处理成功 |
| 400 | 参数错误 / 删除前置条件不满足 | query 非法、上传缺字段、文件名为空 |
| 404 | 资源不存在 | 音源 ID 不存在 |
| 500 | 服务内部异常 | OSS 列表查询失败、上传失败、数据库异常 |

## 7.2 本模块建议 description 文案

| code | description | 触发场景 |
|------|-------------|----------|
| 400 | `参数校验失败: ...` | DTO / Pydantic 校验失败 |
| 400 | `audio_name is required` | 上传缺少音源名称 |
| 400 | `audio_file is required` | 上传缺少文件 |
| 404 | `Audio source not found` | 详情 / 删除目标不存在 |
| 500 | `Failed to list OSS audio files` | OSS 文件列表查询失败 |
| 500 | `OSS upload failed: ...` | 上传 OSS 失败 |
| 500 | `Failed to create audio source` | 上传成功但数据库写入失败 |
| 500 | `Failed to delete audio source` | 删除异常 |

---

## 8. 实现约束与迁移建议

## 8.1 Controller 目标形态

建议实现阶段接口风格如下：

- `GET /list`：`@use_dto(ListAudioSourcesQueryDTO, source='query')`
- `GET /oss-files`：可无 DTO，或空 DTO
- `GET /<id>`：路径参数按 `audio_id: int` 保留，后续可补路径 DTO 注入层
- `DELETE /<id>`：统一返回 `Result.success(...)`
- `POST /upload`：`@use_dto(UploadAudioSourceDTO, source='form')`
- 所有异常统一交给 `Result + errorhandler`

## 8.2 与现有存量代码的主要差异

| 现状 | 目标 |
|------|------|
| 返回裸 `{sources, total}` / `{error}` | 统一 `Result{code, description, result}` |
| detail 兼容 dict/tuple 两套分支 | 统一交由 `AudioSourceVO.from_domain` 处理 |
| delete 成功只返回 `{ok: true}` | 返回 `{ok, audio_source_id}` |
| upload 直接读 `request.form / request.files` | 改为 DTO 注入 |

## 8.3 待确认项

1. **上传音频格式是否需要白名单？**
   - 当前 controller 未限制
   - 建议与 `music/upload` 对齐，统一允许 `mp3 / wav / flac / ogg / m4a / wma`

2. **`GET /oss-files` 返回项是否固定包含 `key` 与 `url`？**
   - 当前依赖 `list_files()` 真实输出
   - 建议实现阶段统一标准化为对象数组

3. **删除失败是否需要区分 404 与 409？**
   - 当前 service 返回 `success, error`
   - 若存在“被引用不可删”等场景，可扩展 `409`

---

## 9. 本阶段交付结论

本阶段 C4 对 `audio_sources_controller` 的 DTO / VO 契约建议如下：

- DTO：
  - `ListAudioSourcesQueryDTO`
  - `AudioSourceIdPathDTO`
  - `UploadAudioSourceDTO`
  - `ListOssAudioFilesQueryDTO`（可选空 DTO）
- VO：
  - `AudioSourceVO`
  - `OSSFileVO`（建议）
- API 成功返回：
  - 列表 → `PageVO[AudioSourceVO]`
  - 详情 → `AudioSourceVO`
  - OSS 文件列表 → `{items, total}`
  - 删除 / 上传 → 轻量结果对象
- 错误码：
  - 统一使用 `400 / 404 / 500`

以上设计可直接作为阶段 C4 审批与后续实现输入。