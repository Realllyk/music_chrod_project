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

@home_controller.route('/outputs/<path:filename>', methods=['GET'])
def serve_output(filename):
    """服务输出文件"""
    from pathlib import Path
    output_dir = Path(__file__).parent.parent / 'outputs'
    file_path = output_dir / filename
    if file_path.exists():
        return send_file(file_path)
    return jsonify({'error': 'File not found'}), 404

@home_controller.route('/pages/<path:filename>')
def serve_page(filename):
    """服务页面文件"""
    from flask import send_from_directory
    import os
    pages_dir = '/home/realllyka/project/music_chrod_project/frontend/pages'
    print(f'Requesting page: {filename}, path: {pages_dir}')
    return send_from_directory(pages_dir, filename)
