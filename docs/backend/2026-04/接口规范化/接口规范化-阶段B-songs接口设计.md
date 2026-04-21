# 接口规范化 - 阶段 B songs 接口设计

> 范围：仅产出 `songs_controller` 的 DTO / VO 设计文档，供前后端对齐与阶段 C 实现使用。
>
> 本文不修改实现代码，只约束接口入参与响应形状。

## 1. 设计范围

本阶段覆盖以下 3 个接口：

1. `POST /api/songs/add`
2. `GET /api/songs/list`
3. `GET /api/songs/<id>/melody-analysis`

设计依据：
- `DTO层设计.md`
- `VO层与Result设计.md`
- 阶段 A 基础设施文档
- 现有 `backend/controllers/songs_controller.py`
- 现有 `backend/services/songs_service.py`

---

## 2. DTO 定义

## 2.1 POST /api/songs/add

### AddSongDTO

> 说明：该接口仅支持 `application/json`，从已有音源记录（audio_source_id）创建歌曲。**不再支持本地上传音频文件**。

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| title | str \| None | 否 | 歌曲标题 | `Field(None, max_length=200)` |
| artist_id | int \| None | 否 | 歌手 ID | `Field(None, gt=0)` |
| category | str \| None | 否 | 歌曲分类 | `Field(None, max_length=100)` |
| audio_source_id | int | 是 | 音源记录 ID；必填 | `Field(..., gt=0)` |

#### 场景校验规则

1. `audio_source_id` 必填，不可为空
2. 若为空 → 返回 `400`

#### 建议 DTO 声明（设计稿）

```python
class AddSongDTO(BaseDTO):
    title: str | None = Field(None, max_length=200)
    artist_id: int | None = Field(None, gt=0)
    category: str | None = Field(None, max_length=100)
    audio_source_id: int = Field(..., gt=0)
```
```

---

## 2.2 GET /api/songs/list

### ListSongsQueryDTO

> 说明：封装列表查询参数，替代 controller 中的 `request.args.get(...)` 与手写分页默认值。

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| keyword | str | 否 | 搜索关键字；为空时走全量列表查询 | `Field('', max_length=100)` |
| limit | int | 否 | 每页条数 | `Field(20, ge=1, le=100)` |
| offset | int | 否 | 分页偏移量 | `Field(0, ge=0)` |

#### 建议 DTO 声明（设计稿）

```python
class ListSongsQueryDTO(BaseDTO):
    keyword: str = Field('', max_length=100)
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
```

---

## 2.3 GET /api/songs/<id>/melody-analysis

### GetSongMelodyAnalysisPathDTO

> 说明：虽然路径参数通常不通过 `@use_dto(..., source='query')` 注入，但为保持"每个接口一个 DTO"的设计口径，本文为路径参数单独定义 DTO。
>
> 实现阶段可选择：
> - 方案 A：保留路由参数 `song_id: int`，仅在文档层声明 DTO
> - 方案 B：补一个轻量路径参数解析层，再落地该 DTO
>
> 本阶段仅定义契约，不强制具体注入方式。

| 字段 | 类型 | 必填 | 说明 | 校验 |
|------|------|------|------|------|
| song_id | int | 是 | 歌曲 ID（来自路径参数） | `Field(..., gt=0)` |

#### 建议 DTO 声明（设计稿）

```python
class GetSongMelodyAnalysisPathDTO(BaseDTO):
    song_id: int = Field(..., gt=0)
```

---

## 3. VO 定义

## 3.1 POST /api/songs/add

### AddSongVO

> 说明：该接口成功时只需返回创建结果，不需要完整歌曲详情。
>
> 虽然 API 对接表中可写作"SongVO（含 song_id）"，但为了避免与列表/详情 VO 混淆，建议阶段 C 实现时单独落地为 `AddSongVO`。

| 字段 | 类型 | 说明 |
|------|------|------|
| song_id | int | 新创建的歌曲主键 ID |
| audio_path | str \| None | 解析得到的音频文件路径；手工无文件创建时可为空 |

#### 建议 VO 声明（设计稿）

```python
class AddSongVO(BaseVO):
    song_id: int
    audio_path: str | None = None
