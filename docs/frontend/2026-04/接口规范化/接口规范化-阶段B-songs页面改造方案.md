# 接口规范化-阶段B-songs页面改造方案

## 1. 文档目标

为配合后端阶段 B 对 `songs_controller` 的规范化改造，先产出 `frontend/pages/songs/*.html` 的前端适配方案。

本阶段 **只输出改造文档，不进入实现**。

前置条件：
- 阶段 A `frontend/js/api.js` 已完成 `unwrap` 兼容层接入。
- 页面后续应优先通过 `api.js` 统一处理 `Result` 响应，不再在页面内自行判断 `code/result`。

---

## 2. 改造范围

受影响页面：
- `frontend/pages/songs/index.html`
- `frontend/pages/songs/add.html`
- `frontend/pages/songs/details.html`
- `frontend/pages/songs/melody.html`

关联后端返回模型：
- `PageVO[SongVO]`
- `SongVO`
- `MelodyAnalysisVO`

---

## 3. 页面改造对照表

| 页面 | 原字段访问 | 新字段访问 | 改动类型 |
|------|-----------|-----------|---------|
| `songs/index.html` | `r.songs` | `r.items` | 字段路径 |
| `songs/index.html` | `r.total` | `r.total` | 不变 |
| `songs/index.html` | `r.songs.map(...)` | `r.items.map(...)` | 字段路径 |
| `songs/index.html` | `if (r.songs && r.songs.length > 0)` | `if (r.items && r.items.length > 0)` | 字段路径 |
| `songs/add.html` | `if (r.ok) {...} else { alert(r.error) }` | `try {...} catch(e) { alert(e.message) }` | 错误处理 |
| `songs/add.html` | 音源选择 UI | audio_source_id 必填选择 | 表单控件 |
| `songs/add.html` | 音频文件上传控件 | 删除 | 表单控件 |
| `songs/add.html` | title / artist_id / category 表单字段 | 保留 | 不变 |
| `songs/add.html` | `r.song_id` | `r.song_id` | 不变 |
| `songs/add.html` | `r.audio_path` | `r.audio_path` | 不变 |
| `songs/add.html` | `r.error` | `e.message` | 错误处理 |
| `songs/details.html` | `if (r.error) { ... }` | `try { ... } catch(e) { ... }` | 错误处理 |
| `songs/details.html` | `if (saveResp.ok)` | `try { await ... } catch(e) { ... }` | 错误处理 |
| `songs/details.html` | `if (deleteResp.ok)` | `try { await ... } catch(e) { ... }` | 错误处理 |
| `songs/melody.html` | 手动读取 `payload.code / payload.result` | `apiGet(...)` + unwrap 后直接用 | 调用方式 |
| `songs/melody.html` | `payload.description` | `e.message` | 错误处理 |

---

## 4. 各页面改造方案

### 4.1 列表页 `songs/index.html`

#### 当前写法
当前列表页直接请求：
- `GET /api/songs/list`

当前按旧响应读取：
```js
if (r.songs && r.songs.length > 0) {
    d.innerHTML = r.songs.map(...)
}
```

#### 后端阶段 B 目标响应
列表接口将由：
```json
{ "songs": [...], "total": 12 }
```
改为 unwrap 后得到：
```json
{ "items": [...], "total": 12, "limit": 20, "offset": 0 }
```

#### 前端改造点
1. `r.songs` 全部替换为 `r.items`
2. `r.total` 保持不变
3. 列表项内 Song 字段访问继续按 `SongVO` 平铺字段使用（如 `id/title/artist_name/category`）
4. 建议后续实现时一并切换到 `apiGet('/api/songs/list?...')`，避免继续裸 `fetch(...).then(x=>x.json())`

#### 影响评估
- 改动量小
- 无需调整 DOM 结构
- 无需新增错误展示逻辑，沿用现有 `try/catch`

---

### 4.2 添加页 `songs/add.html`

#### 当前写法
当前创建接口使用两种模式：
- JSON 创建（从 session_id 或 audio_source_id）
- multipart/form-data 上传音频创建

页面按旧响应读取：
```js
if (r.ok) {
    alert('创建成功! 歌曲ID: ' + r.song_id)
} else {
    alert(r.error)
}
```

