# 接口规范化-阶段C1-transcribe页面改造方案

## 1. 目标与范围

本方案用于配合后端 `transcribe_controller` 在阶段 C1 的接口规范化改造，覆盖以下两个页面：

- `frontend/pages/transcribe/index.html`
- `frontend/pages/transcribe/history.html`

本次仅输出前端改造设计文档，不进入实现。

> 说明：后端 C1 设计文档尚未产出，本文先基于当前 `backend/controllers/transcribe_controller.py` 与阶段 A / B 既有规范推导改造方案。待后端 C1 文档完成后，需再次对照确认字段名是否完全一致。

---

## 2. 现状分析

### 2.1 规范化基线

根据迁移计划：

1. 后端接口将统一返回 `Result` 结构：
   - 成功：`{ code: 200, description: 'success', result: ... }`
   - 失败：`{ code: 非200, description: 错误信息, result: null }`
2. 前端 `api.js` 已在阶段 A / B 方案中引入 `unwrap`：
   - 成功时自动返回 `body.result`
   - 失败时抛出 `Error`，页面通过 `try/catch` 处理
3. 页面层不再保留 `if (r.ok)`、`if (r.error)` 这类旧判断

### 2.2 当前 `transcribe_controller` 返回形状

#### `POST /api/transcribe/start`
当前返回：

```json
{
  "ok": true,
  "task_id": "task_xxx",
  "message": "Task submitted"
}
```

失败时返回：

```json
{
  "error": "..."
}
```

#### `GET /api/transcribe/status/<task_id>`
当前成功返回 `_serialize_task(task)`，字段包括：

- `task_id`
- `song_id`
- `mode`
- `status`
- `result_path`
- `error`
- `created_at`
- `updated_at`
- `vocal_stem_path`（有值时才返回）

失败时返回：

```json
{ "error": "Task not found" }
```

#### `GET /api/transcribe/song/<song_id>`
当前成功返回：

```json
{
  "tasks": [ ...serialized tasks... ]
}
```

异常时当前实现存在兼容性旧写法：

```json
{
  "tasks": [],
  "error": "..."
}
```

---

## 3. 页面当前调用与字段读取

### 3.1 `transcribe/index.html`

页面当前包含两个接口调用场景。

#### 3.1.1 发起转写：`POST /api/transcribe/start`

当前代码：

- 使用原生 `fetch`
- 请求体：`{ song_id, mode }`
- 成功判断：`if (r.ok)`
- 成功字段读取：
  - `r.task_id`
- 失败字段读取：
  - `r.error`

当前依赖点：

- 页面提交成功后显示任务卡片
- 用 `r.task_id` 启动轮询

#### 3.1.2 轮询任务状态：`GET /api/transcribe/status/<task_id>`

当前代码：

- 使用原生 `fetch`
- 直接读取平铺字段：
  - `r.status`
  - `r.result_path`
  - `r.error`

当前页面状态分支：

- `r.status === 'completed'`
- `r.status === 'failed'`
- 其他状态直接展示 `r.status`

> 注意：后端线程内部曾写入 `processing` 状态，而页面样式文案当前历史页对 `running` 做了兼容；C1 实施时需要确认最终规范状态枚举是否统一为 `processing` 或 `running`。

#### 3.1.3 歌曲列表：`GET /api/songs/list`

本页面还调用歌曲列表接口，当前读取：

- `r.songs`

这一部分已经受阶段 B 规范影响，后续应同步按 `songs` 模块既定方案改为：

- `r.items`

虽然本次 C1 核心是 transcribe 接口，但 `transcribe/index.html` 要真正可用，页面内该处也应一并纳入改造范围。

### 3.2 `transcribe/history.html`

页面当前包含两个接口调用场景。

#### 3.2.1 加载歌曲信息：`GET /api/songs/<id>`

当前代码：

- 使用原生 `fetch`
- 错误判断：`if (r.error) return`
- 成功字段读取：
  - `r.title`
  - `r.artist_name`

该接口属于 songs 模块，按阶段 B 经验应统一改为 `try/catch`，不再判断 `r.error`。

