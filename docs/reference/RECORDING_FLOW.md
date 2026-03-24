# 录音采集完整流程参考

## 架构概述

```
┌─────────────┐      HTTP API       ┌─────────────┐      DB       ┌─────────────┐
│   前端      │ ◄─────────────────► │   后端      │ ◄───────────► │   MySQL     │
│ (浏览器)    │                     │ (Flask)     │               │             │
└─────────────┘                     └─────────────┘               └─────────────┘
                                             │
                                             │ HTTP 轮询 (每2秒)
                                             ▼
                                      ┌─────────────┐
                                      │   Agent     │
                                      │ (Windows)   │
                                      └─────────────┘
```

## 完整流程

### 1. 开始录音

```
用户点击"开始录音"
       │
       ▼
前端 POST /api/capture/start-recording
       │
       ▼
后端创建会话，status='recording'，存入数据库
       │
       ▼
返回 {ok: true, session_id: 'sess_xxx'}
       │
       ▼
前端显示"录音中"
```

### 2. Agent 轮询

```
Agent 每2秒轮询 GET /api/capture/active
       │
       ▼
后端返回当前活跃会话 {session_id: 'sess_xxx', status: 'recording'}
       │
       ▼
Agent 检查 status in ['ready', 'recording_requested', 'recording']
       │
       ▼
匹配！开始录音（读取音频帧到内存）
```

### 3. 停止录音

```
用户点击"停止录音"
       │
       ▼
前端弹出输入框，用户输入文件名
       │
       ▼
前端 PUT /api/capture/stop-recording
       │ body: {session_id: 'sess_xxx', file_name: 'xxx.wav'}
       ▼
后端更新数据库: status='stopped', file_name='xxx.wav'
       │
       ▼
返回 {ok: true}
       │
       ▼
前端显示"录音已保存"
```

### 4. Agent 检测停止并上传

```
Agent 轮询 GET /api/capture/active
       │
       ▼
后端返回 {session_id: null} 或不同的session
       │
       ▼
Agent check_should_stop() 返回 True
       │
       ▼
停止录音，保存WAV到本地临时目录
       │
       ▼
Agent GET /api/capture/detail/{session_id} 获取文件名
       │
       ▼
Agent POST /api/capture/upload-file 上传WAV
       │
       ▼
后端保存到 uploads/recordings/YYYYMMDD/{uuid}_{filename}.wav
       │
       ▼
后端更新数据库: file_path='/path/to/file.wav'
```

## API 清单

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/capture/start-recording | 开始录音 |
| PUT | /api/capture/stop-recording | 停止录音 |
| GET | /api/capture/active | 获取活跃会话 |
| GET | /api/capture/detail/{session_id} | 获取会话详情 |
| POST | /api/capture/upload-file | 上传WAV文件 |

## 文件路径

| 阶段 | 路径 |
|------|------|
| Agent临时保存 | `agent/recordings/YYYYMMDD/{session_id}.wav` |
| 后端最终保存 | `backend/uploads/recordings/YYYYMMDD/{uuid}_{filename}.wav` |

## 常见问题

### Agent 无法连接后端

- 检查 Agent 启动参数：`python agent.py --backend 192.168.5.129:5000`
- **不要加** `http://` 前缀
- 确保 Windows 能 ping 通 Ubuntu

### Agent 不开始录音

- 确认 Agent 代码包含 `'recording'` 状态检查
- 查看后端 `/api/capture/active` 返回的状态

### 文件没有上传到后端

- 确认 Agent 已重启（代码更新后需要重启）
- 检查后端 `uploads/recordings/` 目录
