# 接口规范化 - 阶段 C6 music 接口设计

## 1. 目标与范围

本阶段针对 `backend/controllers/music_controller.py` 做接口契约收敛，**仅产出 DTO / VO / API 对接文档，不进入实现代码阶段**。

覆盖接口共 2 个：

1. `POST /api/music/upload`
2. `GET /api/music/download/midi/<filename>`

设计基线：
- 入参遵循《DTO层设计》
- 出参遵循《VO层与Result设计》
- 上传接口成功返回 JSON `Result`
- 下载接口属于**文件流接口**：成功直接 `send_file()`，失败返回 `Result` 错误结构

---

## 2. 现状梳理

当前 `music_controller` 主要特点：

- `upload` 使用 `multipart/form-data`，读取 `audio_name` 与 `audio_file`
- `upload` 对扩展名做白名单校验：`mp3 / wav / flac / ogg / m4a / wma`
- `upload` 上传到 OSS `music/` 目录，成功返回 `{ok, audio_name, filename, file_path, format}`
- `download/midi/<filename>` 对文件扩展名和路径遍历做了基础防护
- `download` 先尝试从 `transcribe/` 下载，再兼容旧 `outputs/`
- `download` 成功时直接 `send_file()`，失败时当前返回 `{error}` + `404`

因此阶段 C6 的设计目标是：
- 将上传成功结果统一为轻量 `UploadMusicResultVO`
- 明确 MIDI 下载接口的文件流规则
- 将错误响应统一为 `400 / 404 / 500`

---

## 3. DTO 定义

## 3.1 文件上传类 DTO

### UploadMusicDTO

用于 `POST /api/music/upload`。

请求体：`multipart/form-data`

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| audio_name | str | 是 | 音频显示名称 | `Field(..., min_length=1, max_length=255)` |
| audio_file | Any | 是 | 上传音频文件对象（`FileStorage`） | 必填，文件名非空 |

建议声明：

```python
class UploadMusicDTO(BaseDTO):
    audio_name: str = Field(..., min_length=1, max_length=255)
    audio_file: Any = Field(...)

    @model_validator(mode='after')
    def _validate_file(self) -> 'UploadMusicDTO':
        if self.audio_file is None:
            raise ValueError('audio_file is required')
        filename = getattr(self.audio_file, 'filename', '') or ''
        if not filename.strip():
            raise ValueError('audio_file filename is empty')
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        allowed = {'mp3', 'wav', 'flac', 'ogg', 'm4a', 'wma'}
        if ext not in allowed:
            raise ValueError(f'Unsupported format: {ext}')
        return self
```

---

## 3.2 路径参数 DTO

### MidiFilenamePathDTO

用于 `GET /api/music/download/midi/<filename>`。

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| filename | str | 是 | MIDI 文件名 | `min_length=1`，仅允许 `.mid` / `.midi`，禁止路径穿越 |

建议声明：

```python
class MidiFilenamePathDTO(BaseDTO):
    filename: str = Field(..., min_length=1)

    @field_validator('filename')
    @classmethod
    def _validate_filename(cls, value: str) -> str:
        if '..' in value or '/' in value or '\\' in value:
            raise ValueError('filename 非法，禁止路径穿越')
        if not value.endswith(('.mid', '.midi')):
            raise ValueError('Invalid file type')
        return value
```

---

## 4. VO 定义

## 4.1 UploadMusicResultVO

用于 `POST /api/music/upload` 成功结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | bool | 固定为 `true` |
| audio_name | str | 音频名称 |
| filename | str | OSS 生成 / 上传后的文件名 |
| file_path | str | OSS 地址 |
| format | str | 文件格式 |

建议声明：

```python
class UploadMusicResultVO(BaseVO):
    ok: bool
    audio_name: str
    filename: str
    file_path: str
    format: str
```

---

## 4.2 文件流接口说明

本模块无额外 JSON 详情 VO。`GET /api/music/download/midi/<filename>` 为文件流接口：

- 成功：直接 `send_file(...)`
- 失败：`Result.bad_request(...)` / `Result.not_found(...)` / `Result.server_error(...)`

---

## 5. API 对接表

| 方法 | 路径 | DTO | 成功 result | 失败码 |
|------|------|-----|-------------|--------|
| POST | `/api/music/upload` | `UploadMusicDTO` | `UploadMusicResultVO` | `400 / 500` |
| GET | `/api/music/download/midi/<filename>` | `MidiFilenamePathDTO` | `send_file()` | `400 / 404 / 500` |

---

## 6. 各接口响应设计

## 6.1 POST /api/music/upload

### content-type

- `multipart/form-data`

### 请求字段

