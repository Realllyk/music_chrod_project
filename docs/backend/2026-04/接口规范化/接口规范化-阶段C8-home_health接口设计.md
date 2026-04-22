# 接口规范化 - 阶段 C8 home + health 接口设计

## 1. 目标与范围

本阶段针对以下 controller 做接口契约收敛，**仅产出 DTO / VO / API 对接文档，不进入实现代码阶段**：

- `backend/controllers/health_controller.py`
- `backend/controllers/home_controller.py`

覆盖接口共 4 个：

### health
1. `GET /api/health`
2. `GET /api/status`
3. `POST /api/db/test`

### home
4. `GET /api/outputs/<filename>`

设计基线：
- 入参遵循《DTO层设计》
- 出参遵循《VO层与Result设计》
- 健康检查类接口成功返回 JSON `Result`
- `GET /api/outputs/<filename>` 属于**文件流接口**：成功 `send_file()`，失败 `Result.not_found(...)`

---

## 2. 现状梳理

当前 controller 主要特点：

### 2.1 health_controller

- `GET /api/health` 返回裸 JSON：`{status, message}`
- `GET /api/status` 返回运行状态、当前时间、数据库连接状态
- `POST /api/db/test` 调用 `test_connection()`，成功返回 `{ok, message}`，失败返回 `{ok, error}` + 500
- 模块当前路径前缀为 `/api`

### 2.2 home_controller

- `GET /outputs/<filename>` 当前未挂 `/api` 前缀，但本阶段需求口径为 `GET /api/outputs/<filename>`，需在设计上以前者为存量、以后者为规范目标
- 成功时 `send_file(file_path)`
- 失败时返回 `{error: 'File not found'}` + 404
- 已做基础本地目录拼接，但未明确路径穿越校验

因此阶段 C8 的设计目标是：
- 将 health/status/db-test 统一收敛到轻量 VO
- 将文件输出下载接口明确为文件流接口
- 明确 `home_controller` 路径规范目标为 `/api/outputs/<filename>`

---

## 3. DTO 定义

## 3.1 健康检查类 DTO

`GET /api/health`、`GET /api/status`、`POST /api/db/test` 当前均无业务入参，原则上**不强制定义 DTO**。

若实现阶段希望统一装饰器形式，可定义空 DTO：

```python
class EmptyDTO(BaseDTO):
    pass
```

---

## 3.2 路径参数 DTO

### OutputFilenamePathDTO

用于 `GET /api/outputs/<filename>`。

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| filename | str | 是 | 输出文件名 | `min_length=1`，禁止路径穿越 |

建议声明：

```python
class OutputFilenamePathDTO(BaseDTO):
    filename: str = Field(..., min_length=1)

    @field_validator('filename')
    @classmethod
    def _validate_filename(cls, value: str) -> str:
        if '..' in value or '/' in value or '\\' in value:
            raise ValueError('filename 非法，禁止路径穿越')
        return value
```

> 说明：是否限制扩展名需视 outputs 目录实际产物而定。当前需求只要求“成功 send_file，失败 Result.not_found”，故先不强绑扩展名白名单。

---

## 4. VO 定义

## 4.1 HealthCheckVO

用于 `GET /api/health`。

| 字段 | 类型 | 说明 |
|------|------|------|
| status | str | 健康状态，建议固定 `ok` |
| message | str | 提示文案 |

建议声明：

```python
class HealthCheckVO(BaseVO):
    status: str
    message: str
```

---

## 4.2 AppStatusVO

用于 `GET /api/status`。

| 字段 | 类型 | 说明 |
|------|------|------|
| status | str | 应用运行状态 |
| timestamp | str | 服务端时间，ISO 8601 |
| database | DatabaseStatusVO | 数据库状态对象 |

### DatabaseStatusVO

| 字段 | 类型 | 说明 |
|------|------|------|
| enabled | bool | 是否启用数据库配置 |
| connected | bool | 当前探测是否连通 |

建议声明：

```python
class DatabaseStatusVO(BaseVO):
    enabled: bool
    connected: bool

class AppStatusVO(BaseVO):
    status: str
    timestamp: str
    database: DatabaseStatusVO
```

---

## 4.3 DbTestResultVO

用于 `POST /api/db/test`。

| 字段 | 类型 | 说明 |
|------|------|------|
| ok | bool | 测试结果 |
| message | str \| None | 成功提示 |
| error | str \| None | 失败原因 |

建议声明：

```python
class DbTestResultVO(BaseVO):
    ok: bool
    message: str | None = None
    error: str | None = None
```

---

## 4.4 文件流接口说明

`GET /api/outputs/<filename>` 无需额外 JSON VO：

- 成功：`send_file(...)`
- 失败：`Result.not_found('File not found')`

---

## 5. API 对接表

| 方法 | 路径 | DTO | 成功 result | 失败码 |
|------|------|-----|-------------|--------|
| GET | `/api/health` | 无 | `HealthCheckVO` | `500` |
| GET | `/api/status` | 无 | `AppStatusVO` | `500` |
| POST | `/api/db/test` | 无 | `DbTestResultVO` | `500` |
| GET | `/api/outputs/<filename>` | `OutputFilenamePathDTO` | `send_file()` | `400 / 404 / 500` |

