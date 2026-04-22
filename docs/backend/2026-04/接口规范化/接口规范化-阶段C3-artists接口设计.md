# 接口规范化 - 阶段 C3 artists 接口设计

## 1. 目标与范围

本阶段针对 `backend/controllers/artists_controller.py` 做接口契约设计，**仅产出 DTO / VO / API 对接文档，不进入实现**。

覆盖接口共 6 个：

1. `GET /api/artists/list`
2. `GET /api/artists/<id>`
3. `POST /api/artists/add`
4. `PUT /api/artists/<id>`
5. `DELETE /api/artists/<id>`
6. `PUT /api/artists/<id>/avatar`

设计基线：
- 入参遵循《DTO层设计》：Controller 使用 DTO 承接 query / json / multipart 入参
- 出参遵循《VO层与Result设计》：统一返回 `Result{code, description, result}`
- 阶段 A 基础设施已可直接复用 `BaseDTO`、`use_dto`、`BaseVO`、`Result`

---

## 2. 现状梳理

当前 `artists_controller` 主要特点：

- `list` 直接返回裸 JSON：`{artists, total}`
- `detail` 直接返回 artist dict，不存在时返回 `{error}`
- `add` 同时兼容 JSON 和 multipart/form-data
- `update` 当前也兼容 JSON 和 multipart，但本阶段按接口清单拆分后：
  - `PUT /api/artists/<id>` 聚焦文本字段更新
  - `PUT /api/artists/<id>/avatar` 聚焦头像文件上传
- 头像上传走 OSS，支持格式：`jpg / jpeg / png / gif / webp`
- service 层现有业务约束：
  - 名称为空不可创建
  - 歌手名唯一，重复时报冲突
  - 删除前若被歌曲引用，禁止删除

因此阶段 C3 的设计目标是：
- 保留 `POST /add` 的双 content-type 兼容能力
- 将 artist 列表 / 详情统一收敛为 `ArtistVO`
- 将错误响应统一到 `Result`
- 将头像更新成功响应明确为 JSON `{ok, avatar_url}` 的业务结果，再包入统一外层 `Result`

---

## 3. DTO 定义

> 说明：本节按“查询类 / 路径类 / 写入类 / 文件上传类”归类，避免按接口重复展开。

## 3.1 查询类 DTO

### ListArtistsQueryDTO

用于 `GET /api/artists/list`。

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| limit | int | 否 | 每页条数 | `Field(20, ge=1, le=100)` |
| offset | int | 否 | 分页偏移量 | `Field(0, ge=0)` |

建议声明：

```python
class ListArtistsQueryDTO(BaseDTO):
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
```

---

## 3.2 路径参数 DTO

> 说明：与阶段 B 一致，路径参数 DTO 先作为契约定义保留。实现阶段可继续沿用路由参数 `artist_id: int`，或后续补统一路径参数注入层。

### ArtistIdPathDTO

用于以下接口：
- `GET /api/artists/<id>`
- `PUT /api/artists/<id>`
- `DELETE /api/artists/<id>`
- `PUT /api/artists/<id>/avatar`

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| artist_id | int | 是 | 歌手 ID（路径参数） | `Field(..., gt=0)` |

建议声明：

```python
class ArtistIdPathDTO(BaseDTO):
    artist_id: int = Field(..., gt=0)
```

---

## 3.3 写入类 DTO

## 3.3.1 AddArtistDTO

用于 `POST /api/artists/add`。

### 设计说明

该接口短期**保留一个 DTO 同时兼容 JSON 与 multipart/form-data**，口径参照前置规范中的“存量迁移期共用 DTO”方案：

- JSON 模式：创建歌手基础信息
- multipart 模式：创建歌手基础信息 + 上传头像文件
- 装饰器层仍建议统一使用 `@use_dto(AddArtistDTO)`，由 content-type 自动切换 `from_json / from_form`

### 字段定义

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| name | str | 是 | 歌手名称 | `Field(..., min_length=1, max_length=100)` |
| bio | str \| None | 否 | 歌手简介 | `Field(None, max_length=5000)` |
| avatar | Any | 否 | multipart 上传文件对象（`FileStorage`） | 文件对象；仅 multipart 模式有效 |

### 场景规则

1. `name` 必填，空字符串视为无效
2. JSON 模式下 `avatar` 通常为空
3. multipart 模式下 `avatar` 可选；若传入则必须是允许的图片格式
4. 若重名 → 返回 `409`
5. DTO 负责基础字段校验；图片扩展名校验仍由 controller/service 的文件处理逻辑完成