- `audio_name=demo song`
- `audio_file=<file>`

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "ok": true,
    "audio_name": "demo song",
    "filename": "4fcae0b3-demo.wav",
    "file_path": "https://oss.example.com/music/4fcae0b3-demo.wav",
    "format": "wav"
  }
}
```

### 失败响应示例（不支持格式）

```json
{
  "code": 400,
  "description": "Unsupported format: exe",
  "result": null
}
```

---

## 6.2 GET /api/music/download/midi/<filename>

该接口为**文件流接口**。

### 成功响应

- HTTP Body：MIDI 文件二进制流
- `Content-Type: audio/midi`
- `Content-Disposition: attachment; filename=<filename>`
- 不包装 `Result.success(...)`

### 失败响应示例（文件类型非法）

```json
{
  "code": 400,
  "description": "Invalid file type",
  "result": null
}
```

### 失败响应示例（文件不存在）

```json
{
  "code": 404,
  "description": "File not found",
  "result": null
}
```

### 兼容规则说明

1. 优先从 `transcribe/<filename>` 查找
2. 若不存在，兼容回退到旧目录 `outputs/<filename>`
3. 该兼容逻辑对前端透明，不改变下载路径

---

## 7. 文件流接口说明

## 7.1 统一规则

`GET /api/music/download/midi/<filename>` 属于下载类接口，采用以下统一约定：

### 入参校验

- 通过 `MidiFilenamePathDTO` 校验
- 禁止路径穿越
- 仅允许 `.mid` / `.midi`

### 成功响应

- 直接返回 `send_file()`
- 不包装 `Result.success(...)`

### 失败响应

- 参数非法：`Result.bad_request(...).to_response()`
- 文件不存在：`Result.not_found(...).to_response()`
- OSS 下载异常或未知异常：`Result.server_error(...).to_response()`

## 7.2 为什么文件流不包装 Result

原因与阶段 C2 文件下载规则一致：

1. `send_file()` 返回二进制流，前端需直接消费文件内容
2. 若外层再包 JSON，将破坏浏览器下载 / Blob 处理路径
3. 因此下载类接口统一采用“成功文件流、失败 JSON 错误”混合模式

---

## 8. 错误码约定

## 8.1 通用错误码

| code | 场景 | 说明 |
|------|------|------|
| 200 | 成功 | 上传成功 / 文件流下载成功 |
| 400 | 参数错误 | 缺少 `audio_name`、缺少文件、格式非法、文件名非法 |
| 404 | 资源不存在 | MIDI 文件不存在 |
| 500 | 服务内部异常 | OSS 上传失败、OSS 下载失败、未捕获异常 |

## 8.2 本模块建议 description 文案

| code | description | 触发场景 |
|------|-------------|----------|
| 400 | `参数校验失败: ...` | DTO / Pydantic 校验失败 |
| 400 | `audio_name is required` | 上传缺少名称 |
| 400 | `audio_file is required` | 上传缺少文件 |
| 400 | `Unsupported format: xxx` | 上传音频格式不在白名单 |
| 400 | `Invalid file type` | 下载目标不是 `.mid/.midi` |
| 404 | `File not found` | MIDI 文件不存在 |
| 500 | `OSS upload failed: ...` | 上传 OSS 失败 |
| 500 | `Failed to download MIDI file` | 下载异常 |

---

## 9. 实现约束与迁移建议

## 9.1 Controller 目标形态

建议实现阶段接口风格如下：

- `POST /api/music/upload`：`@use_dto(UploadMusicDTO, source='form')`
- `GET /api/music/download/midi/<filename>`：路径参数校验后，成功 `send_file()`，失败 `Result.not_found(...)`

## 9.2 与现有存量代码的主要差异

| 现状 | 目标 |
|------|------|
| upload 直接读取 `request.form / request.files` | 改为 DTO 注入 |
| download 失败返回 `{error}` | 统一 `Result.not_found(...)` |
| 上传成功返回裸 `{ok, ...}` | 统一 `Result.success(UploadMusicResultVO)` |

## 9.3 待确认项

1. **上传后返回的 `filename` 是否必须保留？**
   - 当前前端若依赖该字段，建议保留
   - 若未来统一只用 `file_path`，可弱化 `filename`

2. **MIDI 下载找不到文件时是否始终返回 404？**
   - 当前建议：是
   - 不建议把 OSS 内部错误直接混成“文件不存在”

---

## 10. 本阶段交付结论

本阶段 C6 对 `music_controller` 的 DTO / VO 契约建议如下：

- DTO：
  - `UploadMusicDTO`
  - `MidiFilenamePathDTO`
- VO：
  - `UploadMusicResultVO`
- API 成功返回：
  - 上传 → `UploadMusicResultVO`
  - MIDI 下载 → `send_file()`
- 文件流接口说明：
  - 成功直接流式返回，失败统一 `Result`
- 错误码：
  - 统一使用 `400 / 404 / 500`

以上设计可直接作为阶段 C6 审批与后续实现输入。