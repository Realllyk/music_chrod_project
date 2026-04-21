# 接口规范化-阶段C2-capture页面改造方案

## 1. 目标与范围

本方案用于配合后端 `capture_controller` 在阶段 C2 的接口规范化改造，覆盖以下页面：

- `frontend/pages/capture.html`
- `frontend/pages/recordings/index.html`
- `frontend/pages/recordings/detail.html`

本次 **只输出前端改造设计文档，不进入实现**。

> 说明：后端 C2 设计文档尚未产出，本文先基于当前 `backend/controllers/capture_controller.py`、阶段 A 基础设施、以及阶段 B/C1 已采用的前端改造模式推导字段改造方案。待后端 C2 设计文档完成后，需要再次逐项核对字段名与返回模型是否一致。

---

## 2. 现状分析

### 2.1 规范化基线

根据迁移计划与已落地的前端基线：

1. 后端接口会逐步统一为 `Result` 结构：
   - 成功：`{ code: 200, description: 'success', result: ... }`
   - 失败：`{ code: 非200, description: 错误信息, result: null }`
2. `frontend/js/api.js` 已具备 `unwrap`：
   - 成功时返回 `result`
   - 失败时抛出 `Error`
3. 页面侧应统一改成：
   - 使用 `apiGet/apiPost/apiPut/apiDelete/apiPostForm`
   - 使用 `try/catch`
   - 不再读取 `r.ok` / `r.error`

### 2.2 当前 `capture_controller` 返回形状

结合现有后端代码，当前相关接口的返回大致分为四类：

1. **会话对象 / 状态对象**
   - `/start`
   - `/active`
   - `/request-recording`
   - `/detail/<session_id>`
2. **兼容型成功响应（含 `ok` / `message`）**
   - `/register-file`
   - `/upload-file`
   - `/stop`
   - `/start-recording`
   - `/stop-recording`
   - `/save`
   - `/sessions/<id>` PUT / DELETE
3. **列表响应**
   - `/list` → `{ sessions: [...], total }`
   - `/recordings` → `{ recordings: [...] }`
4. **文件流响应**
   - `/uploads/recordings/<filename>`

### 2.3 当前页面实际调用情况

#### `capture.html`
当前实际调用：

- `POST /api/capture/start-recording`
- `PUT /api/capture/stop-recording`
- `GET /api/capture/list?limit=20`
- `DELETE /api/capture/sessions/<session_id>`

当前未接入但属于 C2 目标接口范围、后续应纳入改造预留的有：

- `POST /api/capture/start`
- `GET /api/capture/active`
- `PUT /api/capture/request-recording`
- `PUT /api/capture/stop`
- `PUT /api/capture/save`
- `PUT /api/capture/register-file`
- `POST /api/capture/upload-file`

#### `recordings/index.html`
当前实际调用：

- `GET /api/capture/list?limit=100`
- `PUT /api/capture/sessions/<session_id>`
- `DELETE /api/capture/sessions/<session_id>`

当前页面 **未使用** 但阶段 C2 指定需分析的接口：

- `GET /api/capture/recordings`

#### `recordings/detail.html`
当前实际调用：

- `GET /api/capture/detail/<session_id>`
- `PUT /api/capture/sessions/<session_id>`
- `DELETE /api/capture/sessions/<session_id>`

---

## 3. 当前字段读取与改造方向

### 3.1 `capture.html`

#### 3.1.1 开始录音：`POST /api/capture/start-recording`

当前页面写法：

- 成功判断：`if (r.ok)`
- 成功字段：`r.session_id`、`r.status`
- 失败字段：`r.error`

当前后端返回：

```json
{
  "ok": true,
  "session_id": "xxx",
  "status": "recording",
  "message": "已开始录音"
}
```

按规范化推导，后端 C2 改造后页面 unwrap 后应直接拿到：

```json
{
  "session_id": "xxx",
  "status": "recording"
}
```

改造重点：

- 删除 `if (r.ok)`
- 保留 `r.session_id`、`r.status`
- 失败改为 `catch(e)` + `e.message`

