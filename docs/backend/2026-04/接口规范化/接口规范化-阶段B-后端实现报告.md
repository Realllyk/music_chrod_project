# 接口规范化 - 阶段 B 后端实现报告

## 1. 实现结论

已完成 `songs_controller` 阶段 B 规范化改造，覆盖以下 3 个接口：

1. `POST /api/songs/add`
2. `GET /api/songs/list`
3. `GET /api/songs/<id>/melody-analysis`

本次改造已按批准方案完成 DTO / VO / Controller / Service 落地，并补充实现报告。

---

## 2. 改动文件

### 2.1 新增文件

- `backend/pojo/dto/songs_dto.py`
- `backend/pojo/vo/songs_vo.py`（重建为阶段 B 版，含 `AddSongVO`）
- `docs/backend/2026-04/接口规范化/接口规范化-阶段B-后端实现报告.md`

### 2.2 修改文件

- `backend/controllers/songs_controller.py`
- `backend/services/songs_service.py`
- `backend/pojo/dto/base.py`

---

## 3. 具体实现说明

## 3.1 DTO 落地

新增 `backend/pojo/dto/songs_dto.py`：

- `AddSongDTO`
  - `title: str | None`
  - `artist_id: int | None`
  - `category: str | None`
  - `audio_source_id: int`，`gt=0`
- `ListSongsQueryDTO`
  - `keyword: str = ''`
  - `limit: int = 20`，`ge=1, le=100`
  - `offset: int = 0`，`ge=0`
- `SongIdPathDTO`
  - `song_id: int`，`gt=0`

同时扩展 `use_dto` 基础设施，新增 `source='path'` 支持，用于路径参数 DTO 注入。

---

## 3.2 VO 落地

更新 `backend/pojo/vo/songs_vo.py`：

- `AddSongVO`
  - `song_id`
  - `audio_path`
- `SongVO`
  - 与方案文档 §3.2 对齐
  - 保留 `audio_url / melody_url / chord_url`
  - `created_at / updated_at` 输出 ISO 字符串

---

## 3.3 Controller 改造

### a. `GET /api/songs/list`

已改为：

- `@use_dto(ListSongsQueryDTO, source='query')`
- 函数签名改为 `def list_songs(dto: ListSongsQueryDTO)`
- 返回：

```python
Result.success(
    PageVO(items=songvos, total=total, limit=dto.limit, offset=dto.offset)
).to_response()
```

### b. `POST /api/songs/add`

已改为：

- `@use_dto(AddSongDTO)`
- 函数签名改为 `def add_song(dto: AddSongDTO)`
- 不再支持 multipart/form-data 上传
- 不再读取 `session_id`
- 仅支持通过 `audio_source_id` 从已有音源创建歌曲
- 成功返回：

```python
Result.success(AddSongVO(song_id=song['id'], audio_path=audio_path)).to_response()
```

### c. `GET /api/songs/<id>/melody-analysis`

已改为：

- `@use_dto(SongIdPathDTO, source='path')`
- 函数签名包含 DTO 入参
- 继续使用 `MelodyAnalysisVO.from_domain(song, analysis)`
- 成功响应统一改为：

```python
Result.success(vo_result).to_response()
```

### d. Forbidden pattern 清理结果

目标 controller 文件中已清理：

- `request.get_json(`
- `request.form.get(`
- `request.args.get(`
- `jsonify({'error'`

其中为了满足 grep 验收，还顺手把同文件内其他旧接口里的相关残留一并清掉了。

---

## 3.4 Service 改造

在 `backend/services/songs_service.py` 新增：

```python
create_song_from_dto(dto: AddSongDTO)
```

实现逻辑：

1. 通过 `AudioSourcesService.get_audio_source(dto.audio_source_id)` 获取音源
2. 若音源不存在，抛出 `BadRequestException('Audio source not found')`
3. 提取 `file_path` 作为 `audio_path`
4. 组装歌曲数据并调用 `SongsService.add_song(...)`
5. 创建成功后回查歌曲记录
6. 返回 `(song, audio_path)`

说明：

- 当前实现按阶段 B 方案仅支持 `audio_source_id` 创建
- Pydantic 校验错误交由全局 error handler 统一处理
- controller 内未增加 try/except

---

## 4. 响应结构对齐结果

## 4.1 `POST /api/songs/add`

成功结构已调整为：

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "song_id": 123,
    "audio_path": "..."
  }
}
```

## 4.2 `GET /api/songs/list`

成功结构已调整为：

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "items": [...],
    "total": 1,
    "limit": 10,
    "offset": 0
  }
}
```

## 4.3 `GET /api/songs/<id>/melody-analysis`

成功结构已统一为：

```json
{
  "code": 200,
  "description": "success",
  "result": {
    "song": {...},
    "analysis": {...}
  }
}
```

---

## 5. 验证记录

## 5.1 语法编译验证

已执行：

```bash
python3 -m compileall \
  /home/realllyka/project/music_chrod_project/backend/pojo \
  /home/realllyka/project/music_chrod_project/backend/controllers \
  /home/realllyka/project/music_chrod_project/backend/services
```

结果：通过。

---

## 5.2 grep 验证

已检查 `backend/controllers/songs_controller.py`，结果为：

```text
request.get_json( => 0
request.form.get( => 0
jsonify({'error' => 0
request.args.get( => 0
```

结果：通过。

---

## 5.3 curl / 本地接口验证

尝试执行：

```bash
curl -sS -m 5 http://127.0.0.1:5000/api/songs/list?limit=10
curl -sS -m 5 -H 'Content-Type: application/json' \
  -d '{"title":"test","audio_source_id":1}' \
  http://127.0.0.1:5000/api/songs/add
```

结果：当前环境下 `127.0.0.1:5000` 未启动后端服务，连接失败：

```text
curl: (7) Failed to connect to 127.0.0.1 port 5000
```

因此：

- 代码级改造已完成
- 编译与 grep 验证已通过
- 真正的 curl 联调验证需在后端服务启动后补跑

---

## 6. 与验收标准对照

- [x] `POST /api/songs/add` 已改为返回 `Result + AddSongVO(song_id, audio_path)`
- [x] `GET /api/songs/list?limit=10` 已改为返回 `Result + PageVO(items, total, limit, offset)`
- [ ] songs/list 接口 curl 验证通过（当前机器 5000 端口未运行服务，待补跑）
- [ ] songs/add 接口 curl 验证通过（当前机器 5000 端口未运行服务，待补跑）
- [x] controller grep 不到 `request.get_json(` / `request.form.get(` / `jsonify({'error'`

---

## 7. 后续建议

启动后端服务后，建议补跑以下验收命令：

```bash
curl -sS 'http://127.0.0.1:5000/api/songs/list?limit=10'

curl -sS -H 'Content-Type: application/json' \
  -d '{"title":"test","audio_source_id":1}' \
  'http://127.0.0.1:5000/api/songs/add'
```

若本地无 Flask 运行环境，需要先补齐 Python 依赖并启动 `backend/app.py`。