#### 后端阶段 B 目标响应
**变更**：`songs/add` 不再支持文件上传，只允许从已有音源创建。

unwrap 后成功结果为：
```json
{ "song_id": 123, "audio_path": "..." }
```
失败则由 `unwrap` 直接抛错。

#### 前端改造点
1. 删除全部 `if (r.ok)` 分支
2. 删除 `alert(r.error)` 这类旧错误读取方式
3. 删除音频文件上传相关逻辑（表单控件、apiPostForm 调用）
4. 音源来源固定为用户选择的 audio_source_id，填入 payload
5. title / artist_id / category 表单字段保留（用户仍需填写）
6. 成功时直接使用 `r.song_id`、`r.audio_path`
7. 失败统一走 `catch(e)`，提示 `e.message`

#### 推荐目标写法
```js
try {
    const r = await apiPost('/api/songs/add', {
        title: form.title.value,
        artist_id: form.artist_id.value || null,
        category: form.category.value || null,
        audio_source_id: selectedSourceId  // 必填
    })
    alert('创建成功! 歌曲ID: ' + r.song_id)
} catch (e) {
    alert(e.message)
}
```

#### 影响评估
- 删除文件上传控件，新增音源选择 UI（audio_source_id）
- title / artist_id / category 表单字段保留
- 字段名 `song_id` / `audio_path` 保持稳定
- 错误处理统一为 try/catch

---

### 4.3 详情页 `songs/details.html`

#### 当前页面用途
页面承担以下职责：
1. 获取歌曲详情并展示
2. 编辑歌曲基础信息
3. 删除歌曲
4. 展示旋律/和弦结果入口
5. 发起转写任务

其中与阶段 B `songs_controller` 直接相关的是：
- `GET /api/songs/<id>`
- `PUT /api/songs/<id>`
- `DELETE /api/songs/<id>`

#### `GET /api/songs/<id>` 改造判断
按 `SongVO` 设计，当前详情页主要读取的字段仍为平铺结构，因此 **字段名大概率不变**，重点是错误处理从：
```js
if (r.error) { ... }
```
变为：
```js
try { ... } catch (e) { ... }
```

#### 当前页面实际使用到的 SongVO 字段
- `id`
- `title`
- `artist_id`
- `artist_name`
- `category`
- `audio_path`
- `audio_url`
- `melody_path`
- `melody_url`
- `chord_path`
- `chord_url`
- `status`

#### 前端改造点
1. `loadSongDetail()`
   - 去掉 `if (r.error)` 判断
   - 成功直接按 `SongVO` 字段赋值
   - 失败改为 `catch(e) { alert(e.message) }`
2. `saveSongDetail()`
   - 去掉 `if (r.ok)` 判断
   - 成功即说明保存完成
   - 失败走 `catch(e)`
3. `deleteSongDetail()`
   - 去掉 `if (r.ok)` 判断
   - 成功即跳回列表
   - 失败走 `catch(e)`
4. 音频播放链接优先使用 `audio_url`；当前代码是 `API_BASE + audio_path`，后续可评估是否直接切到 `audio_url`，减少路径拼接耦合
5. 旋律/和弦下载链接可继续兼容 `*_url || *_path`

#### 需要特别说明
`songs/details.html` 中还有：
- `POST /api/transcribe/start`

该接口属于 `transcribe_controller`，不是本次 songs 样板改造范围。页面文档里只记录与 songs 接口有关的调整，转写提交逻辑待对应 controller 迁移时再单独对齐。

---

### 4.4 旋律分析页 `songs/melody.html`

#### 当前页面现状
该页面已经手动适配了 `Result` 形状，当前逻辑是：
1. 自己读 `payload.code`
2. 自己读 `payload.description`
3. 成功时读 `payload.result.song` / `payload.result.analysis`

这意味着它在阶段 A `unwrap` 落地后，实际上还没有切到统一调用方式。

#### 后端返回模型
当前 `MelodyAnalysisVO` 结构为：
```json
{
  "song": {
    "id": 1,
    "melody_key": "..."
  },
  "analysis": {
    "type": "melody",
    "midi_path": "...",
    "key": {...},
    "time_signature": {...},
    "tempo": {...},
    "notation": {...}
  }
}
```