#### 3.2.2 加载转写历史：`GET /api/transcribe/song/<song_id>`

当前代码：

- 使用原生 `fetch`
- 当前任务列表读取：
  - `const tasks = r.tasks || []`
- 列表项字段读取：
  - `t.task_id`
  - `t.mode`
  - `t.status`
  - `t.created_at`
  - `t.result_path`
  - `t.error`

当前页面未调用 `GET /api/transcribe/status/<id>`，历史列表完全来自 `GET /api/transcribe/song/<id>`。

---

## 4. 改造原则

### 4.1 页面统一通过 `api.js` 调用

参考阶段 B 已落地模式：

- 不再在页面内手写 `fetch(...).then(x => x.json())`
- 统一使用 `apiGet` / `apiPost`
- 由 `api.js` 的 `unwrap` 统一处理 `Result` 包裹

即：

- 页面拿到的是 `result` 本体
- 页面不直接感知 `code` / `description` / `result`
- 失败时统一在 `catch(e)` 中读取 `e.message`

### 4.2 页面层统一改为 `try/catch`

参考阶段 B 的标准模式：

- 删除 `if (r.ok)`
- 删除 `if (r.error)`
- 删除对旧响应 `error` 字段的直接判断
- 业务失败统一走异常分支

### 4.3 字段路径变化只关注 unwrap 后结果

由于 `api.js` 已自动做 `Result.result` 解包，页面改造时应按“unwrap 后字段”描述：

- 若后端 `result` 内仍是单对象，则页面仍按对象字段读取
- 若后端 `result` 改为列表，则页面直接把返回值当数组使用
- 若后端 `result` 改为 `PageVO`，则页面使用 `r.items`

---

## 5. 页面改造对照表

| 页面 | 原字段访问 | 新字段访问 | 改动类型 |
|------|-----------|-----------|---------|
| `transcribe/index.html` 歌曲列表 | `r.songs` | `r.items` | 中改（沿用阶段 B 的 songs 列表规范） |
| `transcribe/index.html` 发起转写 | `if (r.ok)`, `r.task_id`, `r.error` | `try/catch` + `r.task_id`，错误改读 `e.message` | 中改 |
| `transcribe/index.html` 轮询状态 | `r.status`, `r.result_path`, `r.error` | `r.status`, `r.result_path`, `r.error`（经 unwrap 后字段本体不变） | 小改（调用方式/错误处理改造） |
| `transcribe/history.html` 歌曲信息 | `if (r.error) return`, `r.title`, `r.artist_name` | `try/catch` + `r.title`, `r.artist_name` | 小改 |
| `transcribe/history.html` 任务历史列表 | `r.tasks` | `r`（直接把 unwrap 后结果当任务数组） | 中改 |
| `transcribe/history.html` 历史任务项 | `t.task_id`, `t.mode`, `t.status`, `t.created_at`, `t.result_path`, `t.error` | 预期保持不变：`t.task_id`, `t.mode`, `t.status`, `t.created_at`, `t.result_path`, `t.error` | 小改 |

---

## 6. 逐页改造方案

### 6.1 `transcribe/index.html`

#### 6.1.1 歌曲列表加载

当前：

- 页面调用 `/api/songs/list`
- 直接读取 `r.songs`

改造后：

- 改为 `apiGet('/api/songs/list', { keyword: kw })`
- 按阶段 B 规范读取：
  - `r.items`
  - `r.total` 如页面后续需要可继续使用

影响：

- 列表空判断：`r.songs && r.songs.length > 0` → `r.items && r.items.length > 0`
- 列表渲染：`r.songs.map(...)` → `r.items.map(...)`

#### 6.1.2 发起转写

当前：

```js
const r = await fetch('/api/transcribe/start', ...).then(x => x.json());
if (r.ok) {
  startPollTask(r.task_id);
} else {
  alert(r.error || '提交失败');
}
```

按规范推导，后端 C1 改造后接口返回应为：

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

> `status` 字段是否在启动接口中保留，需以后端 C1 文档为准；如果后端仅返回 `task_id`，则页面只读取 `r.task_id` 即可。

