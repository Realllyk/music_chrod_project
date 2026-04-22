"""
健康检查 Controller
处理健康检查和系统状态相关的 API 请求
"""

from datetime import datetime

from flask import Blueprint

from database import DatabaseConnection, test_connection
from pojo.vo import Result

health_controller = Blueprint('health', __name__, url_prefix='/api')


@health_controller.route('/health', methods=['GET'])
def health_check():
    return Result.success({'status': 'ok', 'message': 'Service is running'}).to_response()


@health_controller.route('/status', methods=['GET'])
def status():
    conn = DatabaseConnection.get_connection()
    connected = conn is not None
    if conn:
        conn.close()

    return Result.success({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'database': {
            'enabled': DatabaseConnection.config.enabled,
            'connected': connected,
        },
    }).to_response()


@health_controller.route('/db/test', methods=['POST'])
def test_db():
    ok, error = test_connection()
    if ok:
        return Result.success({'ok': True, 'message': 'Database connected'}).to_response()
    return Result.server_error(error or 'Database connection failed').to_response()