---

## 6. 各接口响应设计

## 6.1 GET /api/health

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "status": "ok",
    "message": "Service is running"
  }
}
```

---

## 6.2 GET /api/status

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "status": "running",
    "timestamp": "2026-04-22T01:00:00",
    "database": {
      "enabled": true,
      "connected": true
    }
  }
}
```

---

## 6.3 POST /api/db/test

### 成功响应

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "ok": true,
    "message": "Database connected",
    "error": null
  }
}
```

### 失败响应

```json
{
  "code": 500,
  "description": "Database connection failed",
  "result": {
    "ok": false,
    "message": null,
    "error": "Access denied"
  }
}
```

### 说明

- 保留当前 `ok` 业务字段，降低前端兼容成本
- 规范化后错误说明放到 `description`，详细原因放到 `result.error`

---

## 6.4 GET /api/outputs/<filename>

该接口为**文件流接口**。

### 成功响应

- HTTP Body：文件二进制流
- 不包装 `Result.success(...)`

### 失败响应

```json
{
  "code": 404,
  "description": "File not found",
  "result": null
}
```

---

## 7. 文件流接口说明

## 7.1 统一规则

`GET /api/outputs/<filename>` 采用与 `music/download/midi` 一致的混合模式：

### 入参校验

- 使用 `OutputFilenamePathDTO`
- 必须防止路径穿越

### 成功响应

- 直接 `send_file(file_path)`
- 不包装 `Result.success(...)`

### 失败响应

- 参数非法：`Result.bad_request(...).to_response()`
- 文件不存在：`Result.not_found(...).to_response()`
- 未知异常：`Result.server_error(...).to_response()`

## 7.2 路径规范说明

当前存量 controller 路由为：
- `/outputs/<filename>`

本阶段规范目标为：
- `/api/outputs/<filename>`

这意味着实现阶段需要同步检查：
1. blueprint 注册方式
2. Nginx 代理转发
3. 前端实际调用路径

在未实施前，该项应视为**待落地对齐项**。

---

## 8. 错误码约定

## 8.1 通用错误码

| code | 场景 | 说明 |
|------|------|------|
| 200 | 成功 | 健康检查成功 / 状态查询成功 / DB 测试成功 / 文件下载成功 |
| 400 | 参数错误 | 输出文件名非法 |
| 404 | 资源不存在 | 输出文件不存在 |
| 500 | 服务内部异常 | DB 探测异常、状态查询异常、文件发送异常 |

## 8.2 本模块建议 description 文案

| code | description | 触发场景 |
|------|-------------|----------|
| 400 | `参数校验失败: ...` | DTO / Pydantic 校验失败 |
| 400 | `filename 非法，禁止路径穿越` | 输出文件名非法 |
| 404 | `File not found` | outputs 目录无目标文件 |
| 500 | `Database connection failed` | 数据库测试失败 |
| 500 | `Failed to get app status` | 状态探测异常 |
| 500 | `Failed to serve output file` | 文件发送失败 |

---

## 9. 实现约束与迁移建议

## 9.1 Controller 目标形态

建议实现阶段接口风格如下：

- `GET /api/health`：`Result.success(HealthCheckVO)`
- `GET /api/status`：`Result.success(AppStatusVO)`
- `POST /api/db/test`：成功 `Result.success(DbTestResultVO)`，失败 `Result.fail(500, ..., DbTestResultVO(ok=False,...))`
- `GET /api/outputs/<filename>`：成功 `send_file()`，失败 `Result.not_found(...)`

## 9.2 与现有存量代码的主要差异

| 现状 | 目标 |
|------|------|
| health/status/db-test 返回裸 JSON | 统一 `Result{code, description, result}` |
| db-test 失败返回 `{ok:false,error}` + 500 | 保留 `ok/error` 业务字段，但包进 `Result` |
| `/outputs/<filename>` 未显式挂 `/api` | 规范目标改为 `/api/outputs/<filename>` |
| outputs 文件接口失败返回 `{error}` | 改为 `Result.not_found(...)` |

## 9.3 待确认项

1. **`home_controller` 路由是否确认迁移到 `/api/outputs/<filename>`？**
   - 本文档按需求口径采用 `/api`
   - 但现状代码尚未体现，需实现阶段同步对齐 Nginx 与前端

2. **`/api/outputs/<filename>` 是否需要限制扩展名？**
   - 若 outputs 仅存放 MIDI / 结果文件，建议后续加白名单
   - 当前先不限制，以免误伤历史产物

---

## 10. 本阶段交付结论

本阶段 C8 对 `health_controller + home_controller` 的 DTO / VO 契约建议如下：

- DTO：
  - `OutputFilenamePathDTO`
  - health/status/db-test 无强制 DTO
- VO：
  - `HealthCheckVO`
  - `DatabaseStatusVO`
  - `AppStatusVO`
  - `DbTestResultVO`
- API 成功返回：
  - 健康检查 / 状态 / DB 测试 → JSON `Result`
  - outputs 文件下载 → `send_file()`
- 文件流接口说明：
  - 成功直接流式返回，失败统一 `Result`
- 错误码：
  - 统一使用 `400 / 404 / 500`

以上设计可直接作为阶段 C8 审批与后续实现输入。