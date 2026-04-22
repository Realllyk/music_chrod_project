# 接口规范化-阶段C4-audio_sources页面改造方案

## 1. 目标与范围

本方案用于配合后端 `audio_sources_controller` 在阶段 C4 的接口规范化改造，覆盖以下页面：

- `frontend/pages/audio-sources/index.html`
- `frontend/pages/audio-sources/upload.html`
- `frontend/pages/audio-sources/details.html`

本次 **只输出前端改造设计文档，不进入实现**。

> 说明：本文基于当前 `backend/controllers/audio_sources_controller.py`、`frontend/js/api.js`、以及现有 audio-sources 三个页面的真实调用情况整理。若后端 C4 最终 VO/Result 文档与本文推导不一致，需要在联调前再做一次字段复核。

---

## 2. 现状分析

### 2.1 规范化基线

根据阶段 A 已落地的前端基础设施，C4 页面改造应遵循以下统一规则：

1. 后端接口逐步统一为 `Result` 结构：
   - 成功：`{ code: 200, description: 'success', result: ... }`
   - 失败：`{ code: 非200, description: 错误信息, result: null }`
2. `frontend/js/api.js` 已具备 `unwrap`：
   - 成功时返回 `result`
   - 失败时抛出 `Error`
3. 页面层应统一改为：
   - 使用 `apiGet/apiPost/apiDelete/apiPostForm`
   - 使用 `try/catch`
   - 不再读取 `r.ok` / `r.error`

### 2.2 当前 `audio_sources_controller` 返回形状

结合当前后端代码，audio-sources 相关接口返回大致如下。

#### `GET /api/audio-sources/list`
当前返回：

```json
{
  "sources": [
    {
      "id": 1,
      "source_type": "upload",
      "source_id": null,
      "audio_name": "demo",
      "file_path": "https://...",
      "file_size": 12345,
      "duration_sec": null,
      "sample_rate": null,
      "channels": null,
      "format": "mp3",
      "status": "active",
      "created_at": "2026-04-22 00:00:00"
    }
  ],
  "total": 1
}
```

#### `GET /api/audio-sources/<audio_id>`
当前成功直接返回单个音源对象：

```json
{
  "id": 1,
  "source_type": "upload",
  "source_id": null,
  "audio_name": "demo",
  "file_path": "https://...",
  "file_size": 12345,
  "duration_sec": null,
  "sample_rate": null,
  "channels": null,
  "format": "mp3",
  "status": "active",
  "created_at": "2026-04-22 00:00:00"
}
```

失败返回：

```json
{ "error": "Audio source not found" }
```

#### `DELETE /api/audio-sources/<audio_id>`
当前成功返回：

```json
{ "ok": true }
```

失败返回：

```json
{ "error": "Delete failed" }
```

#### `POST /api/audio-sources/upload`
当前使用 `multipart/form-data`。

成功返回：

```json
{
  "ok": true,
  "audio_source_id": 123,
  "audio_name": "demo",
  "file_path": "https://..."
}
```

失败返回：

```json
{ "error": "请选择音频文件" }
```

#### `GET /api/audio-sources/oss-files`
当前返回：

```json
{
  "files": ["https://...", "https://..."],
  "total": 2
}
```

> 当前前端三个页面均 **未使用** `/oss-files`，但它属于 audio_sources_controller 的接口范围，建议在文档中作为“预留接口”记录。

### 2.3 当前页面实际调用情况

#### `audio-sources/index.html`
当前实际调用：
- `GET /api/audio-sources/list`
- `DELETE /api/audio-sources/<id>`

当前字段读取：
- `r.sources`
- `s.id`
- `s.audio_name`
- `s.format`
- `s.file_size`
- `s.status`
- `s.created_at`
- 删除时读取 `r.ok` / `r.error`

#### `audio-sources/upload.html`
当前实际调用：
- `POST /api/audio-sources/upload`

当前字段读取：
- 成功判断：`data.ok`
- 成功字段：`data.audio_source_id`
- 失败字段：`data.error`

提交字段：
- `audio_name`
- `audio_file`

#### `audio-sources/details.html`
当前实际调用：
- `GET /api/audio-sources/<id>`
- `DELETE /api/audio-sources/<id>`

当前字段读取：
- 加载失败判断：`if(r.error)`
- 详情字段：
  - `r.id`
  - `r.audio_name`
  - `r.format`
  - `r.file_size`
  - `r.status`
  - `r.created_at`
  - `r.file_path`
