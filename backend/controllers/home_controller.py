"""
主页 Controller
处理前端页面路由 - 已移交给 Nginx
"""

from pathlib import Path

from flask import Blueprint, send_file

from pojo.vo import Result

home_controller = Blueprint('home', __name__, url_prefix='/api')


@home_controller.route('/outputs/<path:filename>', methods=['GET'])
def serve_output(filename):
    """服务输出文件。"""
    output_dir = Path(__file__).parent.parent / 'outputs'
    file_path = output_dir / filename
    if file_path.exists() and file_path.is_file():
        return send_file(file_path)
    return Result.not_found('File not found').to_response()