#### 3.1.2 停止录音：`PUT /api/capture/stop-recording`

当前页面写法：

- 成功判断：`if (r.ok)`
- 成功字段：未依赖返回值主体，只依赖调用成功
- 失败字段：`r.error`

当前后端返回：

```json
{
  "ok": true,
  "status": "stopped",
  "session_id": "xxx",
  "message": "已停止录音"
}
```

unwrap 后预期仍是：

```json
{
  "status": "stopped",
  "session_id": "xxx"
}
```

改造重点：

- 不再依赖 `r.ok`
- 成功直接继续执行 `setStatus('idle') / loadRecordings()`
- 错误统一走 `catch(e)`

#### 3.1.3 历史列表：`GET /api/capture/list`

当前页面写法：

- 列表读取：`r.sessions`
- 列表项字段：
  - `s.session_id`
  - `s.audio_name`
  - `s.status`

当前后端返回：

```json
{
  "sessions": [...],
  "total": 20
}
```

根据迁移计划 §4.3，列表接口规范化后应转为 `PageVO[CaptureSessionVO]`，因此 unwrap 后预期读取：

```json
{
  "items": [...],
  "total": 20,
  "limit": 20,
  "offset": 0
}
```

改造重点：

- `r.sessions` → `r.items`
- `if (r.sessions && r.sessions.length > 0)` → `if (r.items && r.items.length > 0)`
- `r.total` 如后续使用可保持不变

#### 3.1.4 删除录音：`DELETE /api/capture/sessions/<session_id>`

当前页面写法：

- 调用后不检查返回 JSON 字段，仅在 `try/catch` 中按成功/失败分支处理

当前后端返回：

```json
{ "ok": true }
```

规范化后 unwrap 后预期可能为：

```json
{}
```
或
```json
{ "session_id": "xxx" }
```

前端建议：

- 不依赖任何成功字段
- 只要请求成功即视为删除成功
- 失败统一显示 `e.message`

#### 3.1.5 当前未接入但应预留的接口

为配合 `capture_controller` 正式规范化，`capture.html` 后续更推荐按“完整采集会话流”重构为：

1. `POST /api/capture/start` 创建会话
2. `GET /api/capture/active` 恢复活跃会话
3. `PUT /api/capture/request-recording` 请求录音
4. `PUT /api/capture/stop` 停止会话
5. `PUT /api/capture/save` 保存名称
6. `PUT /api/capture/register-file` 注册文件
7. `POST /api/capture/upload-file` 上传文件

这些接口当前页面还未用到，但规范化后建议统一按以下原则接入：

- `/start`、`/active`、`/request-recording`：继续读取平铺会话字段，如 `session_id`、`status`
- `/save`、`/register-file`、`/upload-file`、`/stop`：去掉 `ok/message` 分支，成功只读取实际业务字段
- `/upload-file` 成功后保留 `session_id`、`file_path` 等字段即可

### 3.2 `recordings/index.html`

#### 3.2.1 会话列表：`GET /api/capture/list`

当前页面写法：

- `r.sessions`
- `r.sessions.map(...)`
- 列表项字段：
  - `s.session_id`
  - `s.audio_name`
  - `s.duration_sec`
  - `s.status`
  - `s.created_at`

规范化后 unwrap 预期：

- `r.sessions` → `r.items`
- `r.total` 保持 `r.total`
- 列表项内部字段大概率保持不变，继续按 `CaptureSessionVO` 平铺读取

#### 3.2.2 编辑文件名：`PUT /api/capture/sessions/<session_id>`

当前页面写法：

- `if (r.ok)` 成功
- 否则读取 `r.error`

当前后端返回：

```json
{ "ok": true, "audio_name": "xxx.wav" }
```

规范化后 unwrap 后建议按：

```json
{ "audio_name": "xxx.wav" }
```

改造重点：