#### 前端改造点
1. 推荐把 `fetch(...).json()` 改为 `apiGet('/api/songs/:id/melody-analysis')`
2. 成功时直接把 unwrap 后结果当作 `r`
3. 原先：
   - `payload.result.song` → `r.song`
   - `payload.result.analysis` → `r.analysis`
4. 原先：
   - `payload.description` → `e.message`
5. 404 分支仍需保留，但改为根据 `e.code` / `e.message` 判断

#### 错误处理建议
当前页面对 404 做了较细的文案分流：
- 歌曲不存在
- 旋律结果不存在

建议保留该交互，但实现方式改为：
- `apiGet` 抛错后，在 `catch(e)` 中读取 `e.code`
- 根据 `e.code === 404` 和 `e.message` 内容决定展示文案

#### 标题兜底逻辑
当前页面会从：
- `r.song.title`（如果后端给）
- 或再次请求 `/api/songs/:id` 兜底补标题

而现有 `MelodyAnalysisVO` 仅明确提供：
- `song.id`
- `song.melody_key`

**待确认**：后端阶段 B 是否要把 `song.title` 一并补进 `MelodyAnalysisVO.song`。若不补，前端需继续保留二次查询标题的兜底逻辑。

---

## 5. SongVO 字段对照

> **注意**：后端尚未单独提交阶段 B 的 SongVO 设计文档。此处先按需求文档《VO层与Result设计》中的 SongVO 结构，以及当前 `backend/pojo/vo/songs_vo.py` 现状填写。待后端阶段 B 正式设计文档产出后，再做逐项对照补齐。

| 字段名 | 类型 | 说明 | 前端页面使用方式 |
|------|------|------|----------------|
| `id` | `int` | 歌曲 ID | `index.html` 点击跳详情；`details.html` 展示只读 ID |
| `title` | `string?` | 歌曲名 | `index.html` 列表标题；`details.html` 编辑框；`melody.html` 标题兜底可复用 |
| `artist_id` | `int?` | 歌手 ID | `details.html` 回填歌手下拉框 |
| `artist_name` | `string?` | 歌手名称 | `index.html` 列表展示；`details.html` 可辅助展示 |
| `category` | `string?` | 歌曲分类 | `index.html` 列表右侧展示；`details.html` 编辑 |
| `duration` | `float?` | 时长（秒） | 当前 songs 页面未直接使用，可预留 |
| `source` | `string?` | 音源来源类型 | 当前 songs 页面未直接使用，可用于后续展示录音/上传来源 |
| `source_id` | `string?` | 外部来源 ID | 当前页面未使用 |
| `session_id` | `string?` | 关联录音会话 ID | 当前页面未使用，后续若回链采集页可用 |
| `audio_path` | `string?` | 音频文件路径 | `details.html` 展示路径；当前播放器也依赖该字段 |
| `audio_url` | `string?` | 音频公开访问 URL | `details.html` 音频播放器更推荐使用该字段 |
| `melody_path` | `string?` | 旋律 MIDI/结果文件路径 | `details.html` 生成“查看旋律简谱/下载”入口时使用 |
| `melody_url` | `string?` | 旋律结果公开访问 URL | `details.html` 下载链接优先使用 |
| `melody_key` | `string?` | 旋律结果标识/键值 | `melody.html` 与旋律分析关联字段；当前详情页未直接展示 |
| `chord_path` | `string?` | 和弦结果文件路径 | `details.html` 下载和弦结果时使用 |
| `chord_url` | `string?` | 和弦结果公开访问 URL | `details.html` 下载链接优先使用 |
| `chord_key` | `string?` | 和弦结果标识/键值 | 当前页面未直接使用 |
| `status` | `string?` | 歌曲状态 | `details.html` 状态只读展示 |
| `created_at` | `string?` | 创建时间（ISO） | 当前 songs 页面未使用，可作为后续列表排序/详情展示字段 |
| `updated_at` | `string?` | 更新时间（ISO） | 当前 songs 页面未使用 |

### 5.1 SongVO 对页面影响总结

- `songs/index.html`：只需要关注集合外层由 `songs` 改成 `items`
- `songs/details.html`：内部字段大部分与当前页面读取方式一致，可按平铺字段继续使用
- `songs/melody.html`：仅在兜底查歌曲标题时可能间接依赖 `SongVO.title`

