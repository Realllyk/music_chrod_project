# 接口规范化-阶段C3-artists页面改造方案

## 1. 目标与范围

本方案用于配合后端 `artists_controller` 在阶段 C3 的接口规范化改造，覆盖以下页面：

- `frontend/pages/artists/index.html`
- `frontend/pages/artists/add.html`
- `frontend/pages/artists/details.html`

本次 **只输出前端改造设计文档，不进入实现**。

> 说明：后端阶段 C3 设计文档尚未单独提供，本文基于当前 `backend/controllers/artists_controller.py`、阶段 A 基础设施、以及阶段 B/C1/C2 已采用的前端改造模式，推导 artists 页面适配方案。待后端 C3 文档完成后，需再逐项核对 VO 字段与成功返回体形状。

---

## 2. 现状分析

### 2.1 规范化基线

根据迁移计划与阶段 A 已落地能力：

1. 后端接口将逐步统一为 `Result` 结构：
   - 成功：`{ code: 200, description: 'success', result: ... }`
   - 失败：`{ code: 非200, description: 错误信息, result: null }`
2. `frontend/js/api.js` 已具备 `unwrap`：
   - 成功时返回 `result`
   - 失败时抛出 `Error`
3. 页面层应统一为：
   - 使用 `apiGet/apiPost/apiPut/apiDelete/apiPostForm/apiPutForm`
   - 使用 `try/catch`
   - 不再读取 `r.ok` / `r.error`

### 2.2 当前 `artists_controller` 返回形状

结合现有后端代码，artists 模块当前接口返回大致如下。

#### `GET /api/artists/list`
当前返回：

```json
{
  "artists": [
    {
      "id": 1,
      "name": "...",
      "bio": "...",
      "avatar": "..."
    }
  ],
  "total": 10
}
```

#### `GET /api/artists/<artist_id>`
当前成功直接返回 artist 对象：

```json
{
  "id": 1,
  "name": "...",
  "bio": "...",
  "avatar": "..."
}
```

失败返回：

```json
{ "error": "Artist not found" }
```

#### `POST /api/artists/add`
当前支持两种 content-type：
- `application/json`
- `multipart/form-data`

成功返回：

```json
{ "ok": true, "artist_id": 123 }
```

失败返回：

```json
{ "error": "..." }
```

#### `PUT /api/artists/<artist_id>`
当前也支持：
- `application/json`
- `multipart/form-data`

成功返回：

```json
{ "ok": true, "message": "Artist updated" }
```

失败返回：

```json
{ "error": "..." }
```

#### `DELETE /api/artists/<artist_id>`
当前成功返回：

```json
{ "ok": true, "message": "Artist deleted" }
```

失败返回：

```json
{ "error": "..." }
```

#### `PUT /api/artists/<artist_id>/avatar`
当前成功返回：

```json
{ "ok": true, "avatar": "https://..." }
```

失败返回：

```json
{ "error": "..." }
```

> 迁移计划 C3 已明确：关键接口为 `/list`、`/add`（双 content-type）、`/<id>`（PUT）、`/<id>/avatar`。虽然当前详情页实际尚未单独调用 `/<id>/avatar`，但该接口应纳入前端页面改造预留。

### 2.3 当前页面实际调用情况

#### `artists/index.html`
当前实际调用：
- `GET /api/artists/list`

当前字段读取：
- `r.artists`
- `a.id`
- `a.name`
- `a.avatar`

页面特征：
- 前端本地用搜索框对 `r.artists` 做过滤
- 请求失败时 `catch(e){}` 静默吞错，没有任何失败提示

#### `artists/add.html`
当前实际调用：
- `POST /api/artists/add`（`multipart/form-data`）

当前字段读取：
- 成功判断：`if (r.ok)`
- 成功字段：`r.artist_id`
- 失败字段：`r.error`

页面特征：
- 表单包含 `name`、`bio`、`avatar`
- 当前保存成功后仅清空表单，不跳转详情页

#### `artists/details.html`
当前实际调用：
- `GET /api/artists/<id>`
- `PUT /api/artists/<id>`（JSON）
- `PUT /api/artists/<id>`（multipart/form-data）
- `DELETE /api/artists/<id>`

当前字段读取：
- 加载详情时：`if (r.error)`
- 详情字段：`r.id`、`r.name`、`r.bio`、`r.avatar`
- 保存时：`if (r.ok)` / `r.error`
- 删除时：`if (r.ok)` / `r.error`