- 删除时读取 `r.ok` / `r.error`
- 音频预览直接使用 `audioPlayer.src = API_BASE + s.file_path`

---

## 3. 页面改造对照表

| 页面 | 接口 | 原字段访问 | 新字段访问 | 改动类型 |
|------|------|-----------|-----------|---------|
| `audio-sources/index.html` | `GET /api/audio-sources/list` | `r.sources` | `r.items` | 字段路径 |
| `audio-sources/index.html` | `GET /api/audio-sources/list` | `r.sources.map(...)` | `r.items.map(...)` | 字段路径 |
| `audio-sources/index.html` | `DELETE /api/audio-sources/:id` | `if(r.ok)` | `try/catch` | 错误处理 |
| `audio-sources/index.html` | `DELETE /api/audio-sources/:id` | `r.error` | `e.message` | 错误处理 |
| `audio-sources/upload.html` | `POST /api/audio-sources/upload` | `if(data.ok)` | `try/catch` | 错误处理 |
| `audio-sources/upload.html` | `POST /api/audio-sources/upload` | `data.audio_source_id` | `r.audio_source_id` | 不变 |
| `audio-sources/upload.html` | `POST /api/audio-sources/upload` | `data.error` | `e.message` | 错误处理 |
| `audio-sources/details.html` | `GET /api/audio-sources/:id` | `if(r.error)` | `try/catch` | 错误处理 |
| `audio-sources/details.html` | `GET /api/audio-sources/:id` | `r.id / r.audio_name / r.format / r.file_size / r.status / r.created_at / r.file_path` | 预期保持不变 | 不变 |
| `audio-sources/details.html` | `DELETE /api/audio-sources/:id` | `if(r.ok)` | `try/catch` | 错误处理 |
| `audio-sources/details.html` | `DELETE /api/audio-sources/:id` | `r.error` | `e.message` | 错误处理 |
| `audio-sources/details.html` | 音频预览 | `API_BASE + s.file_path` | `s.file_url || s.file_path` | 字段/兼容性 |
| `audio-sources/*` | `GET /api/audio-sources/oss-files` | 当前未使用 | 预留接入 | 预留 |

---

## 4. 逐页改造方案

### 4.1 `audio-sources/index.html`

#### 4.1.1 当前写法

当前列表页直接请求：

- `GET /api/audio-sources/list`

并按旧响应读取：

```js
const r = await fetch('/api/audio-sources/list').then(x => x.json());
if (r.sources && r.sources.length > 0) {
  r.sources.map(...)
}
```

删除时使用：

```js
const r = await fetch('/api/audio-sources/' + id, { method: 'DELETE' }).then(x => x.json());
if (r.ok) {
  loadSources();
} else {
  alert(r.error || '删除失败');
}
```

#### 4.1.2 规范化后的预期返回

根据阶段 B/C2/C3 已采用的列表规范，`GET /api/audio-sources/list` 建议在 C4 规范化后返回 `PageVO[AudioSourceVO]`，unwrap 后页面读取：