建议声明：

```python
class AddArtistDTO(BaseDTO):
    name: str = Field(..., min_length=1, max_length=100)
    bio: str | None = Field(None, max_length=5000)
    avatar: Any = None
```

> 注：若后续确认要彻底拆分 JSON 创建与 multipart 创建，可在阶段 C 之后拆成 `AddArtistDTO` + `AddArtistWithAvatarDTO`，本阶段先不拆。

---

## 3.3.2 UpdateArtistDTO

用于 `PUT /api/artists/<id>`。

### 设计说明

本接口聚焦“文本信息更新”，不再承担头像文件上传主职责；头像变更统一走 `PUT /api/artists/<id>/avatar`。

为兼容当前存量调用，可接受 `application/json`；若后续仍需兼容 `multipart/form-data` 的纯文本表单，也可沿用同一 DTO，但**文档主口径按无文件更新设计**。

### 字段定义

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| name | str \| None | 否 | 歌手名称 | `Field(None, min_length=1, max_length=100)` |
| bio | str \| None | 否 | 歌手简介 | `Field(None, max_length=5000)` |

### 场景规则

1. 至少提供一个可更新字段：`name` / `bio`
2. `name` 若传入，不允许空白字符串
3. 若修改后的 `name` 与其他歌手重名 → 返回 `409`
4. 不接受头像文件；头像更新走专用接口

建议声明：

```python
class UpdateArtistDTO(BaseDTO):
    name: str | None = Field(None, min_length=1, max_length=100)
    bio: str | None = Field(None, max_length=5000)

    @model_validator(mode='after')
    def _check_any_field_provided(self) -> 'UpdateArtistDTO':
        if self.name is None and self.bio is None:
            raise ValueError('name 或 bio 至少提供一个')
        return self
```

---

## 3.4 文件上传类 DTO

### UpdateArtistAvatarDTO

用于 `PUT /api/artists/<id>/avatar`。

### 设计说明

该接口是纯文件上传接口：
- 请求体为 `multipart/form-data`
- 成功时业务结果只需要 `{ok, avatar_url}`
- 不返回文件流，不返回完整 `ArtistVO`

### 字段定义

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| avatar | Any | 是 | 头像文件对象（`FileStorage`） | 必填；扩展名需在白名单内 |

建议声明：

```python
class UpdateArtistAvatarDTO(BaseDTO):
    avatar: Any
```

### 场景规则

1. `avatar` 必须存在且文件名非空
2. 文件格式仅允许：`jpg` / `jpeg` / `png` / `gif` / `webp`
3. OSS 上传失败 → 返回 `500`
4. 若歌手不存在，建议返回 `404`

---

## 4. VO 定义

## 4.1 ArtistVO

用于：
- `GET /api/artists/list` 分页项
- `GET /api/artists/<id>` 详情
- 需要回显歌手实体时的统一表示

### 字段定义

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 歌手 ID |
| name | str | 歌手名称 |
| avatar | str \| None | 头像存储地址 / OSS 公网 URL |
| bio | str \| None | 歌手简介 |
| created_at | str \| None | 创建时间，ISO 8601 字符串 |
| updated_at | str \| None | 更新时间，ISO 8601 字符串 |
| deleted_at | str \| None | 删除时间；正常查询场景通常为 `None`，可按需省略输出 |

### 建议口径

考虑到 `find_all / find_by_id` 来自 `artists` 表直接查询，字段基本与表结构一一对应。为避免把软删除内部字段暴露给前端，**建议默认不对外输出 `deleted_at`**。因此推荐最终 VO 仅保留以下 6 个字段：

- `id`
- `name`
- `avatar`
- `bio`
- `created_at`
- `updated_at`

建议声明：

```python
class ArtistVO(BaseVO):
    id: int
    name: str
    avatar: str | None = None
    bio: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_domain(cls, artist: dict, **extra) -> 'ArtistVO':
        if not artist:
            return None
        return cls(
            id=artist.get('id'),
            name=artist.get('name'),
            avatar=artist.get('avatar'),
            bio=artist.get('bio'),
            created_at=artist.get('created_at').isoformat() if artist.get('created_at') else None,
            updated_at=artist.get('updated_at').isoformat() if artist.get('updated_at') else None,
        )
```

---

## 4.2 辅助结果 VO（轻量返回）

> 本阶段强制要求只有 `ArtistVO` 必须定义；以下轻量结果对象不要求单独落地为独立 VO 文件，但需在 API 契约中明确返回字段。

