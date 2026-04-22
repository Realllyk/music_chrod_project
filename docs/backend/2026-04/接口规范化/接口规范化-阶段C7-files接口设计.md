# 接口规范化 - 阶段 C7 files 接口设计

## 1. 目标与范围

本阶段针对 `backend/controllers/files_controller.py` 做接口契约设计，**仅产出 DTO / VO / API 对接文档，不进入实现代码阶段**。

覆盖接口共 1 个：

1. `GET /api/files/oss-url`

设计基线：
- 入参遵循《DTO层设计》
- 出参遵循《VO层与Result设计》
- 本接口属于资源定位查询接口，成功返回 JSON `Result`
- 通过 DTO 明确“资源标识三选一 + type 可选”的约束

---

## 2. 现状梳理

当前 `files_controller` 主要特点：

- 通过 query 参数 `song_id / session_id / audio_source_id` 查询对应资源的 OSS URL
- 三类资源要求**恰好提供一个**标识
- 通过 `type` 过滤返回字段，允许值：`audio / melody / chord / recording / source`
- controller 内根据资源类型动态查询 `SongsService / CaptureService / AudioSourcesService`
- 成功时返回裸 JSON：`{resource, requested_type, data}`
- 失败时返回 `{error}`，状态码为 `400 / 404`

因此阶段 C7 的设计目标是：
- 将“单资源定位 + 类型过滤”约束收敛到 DTO
- 将成功结果统一为 `FileResourceUrlsVO`
- 保持当前灵活返回能力，但明确字段规范

---

## 3. DTO 定义

### GetFileOssUrlQueryDTO

用于 `GET /api/files/oss-url`。

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| song_id | int \| None | 条件必填 | 歌曲 ID | `gt=0` |
| session_id | str \| None | 条件必填 | 采集会话 ID | `min_length=1` |
| audio_source_id | int \| None | 条件必填 | 音源 ID | `gt=0` |
| type | Literal[...] \| None | 否 | 文件类型过滤 | 允许 `audio / melody / chord / recording / source` |

建议声明：

```python
class GetFileOssUrlQueryDTO(BaseDTO):
    song_id: int | None = Field(None, gt=0)
    session_id: str | None = Field(None, min_length=1)
    audio_source_id: int | None = Field(None, gt=0)
    type: Literal['audio', 'melody', 'chord', 'recording', 'source'] | None = None

    @model_validator(mode='after')
    def _validate_exactly_one_resource(self) -> 'GetFileOssUrlQueryDTO':
        provided = [v for v in [self.song_id, self.session_id, self.audio_source_id] if v is not None]
        if len(provided) != 1:
            raise ValueError('Exactly one of song_id, session_id, audio_source_id is required')
        return self
```

### 业务规则说明

1. `song_id / session_id / audio_source_id` 三选一且必须恰好提供一个
2. `type` 可空；为空时返回该资源可解析出的全部文件 URL
3. `type` 非空时仅返回匹配类型
4. 资源存在但对应类型文件不存在时，返回 `404`

---

## 4. VO 定义

## 4.1 FileResourceDataVO

用于承载实际路径与 URL 字段集合。

> 说明：本接口返回字段随资源类型动态变化，因此适合定义为“统一外层 + 可选字段集合”。

| 字段 | 类型 | 说明 |
|------|------|------|
| audio_path | str \| None | 歌曲原始音频路径 |
| audio_url | str \| None | 歌曲原始音频公网地址 |
| melody_path | str \| None | 旋律文件路径 |
| melody_url | str \| None | 旋律文件公网地址 |
| chord_path | str \| None | 和弦文件路径 |
| chord_url | str \| None | 和弦文件公网地址 |
| recording_path | str \| None | 录音文件路径 |
| recording_url | str \| None | 录音文件公网地址 |
| source_path | str \| None | 音源文件路径 |
| source_url | str \| None | 音源文件公网地址 |

建议声明：

```python
class FileResourceDataVO(BaseVO):
    audio_path: str | None = None
    audio_url: str | None = None
    melody_path: str | None = None
    melody_url: str | None = None
    chord_path: str | None = None
    chord_url: str | None = None
    recording_path: str | None = None
    recording_url: str | None = None
    source_path: str | None = None
    source_url: str | None = None
```

---

## 4.2 FileResourceUrlsVO

用于 `GET /api/files/oss-url` 整体结果对象。