```

---

## 3.2 GET /api/songs/list

### SongVO

> 说明：`GET /api/songs/list` 的分页项使用 `SongVO`，字段与现有 `_serialize_song` 对齐。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 歌曲 ID |
| title | str \| None | 歌曲标题 |
| artist_id | int \| None | 歌手 ID |
| artist_name | str \| None | 歌手名称 |
| category | str \| None | 歌曲分类 |
| duration | float \| int \| None | 时长；现有存量中存在秒/毫秒混用风险，接口先保持兼容输出 |
| source | str \| None | 数据来源，如 `local_mp3` / `recording` / `wasapi_loopback` / `manual` |
| source_id | str \| None | 来源记录 ID |
| session_id | str \| None | 采集会话 ID |
| audio_path | str \| None | 音频存储路径 |
| audio_url | str \| None | 音频公开访问地址 |
| melody_path | str \| None | 旋律 MIDI/结果路径 |
| melody_url | str \| None | 旋律公开访问地址 |
| melody_key | str \| None | 旋律分析缓存业务 key |
| chord_path | str \| None | 和弦结果路径 |
| chord_url | str \| None | 和弦公开访问地址 |
| chord_key | str \| None | 和弦分析缓存业务 key |
| status | str \| None | 歌曲状态 |
| created_at | str \| None | 创建时间，ISO 8601 字符串 |
| updated_at | str \| None | 更新时间，ISO 8601 字符串 |

### PageVO[SongVO]

| 字段 | 类型 | 说明 |
|------|------|------|
| items | list[SongVO] | 当前页歌曲列表 |
| total | int | 总记录数 |
| limit | int \| None | 当前分页大小 |
| offset | int \| None | 当前偏移量 |

#### 响应示意

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "items": [
      {
        "id": 1,
        "title": "Song A",
        "artist_id": 2,
        "artist_name": "Artist A",
        "category": "pop",
        "duration": 215.3,
        "source": "local_mp3",
        "source_id": null,
        "session_id": null,
        "audio_path": "songs/a.mp3",
        "audio_url": "/api/files/...",
        "melody_path": null,
        "melody_url": null,
        "melody_key": null,
        "chord_path": null,
        "chord_url": null,
        "chord_key": null,
        "status": "ready",
        "created_at": "2026-04-21T10:00:00",
        "updated_at": "2026-04-21T10:00:00"
      }
    ],
    "total": 12,
    "limit": 20,
    "offset": 0
  }
}
```

---

## 3.3 GET /api/songs/<id>/melody-analysis

### MelodyAnalysisVO

> 说明：该 VO 已在阶段 A 迁移至 `backend/pojo/vo/melody_analysis_vo.py`。本阶段文档只做字段契约固化。
>
> 当前实现结构为：
> - `result.song`
> - `result.analysis`
>
> 其中 `analysis` 由 `song_analysis.result_json` 展开，并补充 `type`、`midi_path`。

### MelodyAnalysisSongVO

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 歌曲 ID |
| melody_key | str \| None | 旋律分析缓存业务 key；优先取 `songs.melody_key`，否则回退 `song_analysis.analysis_key` |

### MelodyAnalysisDetailVO

| 字段 | 类型 | 说明 |
|------|------|------|
| type | str | 分析类型，固定为 `melody` 或来自 `analysis_type` |
| midi_path | str \| None | 旋律分析生成的 MIDI 文件路径 |
| key | dict \| None | 调性信息，典型字段见下表 |
| time_signature | dict \| None | 拍号信息，典型字段见下表 |
| tempo | dict \| None | 速度信息，典型字段见下表 |
| duration | dict \| None | 时长信息，典型字段见下表 |
| notation | dict \| None | 结构化简谱信息，典型字段见下表 |

#### analysis.key 典型字段

| 字段 | 类型 | 说明 |
|------|------|------|
| tonic | str \| None | 主音，如 `C` |
| mode | str \| None | 调式，如 `major` / `minor` |
| display | str \| None | 展示文案，如 `C major` |
| confidence | float \| None | 调性置信度 |

#### analysis.time_signature 典型字段

| 字段 | 类型 | 说明 |
|------|------|------|
| numerator | int \| None | 分子 |
| denominator | int \| None | 分母 |
| source | str \| None | 拍号来源 |

#### analysis.tempo 典型字段

| 字段 | 类型 | 说明 |
|------|------|------|
| bpm | float \| int \| None | BPM |

#### analysis.duration 典型字段

| 字段 | 类型 | 说明 |
|------|------|------|
| seconds | float \| int \| None | 总时长（秒） |

#### analysis.notation

| 字段 | 类型 | 说明 |
|------|------|------|
| notes | list[dict] \| None | 音符明细列表 |
| measures | list[dict] \| None | 小节列表 |

#### analysis.notation.notes[] 典型字段

| 字段 | 类型 | 说明 |
|------|------|------|
| start | float \| int | 起始秒数 |
| end | float \| int | 结束秒数 |
| midi | int | MIDI 音高 |
| pitch_name | str \| None | 绝对音名，如 `C4` |
| degree | str \| None | 简谱级数，如 `1` / `#1` / `b3` |
| octave_offset | int \| None | 八度偏移 |
| duration_beats | float \| int \| None | 拍长 |

#### analysis.notation.measures[] 典型字段

| 字段 | 类型 | 说明 |
|------|------|------|
| index | int | 小节序号 |
| start | float \| int | 小节起始秒数 |
| end | float \| int | 小节结束秒数 |
| degrees | list[str] \| None | 当前小节的简谱级数列表 |

### MelodyAnalysisVO 总结构

