"""
主页 Controller
处理前端页面路由
"""

from flask import Blueprint, send_file
from pathlib import Path

# 创建 Blueprint
home_controller = Blueprint('home', __name__)


@home_controller.route('/')
@home_controller.route('/app')
def index():
    """前端主页"""
    frontend_path = Path(__file__).parent.parent.parent / 'frontend' / 'index.html'
    return send_file(frontend_path)


@home_controller.route('/health')
def health():
    """健康检查（兼容旧版）"""
    from flask import jsonify
    return jsonify({
        'status': 'ok',
        'message': 'Service is running'
    })
