# 接口规范化 - 阶段 A 基础设施

## 本次产出

- 新增 `backend/pojo/dto/` 与 `backend/pojo/vo/` 基础骨架
- 迁移 `MelodyAnalysisVO` 至 `backend/pojo/vo/`
- 在 `backend/app.py` 注册全局错误处理
- `backend/requirements.txt` 增加 `pydantic>=2.5,<3`
- 删除旧目录 `backend/vos/`

## 验证记录

- 已执行 Python 导入验证：`app` / `pojo.dto` / `pojo.vo` / `controllers.songs_controller`
- 已确认 `backend/vos/` 不存在

## 备注

本阶段未改动存量 controller 业务逻辑，仅做基础设施落地与必要 import 迁移。