unwrap 后页面应读取：

- `r.task_id`
- 如后端保留初始状态字段，可读取 `r.status`

改造要点：

- 调用改为 `apiPost('/api/transcribe/start', { song_id, mode })`
- 删除 `if (r.ok)` 分支
- 统一用 `try/catch`
- 失败提示改为 `alert(e.message)`

#### 6.1.3 任务状态轮询

当前调用：

- `GET /api/transcribe/status/<task_id>`

当前读取：

- `r.status`
- `r.result_path`
- `r.error`

按规范推导，后端 C1 改造后接口返回应为：

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "task_id": "task_xxx",
    "song_id": 1,
    "mode": "melody",
    "status": "completed",
    "result_path": "/uploads/...",
    "error": null,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

unwrap 后页面字段路径：

- `r.status`
- `r.result_path`
- `r.error`

因此本处**字段本体大概率不变**，改造重点在：

- 调用方式切为 `apiGet`
- 错误处理切为 `try/catch`
- 页面轮询异常时避免无提示静默失败，可保留 `console.error(e)` 或在状态区显示错误信息

### 6.2 `transcribe/history.html`

#### 6.2.1 歌曲信息加载

当前：

```js
const r = await fetch('/api/songs/'+songId).then(x => x.json());
if (r.error) return;
```

改造后：

- 改为 `apiGet('/api/songs/' + songId)`
- 删除 `if (r.error)`
- 通过 `try/catch` 控制失败分支
- 成功字段继续读取：
  - `r.title`
  - `r.artist_name`

#### 6.2.2 转写历史加载

当前：

```js
const r = await fetch('/api/transcribe/song/'+currentSongId).then(x => x.json());
const tasks = r.tasks || [];
```

根据迁移计划 §4.3：

- 原响应：`{ tasks: [...] }`
- 新响应：`result` 中直接放 `list[TranscribeTaskVO]`

因此后端 C1 改造后预期返回：