- 删除 `if (r.ok)`
- 只要请求成功即关闭弹窗并刷新列表
- 如需使用返回值，仅读取 `r.audio_name`
- 错误统一 `catch(e)`

#### 3.2.3 删除录音：`DELETE /api/capture/sessions/<session_id>`

当前页面写法：

- `if (r.ok)` 成功
- 否则读取 `r.error`

规范化后：

- 不再读取 `r.ok`
- 成功即刷新列表
- 失败统一 `catch(e)`

#### 3.2.4 录音列表接口预留：`GET /api/capture/recordings`

当前页面未调用该接口。

现有后端返回：

```json
{
  "recordings": [
    {
      "session_id": "xxx",
      "audio_name": "xxx.wav",
      "file_path": "...",
      "duration_sec": 12.3
    }
  ]
}
```

根据迁移计划，非分页集合响应应直接把 `list[VO]` 放在 `Result.result` 中。因此规范化后 unwrap 后页面若未来切换到该接口，应改为：

- `r.recordings` → `r`
- 列表项字段继续读取：
  - `item.session_id`
  - `item.audio_name`
  - `item.file_path`
  - `item.duration_sec`

这意味着如果后续 `recordings/index.html` 从“会话视角”改成“录音文件视角”，应优先选择 `/api/capture/recordings`，并直接把 unwrap 后结果当数组使用。

### 3.3 `recordings/detail.html`

#### 3.3.1 会话详情：`GET /api/capture/detail/<session_id>`

当前页面写法：

- 错误判断：`if (r.error) { alert(r.error); return; }`
- 成功时直接把 `r` 当详情对象
- 读取字段：
  - `r.session_id`
  - `r.audio_name`
  - `r.duration_sec`
  - `r.sample_rate`
  - `r.status`
  - `r.created_at`
  - `r.file_path`

当前后端直接返回 session dict。

规范化后 unwrap 后仍应是单个 `CaptureSessionVO` 或等价详情对象，因此页面字段大概率可以保持：

- `r.session_id`
- `r.audio_name`
- `r.duration_sec`
- `r.sample_rate`
- `r.status`
- `r.created_at`
- `r.file_path`

改造重点：

- 删除 `if (r.error)`
- 改为 `try/catch`
- 音频预览逻辑继续基于 `file_path`，但需待后端 C2 确认是否会改成 `file_url`

#### 3.3.2 编辑文件名：`PUT /api/capture/sessions/<session_id>`

当前页面写法：

- `if (r.ok)` 成功
- 否则读取 `r.error`

规范化后建议：

- 成功即 `alert('保存成功')` 并刷新详情
- 不再读取 `r.ok`
- 如需读取返回值，仅使用 `r.audio_name`
- 错误统一 `catch(e)`

#### 3.3.3 删除录音：`DELETE /api/capture/sessions/<session_id>`

当前页面写法：

- `if (r.ok)` 成功
- 否则读取 `r.error`

规范化后建议：

- 成功即跳转回列表
- 不再读取 `r.ok`
- 失败统一 `catch(e)`

---

## 4. 页面改造对照表

