"""
健康检查 Controller
处理健康检查和系统状态相关的 API 请求
"""

from flask import Blueprint, jsonify, request
from database import test_connection, DatabaseConnection

# 创建 Blueprint
health_controller = Blueprint('health', __name__, url_prefix='/api')


@health_controller.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'message': 'Service is running'
    })


@health_controller.route('/status', methods=['GET'])
def status():
    """系统状态"""
    from datetime import datetime
    
    conn = DatabaseConnection.get_connection()
    connected = conn is not None
    if conn:
        conn.close()

    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'database': {
            'enabled': DatabaseConnection.config.enabled,
            'connected': connected
        }
    })


@health_controller.route('/db/test', methods=['POST'])
def test_db():
    """测试数据库连接"""
    ok, error = test_connection()
    
    if ok:
        return jsonify({"ok": True, "message": "Database connected"})
    return jsonify({"ok": False, "error": error}), 500
