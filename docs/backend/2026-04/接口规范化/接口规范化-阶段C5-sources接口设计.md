# 接口规范化 - 阶段 C5 sources 接口设计

## 1. 目标与范围

本阶段针对 `backend/controllers/sources_controller.py` 做接口契约设计，**仅产出 DTO / VO / API 对接文档，不进入实现代码阶段**。

覆盖接口共 3 个：

1. `GET /api/sources`
2. `PUT /api/sources/switch`
3. `GET /api/sources/search`

设计基线：
- 入参遵循《DTO层设计》
- 出参遵循《VO层与Result设计》
- 列表型结果统一收敛到 `PageVO` 或稳定数组对象
- 不改变 SourceFactory / 各 source provider 的领域职责，仅规范 controller 对外契约

---

## 2. 现状梳理

当前 `sources_controller` 主要特点：

- `GET /api/sources` 返回裸 JSON：`{sources, current, total}`
- `PUT /switch` 使用 `request.get_json()` 手写读取 `source` 与 `config`
- `switch` 在切到 `spotify` 且未传 config 时，会自动从 `config.json` 注入 `client_id / client_secret`
- `GET /search` 读取 query 参数 `q` / `limit`
- `search` 依赖当前激活源，且要求 `source.is_authenticated == True`
- 错误响应当前分布为 `400 / 401 / 500`，但未统一 `Result` 外层

因此阶段 C5 的设计目标是：
- 将音乐源列表统一收敛为 `MusicSourceVO`
- 将切换结果统一为 `SwitchSourceResultVO`
- 将搜索结果统一为 `MusicSearchResultVO` 列表分页或稳定数组结构
- 保留 `401` 语义，显式表达“源存在但未认证”

---

## 3. DTO 定义

## 3.1 查询类 DTO

### ListSourcesQueryDTO

用于 `GET /api/sources`。

当前接口无业务入参，可不强制定义 DTO；若实现阶段希望统一，可定义空 DTO：

```python
class ListSourcesQueryDTO(BaseDTO):
    pass
```

### SearchMusicQueryDTO

用于 `GET /api/sources/search`。

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| q | str | 是 | 搜索关键字 | `Field(..., min_length=1, max_length=200)` |
| limit | int | 否 | 返回条数 | `Field(20, ge=1, le=50)` |

建议声明：

```python
class SearchMusicQueryDTO(BaseDTO):
    q: str = Field(..., min_length=1, max_length=200)
    limit: int = Field(20, ge=1, le=50)
```

---

## 3.2 写入类 DTO

### SwitchSourceDTO

用于 `PUT /api/sources/switch`。

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| source | str | 是 | 目标音乐源名称 | `Field(..., min_length=1)` |
| config | dict[str, Any] \| None | 否 | 源切换附带配置 | 默认 `{}` |

建议声明：

```python
class SwitchSourceDTO(BaseDTO):
    source: str = Field(..., min_length=1, description='目标音乐源名称')
    config: dict[str, Any] | None = Field(default_factory=dict, description='附加配置')
```

### 业务补充规则

1. `source` 必填
2. `source` 必须在 `SourceFactory.get_available_sources()` 返回集合内
3. 若切换到 `spotify` 且请求未传 `config`，可继续沿用“从 `config.json` 注入默认配置”的兼容行为
4. 若底层认证失败：
   - 若是“切换成功但认证未通过”，建议仍返回 `200`，并在 `authenticated=false` 表达状态
   - 若是“初始化/切换动作本身失败”，返回 `500`

---

## 4. VO 定义

## 4.1 MusicSourceVO

用于 `GET /api/sources` 列表项。

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 源名称，如 `spotify` / `local_file` |
| label | str | 展示名称 |
| is_current | bool | 是否当前激活源 |

建议声明：

```python
class MusicSourceVO(BaseVO):
    name: str
    label: str
    is_current: bool
```

---

## 4.2 SwitchSourceResultVO