---

## 6. MelodyAnalysisVO 字段对照

当前 `backend/pojo/vo/melody_analysis_vo.py` 的结构是二级对象：
- `song`
- `analysis`

### 6.1 顶层字段

| 字段路径 | 类型 | 说明 | 前端页面使用方式 |
|---------|------|------|----------------|
| `song` | `object` | 当前歌曲相关信息 | `melody.html` 用于拿歌曲标识、旋律 key、标题兜底关联 |
| `analysis` | `object` | 旋律分析结果主体 | `melody.html` 所有可视化都从这里读取 |

### 6.2 `song` 子对象字段

| 字段路径 | 类型 | 说明 | 前端页面使用方式 |
|---------|------|------|----------------|
| `song.id` | `int?` | 歌曲 ID | `melody.html` 回链详情页、关联当前歌曲 |
| `song.melody_key` | `string?` | 旋律结果 key | 当前页面暂未直接展示，可用于后续缓存/标识 |
| `song.title` | `string?` | 歌曲标题 | **待确认**：现实现未保证返回；若后端补齐，`melody.html` 可直接用于页标题 |

### 6.3 `analysis` 子对象字段

| 字段路径 | 类型 | 说明 | 前端页面使用方式 |
|---------|------|------|----------------|
| `analysis.type` | `string?` | 分析类型，当前应为 `melody` | `melody.html` 可用于调试/状态判断 |
| `analysis.midi_path` | `string?` | 生成的 MIDI 路径 | 当前页面未直接展示，后续可加入下载按钮 |
| `analysis.key` | `object?` | 调性信息 | `melody.html` 信息卡展示调、播放换算音高 |
| `analysis.key.tonic` | `string?` | 主音 | `melody.html` 简谱转 MIDI 时使用 |
| `analysis.key.mode` | `string?` | 大调/小调 | `melody.html` 简谱转 MIDI 时使用 |
| `analysis.key.display` | `string?` | 调性展示文本 | `melody.html` 顶部信息卡展示 |
| `analysis.key.confidence` | `number?` | 调性识别置信度 | `melody.html` 顶部信息卡展示 |
| `analysis.time_signature` | `object?` | 拍号信息 | `melody.html` 顶部信息卡、小节换算使用 |
| `analysis.time_signature.numerator` | `int?` | 拍号分子 | `melody.html` 展示与播放排程使用 |
| `analysis.time_signature.denominator` | `int?` | 拍号分母 | `melody.html` 展示使用 |
| `analysis.tempo` | `object?` | 速度信息 | `melody.html` 顶部信息卡、播放器速度初值 |
| `analysis.tempo.bpm` | `number?` | BPM | `melody.html` 显示与播放排程使用 |
| `analysis.notation` | `object?` | 简谱数据 | `melody.html` 核心渲染对象 |
| `analysis.notation.notes` | `array?` | 音符序列 | `melody.html` 渲染简谱、播放、tooltip |
| `analysis.notation.measures` | `array?` | 小节序列 | `melody.html` 按小节分组渲染 |

### 6.4 `analysis.notation.notes[]` 页面依赖字段

| 字段路径 | 类型 | 说明 | 前端页面使用方式 |
|---------|------|------|----------------|
| `index` | `int?` | 音符序号 | DOM `data-note-index` 高亮定位 |
| `degree` | `string?` | 简谱音级，如 `1/#4/b3/0` | 简谱字符渲染 |
| `octave_offset` | `int?` | 八度偏移 | 简谱上下点渲染、MIDI 音高换算 |
| `pitch_name` | `string?` | 音名，如 `C4` | tooltip 展示 |
| `start` | `number?` | 起始秒数 | 播放排程、按小节归类 |
| `end` | `number?` | 结束秒数 | tooltip 展示 |
| `duration_beats` | `number?` | 持续拍数 | 播放排程、tooltip 展示 |

### 6.5 `analysis.notation.measures[]` 页面依赖字段

| 字段路径 | 类型 | 说明 | 前端页面使用方式 |
|---------|------|------|----------------|
| `index` | `int?` | 小节索引 | 小节标题“第 N 小节” |
| `start` | `number?` | 小节开始秒数 | 归类音符 |
| `end` | `number?` | 小节结束秒数 | 归类音符 |
| `degrees` | `array?` | 该小节内的简谱音级列表 | 小节简谱文本渲染 |