页面特征：
- 若带头像文件，当前直接走 `PUT /api/artists/<id>` multipart 更新全部字段
- 尚未拆分成“资料更新”与“头像单独上传”两条调用路径

---

## 3. 页面改造对照表

| 页面 | 接口 | 原字段访问 | 新字段访问 | 改动类型 |
|------|------|-----------|-----------|---------|
| `artists/index.html` | `GET /api/artists/list` | `r.artists` | `r.items` | 字段路径 |
| `artists/index.html` | `GET /api/artists/list` | `r.artists.filter(...)` | `r.items.filter(...)` | 字段路径 |
| `artists/index.html` | `GET /api/artists/list` | `r.artists.map(...)` | `r.items.map(...)` | 字段路径 |
| `artists/index.html` | `GET /api/artists/list` | `if(list.length>0)` | 保持不变 | 不变 |
| `artists/index.html` | `GET /api/artists/list` | 静默吞错 `catch(e){}` | `catch(e)` 展示加载失败信息 | 错误处理 |
| `artists/add.html` | `POST /api/artists/add` | `if (r.ok)` | `try/catch` | 错误处理 |
| `artists/add.html` | `POST /api/artists/add` | `r.artist_id` | `r.artist_id` | 不变 |
| `artists/add.html` | `POST /api/artists/add` | `r.error` | `e.message` | 错误处理 |
| `artists/details.html` | `GET /api/artists/<id>` | `if (r.error)` | `try/catch` | 错误处理 |
| `artists/details.html` | `GET /api/artists/<id>` | `r.id / r.name / r.bio / r.avatar` | 预期保持不变 | 不变 |
| `artists/details.html` | `PUT /api/artists/<id>` | `if (r.ok)` | `try/catch` | 错误处理 |
| `artists/details.html` | `PUT /api/artists/<id>` | `r.error || '保存失败'` | `e.message || '保存失败'` | 错误处理 |
| `artists/details.html` | `DELETE /api/artists/<id>` | `if (r.ok)` | `try/catch` | 错误处理 |
| `artists/details.html` | `DELETE /api/artists/<id>` | `r.error || '删除失败'` | `e.message || '删除失败'` | 错误处理 |
| `artists/details.html` | `PUT /api/artists/<id>/avatar` | 当前页面未使用 | 若拆分头像上传，成功读 `r.avatar` | 预留接入 |

---

## 4. 逐页改造方案

### 4.1 `artists/index.html`

#### 4.1.1 当前写法

当前页面直接请求：
- `GET /api/artists/list`

并按旧响应读取：

```js
const r = await fetch('/api/artists/list').then(x => x.json());
let list = r.artists || [];
```

随后前端本地执行：
- `list.filter(a => a.name.toLowerCase().includes(search.toLowerCase()))`
- `list.map(...)`

#### 4.1.2 规范化后的预期返回

根据迁移计划 §4.3：

- 原响应：`{ artists: [...], total: N }`
- 新响应：`PageVO[ArtistVO]`

因此 unwrap 后页面应读取：

```json
{
  "items": [
    {
      "id": 1,
      "name": "...",
      "bio": "...",
      "avatar": "..."
    }
  ],
  "total": 10,
  "limit": 20,
  "offset": 0
}
```

#### 4.1.3 前端改造点

1. 请求方式改为 `apiGet('/api/artists/list', { limit, offset })`
2. `r.artists` 全部替换为 `r.items`
3. `r.total` 保持不变，可用于后续分页信息展示
4. 搜索过滤继续在前端执行，但对象来源改为 `r.items`
5. 请求失败不应再静默吞错，至少要在列表区域显示“加载失败：${e.message}”

#### 4.1.4 ArtistVO 字段影响

当前列表页实际依赖字段只有：
- `id`
- `name`
- `avatar`

按当前 controller / mapper 形态判断，这些字段在 `ArtistVO` 中大概率保持平铺不变，因此列表页主要改动集中在集合外层：
- `artists` → `items`

---

### 4.2 `artists/add.html`

#### 4.2.1 当前写法

当前页面使用 `multipart/form-data` 提交：
- `name`
- `bio`
- `avatar`

按旧响应读取：

```js
const r = await fetch('/api/artists/add', { method: 'POST', body: formData }).then(x => x.json());
if (r.ok) {
    alert('保存成功');
} else {
    alert(r.error);
}
```

#### 4.2.2 规范化后的预期返回

迁移计划已说明：
- `POST /api/artists/add` 继续保留双 content-type
- 页面不再读 `ok/error`
- 由 `unwrap` 统一处理成功与失败

预计 unwrap 后成功结果为：