用于 `PUT /api/sources/switch` 成功结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | bool | 固定为 `true` |
| source | str | 当前已切换到的源 |
| authenticated | bool | 切换后是否已通过认证 |
| message | str | 提示文案 |

建议声明：

```python
class SwitchSourceResultVO(BaseVO):
    ok: bool
    source: str
    authenticated: bool
    message: str
```

---

## 4.3 MusicSearchItemVO

用于 `GET /api/sources/search` 列表项。

> 说明：不同 provider 返回字段可能不同。为避免前端直接绑定第三方平台原始结构，建议抽象稳定公共字段，并允许保留 `raw` 扩展区。

| 字段 | 类型 | 说明 |
|------|------|------|
| source_id | str \| None | 音乐源内部资源 ID |
| title | str \| None | 曲目标题 |
| artist | str \| None | 艺术家名称 |
| album | str \| None | 专辑名称 |
| duration_ms | int \| None | 时长（毫秒） |
| cover_url | str \| None | 封面图 |
| preview_url | str \| None | 试听地址 |
| raw | dict \| None | 原始 provider 字段（可选） |

建议声明：

```python
class MusicSearchItemVO(BaseVO):
    source_id: str | None = None
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    duration_ms: int | None = None
    cover_url: str | None = None
    preview_url: str | None = None
    raw: dict | None = None
```

---

## 4.4 MusicSearchResultVO

用于 `GET /api/sources/search` 整体结果对象。

| 字段 | 类型 | 说明 |
|------|------|------|
| query | str | 搜索关键字 |
| source | str | 实际执行搜索的源 |
| items | list[MusicSearchItemVO] | 搜索结果 |
| total | int | 结果数 |
| limit | int | 请求 limit |

建议声明：

```python
class MusicSearchResultVO(BaseVO):
    query: str
    source: str
    items: list[MusicSearchItemVO]
    total: int
    limit: int
```

---

## 5. API 对接表

> 外层统一使用 `Result`：`{code, description, result}`。

| 方法 | 路径 | DTO | 成功 result | 失败码 |
|------|------|-----|-------------|--------|
| GET | `/api/sources` | `ListSourcesQueryDTO`（可选） | `{items: list[MusicSourceVO], current, total}` | `500` |
| PUT | `/api/sources/switch` | `SwitchSourceDTO` | `SwitchSourceResultVO` | `400 / 500` |
| GET | `/api/sources/search` | `SearchMusicQueryDTO` | `MusicSearchResultVO` | `400 / 401 / 500` |

---

## 6. 各接口响应设计

## 6.1 GET /api/sources

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "items": [
      {
        "name": "local_file",
        "label": "本地文件",
        "is_current": true
      },
      {
        "name": "spotify",
        "label": "Spotify",
        "is_current": false
      }
    ],
    "current": "local_file",
    "total": 2
  }
}
```

### 说明

- 现状字段 `sources` 建议统一改为 `items`
- `current` 保留，便于前端做全局状态展示

---

## 6.2 PUT /api/sources/switch

### 请求示例

```json
{
  "source": "spotify",
  "config": {
    "client_id": "***",
    "client_secret": "***"
  }
}
```

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "ok": true,
    "source": "spotify",
    "authenticated": true,
    "message": "已切换到音乐源: spotify"
  }
}
```

### 失败响应示例（未知 source）

```json
{
  "code": 400,
  "description": "Unknown source: qqmusic",
  "result": {
    "available": ["local_file", "spotify"]
  }
}
```

### 说明

- 当前 controller 将 `available` 放在错误对象内，规范化后建议作为 `Result.result` 的补充信息返回
- 若切换成功但认证失败，建议仍返回 `200`，由 `authenticated=false` 体现

---

## 6.3 GET /api/sources/search

### 请求

