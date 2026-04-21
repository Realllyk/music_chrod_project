# 接口规范化-阶段A-unwrap实现报告

## 1. 产出文件

- 代码修改：`/home/realllyka/project/music_chrod_project/frontend/js/api.js`
- 实现报告：`/home/realllyka/project/music_chrod_project/docs/frontend/2026-04/接口规范化-阶段A-unwrap实现报告.md`

## 2. 代码改动说明

### 2.1 新增 `unwrap(body)`

在 `frontend/js/api.js` 第 21-41 行新增 `unwrap(body)` 函数。

判断逻辑如下：

1. `!body || typeof body !== 'object'`
   - 说明返回值不是 JSON 对象（如 text / blob / null），直接原样返回。
2. `!('code' in body) || !('result' in body)`
   - 说明不是后端新的 `Result` 形状，兼容旧接口，直接原样返回。
3. `body.code !== 200`
   - 说明是 `Result` 形状但业务失败，抛出 `Error`。
   - 错误消息优先使用 `body.description`。
   - 同时补充：`err.code = body.code`、`err.result = body.result`。
4. 其余情况
   - 视为 `Result` 成功响应，仅返回 `body.result`，保持页面原有数据读取逻辑尽量不变。

### 2.2 修改的六个 API 封装函数

把原来的：

```js
return handleResponse(response);
```

统一改为：

```js
const body = await handleResponse(response);
return unwrap(body);
```

具体位置：

- `apiGet`：第 49-59 行
- `apiPost`：第 67-76 行
- `apiPostForm`：第 84-92 行
- `apiPut`：第 100-109 行
- `apiPutForm`：第 117-125 行
- `apiDelete`：第 132-139 行

## 3. 验证方式

本次已按目标用等价 JS 逻辑做快速验证，结果如下：

### 3.1 成功场景

输入：

```js
unwrap({code:200, result:{foo:'bar'}})
```

结果：

```js
{foo:'bar'}
```

### 3.2 业务失败场景

输入：

```js
unwrap({code:400, description:'bad', result:null})
```

结果：

- 抛出 `Error`
- `message === 'bad'`
- `code === 400`
- `result === null`

### 3.3 旧接口透传场景

输入：

```js
unwrap({ok:true, data:123})
```

结果：

```js
{ok:true, data:123}
```

## 4. 结论

已完成阶段 A 前置动作：`frontend/js/api.js` 增加 `unwrap` 兼容层，并接入全部 6 个通用 API 方法；未改动任何页面逻辑。该改动满足迁移计划 §4.2 的要求，可作为后续各模块逐步切换到 `Result` 响应形状的前置基础。