```json
{
  "items": [
    {
      "id": 1,
      "audio_name": "demo",
      "format": "mp3",
      "file_size": 12345,
      "status": "active",
      "created_at": "2026-04-22 00:00:00"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

#### 4.1.3 前端改造点

1. 请求方式改为 `apiGet('/api/audio-sources/list', { limit, offset })`
2. `r.sources` 全部替换为 `r.items`
3. `r.total` 可保留用于后续分页/统计展示
4. 删除请求改为 `apiDelete('/api/audio-sources/' + id)`
5. 删除成功后不再依赖 `r.ok`，只要请求成功就刷新列表
6. 删除失败统一走 `catch(e)`，提示 `e.message`
7. 列表加载失败时继续在列表区域显示错误提示，而不是仅在控制台打印

#### 4.1.4 AudioSourceVO 字段影响

当前列表页实际依赖字段：

- `id`
- `audio_name`
- `format`
- `file_size`
- `status`
- `created_at`

这些字段都属于单条音源记录本身，预计在 `AudioSourceVO` 中仍保持平铺；C4 的主要变化集中在列表外层从 `sources` 改为 `items`。

---

### 4.2 `audio-sources/upload.html`

#### 4.2.1 当前写法

当前页面通过 `multipart/form-data` 提交：

- `audio_name`
- `audio_file`

当前按旧响应读取：

```js
const r = await fetch('/api/audio-sources/upload', {
  method: 'POST',
  body: formData
});
const data = await r.json();
if (data.ok) {
  alert('上传成功！音源ID: ' + data.audio_source_id);
} else {
  alert('上传失败: ' + (data.error || '未知错误'));
}
```

#### 4.2.2 规范化后的预期返回

C4 规范化后，建议 unwrap 后成功结果保持最小可用形状：

```json
{
  "audio_source_id": 123,
  "audio_name": "demo",
  "file_path": "https://..."
}
```

前端最关心的成功字段是：

- `audio_source_id`

其余字段可作为回显或跳转辅助，不应成为成功分支的强依赖。

#### 4.2.3 前端改造点

1. 请求方式改为 `apiPostForm('/api/audio-sources/upload', formData)`
2. 删除 `if (data.ok)` 分支
3. 删除对 `data.error` 的直接读取
4. 成功时继续可读取 `r.audio_source_id`
5. 失败统一通过 `catch(e)` 读取 `e.message`
6. 前端本地校验仍保留：
   - `audio_name` 为空时拦截
   - 未选择文件时拦截
7. 成功后当前“清空表单但不跳转”的交互可以保留
8. 可选优化：成功后跳转 `details?id=${r.audio_source_id}`，但这属于交互优化，不是本次规范化必做项

#### 4.2.4 上传接口字段提醒

当前后端写入记录时会返回：

- `audio_source_id`
- `audio_name`
- `file_path`

但不会返回 `format`、`status`、`created_at` 等完整详情字段。因此上传页不应假设上传接口返回的是完整 `AudioSourceVO`。

---

### 4.3 `audio-sources/details.html`

#### 4.3.1 详情加载：`GET /api/audio-sources/<id>`

当前页面写法：

```js
const r = await fetch('/api/audio-sources/' + id).then(x => x.json());
if (r.error) {
  alert(r.error);
  return;
}
const s = r;
```

随后读取：

- `s.id`
- `s.audio_name`
- `s.format`
- `s.file_size`
- `s.status`
- `s.created_at`
- `s.file_path`

#### 4.3.2 规范化后的预期返回

详情接口规范化后，预计为：

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "id": 1,
    "audio_name": "demo",
    "format": "mp3",
    "file_size": 12345,
    "status": "active",
    "created_at": "2026-04-22 00:00:00",
    "file_path": "https://..."
  }
}
```

unwrap 后页面仍可继续把返回值当详情对象使用，因此详情页核心改造不是字段名，而是错误处理方式。

#### 4.3.3 前端改造点

1. 请求方式改为 `apiGet('/api/audio-sources/' + id)`
2. 删除 `if(r.error)` 判断，改为 `try/catch`
3. 详情对象字段预期仍可平铺访问：
   - `id`
   - `audio_name`
   - `format`
   - `file_size`
   - `status`
   - `created_at`
   - `file_path`
4. 删除请求改为 `apiDelete('/api/audio-sources/' + currentId)`
5. 删除成功后不再依赖 `r.ok`，直接提示成功并跳回列表
6. 删除失败统一通过 `catch(e)` 显示 `e.message`

#### 4.3.4 音频预览地址问题

当前页面预览逻辑是：

```js
audioPlayer.src = API_BASE + s.file_path;
```

但当前后端上传逻辑 `file_path` 实际很可能已经是 OSS 公网 URL，例如：

```text
https://bucket.oss-cn-xxx.aliyuncs.com/audio-sources/xxx.mp3
```

在这种情况下，继续拼接 `API_BASE` 虽然由于当前 `API_BASE=''` 暂时无害，但它表达的是“相对路径”假设，不够稳妥。

因此 C4 推荐改成更明确的兼容策略：

```js
audioPlayer.src = s.file_url || s.file_path || '';
```

含义：

1. 若后端 C4 补充 `file_url`，优先使用 `file_url`
2. 否则直接使用 `file_path`
3. 不再假设一定需要加 `API_BASE`

这部分是 `details.html` 里最值得注意的兼容性改造点。

---

## 5. AudioSourceVO 字段对照

基于当前 controller 与页面读取方式，C4 阶段前端最关心的 `AudioSourceVO` 字段如下。