| 页面 | 接口 | 原字段访问 | 新字段访问 | 改动类型 |
|------|------|-----------|-----------|---------|
| `capture.html` | `POST /api/capture/start-recording` | `if (r.ok)` | `try/catch` | 错误处理 |
| `capture.html` | `POST /api/capture/start-recording` | `r.session_id` | `r.session_id` | 不变 |
| `capture.html` | `POST /api/capture/start-recording` | `r.status` | `r.status` | 不变 |
| `capture.html` | `POST /api/capture/start-recording` | `r.error` | `e.message` | 错误处理 |
| `capture.html` | `PUT /api/capture/stop-recording` | `if (r.ok)` | `try/catch` | 错误处理 |
| `capture.html` | `PUT /api/capture/stop-recording` | `r.error` | `e.message` | 错误处理 |
| `capture.html` | `GET /api/capture/list` | `r.sessions` | `r.items` | 字段路径 |
| `capture.html` | `GET /api/capture/list` | `r.sessions.map(...)` | `r.items.map(...)` | 字段路径 |
| `capture.html` | `GET /api/capture/list` | `if (r.sessions && r.sessions.length > 0)` | `if (r.items && r.items.length > 0)` | 字段路径 |
| `capture.html` | `DELETE /api/capture/sessions/<id>` | 成功后默认继续执行，不依赖字段 | 保持不依赖字段 | 不变 |
| `capture.html` | `POST /api/capture/start` | 当前页面未使用 | 预期读取 `r.session_id`、`r.status`、`r.created_at` | 预留接入 |
| `capture.html` | `GET /api/capture/active` | 当前页面未使用 | 预期读取 `r.session_id`、`r.status` | 预留接入 |
| `capture.html` | `PUT /api/capture/request-recording` | 当前页面未使用 | 预期读取 `r.session_id`、`r.status` | 预留接入 |
| `capture.html` | `PUT /api/capture/stop` | 当前页面未使用 | 成功不再依赖 `ok`，按 `try/catch` 处理 | 预留接入 |
| `capture.html` | `PUT /api/capture/save` | 当前页面未使用 | 预期读取 `r.session_id`、`r.audio_name` | 预留接入 |
| `capture.html` | `PUT /api/capture/register-file` | 当前页面未使用 | 成功不再依赖 `ok/message`，保留 `r.session_id`、`r.status` | 预留接入 |
| `capture.html` | `POST /api/capture/upload-file` | 当前页面未使用 | 成功不再依赖 `ok`，保留 `r.session_id`、`r.file_path` | 预留接入 |
| `recordings/index.html` | `GET /api/capture/list` | `r.sessions` | `r.items` | 字段路径 |
| `recordings/index.html` | `GET /api/capture/list` | `r.sessions.map(...)` | `r.items.map(...)` | 字段路径 |
| `recordings/index.html` | `PUT /api/capture/sessions/<id>` | `if (r.ok)` | `try/catch` | 错误处理 |
| `recordings/index.html` | `PUT /api/capture/sessions/<id>` | `r.audio_name` | `r.audio_name` | 不变 |
| `recordings/index.html` | `PUT /api/capture/sessions/<id>` | `r.error` | `e.message` | 错误处理 |
| `recordings/index.html` | `DELETE /api/capture/sessions/<id>` | `if (r.ok)` | `try/catch` | 错误处理 |
| `recordings/index.html` | `DELETE /api/capture/sessions/<id>` | `r.error` | `e.message` | 错误处理 |
| `recordings/index.html` | `GET /api/capture/recordings` | 当前页面未使用 | 若切换接入：`r.recordings` → `r` | 预留接入 |
| `recordings/detail.html` | `GET /api/capture/detail/<session_id>` | `if (r.error)` | `try/catch` | 错误处理 |
| `recordings/detail.html` | `GET /api/capture/detail/<session_id>` | `const s = r` | `const s = r` | 不变 |
| `recordings/detail.html` | `GET /api/capture/detail/<session_id>` | `s.session_id / s.audio_name / s.duration_sec / s.sample_rate / s.status / s.created_at / s.file_path` | 预期保持不变 | 不变 |
| `recordings/detail.html` | `PUT /api/capture/sessions/<id>` | `if (r.ok)` | `try/catch` | 错误处理 |
| `recordings/detail.html` | `PUT /api/capture/sessions/<id>` | `r.error` | `e.message` | 错误处理 |
| `recordings/detail.html` | `DELETE /api/capture/sessions/<id>` | `if (r.ok)` | `try/catch` | 错误处理 |
| `recordings/detail.html` | `DELETE /api/capture/sessions/<id>` | `r.error` | `e.message` | 错误处理 |

---

## 5. 推荐的页面级改造方案

## 5.1 `capture.html`

### 5.1.1 调用层统一

当前页面全部使用原生 `fetch(...).then(x=>x.json())`。

建议改为：

- `start-recording` → `apiPost`
- `stop-recording` → `apiPut`
- `list` → `apiGet`
- `sessions/<id>` DELETE → `apiDelete`

