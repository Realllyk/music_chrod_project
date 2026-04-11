/**
 * api.js - 统一 API 调用封装
 * 所有页面通过此模块调用后端接口
 */

const API_BASE = '';

/**
 * 统一处理 fetch 响应
 * @param {Response} response
 * @returns {Promise<any>}
 */
async function handleResponse(response) {
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
        return response.json();
    }
    return response.text();
}

/**
 * GET 请求
 * @param {string} path - API 路径（如 '/api/songs/list'）
 * @param {Object} [params] - URLSearchParams 参数对象
 * @returns {Promise<any>}
 */
async function apiGet(path, params) {
    let url = API_BASE + path;
    if (params) {
        const qs = new URLSearchParams(params).toString();
        if (qs) url += '?' + qs;
    }
    const response = await fetch(url);
    if (!response.ok) throw new Error(`GET ${path} failed: ${response.status}`);
    return handleResponse(response);
}

/**
 * POST 请求（JSON body）
 * @param {string} path - API 路径
 * @param {Object} [data] - 请求体对象
 * @returns {Promise<any>}
 */
async function apiPost(path, data) {
    const response = await fetch(API_BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: data ? JSON.stringify(data) : '{}'
    });
    if (!response.ok) throw new Error(`POST ${path} failed: ${response.status}`);
    return handleResponse(response);
}

/**
 * POST 请求（FormData，用于文件上传）
 * @param {string} path - API 路径
 * @param {FormData} formData
 * @returns {Promise<any>}
 */
async function apiPostForm(path, formData) {
    const response = await fetch(API_BASE + path, {
        method: 'POST',
        body: formData
    });
    if (!response.ok) throw new Error(`POST ${path} failed: ${response.status}`);
    return handleResponse(response);
}

/**
 * PUT 请求（JSON body）
 * @param {string} path - API 路径
 * @param {Object} [data] - 请求体对象
 * @returns {Promise<any>}
 */
async function apiPut(path, data) {
    const response = await fetch(API_BASE + path, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: data ? JSON.stringify(data) : '{}'
    });
    if (!response.ok) throw new Error(`PUT ${path} failed: ${response.status}`);
    return handleResponse(response);
}

/**
 * PUT 请求（FormData，用于带文件的更新）
 * @param {string} path - API 路径
 * @param {FormData} formData
 * @returns {Promise<any>}
 */
async function apiPutForm(path, formData) {
    const response = await fetch(API_BASE + path, {
        method: 'PUT',
        body: formData
    });
    if (!response.ok) throw new Error(`PUT ${path} failed: ${response.status}`);
    return handleResponse(response);
}

/**
 * DELETE 请求
 * @param {string} path - API 路径
 * @returns {Promise<any>}
 */
async function apiDelete(path) {
    const response = await fetch(API_BASE + path, {
        method: 'DELETE'
    });
    if (!response.ok) throw new Error(`DELETE ${path} failed: ${response.status}`);
    return handleResponse(response);
}
