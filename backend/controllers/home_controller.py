"""
主页 Controller
处理前端页面路由 - 已移交给 Nginx
"""

from flask import Blueprint, jsonify

# 创建 Blueprint
home_controller = Blueprint('home', __name__)


@home_controller.route('/outputs/<path:filename>', methods=['GET'])
def serve_output(filename):
    """服务输出文件"""
    from flask import send_file
    from pathlib import Path
    output_dir = Path(__file__).parent.parent / 'outputs'
    file_path = output_dir / filename
    if file_path.exists():
        return send_file(file_path)
    return jsonify({'error': 'File not found'}), 404