---

## 7. 错误处理改造

阶段 B 之后，songs 相关页面统一不再读取：
- `r.ok`
- `r.error`
- 手动 `payload.code / payload.description`

统一改为 `try/catch`。

### 7.1 标准写法

```js
try {
    const r = await apiPost('/api/songs/add', formData);
    // 成功逻辑，r 是 unwrap 后的 result
} catch(e) {
    alert(e.message); // e.message 即后端 description
}
```

### 7.2 各页面落地原则

#### `songs/index.html`
- 请求失败时进入 `catch(e)`
- 可先保持静默失败，或补充“加载失败”提示

#### `songs/add.html`
- 创建失败统一 `alert(e.message)`
- 不再区分 `r.ok/r.error`

#### `songs/details.html`
- 加载详情失败：`alert(e.message)` 或页面跳回列表
- 保存失败：`alert(e.message)`
- 删除失败：`alert(e.message)`

#### `songs/melody.html`
- 404：根据 `e.code === 404` 与 `e.message` 分流提示
- 5xx/网络失败：显示重试态

### 7.3 迁移后的收益

1. 页面逻辑统一
2. 后端错误文案可直接透传
3. 新旧接口共存期由 `api.js` 兼容层承担适配责任
4. 后续其它 controller 迁移时可复用同一模式

---

## 8. 页面级验收清单

### 8.1 `songs/index.html`
- [ ] 能正常请求 `/api/songs/list`
- [ ] 能从 `r.items` 渲染列表
- [ ] `r.total` 读取保持正常
- [ ] 搜索结果为空时仍显示“暂无歌曲”

### 8.2 `songs/add.html`
- [ ] 音源选择 UI 正常（audio_source_id 必填）
- [ ] title / artist_id / category 表单字段保留
- [ ] JSON 创建路径成功后可读取 `r.song_id`
- [ ] 页面内不再出现 `if (r.ok)`
- [ ] 页面内不再读取 `r.error`
- [ ] 不再出现文件上传相关代码（apiPostForm / 文件控件）
- [ ] 创建失败时提示 `e.message`

### 8.3 `songs/details.html`
- [ ] 能正常加载 `SongVO` 并回填表单
- [ ] 音频路径/播放器展示正常
- [ ] 旋律与和弦结果入口展示正常
- [ ] 保存、删除操作改为 `try/catch`
- [ ] 页面内不再读取 `r.error` / `r.ok`

### 8.4 `songs/melody.html`
- [ ] 成功时能直接从 unwrap 后结果读取 `song/analysis`
- [ ] 404 歌曲不存在提示正常
- [ ] 404 旋律结果不存在提示正常
- [ ] 调性、拍号、BPM、简谱渲染正常
- [ ] 页面错误处理统一为 `try/catch`

---

## 9. 待对齐事项

| 项目 | 状态 | 说明 |
|------|------|------|
| `MelodyAnalysisVO.song.title` 是否纳入返回 | 待确认 | 现有实现未明确返回，前端仍需保留标题兜底查询 |
| `songs/details.html` 是否统一切到 `audio_url/chord_url/melody_url` | 待确认 | 当前代码仍兼容 `*_path`，可继续保留回退 |
| `songs/details.html` 中 `PUT/DELETE` 的 Result 形状 | 待后端确认 | 前端方案按 unwrap + try/catch 设计，不依赖 `ok` |
| `songs/*.html` 是否统一切到 `api.js` 封装 | 建议执行 | 尤其 `melody.html` 当前仍手动解 Result |

---

## 10. 结论

阶段 B 的 songs 前端改造重点如下：

1. **列表页**：`r.songs -> r.items`
2. **添加页**：删除 `r.ok/r.error` 分支，统一为 `try/catch`
3. **详情页**：SongVO 字段大体保持平铺不变，核心改动在错误处理统一
4. **旋律页**：字段结构仍是 `song + analysis`，建议从“手动解 Result”切换为“走 `api.js` unwrap”

本方案文档可作为前后端阶段 B 对齐依据；待后端阶段 B 设计/实现文档补齐后，再做一次字段级复核。