| 字段名 | 类型 | 说明 | 前端页面使用方式 |
|------|------|------|----------------|
| `id` | `int` | 音源 ID | 列表跳详情、删除目标、详情展示 |
| `audio_name` | `string` | 音源名称 | 列表展示、上传成功提示、详情展示 |
| `file_path` | `string?` | 文件路径或 OSS URL | 详情页音频预览 |
| `file_url` | `string?` | 可选的前端直连播放 URL | 详情页推荐预留 |
| `file_size` | `number?` | 文件大小 | 列表/详情展示 |
| `format` | `string?` | 文件格式 | 列表/详情展示 |
| `status` | `string?` | 状态 | 列表/详情展示 |
| `created_at` | `string?` | 上传时间 | 列表/详情展示 |
| `duration_sec` | `number?` | 时长 | 当前页面未展示，可预留 |
| `sample_rate` | `number?` | 采样率 | 当前页面未展示，可预留 |
| `channels` | `number?` | 声道数 | 当前页面未展示，可预留 |
| `source_type` | `string?` | 来源类型 | 当前页面未展示，可预留 |
| `source_id` | `string|number|null` | 来源标识 | 当前页面未展示，可预留 |

### 5.1 对页面影响总结

- `index.html`：主要变化是列表集合外层从 `sources` 改为 `items`
- `upload.html`：主要变化是去掉 `ok/error` 分支，保留 `audio_source_id`
- `details.html`：详情字段大概率保持平铺，重点在 `try/catch` 和播放地址兼容

### 5.2 跨页面关联提醒

虽然本任务只覆盖 audio-sources 三个页面，但项目中还有两个位置与该 controller 存在旁路依赖：

1. `frontend/pages/songs/add.html`
   - 当前调用 `GET /api/audio-sources/list`
   - 目前读取 `(r.sources || [])`
   - 若 C4 将列表统一成 `PageVO[AudioSourceVO]`，这里也需要同步改成 `(r.items || [])`
2. `frontend/index.html`
   - 首页统计当前直接 `fetch('/api/audio-sources/list?limit=1')`
   - 目前只读取 `total` 或 `sources.length`
   - 若 C4 切为 Result 包装，首页统计逻辑也要同步调整

因此，虽然本方案的主范围是 audio-sources 三页，联调时仍需把上述两个页面纳入回归清单。

---

## 6. 预留接口：`GET /api/audio-sources/oss-files`

当前三个页面都未接入该接口。

现有返回形状为：

```json
{
  "files": ["https://..."],
  "total": 1
}
```

若 C4 后端也对该接口做 Result 化，前端建议采用以下原则：

1. 若它被定义为“非分页纯数组接口”，则 unwrap 后前端最好直接拿数组
2. 若它被定义为“文件列表对象”，则至少保证字段语义稳定，例如：
   - `items`
   - `total`
3. 由于当前页面没有 OSS 文件浏览器，本接口先只做预留记录，不要求在 C4 首版页面中强制接入

---

## 7. 错误处理改造

阶段 C4 应完全沿用阶段 B/C1/C2/C3 的统一模式：**页面层统一 `try/catch`，不再在业务代码里判断 `r.ok` / `r.error`。**

### 7.1 需要清理的旧模式

以下旧模式在 audio-sources 页面中都应清理：

- `if (r.ok) { ... } else { ... }`
- `if (r.error) { ... }`
- 原生 `fetch(...).then(x => x.json())` 直接读取旧响应

### 7.2 推荐标准写法

#### 列表页

```js
try {
  const r = await apiGet('/api/audio-sources/list', { limit: 100, offset: 0 });
  const list = r.items || [];
  // 渲染列表
} catch (e) {
  sourcesList.innerHTML = '<p style="color:red">加载失败: ' + e.message + '</p>';
}
```

#### 上传页

```js
try {
  const r = await apiPostForm('/api/audio-sources/upload', formData);
  alert('上传成功！音源ID: ' + r.audio_source_id);
} catch (e) {
  alert('上传失败: ' + e.message);
}
```

#### 详情页删除

```js
try {
  await apiDelete('/api/audio-sources/' + currentId);
  alert('删除成功');
  window.location.href = '/audio-sources';
} catch (e) {
  alert('删除失败: ' + e.message);
}
```

### 7.3 页面分场景要求

#### `audio-sources/index.html`
- 列表加载失败时在页面区域显示错误，不要只弹窗
- 删除失败时提示 `e.message`
- 无数据与加载失败要区分展示文案

#### `audio-sources/upload.html`
- 名称为空时保留前端同步校验
- 未选择文件时保留前端同步校验
- OSS 上传失败、格式校验失败、服务端保存失败统一提示 `e.message`
- 成功后不再依赖 `ok`

#### `audio-sources/details.html`
- 详情加载失败：`alert(e.message)`，必要时可返回列表
- 删除失败：`alert(e.message)`
- 404 时建议给出更明确提示，但第一版不是必做项