- Query：`q`、`limit`

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "query": "Jay Chou",
    "source": "spotify",
    "items": [
      {
        "source_id": "abc123",
        "title": "晴天",
        "artist": "周杰伦",
        "album": "叶惠美",
        "duration_ms": 269000,
        "cover_url": "https://example.com/cover.jpg",
        "preview_url": null,
        "raw": null
      }
    ],
    "total": 1,
    "limit": 20
  }
}
```

### 未切换源响应

```json
{
  "code": 400,
  "description": "No active music source. Please switch to a source first.",
  "result": null
}
```

### 未认证响应

```json
{
  "code": 401,
  "description": "Source SpotifySource not authenticated",
  "result": null
}
```

---

## 7. 错误码约定

## 7.1 通用错误码

| code | 场景 | 说明 |
|------|------|------|
| 200 | 成功 | 查询 / 切换 / 搜索成功 |
| 400 | 参数错误 / 前置条件不满足 | `source` 缺失、`q` 为空、无激活源 |
| 401 | 已选源未认证 | provider 未通过认证 |
| 500 | 服务内部异常 | provider 初始化失败、搜索异常、未捕获异常 |

## 7.2 本模块建议 description 文案

| code | description | 触发场景 |
|------|-------------|----------|
| 400 | `参数校验失败: ...` | DTO / Pydantic 校验失败 |
| 400 | `source is required` | 切换缺少 source |
| 400 | `Unknown source: xxx` | 请求的 source 不在可用列表内 |
| 400 | `q (query) is required` | 搜索关键字为空 |
| 400 | `No active music source. Please switch to a source first.` | 未先切换有效源 |
| 401 | `Source xxx not authenticated` | 当前源未认证 |
| 500 | `Failed to switch source` | 切换异常 |
| 500 | `Search failed: ...` | provider 搜索失败 |

---

## 8. 实现约束与迁移建议

## 8.1 Controller 目标形态

建议实现阶段的接口风格如下：

- `GET /api/sources`：可无 DTO，统一返回 `Result.success({...}).to_response()`
- `PUT /api/sources/switch`：`@use_dto(SwitchSourceDTO)`
- `GET /api/sources/search`：`@use_dto(SearchMusicQueryDTO, source='query')`
- 未认证保留 `401`，不要混成通用 `400`

## 8.2 与现有存量代码的主要差异

| 现状 | 目标 |
|------|------|
| 返回裸 `{sources, current, total}` | 统一 `Result{code, description, result}` |
| `switch` 直接拼 `{error, available}` | `available` 放入 `result`，错误外层统一 `Result.fail(...)` |
| `search` 透传 provider 原始列表 | 通过 `MusicSearchItemVO` 统一输出公共字段 |

## 8.3 待确认项

1. **搜索结果是否保留 `raw` 原始字段？**
   - 若前端需要平台特有字段，建议保留 `raw`
   - 若追求严格契约，可仅保留公共字段

2. **切换成功但未认证是否算成功？**
   - 当前建议：算成功，返回 `authenticated=false`
   - 若业务要求“未认证即切换失败”，则应改为 `409` 或 `500`

3. **`GET /api/sources` 是否需要返回更多 provider 能力信息？**
   - 当前仅保留 `name / label / is_current`
   - 若后续需要显示“是否已认证 / 是否支持搜索”等，可扩展 VO

---

## 9. 本阶段交付结论

本阶段 C5 对 `sources_controller` 的 DTO / VO 契约建议如下：

- DTO：
  - `SwitchSourceDTO`
  - `SearchMusicQueryDTO`
  - `ListSourcesQueryDTO`（可选空 DTO）
- VO：
  - `MusicSourceVO`
  - `SwitchSourceResultVO`
  - `MusicSearchItemVO`
  - `MusicSearchResultVO`
- API 成功返回：
  - 音乐源列表 → `{items, current, total}`
  - 切换结果 → `SwitchSourceResultVO`
  - 搜索结果 → `MusicSearchResultVO`
- 错误码：
  - 统一使用 `400 / 401 / 500`

以上设计可直接作为阶段 C5 审批与后续实现输入。