### 5.1.2 业务流调整建议

当前页面仍使用兼容接口 `/start-recording` + `/stop-recording`。

阶段 C2 文档层建议同时预留两种方案：

1. **最小改造方案**
   - 保留现有兼容接口
   - 只做字段路径与错误处理升级
2. **正式流程方案**
   - 切换为 `/start` → `/active` → `/request-recording` → `/stop` → `/save` / `/register-file` / `/upload-file`
   - 页面状态机按会话状态驱动，而不是仅靠本地 `currentSessionId`

在后端 C2 设计文档未定前，前端先按 **最小改造方案** 落地更稳妥。

## 5.2 `recordings/index.html`

### 5.2.1 列表视图

当前页面实际展示的是“录音会话列表”，不是纯“已上传录音文件列表”。

因此若继续保留现有表结构，推荐继续使用：

- `GET /api/capture/list`
- 读取 `r.items`

### 5.2.2 是否切换到 `/api/capture/recordings`

若后续要把页面聚焦为“可用录音文件选择器”，则更适合切换到：

- `GET /api/capture/recordings`

届时页面要从：

- `r.sessions` / `r.items`

切换为：

- 直接使用数组 `r`

此项属于后续交互层面的待确认，不必在 C2 第一版前端改造中强制切换。

## 5.3 `recordings/detail.html`

### 5.3.1 详情对象字段

基于现有后端 `get_session_detail` 直接返回 session dict 的实现判断，规范化后该页面最可能是“外层 Result 包裹变化、内层详情字段尽量保持不变”。

因此该页面的主要改造应集中在：

- 请求方式统一到 `api.js`
- `if (r.error)` → `try/catch`
- `if (r.ok)` → `try/catch`

### 5.3.2 音频预览字段

当前页面使用：

- `s.file_path`

并直接设置：

- `audio.src = API_BASE + s.file_path`

待确认项：

- 后端 C2 是否继续返回 `file_path`
- 是否会新增更适合前端直接播放的 `file_url`

若后端 VO 新增 `file_url`，前端建议优先使用：

- `s.file_url || (API_BASE + s.file_path)`

---

## 6. 错误处理改造

阶段 C2 应完全沿用阶段 B / C1 的统一模式：**页面层统一 `try/catch`，不再在业务代码里判断 `r.ok` / `r.error`。**

### 6.1 需要清理的旧模式

以下模式在三个页面中均应清理：

- `if (r.ok) { ... } else { alert(r.error) }`
- `if (r.error) { ... }`
- 原生 `fetch(...).then(x=>x.json())` 直接读旧响应

### 6.2 推荐标准写法

```js
try {
    const r = await apiPut('/api/capture/sessions/' + sessionId, {
        audio_name: fileName
    });
    // 成功逻辑
} catch (e) {
    alert(e.message);
}
```

### 6.3 页面分场景要求

#### `capture.html`
- 开始录音失败：`alert('开始录音失败: ' + e.message)`
- 停止录音失败：`alert('停止录音失败: ' + e.message)`
- 放弃录音失败：`alert('放弃失败: ' + e.message)`
- 加载历史失败：不要静默吞错，建议展示“加载失败”文案

#### `recordings/index.html`
- 列表加载失败：页面区域显示 `加载失败: ${e.message}`
- 编辑失败：`alert(e.message)`
- 删除失败：`alert(e.message)`

#### `recordings/detail.html`
- 详情加载失败：`alert('加载失败: ' + e.message)`
- 保存失败：`alert('保存失败: ' + e.message)`
- 删除失败：`alert('删除失败: ' + e.message)`

### 6.4 与阶段 B/C1 的一致性要求

C2 改造完成后，capture/recordings 页面应满足：

- grep 不到 `if (r.ok)`
- grep 不到 `if (r.error)` 作为接口成功失败判断
- 统一走 `api.js` 封装
- 错误文案统一来自 `e.message`

---

## 7. 验收清单

