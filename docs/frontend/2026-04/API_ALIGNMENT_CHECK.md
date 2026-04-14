# 前端 API 对齐检查

> 说明：任务要求参考 `docs/backend/2026-04/API_LIST.md`，但当前仓库中未找到该文件；本次对齐检查实际基于 `docs/backend/API_ALIGNMENT_ANALYSIS.md` 中列出的后端已注册接口进行比对。

## 对齐的接口
| 页面 | API | 状态 |
|------|-----|------|
| `pages/artists/index.html` | `GET /api/artists/list` | 对齐 |
| `pages/artists/add.html` | `POST /api/artists/add` | 对齐 |
| `pages/artists/details.html` | `GET /api/artists/:id` | 对齐 |
| `pages/artists/details.html` | `PUT /api/artists/:id` | 对齐 |
| `pages/artists/details.html` | `DELETE /api/artists/:id` | 对齐 |
| `pages/audio-sources/index.html` | `GET /api/audio-sources/list` | 对齐 |
| `pages/audio-sources/upload.html` | `POST /api/audio-sources/upload` | 对齐 |
| `pages/capture.html` | `POST /api/capture/start-recording` | 对齐 |
| `pages/capture.html` | `PUT /api/capture/stop-recording` | 对齐 |
| `pages/capture.html` | `GET /api/capture/list` | 对齐 |
| `pages/capture.html` | `DELETE /api/capture/sessions/:id` | 对齐 |
| `pages/recordings/index.html` | `GET /api/capture/list` | 对齐 |
| `pages/recordings/index.html` | `PUT /api/capture/sessions/:id` | 对齐 |
| `pages/recordings/index.html` | `DELETE /api/capture/sessions/:id` | 对齐 |
| `pages/songs/index.html` | `GET /api/songs/list` | 对齐 |
| `pages/songs/add.html` | `GET /api/audio-sources/list` | 对齐 |
| `pages/songs/add.html` | `GET /api/artists/list` | 对齐 |
| `pages/songs/add.html` | `POST /api/songs/add` | 对齐 |
| `pages/songs/details.html` | `GET /api/songs/:id` | 对齐 |
| `pages/songs/details.html` | `GET /api/artists/list` | 对齐 |
| `pages/songs/details.html` | `PUT /api/songs/:id` | 对齐 |
| `pages/songs/details.html` | `DELETE /api/songs/:id` | 对齐 |
| `pages/transcribe/index.html` | `GET /api/songs/list` | 对齐 |
| `pages/transcribe/index.html` | `POST /api/transcribe/start` | 对齐 |
| `pages/transcribe/index.html` | `GET /api/transcribe/status/:taskId` | 对齐 |

## 不对齐的接口
| 页面 | 前端调用 | 后端实际 | 问题 |
|------|----------|----------|------|
| 暂未发现 | - | - | 以当前前端页面中的实际 `fetch` 调用与现有后端接口清单比对，未发现路径或 HTTP 方法不对齐的接口 |

## 补充说明
- 已扫描前端 HTML/JS 页面中的实际 `fetch(...)` 调用；`frontend/js/api.js` 为统一封装文件，本身未直接落地具体业务接口调用。
- 首页 `index.html` 与 `js/menu.js` 未发现后端 API 调用。
- `pages/songs/add.html` 中存在 `GET /api/audio-sources/list?status=active`，后端清单中明确存在 `GET /api/audio-sources/list`，但清单未展开查询参数定义；当前仅能确认路径与方法对齐，参数支持情况建议后端补充文档说明。