### AddArtistResult

用于 `POST /api/artists/add` 成功结果：

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | bool | 固定为 `true` |
| artist_id | int | 新建歌手 ID |

### UpdateArtistResult

用于 `PUT /api/artists/<id>` / `DELETE /api/artists/<id>` 成功结果：

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | bool | 固定为 `true` |
| message | str | 成功提示文案 |

### UpdateArtistAvatarResult

用于 `PUT /api/artists/<id>/avatar` 成功结果：

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | bool | 固定为 `true` |
| avatar_url | str | 上传成功后的头像公网地址 |

> 说明：当前旧实现返回字段名为 `avatar`，本阶段统一改为 `avatar_url`，与接口语义保持一致。

---

## 5. API 对接表

> 外层统一使用 `Result`：`{code, description, result}`。

| 方法 | 路径 | DTO | 成功 result | 失败码 |
|------|------|-----|-------------|--------|
| GET | `/api/artists/list` | `ListArtistsQueryDTO` | `PageVO[ArtistVO]` | `400 / 500` |
| GET | `/api/artists/<id>` | `ArtistIdPathDTO` | `ArtistVO` | `400 / 404 / 500` |
| POST | `/api/artists/add` | `AddArtistDTO` | `{ok, artist_id}` | `400 / 409 / 500` |
| PUT | `/api/artists/<id>` | `ArtistIdPathDTO` + `UpdateArtistDTO` | `{ok, message}` | `400 / 404 / 409 / 500` |
| DELETE | `/api/artists/<id>` | `ArtistIdPathDTO` | `{ok, message}` | `400 / 404 / 409 / 500` |
| PUT | `/api/artists/<id>/avatar` | `ArtistIdPathDTO` + `UpdateArtistAvatarDTO` | `{ok, avatar_url}` | `400 / 404 / 500` |

---

## 6. 各接口响应设计

## 6.1 GET /api/artists/list

### 请求

- Query：`limit`、`offset`

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "items": [
      {
        "id": 1,
        "name": "周杰伦",
        "avatar": "https://oss.example.com/artists/jay.png",
        "bio": "华语流行歌手",
        "created_at": "2026-04-20T10:00:00",
        "updated_at": "2026-04-20T10:00:00"
      }
    ],
    "total": 1,
    "limit": 20,
    "offset": 0
  }
}
```

### 说明

- 将现有裸结构 `{artists, total}` 统一收敛为 `PageVO[ArtistVO]`
- `items` 对应原 `artists`

---

## 6.2 GET /api/artists/<id>

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "id": 1,
    "name": "周杰伦",
    "avatar": "https://oss.example.com/artists/jay.png",
    "bio": "华语流行歌手",
    "created_at": "2026-04-20T10:00:00",
    "updated_at": "2026-04-20T10:00:00"
  }
}
```

### 不存在响应

```json
{
  "code": 404,
  "description": "Artist not found",
  "result": null
}
```

---

## 6.3 POST /api/artists/add

### content-type

- `application/json`
- `multipart/form-data`

### JSON 示例

```json
{
  "name": "周杰伦",
  "bio": "华语流行歌手"
}
```

### multipart 示例

- `name=周杰伦`
- `bio=华语流行歌手`
- `avatar=<file>`

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "ok": true,
    "artist_id": 12
  }
}
```

### 失败响应示例（重名）

```json
{
  "code": 409,
  "description": "Artist name already exists",
  "result": null
}
```

---

## 6.4 PUT /api/artists/<id>

### 请求

推荐 `application/json`：

```json
{
  "name": "周杰伦",
  "bio": "更新后的简介"
}
```

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "ok": true,
    "message": "Artist updated"
  }
}
```

### 说明

- 本接口仅更新文本字段
- 不再承担头像文件上传主职责
- 若请求体为空或无可更新字段 → `400`
- 若目标歌手不存在，建议语义化改为 `404`

---

## 6.5 DELETE /api/artists/<id>

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "ok": true,
    "message": "Artist deleted"
  }
}
```

### 说明

- 若歌手被歌曲引用，删除应失败并返回 `409`
- 若歌手不存在，建议返回 `404`

---

## 6.6 PUT /api/artists/<id>/avatar

### content-type

- `multipart/form-data`

### 请求字段

- `avatar=<file>`

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "ok": true,
    "avatar_url": "https://oss.example.com/artists/12/avatar.webp"
  }
}
```

### 说明