### 7.1 `capture.html`

- [ ] `POST /api/capture/start-recording` 改为通过 `apiPost` 调用
- [ ] `PUT /api/capture/stop-recording` 改为通过 `apiPut` 调用
- [ ] `GET /api/capture/list` 改为通过 `apiGet` 调用
- [ ] `DELETE /api/capture/sessions/<id>` 改为通过 `apiDelete` 调用
- [ ] 页面内不再出现 `if (r.ok)`
- [ ] 页面内不再出现 `r.error`
- [ ] 历史列表读取从 `r.sessions` 改为 `r.items`
- [ ] 开始/停止/放弃录音失败时统一提示 `e.message`
- [ ] `loadRecordings()` 失败时不再静默吞错

### 7.2 `recordings/index.html`

- [ ] 会话列表请求改为通过 `apiGet('/api/capture/list', ...)` 发起
- [ ] 列表读取从 `r.sessions` 改为 `r.items`
- [ ] 编辑文件名请求改为通过 `apiPut('/api/capture/sessions/:id', ...)` 发起
- [ ] 删除请求改为通过 `apiDelete('/api/capture/sessions/:id')` 发起
- [ ] 页面内不再出现 `if (r.ok)`
- [ ] 页面内不再读取 `r.error`
- [ ] 编辑成功后仍能正确关闭弹窗并刷新列表
- [ ] 删除成功后仍能正确刷新列表
- [ ] 列表项字段 `session_id / audio_name / duration_sec / status / created_at` 显示正常

### 7.3 `recordings/detail.html`

- [ ] 详情请求改为通过 `apiGet('/api/capture/detail/:id')` 发起
- [ ] 页面内不再出现 `if (r.error)`
- [ ] 页面内不再出现 `if (r.ok)`
- [ ] 保存名称请求改为 `try/catch`
- [ ] 删除请求改为 `try/catch`
- [ ] 详情字段 `session_id / audio_name / duration_sec / sample_rate / status / created_at / file_path` 渲染正常
- [ ] 音频预览仍能正常播放
- [ ] 删除成功后仍能正确跳转回录音列表

### 7.4 待后端 C2 文档确认项

- [ ] `GET /api/capture/list` 是否确定返回 `PageVO[CaptureSessionVO]`，字段名是否为 `items`
- [ ] `GET /api/capture/detail/<session_id>` 的详情字段是否完全沿用当前 session dict 字段
- [ ] `PUT /api/capture/sessions/<id>` 的成功 `result` 是否保留 `audio_name`
- [ ] `DELETE /api/capture/sessions/<id>` 的成功 `result` 是否为空对象
- [ ] `GET /api/capture/recordings` 是否确定返回 `list[CaptureRecordingVO]` 而非 `{ recordings: [...] }`
- [ ] 详情页与列表页中的音频地址字段是否继续使用 `file_path`，还是新增 `file_url`
- [ ] `capture.html` 是否继续保留兼容接口 `/start-recording`、`/stop-recording`，还是要求切换到正式流程接口组

---

## 8. 结论

阶段 C2 对 capture/recordings 页面前端的核心影响主要有三类：

1. **外层响应包装统一**：所有页面都要切到 `api.js + unwrap + try/catch`，移除 `r.ok / r.error`。
2. **列表接口字段变化**：`/api/capture/list` 的页面读取将从 `r.sessions` 改成 `r.items`。
3. **非分页录音列表接口变化**：若后续接入 `/api/capture/recordings`，页面读取要从 `r.recordings` 改成直接使用数组 `r`。

整体来看，C2 前端改造属于 **中等规模适配**：

- `recordings/detail.html` 以错误处理改造为主，详情字段大概率可维持平铺访问。
- `capture.html` 和 `recordings/index.html` 除错误处理外，还需要处理列表字段从 `sessions` 到 `items` 的切换。
- `capture.html` 还存在“兼容接口继续沿用 / 正式流程接口切换”的方案选择，需待后端 C2 设计文档确认后再最终拍板。
