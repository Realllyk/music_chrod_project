"""
音乐扒谱应用 - Flask 后端
主应用入口
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pathlib import Path
import os
import logging
import json

# 添加 backend 目录到 Python 路径
import sys
sys.path.insert(0, os.path.dirname(__file__))

# 导入配置
from database import DatabaseConnection

# 导入 Controllers
from controllers import (
    home_controller,
    songs_controller,
    capture_controller,
    health_controller,
    music_controller
)

# ============================================================================
# 初始化 Flask 应用
# ============================================================================

app = Flask(__name__)
CORS(app)  # 启用跨域请求

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载配置文件
config_path = Path(__file__).parent / 'config.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 配置文件夹
UPLOAD_FOLDER = Path(__file__).parent.parent / config['paths']['uploads']
OUTPUT_FOLDER = Path(__file__).parent.parent / config['paths']['outputs']
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config['audio']['max_file_size']
app.config['CONFIG'] = config

# ============================================================================
# 注册 Controllers
# ============================================================================

app.register_blueprint(home_controller)
app.register_blueprint(songs_controller)
app.register_blueprint(capture_controller)
app.register_blueprint(health_controller)
app.register_blueprint(music_controller)

# ============================================================================
# ============================================================================
# 初始化
# ============================================================================

# 日志
logger.info("=" * 50)
logger.info("🎵 音乐扒谱应用已启动")
logger.info(f"访问 http://localhost:{config['api']['port']}/app 查看前端")
logger.info("=" * 50)

# 启动 Flask
if __name__ == '__main__':
    app.run(
        debug=config['api'].get('debug', True),
        host=config['api'].get('host', '0.0.0.0'),
        port=config['api'].get('port', 5000)
    )