```json
{
  "artist_id": 123
}
```

若后端在 C3 增加更多字段，也应仅作为附加信息，不影响现有页面最小适配方案。

#### 4.2.3 前端改造点

1. 请求方式改为 `apiPostForm('/api/artists/add', formData)`
2. 删除 `if (r.ok)` 分支
3. 删除 `alert(r.error)` 这类旧错误读取方式
4. 成功时继续使用 `r.artist_id`
5. 失败统一走 `catch(e)`，提示 `e.message`
6. 当前“保存成功后只清空表单”的交互可以保持；是否跳详情页属于后续交互优化，不是本次规范化必做项

#### 4.2.4 双 content-type 说明

当前页面只走 multipart。

但后端 C3 会继续支持：
- JSON 新增
- multipart 新增

因此文档层建议前端保持以下约束：
- `artists/add.html` 继续使用 multipart，因为页面本身包含头像上传控件
- 若未来新增“无头像快速创建”入口，可复用同一路由的 JSON 版本，但不影响本页面方案

---

### 4.3 `artists/details.html`

#### 4.3.1 详情加载：`GET /api/artists/<id>`

当前页面写法：

```js
const r = await fetch('/api/artists/' + id).then(x => x.json());
if (r.error) { alert(r.error); return; }
```

随后直接读取：
- `r.id`
- `r.name`
- `r.bio`
- `r.avatar`

#### 4.3.2 规范化后的预期返回