| 字段 | 类型 | 说明 |
|------|------|------|
| resource | str | 资源类型：`song / capture_session / audio_source` |
| requested_type | str \| None | 请求过滤类型 |
| data | FileResourceDataVO | 文件路径与 URL 数据 |

建议声明：

```python
class FileResourceUrlsVO(BaseVO):
    resource: str
    requested_type: str | None = None
    data: FileResourceDataVO
```

---

## 5. API 对接表

| 方法 | 路径 | DTO | 成功 result | 失败码 |
|------|------|-----|-------------|--------|
| GET | `/api/files/oss-url` | `GetFileOssUrlQueryDTO` | `FileResourceUrlsVO` | `400 / 404 / 500` |

---

## 6. 接口响应设计

## 6.1 GET /api/files/oss-url

### 请求示例 1：按歌曲取全部可用文件

`GET /api/files/oss-url?song_id=12`

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "resource": "song",
    "requested_type": null,
    "data": {
      "audio_path": "music/demo.wav",
      "audio_url": "https://oss.example.com/music/demo.wav",
      "melody_path": "transcribe/demo.mid",
      "melody_url": "https://oss.example.com/transcribe/demo.mid",
      "chord_path": null,
      "chord_url": null,
      "recording_path": null,
      "recording_url": null,
      "source_path": null,
      "source_url": null
    }
  }
}
```

### 请求示例 2：按 session 仅取 recording

`GET /api/files/oss-url?session_id=cap_001&type=recording`

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "resource": "capture_session",
    "requested_type": "recording",
    "data": {
      "recording_path": "recordings/demo.wav",
      "recording_url": "https://oss.example.com/recordings/demo.wav"
    }
  }
}
```

### 不存在响应

```json
{
  "code": 404,
  "description": "No file matched the requested resource/type",
  "result": null
}
```

---

## 7. 错误码约定

## 7.1 通用错误码

| code | 场景 | 说明 |
|------|------|------|
| 200 | 成功 | OSS URL 查询成功 |
| 400 | 参数错误 | 三个资源标识不是“恰好一个”、type 非法 |
| 404 | 资源不存在 / 无匹配文件 | song/session/audio_source 不存在，或对应 type 无文件 |
| 500 | 服务内部异常 | service 查询异常、URL 解析异常 |

## 7.2 本模块建议 description 文案

| code | description | 触发场景 |
|------|-------------|----------|
| 400 | `参数校验失败: ...` | DTO / Pydantic 校验失败 |
| 400 | `Exactly one of song_id, session_id, audio_source_id is required` | 资源标识不满足三选一 |
| 400 | `type must be one of audio, melody, chord, recording, source` | type 非法 |
| 404 | `Song not found` | song_id 对应资源不存在 |
| 404 | `Session not found` | session_id 对应资源不存在 |
| 404 | `Audio source not found` | audio_source_id 对应资源不存在 |
| 404 | `No file matched the requested resource/type` | 资源存在但找不到目标文件 |
| 500 | `Failed to resolve OSS url` | 未捕获异常 |

---

## 8. 实现约束与迁移建议

## 8.1 Controller 目标形态

建议实现阶段风格如下：

- `GET /api/files/oss-url`：`@use_dto(GetFileOssUrlQueryDTO, source='query')`
- 根据 DTO 中三选一资源标识分支处理
- 成功统一返回 `Result.success(FileResourceUrlsVO)`

## 8.2 与现有存量代码的主要差异

| 现状 | 目标 |
|------|------|
| controller 手写判断三选一与 type 合法性 | 改为 DTO 校验 |
| 成功返回裸 `{resource, requested_type, data}` | 包装到 `Result.success(...)` |
| `data` 字段结构动态且未文档化 | 通过 `FileResourceDataVO` 明确可选字段集 |

## 8.3 待确认项

1. **是否需要把 `data` 中未命中的字段全部显式返回为 `null`？**
   - 当前建议：可选
   - 若前端希望固定字段结构，建议显式返回 `null`

2. **`type` 为空时是否总是返回全部可用类型？**
   - 当前建议：是
   - 这是本接口作为“统一资源定位入口”的主要价值

---

## 9. 本阶段交付结论

本阶段 C7 对 `files_controller` 的 DTO / VO 契约建议如下：

- DTO：
  - `GetFileOssUrlQueryDTO`
- VO：
  - `FileResourceDataVO`
  - `FileResourceUrlsVO`
- API 成功返回：
  - `FileResourceUrlsVO`
- 错误码：
  - 统一使用 `400 / 404 / 500`

以上设计可直接作为阶段 C7 审批与后续实现输入。