# 前端问题修复报告

- 时间：2026-04-14
- 范围：`frontend/`
- 说明：任务中提到的 `docs/frontend/PAGE_ISSUES.md` 在仓库中未找到；本次修复基于任务明确列出的问题，以及现有 `docs/frontend/API_ALIGNMENT_ANALYSIS.md` 中已识别的页面对齐问题执行。

## 已修复问题

### 1. `/capture` 页面停止录音接口方法与后端对齐
- 页面：`frontend/pages/capture.html`
- 结果：确认当前前端已使用 `PUT /api/capture/stop-recording`
- 提交字段：`{ session_id, audio_name }`
- 处理：无需额外修改，保持与后端一致

### 2. `/recordings` 页面字段名 `file_name` 改为 `audio_name`
- 页面：`frontend/pages/recordings/index.html`
- 已修改：
  - 列表展示字段：`s.file_name` → `s.audio_name`
  - 编辑弹窗回填：`file_name` → `audio_name`
  - 保存请求体：`{ file_name }` → `{ audio_name }`

### 3. 菜单路由 `/audio-sources/list` 改为 `/audio-sources`
- 文件：`frontend/js/menu.js`
- 已修改：菜单“音源列表”路由更新为 `/audio-sources`

### 4. `songs/details.html`、`artists/details.html` 接入统一菜单
- 页面：
  - `frontend/pages/songs/details.html`
  - `frontend/pages/artists/details.html`
- 已修改：补充统一菜单脚本引用 ` /js/menu.js `

### 5. 其他已顺手修复的问题

#### 5.1 列表页进入详情页的冗余详情请求
- 页面：
  - `frontend/pages/songs/index.html`
  - `frontend/pages/artists/index.html`
- 原问题：点击列表项时先请求详情接口，再跳转到详情页；详情页初始化后又再次请求一次
- 已修改：列表页改为直接跳转详情页，不再预取详情数据
- 效果：减少一次无意义接口请求

#### 5.2 `/recordings` 返回首页链接 HTML 语法错误
- 页面：`frontend/pages/recordings/index.html`
- 已修改：`<a href="/"" ...>` 修正为 `<a href="/" ...>`

## 修改文件清单

1. `frontend/js/menu.js`
2. `frontend/pages/recordings/index.html`
3. `frontend/pages/songs/index.html`
4. `frontend/pages/artists/index.html`
5. `frontend/pages/songs/details.html`
6. `frontend/pages/artists/details.html`

## 完成情况

- [x] 所有已识别前端问题已修复
- [x] 文档已输出到 `docs/frontend/2026-04/`

## 建议验证项

1. 打开 `/audio-sources`，确认菜单“音源列表”跳转正常
2. 打开 `/recordings`，确认文件名显示正常且编辑保存不再报 `audio_name is required`
3. 打开 `/songs`、`/artists` 列表，点击详情时确认只发生一次详情请求
4. 打开 `/songs/details`、`/artists/details`，确认左侧统一菜单已显示