详情接口规范化后，预计为：

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "id": 1,
    "name": "...",
    "bio": "...",
    "avatar": "..."
  }
}
```

unwrap 后页面继续把返回值当 artist 对象使用，因此字段大概率保持：
- `r.id`
- `r.name`
- `r.bio`
- `r.avatar`

本处核心改造不是字段名，而是错误处理方式：
- `if (r.error)` → `try/catch`

#### 4.3.3 保存资料：`PUT /api/artists/<id>`

当前页面有两条提交路径：

1. **有头像文件**：
   - `PUT /api/artists/<id>`
   - `multipart/form-data`
2. **无头像文件**：
   - `PUT /api/artists/<id>`
   - `application/json`

当前成功判断：

```js
if (r.ok) { ... } else { alert(r.error || '保存失败'); }
```

规范化后，unwrap 成功结果预计可能为：

```json
{}
```
或
```json
{ "artist_id": 1 }
```
或
```json
{ "message": "Artist updated" }
```

前端建议：
- **不要依赖任何成功字段**
- 只要请求成功即视为保存完成
- 失败统一读取 `e.message`

这是因为阶段 B/C1/C2 的改造经验已经表明：对这类“更新成功”接口，页面更稳妥的做法是不再依赖 `ok/message`。

#### 4.3.4 删除：`DELETE /api/artists/<id>`

当前写法：

```js
if (r.ok) {
    alert('删除成功');
    window.location.href='/artists';
} else {
    alert(r.error || '删除失败');
}
```

规范化后建议：
- 不再读取 `r.ok`
- 不再依赖返回体的 `message`
- 请求成功即视为删除成功并跳回列表
- 请求失败通过 `catch(e)` 展示错误

结合当前 `ArtistsService.delete_artist()` 逻辑，还需要特别注意一个典型业务错误：
- 当歌手被歌曲引用时，后端会抛出 `ValueError('Artist is referenced by songs and cannot be deleted')`
- 规范化后应由 `unwrap` 抛出异常，页面直接展示 `e.message`

这类冲突错误在 artists 页面中属于高频场景，删除逻辑必须保留清晰的错误提示。

#### 4.3.5 头像接口预留：`PUT /api/artists/<id>/avatar`

当前 `artists/details.html` 尚未单独调用该接口，而是“有文件就通过 `PUT /api/artists/<id>` multipart 一次性更新”。

但迁移计划 C3 已明确 `/<id>/avatar` 是关键接口之一，因此前端文档应预留两种方案：

1. **最小改造方案（优先）**
   - 保留当前写法
   - 继续使用 `PUT /api/artists/<id>` multipart 同步更新名字、简介、头像
   - 只做 Result 结构与错误处理升级

2. **职责拆分方案（后续可选）**
   - `PUT /api/artists/<id>` 仅更新基础资料（JSON）
   - `PUT /api/artists/<id>/avatar` 单独上传头像（FormData）
   - 成功后读取 `r.avatar` 更新预览

在后端 C3 未明确是否要求前端切分调用路径前，建议前端第一版按 **最小改造方案** 落地，避免一次引入额外交互变更。

---

## 5. ArtistVO 字段对照

基于当前 `artists_controller` / `ArtistsService` / 页面读取方式，C3 阶段前端最关注的 ArtistVO 字段如下。

| 字段名 | 类型 | 说明 | 前端页面使用方式 |
|------|------|------|----------------|
| `id` | `int` | 歌手 ID | `index.html` 点击跳详情；`details.html` 展示只读 ID |
| `name` | `string` | 歌手名称 | `index.html` 列表展示；`add.html` 提交；`details.html` 编辑 |
| `bio` | `string?` | 歌手简介 | `add.html` 提交；`details.html` 回填与编辑 |
| `avatar` | `string?` | 头像 URL | `index.html` 卡片头像；`details.html` 头像预览 |
| `created_at` | `string?` | 创建时间 | 当前 artists 页面未使用，可预留 |
| `updated_at` | `string?` | 更新时间 | 当前 artists 页面未使用，可预留 |

### 5.1 对页面影响总结

- `artists/index.html`：主要变化在集合外层从 `artists` 改成 `items`
- `artists/add.html`：主要变化在去掉 `ok/error` 分支，保留 `artist_id`
- `artists/details.html`：详情对象字段大概率继续平铺使用，核心改动在错误处理统一

### 5.2 跨页面关联提醒

虽然本任务聚焦 artists 三个页面，但项目中还有以下页面会读歌手列表：
- `frontend/pages/songs/add.html`
- `frontend/pages/songs/details.html`

这两个页面当前已做了兼容写法：

```js
(r.items || r.artists || []).forEach(...)
```

因此 C3 后端合并后，它们大概率无需阻塞式改造，但仍建议在联调时一并回归验证，确保 `artists/list -> PageVO[ArtistVO]` 不影响歌曲页的歌手选择下拉框。

---

## 6. 错误处理改造

阶段 C3 应完全沿用阶段 B/C1/C2 的统一模式：**页面层统一 `try/catch`，不再在业务代码里判断 `r.ok` / `r.error`。**

### 6.1 需要清理的旧模式

以下旧模式在 artists 页面中都应清理：

- `if (r.ok) { ... } else { ... }`
- `if (r.error) { ... }`
- 原生 `fetch(...).then(x => x.json())` 直接读取旧响应
- 列表请求失败后静默吞错 `catch(e){}`

### 6.2 推荐标准写法

#### 列表页

```js
try {
    const r = await apiGet('/api/artists/list');
    const list = r.items || [];
    // 渲染列表
} catch (e) {
    listContainer.innerHTML = '<p style="color:#ff6b6b">加载失败：' + e.message + '</p>';
}
```

#### 新增页

```js
try {
    const r = await apiPostForm('/api/artists/add', formData);
    alert('保存成功');
    // r.artist_id 可选用于后续跳转
} catch (e) {
    alert(e.message);
}
```

#### 详情页保存/删除

```js
try {
    await apiPut('/api/artists/' + currentArtistId, { name, bio });
    alert('保存成功');
} catch (e) {
    alert(e.message);
}
```

### 6.3 页面分场景要求

#### `artists/index.html`
- 加载失败不应静默
- 至少要有列表区域错误提示
- 搜索为空与加载失败要区分文案，避免都显示“暂无歌手”

#### `artists/add.html`
- 名字为空仍可保留前端同步校验：`alert('请输入名字')`
- 后端校验失败（如重名、非法头像格式、OSS 上传失败）统一提示 `e.message`
- 成功后不再依赖 `r.ok`

#### `artists/details.html`
- 加载详情失败：`alert(e.message)`，必要时可跳回列表
- 保存失败：`alert(e.message)`
- 删除失败：`alert(e.message)`
- 对 404 / 409 可根据 `e.code` 做更细提示，但第一版不是必做项

### 6.4 artists 模块中的关键错误场景

结合当前后端逻辑，前端联调时应重点覆盖以下错误提示：

1. **名称缺失**
   - 典型接口：`POST /api/artists/add`
   - 页面表现：提示 `e.message`

2. **歌手重名冲突**
   - 典型接口：`POST /api/artists/add`、`PUT /api/artists/<id>`
   - 页面表现：提示 `e.message`

3. **头像格式不支持**
   - 典型接口：`POST /api/artists/add`、`PUT /api/artists/<id>`、`PUT /api/artists/<id>/avatar`
   - 页面表现：提示 `e.message`

4. **OSS 上传失败**
   - 典型接口：同上
   - 页面表现：提示 `e.message`

5. **歌手不存在**
   - 典型接口：`GET /api/artists/<id>`、`PUT /api/artists/<id>`、`DELETE /api/artists/<id>`
   - 页面表现：详情页加载失败或保存/删除失败，提示 `e.message`

6. **删除冲突：歌手被歌曲引用**
   - 典型接口：`DELETE /api/artists/<id>`
   - 页面表现：提示 `e.message`，且页面不跳转

---

## 7. 验收清单

### 7.1 `artists/index.html`

- [ ] 请求改为通过 `apiGet('/api/artists/list', ...)` 发起
- [ ] 列表读取从 `r.artists` 改为 `r.items`
- [ ] 本地搜索过滤从 `r.artists.filter(...)` 改为 `r.items.filter(...)`
- [ ] 列表项字段 `id / name / avatar` 渲染正常
- [ ] 无数据时仍显示“暂无歌手”
- [ ] 请求失败时不再静默吞错，而是显示“加载失败”提示

### 7.2 `artists/add.html`

- [ ] 新增请求改为通过 `apiPostForm('/api/artists/add', formData)` 发起
- [ ] 页面内不再出现 `if (r.ok)`
- [ ] 页面内不再读取 `r.error`
- [ ] 成功后仍能读取 `r.artist_id`
- [ ] 名字为空时前端校验仍有效
- [ ] 重名、头像格式错误、OSS 上传失败时能正确提示 `e.message`
- [ ] 保存成功后表单清空逻辑保持正常

### 7.3 `artists/details.html`

- [ ] 详情请求改为通过 `apiGet('/api/artists/:id')` 发起
- [ ] 页面内不再出现 `if (r.error)`
- [ ] 页面内不再出现 `if (r.ok)`
- [ ] 详情字段 `id / name / bio / avatar` 回填正常
- [ ] JSON 保存请求改为 `apiPut('/api/artists/:id', data)`
- [ ] multipart 保存请求改为 `apiPutForm('/api/artists/:id', formData)`
- [ ] 删除请求改为 `apiDelete('/api/artists/:id')`
- [ ] 保存成功后仍能正确提示并跳回列表
- [ ] 删除成功后仍能正确提示并跳回列表
- [ ] 删除被歌曲引用的歌手时，能正确提示冲突错误且不跳转

### 7.4 `PUT /api/artists/<id>/avatar` 预留验收项

- [ ] 若后端 C3 要求头像上传拆分接口，前端已预留 `apiPutForm('/api/artists/:id/avatar', formData)` 接入方案
- [ ] 成功返回 `r.avatar` 时，页面能即时刷新头像预览
- [ ] 头像格式非法时能正确提示 `e.message`

### 7.5 待后端 C3 文档确认项

- [ ] `GET /api/artists/list` 是否确定返回 `PageVO[ArtistVO]`，字段名是否为 `items`
- [ ] `GET /api/artists/<id>` 的 `ArtistVO` 是否只包含 `id/name/bio/avatar`，还是会补充 `created_at/updated_at`
- [ ] `POST /api/artists/add` 的成功 `result` 是否稳定保留 `artist_id`
- [ ] `PUT /api/artists/<id>` 的成功 `result` 是否为空对象，还是保留 `message` / `artist_id`
- [ ] `DELETE /api/artists/<id>` 的成功 `result` 是否为空对象
- [ ] `PUT /api/artists/<id>/avatar` 是否要求前端在 C3 第一版就切换为独立上传路径
- [ ] 删除冲突错误是否规范为 409，并统一通过 `description` 输出

---

## 8. 结论

阶段 C3 对 artists 页面前端的核心影响主要有三类：

1. **外层响应包装统一**：三个页面都要切到 `api.js + unwrap + try/catch`，移除 `r.ok / r.error`。
2. **列表字段变化**：`artists/index.html` 需要把 `r.artists` 改成 `r.items`。
3. **更新/删除成功分支去状态化**：`add.html`、`details.html` 不再依赖 `ok/message`，只要请求成功即继续执行成功分支。

整体来看，C3 的 artists 前端改造属于 **中等偏小规模适配**：

- `artists/index.html` 主要是列表字段切换 + 补上失败提示。
- `artists/add.html` 主要是 `r.ok/r.error` → `try/catch`。
- `artists/details.html` 主要是加载/保存/删除全部统一到 `api.js` 封装，并为 `/<id>/avatar` 独立接口预留后续接入点。

本方案可以作为阶段 C3 前后端联调与验收依据；待后端 C3 文档补齐后，再做一次字段级复核即可。