| 字段 | 类型 | 说明 |
|------|------|------|
| song | MelodyAnalysisSongVO | 歌曲基础标识信息 |
| analysis | MelodyAnalysisDetailVO | 旋律分析详情 |

#### 响应示意

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "song": {
      "id": 1,
      "melody_key": "melody_1_abcd1234"
    },
    "analysis": {
      "type": "melody",
      "midi_path": "outputs/melody/1.mid",
      "key": {
        "tonic": "C",
        "mode": "major",
        "display": "C major",
        "confidence": 0.92
      },
      "time_signature": {
        "numerator": 4,
        "denominator": 4,
        "source": "midi_default"
      },
      "tempo": {
        "bpm": 120
      },
      "duration": {
        "seconds": 18.6
      },
      "notation": {
        "notes": [],
        "measures": []
      }
    }
  }
}
```

---

## 4. API 对接表

| 方法 | 路径 | DTO | 成功响应 VO | 错误 code |
|------|------|-----|-------------|-----------|
| POST | /api/songs/add | AddSongDTO | AddSongVO（对接表可视为 SongVO 的精简创建态，仅含 `song_id` / `audio_path`） | 400 / 409 / 500 |
| GET | /api/songs/list | ListSongsQueryDTO | PageVO[SongVO] | 400 / 500 |
| GET | /api/songs/<id>/melody-analysis | GetSongMelodyAnalysisPathDTO（路径参数） | MelodyAnalysisVO | 404 / 500 |

---

## 5. 前后端字段对齐说明

### 5.1 songs/list 返回结构调整

`GET /api/songs/list` 在规范化后，成功响应必须统一包裹为：

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "items": [...],
    "total": 0,
    "limit": 20,
    "offset": 0
  }
}
```

### 5.2 与现有存量接口的差异

现有 `songs_controller.py` 返回：

```json
{
  "songs": [...],
  "total": 0
}
```

规范化后应改为读取：
- `result.items`
- `result.total`
- `result.limit`
- `result.offset`

### 5.3 前端必须同步修改点

明确要求前端页面把：

- `r.songs` → `r.items`

若前端当前逻辑是：

```javascript
const songs = r.songs || [];
```

则规范化后应改为：

```javascript
const page = res.result || {};
const songs = page.items || [];
```

---

## 6. 设计决策与说明

### 6.1 为什么 `POST /api/songs/add` 简化为纯 JSON 音源创建

原因：用户新增歌曲改为从已有音源记录选择（不再本地上传音频文件），音频来源固定为 `audio_source_id`。

接口设计为：
- 必填：`audio_source_id`（指定音频来源）
- 可选：title / artist_id / category（歌曲基础信息，服务端可补全）
- `audio_source_id` 必填校验由 Pydantic `Field(..., gt=0)` 接管

### 6.2 为什么 `GET /api/songs/<id>/melody-analysis` 仍单列路径 DTO

虽然实现时可能继续直接使用 Flask 路由参数，但在接口规范化文档中仍建议为路径参数建立 DTO 定义，这样：
- 可以统一参数命名与校验口径
- 可以作为后续自动化校验/生成文档的输入
- 便于与其他 query / body DTO 统一管理

### 6.3 `MelodyAnalysisVO` 为什么允许 analysis 下存在扩展字段

现有实现是将 `song_analysis.result_json` 直接展开到 `result.analysis`。这意味着除了本文列出的典型字段外，后续还可能追加更多分析元数据。

因此本设计采用：
- 文档层列清"前端当前依赖字段"
- 实现层允许兼容性扩展，不把 `analysis` 锁死为过窄结构

---

## 7. 阶段 C 实现注意事项

- `POST /api/songs/add`：使用 `@use_dto(AddSongDTO)`，JSON 模式，`session_id` 与 `audio_source_id` 互斥校验
- `GET /api/songs/list`：改为 `Result.success(PageVO(items=..., total=..., limit=..., offset=...)).to_response()`
- `GET /api/songs/<id>/melody-analysis`：保留现有 `MelodyAnalysisVO.from_domain(song, analysis)` 的领域映射方式
- 所有错误响应统一走 `Result` / 全局 errorhandler，不再返回裸 `{'error': '...'}`

---

## 8. 本文档结论

本阶段已完成 `songs_controller` 三个典型接口的 DTO / VO 设计，核心结论如下：

1. `POST /api/songs/add` 使用 `AddSongDTO`（仅 JSON 模式，session_id / audio_source_id 二选一，不支持文件上传）
2. `GET /api/songs/list` 使用 `ListSongsQueryDTO + PageVO[SongVO]`
3. `GET /api/songs/<id>/melody-analysis` 使用路径参数 DTO 口径，并沿用 `MelodyAnalysisVO`
4. `songs/list` 前后端字段必须统一到 `result.items`，不再使用 `songs`
5. 本文档可直接作为阶段 C 的实现输入与前端联调依据