- 该接口成功时只返回 JSON 结果，不返回文件流
- 返回字段统一命名为 `avatar_url`
- 若缺少文件或扩展名不合法 → `400`
- 若 OSS 上传失败或更新失败 → `500`

---

## 7. 错误码约定

## 7.1 通用错误码

| code | 场景 | 说明 |
|------|------|------|
| 200 | 成功 | 请求处理成功 |
| 400 | 参数错误 / 请求不合法 | DTO 校验失败、缺少必要字段、文件缺失、文件格式错误 |
| 404 | 资源不存在 | 歌手 ID 不存在 |
| 409 | 业务冲突 | 名称重复、删除时存在歌曲引用 |
| 500 | 服务内部异常 | OSS 上传失败、数据库异常、未捕获异常 |

---

## 7.2 本模块建议 description 文案

| code | description | 触发场景 |
|------|-------------|----------|
| 400 | `参数校验失败: ...` | DTO / Pydantic 校验失败 |
| 400 | `name is required` | 新增歌手缺少名称 |
| 400 | `name 或 bio 至少提供一个` | 更新接口空请求 |
| 400 | `avatar file is required` | 头像接口缺少文件 |
| 400 | `不支持的图片格式: xxx` | 扩展名不在白名单 |
| 404 | `Artist not found` | 查询 / 更新 / 删除目标不存在 |
| 409 | `Artist name already exists` | 歌手名称冲突 |
| 409 | `Artist is referenced by songs and cannot be deleted` | 删除时被歌曲引用 |
| 500 | `OSS upload failed: ...` | 上传 OSS 失败 |
| 500 | `Failed to add artist` | 创建失败但无更明确原因 |
| 500 | `Failed to update artist` | 更新失败但无更明确原因 |
| 500 | `Failed to delete artist` | 删除失败但无更明确原因 |
| 500 | `Failed to update avatar` | 头像更新失败但无更明确原因 |

---

## 8. 实现约束与迁移建议

## 8.1 Controller 目标形态

建议实现阶段的接口风格如下：

- `GET /list`：`@use_dto(ListArtistsQueryDTO, source='query')`
- `POST /add`：`@use_dto(AddArtistDTO)`，自动兼容 JSON / multipart
- `PUT /<id>`：`@use_dto(UpdateArtistDTO)`
- `PUT /<id>/avatar`：`@use_dto(UpdateArtistAvatarDTO, source='form')`
- 全部响应统一为 `Result.success(...).to_response()`
- 参数错误 / 业务异常改抛异常，由全局 errorhandler 统一接管

## 8.2 与现有存量代码的主要差异

| 现状 | 目标 |
|------|------|
| 返回裸 dict / `{error}` | 统一 `Result{code, description, result}` |
| `list` 返回 `{artists, total}` | 统一为 `PageVO[ArtistVO]` |
| `detail` 直接返回 mapper dict | 统一映射为 `ArtistVO` |
| `add` 与 `update` 手写读取 `request.form / request.get_json()` | 改为 DTO 注入 |
| `avatar` 返回 `{ok, avatar}` | 统一为 `{ok, avatar_url}` |

## 8.3 待确认项

1. **`PUT /api/artists/<id>` 是否需要继续兼容 multipart 纯文本表单？**
   - 当前文档主口径：推荐只保留 JSON 文本更新
   - 若前端已有 multipart 调用，可在实现时兼容，但不再接收头像文件

2. **`ArtistVO` 是否需要暴露 `deleted_at`？**
   - 当前建议：不暴露，仅保留对前端有业务意义的字段

3. **更新 / 删除 / 头像更新遇到不存在 ID 时是否强制返回 404？**
   - 当前建议：是，避免把“目标不存在”混淆为通用 500

---

## 9. 本阶段交付结论

本阶段 C3 对 `artists_controller` 的 DTO / VO 契约建议如下：

- DTO：
  - `ListArtistsQueryDTO`
  - `ArtistIdPathDTO`
  - `AddArtistDTO`
  - `UpdateArtistDTO`
  - `UpdateArtistAvatarDTO`
- VO：
  - `ArtistVO`
- API 成功返回：
  - 列表 → `PageVO[ArtistVO]`
  - 详情 → `ArtistVO`
  - 新增 / 更新 / 删除 / 头像更新 → 轻量结果对象
- 错误码：
  - 统一使用 `400 / 404 / 409 / 500`

以上设计与阶段 A 基础设施、DTO / VO 总体规范保持一致，可直接作为后续实现阶段的契约依据。