### 7.4 典型错误场景

结合当前后端逻辑，前端联调时应重点覆盖：

1. **缺少音源名称**
   - 典型接口：`POST /api/audio-sources/upload`
2. **未选择文件**
   - 典型接口：`POST /api/audio-sources/upload`
3. **音源不存在**
   - 典型接口：`GET /api/audio-sources/<id>`、`DELETE /api/audio-sources/<id>`
4. **OSS 上传失败**
   - 典型接口：`POST /api/audio-sources/upload`
5. **删除失败**
   - 典型接口：`DELETE /api/audio-sources/<id>`

这些错误在规范化后都应通过 `unwrap + catch(e)` 暴露给页面。

---

## 8. 验收清单

### 8.1 `audio-sources/index.html`

- [ ] 请求改为通过 `apiGet('/api/audio-sources/list', ...)` 发起
- [ ] 列表读取从 `r.sources` 改为 `r.items`
- [ ] 列表项字段 `id / audio_name / format / file_size / status / created_at` 渲染正常
- [ ] 删除请求改为通过 `apiDelete('/api/audio-sources/:id')` 发起
- [ ] 页面内不再出现 `if (r.ok)`
- [ ] 页面内不再读取 `r.error`
- [ ] 删除成功后仍能正确刷新列表
- [ ] 加载失败时页面展示错误提示

### 8.2 `audio-sources/upload.html`

- [ ] 上传请求改为通过 `apiPostForm('/api/audio-sources/upload', formData)` 发起
- [ ] 页面内不再出现 `if (data.ok)`
- [ ] 页面内不再读取 `data.error`
- [ ] 成功后仍能读取 `r.audio_source_id`
- [ ] 名称为空时前端校验仍有效
- [ ] 未选择文件时前端校验仍有效
- [ ] 上传失败时能正确提示 `e.message`
- [ ] 成功后清空表单逻辑保持正常

### 8.3 `audio-sources/details.html`

- [ ] 详情请求改为通过 `apiGet('/api/audio-sources/:id')` 发起
- [ ] 页面内不再出现 `if (r.error)`
- [ ] 页面内不再出现 `if (r.ok)`
- [ ] 详情字段 `id / audio_name / format / file_size / status / created_at / file_path` 渲染正常
- [ ] 删除请求改为通过 `apiDelete('/api/audio-sources/:id')` 发起
- [ ] 删除成功后仍能正确提示并跳回列表
- [ ] 音频预览地址兼容 `file_url || file_path`

### 8.4 旁路回归项

- [ ] `frontend/pages/songs/add.html` 中的音源下拉列表已从 `(r.sources || [])` 适配到 `(r.items || [])`
- [ ] `frontend/index.html` 首页音源统计已适配 Result 包装与列表结构变化

### 8.5 待后端 C4 文档确认项

- [ ] `GET /api/audio-sources/list` 是否确定返回 `PageVO[AudioSourceVO]`，字段名是否为 `items`
- [ ] `GET /api/audio-sources/<id>` 的 `AudioSourceVO` 是否会补充 `file_url`
- [ ] `POST /api/audio-sources/upload` 的成功 `result` 是否稳定保留 `audio_source_id`
- [ ] `DELETE /api/audio-sources/<id>` 的成功 `result` 是否为空对象
- [ ] `GET /api/audio-sources/oss-files` 在规范化后是返回数组还是分页对象
- [ ] `file_path` 在 C4 中是否明确约定为“OSS 直链 URL”而非站内相对路径

---

## 9. 结论

阶段 C4 对 audio-sources 页面前端的核心影响主要有三类：

1. **外层响应包装统一**：三个页面都要切到 `api.js + unwrap + try/catch`，移除 `r.ok / r.error`。
2. **列表接口字段变化**：`audio-sources/index.html` 需要把 `r.sources` 改成 `r.items`。
3. **详情播放地址兼容**：`details.html` 需要把音频预览从“默认拼接路径”调整为更稳妥的 `file_url || file_path`。

整体来看，C4 的 audio-sources 页面改造属于 **中等偏小规模适配**：

- `index.html` 主要是列表字段切换 + 删除逻辑改造；
- `upload.html` 主要是 `ok/error` → `try/catch`；
- `details.html` 主要是错误处理统一 + 音频播放地址兼容；
- 另外还要关注 `songs/add.html` 与首页统计对 `audio-sources/list` 的旁路依赖，避免联调时遗漏。