```json
{
  "code": 200,
  "description": "success",
  "result": [
    {
      "task_id": "task_xxx",
      "song_id": 1,
      "mode": "melody",
      "status": "completed",
      "result_path": "...",
      "error": null,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

unwrap 后页面应改为：

```js
const tasks = r || [];
```

即：

- `r.tasks` → `r`
- 任务项内部字段暂按 VO 平铺读取

#### 6.2.3 历史任务字段访问

当前列表项读取字段：

- `t.task_id`
- `t.mode`
- `t.status`
- `t.created_at`
- `t.result_path`
- `t.error`

按当前 `_serialize_task` 迁移到 `TranscribeTaskVO.from_domain` 的路线判断，字段名大概率保持不变。

但以下项需在后端 C1 文档出炉后重点复核：

1. `status` 枚举值是否统一
   - 当前页面兼容 `pending` / `running` / `failed` / `completed`
   - 现有后端线程中出现 `processing`
2. `result_path` 是否保留该字段名
   - 若后端 VO 改成 `result_url` 或 `download_url`，前端下载链接需同步调整
3. `error` 是否继续作为失败原因字段
   - 若改为 `error_message`，页面展示字段需同步

---

## 7. 错误处理改造

本模块统一采用阶段 B 已落地模式：**页面侧全部改为 `try/catch`**。

### 7.1 需要删除的旧模式

#### `transcribe/index.html`

- `if (r.ok) { ... } else { ... }`
- `alert(r.error || '提交失败')`
- 直接 `fetch(...).then(x => x.json())`

#### `transcribe/history.html`

- `if (r.error) return`
- `const tasks = r.tasks || []`
- 直接 `fetch(...).then(x => x.json())`

### 7.2 统一后的页面处理模式

推荐统一结构：

```js
try {
  const r = await apiGet(...);
  // 成功分支直接使用 unwrap 后结果
} catch (e) {
  alert(e.message);
}
```

对于轮询类接口，可根据场景稍作调整：

- 用户主动触发的提交/刷新：可直接 `alert(e.message)`
- 后台轮询：优先更新页面状态区，避免反复弹窗干扰

### 7.3 与阶段 B 的一致性要求

C1 改造完成后，transcribe 页面应满足与阶段 B 相同的代码风格验收：

- grep 不到 `r.ok`
- grep 不到 `r.error`（作为响应判断）
- 不手动处理 `payload.code` / `payload.result`
- 页面调用优先统一走 `apiGet` / `apiPost`

> 说明：任务对象上的 `t.error` 属于业务数据字段，不属于旧响应判断逻辑，可保留。

---

## 8. 验收清单

### 8.1 页面结构与调用改造

- [ ] `transcribe/index.html` 的歌曲列表请求改为通过 `apiGet('/api/songs/list', ...)` 发起
- [ ] `transcribe/index.html` 列表渲染从 `r.songs` 改为 `r.items`
- [ ] `transcribe/index.html` 发起转写请求改为通过 `apiPost('/api/transcribe/start', ...)` 发起
- [ ] `transcribe/index.html` 不再使用 `if (r.ok)` 判断提交结果
- [ ] `transcribe/index.html` 轮询状态请求改为通过 `apiGet('/api/transcribe/status/:taskId')` 发起
- [ ] `transcribe/history.html` 歌曲信息请求改为通过 `apiGet('/api/songs/:id')` 发起
- [ ] `transcribe/history.html` 历史列表请求改为通过 `apiGet('/api/transcribe/song/:songId')` 发起
- [ ] `transcribe/history.html` 任务列表读取从 `r.tasks` 改为 `r`

### 8.2 错误处理改造

- [ ] `transcribe/index.html` 提交任务改为 `try/catch`
- [ ] `transcribe/index.html` 加载歌曲列表改为 `try/catch`
- [ ] `transcribe/index.html` 轮询状态请求具备统一异常处理
- [ ] `transcribe/history.html` 加载歌曲信息改为 `try/catch`
- [ ] `transcribe/history.html` 加载历史列表改为 `try/catch`
- [ ] 页面中不再出现 `alert(r.error)` / `if (r.error)` / `if (r.ok)`

### 8.3 字段访问验收

- [ ] `transcribe/index.html` 启动任务后仍能正确读取 `r.task_id` 并开始轮询
- [ ] `transcribe/index.html` 任务完成后仍能正确读取 `r.result_path`
- [ ] `transcribe/index.html` 任务失败后仍能正确读取 `r.error` 作为任务失败原因展示
- [ ] `transcribe/history.html` 能正确渲染任务数组
- [ ] `transcribe/history.html` 能正确展示 `task_id / mode / status / created_at`
- [ ] `transcribe/history.html` 在完成态能正确生成下载链接
- [ ] `transcribe/history.html` 在失败态能正确展示任务错误信息

### 8.4 待后端 C1 文档确认项

- [ ] `POST /api/transcribe/start` 的 `result` 是否包含 `status`
- [ ] `GET /api/transcribe/status/<id>` 的状态枚举是否为 `pending / processing / completed / failed`
- [ ] `GET /api/transcribe/song/<id>` 是否确定返回 `list[TranscribeTaskVO]` 而非 `{ tasks: [...] }`
- [ ] `TranscribeTaskVO` 是否保留 `result_path` / `error` 字段名不变
- [ ] `vocal_stem_path` 是否需要在前端历史页补充展示能力

---

## 9. 结论

阶段 C1 对 transcribe 页面前端的核心影响，不在于“所有字段都改名”，而在于以下两类变化：

1. **响应包装变化**：所有 transcribe 接口都会从“平铺 JSON / error 字段”切换为 `Result` 包裹，由 `api.js` `unwrap` 统一解包；页面侧必须改为 `try/catch`。
2. **列表字段变化**：`history.html` 的任务列表读取将从 `r.tasks` 改为直接使用 `r`；`index.html` 内部歌曲列表读取也需从 `r.songs` 改为 `r.items`。

除了上述变化外，按当前 `_serialize_task` → `TranscribeTaskVO` 的迁移推断，任务项内部字段大概率可保持平铺访问方式，页面改动量整体可控，属于**中小规模前端适配**。
