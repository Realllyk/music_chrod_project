"""
音乐扒谱应用 - Flask 后端
主应用和路由定义
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pathlib import Path
import os
import traceback
import logging
import json
from datetime import datetime

# 添加 backend 目录到 Python 路径
import sys
sys.path.insert(0, os.path.dirname(__file__))

from sources import SourceFactory
from transcriber import MelodyTranscriber, PolyphonicTranscriber

# ============================================================================
# 初始化
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

# 全局状态
current_music_source = None


# ============================================================================
# 错误处理
# ============================================================================

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': '请求错误', 'message': str(error)}), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '未找到', 'message': str(error)}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"内部错误: {traceback.format_exc()}")
    return jsonify({'error': '服务器错误', 'message': '发生了意外错误'}), 500


# ============================================================================
# 1. 音乐源管理 API
# ============================================================================

@app.route('/api/sources', methods=['GET'])
def get_sources():
    """获取所有可用的音乐源"""
    try:
        sources = SourceFactory.get_available_sources()
        current = current_music_source.__class__.__name__ if current_music_source else None
        
        return jsonify({
            'status': 'success',
            'available_sources': sources,
            'current_source': current,
            'total': len(sources)
        })
    except Exception as e:
        logger.error(f"获取源列表失败: {e}")
        return jsonify({'error': '获取源列表失败', 'message': str(e)}), 500


@app.route('/api/sources/switch', methods=['POST'])
def switch_source():
    """切换音乐源"""
    global current_music_source
    
    try:
        data = request.get_json()
        source_name = data.get('source_name')
        config = data.get('config', {})
        
        if not source_name:
            return jsonify({'error': '缺少参数', 'message': 'source_name 为必需'}), 400
        
        # 切换源
        current_music_source = SourceFactory.set_current(source_name, config)
        
        # 尝试认证
        if hasattr(current_music_source, 'authenticate'):
            if not current_music_source.authenticate():
                return jsonify({
                    'error': '认证失败',
                    'message': f'{source_name} 认证失败，请检查凭证'
                }), 401
        
        return jsonify({
            'status': 'success',
            'message': f'已切换到 {source_name}',
            'source': source_name
        })
    
    except ValueError as e:
        logger.error(f"切换源失败: {e}")
        return jsonify({'error': '未知的源', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"切换源失败: {e}")
        return jsonify({'error': '切换失败', 'message': str(e)}), 500


# ============================================================================
# 2. 音乐搜索 API
# ============================================================================

@app.route('/api/search', methods=['GET'])
def search_music():
    """搜索音乐"""
    global current_music_source
    
    try:
        if not current_music_source:
            return jsonify({
                'error': '未设置音乐源',
                'message': '请先调用 /api/sources/switch 切换音乐源'
            }), 400
        
        query = request.args.get('q')
        limit = request.args.get('limit', default=10, type=int)
        
        if not query:
            return jsonify({'error': '缺少参数', 'message': 'q (搜索词) 为必需'}), 400
        
        if limit < 1 or limit > 50:
            limit = 10
        
        logger.info(f"搜索: {query} (limit={limit})")
        
        # 执行搜索
        results = current_music_source.search(query, limit=limit)
        
        return jsonify({
            'status': 'success',
            'query': query,
            'results': results,
            'total': len(results)
        })
    
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return jsonify({'error': '搜索失败', 'message': str(e)}), 500


# ============================================================================
# 3. 音乐上传/获取 API
# ============================================================================

@app.route('/api/music/upload', methods=['POST'])
def upload_music():
    """上传本地音乐文件"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': '缺少文件', 'message': 'file 为必需'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': '文件名为空', 'message': '请选择一个文件'}), 400
        
        # 检查文件扩展名
        allowed_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma'}
        ext = Path(file.filename).suffix.lower()
        
        if ext not in allowed_extensions:
            return jsonify({
                'error': '不支持的格式',
                'message': f'支持的格式: {", ".join(allowed_extensions)}'
            }), 400
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"upload_{timestamp}_{file.filename}"
        filepath = UPLOAD_FOLDER / filename
        
        # 保存文件
        file.save(filepath)
        logger.info(f"上传文件: {filename}")
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'filepath': str(filepath),
            'size_bytes': filepath.stat().st_size
        })
    
    except Exception as e:
        logger.error(f"上传失败: {e}")
        return jsonify({'error': '上传失败', 'message': str(e)}), 500


@app.route('/api/music/download/<source>/<music_id>', methods=['GET'])
def download_music(source, music_id):
    """从音乐源下载音乐"""
    global current_music_source
    
    try:
        if not current_music_source:
            return jsonify({
                'error': '未设置音乐源',
                'message': '请先切换音乐源'
            }), 400
        
        # 生成保存路径
        filename = f"{source}_{music_id}.mp3"
        filepath = UPLOAD_FOLDER / filename
        
        logger.info(f"从 {source} 下载: {music_id}")
        
        # 如果已存在，直接返回
        if not filepath.exists():
            # 下载文件
            current_music_source.get_audio_file(music_id, str(filepath))
        
        return jsonify({
            'status': 'success',
            'filename': filename,
            'filepath': str(filepath),
            'size_bytes': filepath.stat().st_size
        })
    
    except Exception as e:
        logger.error(f"下载失败: {e}")
        return jsonify({'error': '下载失败', 'message': str(e)}), 500


# ============================================================================
# 4. 扒谱 API
# ============================================================================

@app.route('/api/transcribe/melody', methods=['POST'])
def transcribe_melody():
    """单旋律提取"""
    try:
        data = request.get_json()
        audio_file = data.get('audio_file')
        
        if not audio_file:
            return jsonify({'error': '缺少参数', 'message': 'audio_file 为必需'}), 400
        
        filepath = UPLOAD_FOLDER / audio_file
        
        if not filepath.exists():
            return jsonify({'error': '文件不存在', 'message': f'{audio_file} 未找到'}), 404
        
        logger.info(f"开始单旋律提取: {audio_file}")
        
        # 执行扒谱
        transcriber = MelodyTranscriber()
        result = transcriber.transcribe(str(filepath))
        
        # 生成 MIDI 文件
        midi_filename = f"melody_{Path(audio_file).stem}.mid"
        midi_path = OUTPUT_FOLDER / midi_filename
        transcriber.save_midi(str(midi_path))
        
        logger.info(f"单旋律提取完成: {midi_filename}")
        
        return jsonify({
            'status': 'success',
            'mode': 'melody',
            'audio_file': audio_file,
            'result': result,
            'midi_file': midi_filename,
            'midi_path': str(midi_path)
        })
    
    except Exception as e:
        logger.error(f"单旋律提取失败: {e}\n{traceback.format_exc()}")
        return jsonify({'error': '提取失败', 'message': str(e)}), 500


@app.route('/api/transcribe/polyphonic', methods=['POST'])
def transcribe_polyphonic():
    """多声部分离"""
    try:
        data = request.get_json()
        audio_file = data.get('audio_file')
        
        if not audio_file:
            return jsonify({'error': '缺少参数', 'message': 'audio_file 为必需'}), 400
        
        filepath = UPLOAD_FOLDER / audio_file
        
        if not filepath.exists():
            return jsonify({'error': '文件不存在', 'message': f'{audio_file} 未找到'}), 404
        
        logger.info(f"开始多声部分离: {audio_file}")
        
        # 执行扒谱
        transcriber = PolyphonicTranscriber()
        result = transcriber.transcribe(str(filepath))
        
        # 生成 MIDI 文件
        midi_filename = f"polyphonic_{Path(audio_file).stem}.mid"
        midi_path = OUTPUT_FOLDER / midi_filename
        transcriber.save_midi(str(midi_path))
        
        logger.info(f"多声部分离完成: {midi_filename}")
        
        return jsonify({
            'status': 'success',
            'mode': 'polyphonic',
            'audio_file': audio_file,
            'result': result,
            'midi_file': midi_filename,
            'midi_path': str(midi_path)
        })
    
    except Exception as e:
        logger.error(f"多声部分离失败: {e}\n{traceback.format_exc()}")
        return jsonify({'error': '分离失败', 'message': str(e)}), 500


# ============================================================================
# 5. 文件下载 API
# ============================================================================

@app.route('/api/download/<file_type>/<filename>', methods=['GET'])
def download_file(file_type, filename):
    """下载输出文件（MIDI、JSON等）"""
    try:
        if file_type == 'midi':
            filepath = OUTPUT_FOLDER / filename
        elif file_type == 'upload':
            filepath = UPLOAD_FOLDER / filename
        else:
            return jsonify({'error': '未知的文件类型'}), 400
        
        if not filepath.exists():
            return jsonify({'error': '文件不存在'}), 404
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"下载失败: {e}")
        return jsonify({'error': '下载失败', 'message': str(e)}), 500


# ============================================================================
# 6. 健康检查和状态 API
# ============================================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取应用状态"""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'upload_folder': str(UPLOAD_FOLDER),
            'output_folder': str(OUTPUT_FOLDER),
            'current_source': current_music_source.__class__.__name__ if current_music_source else None
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({'status': 'ok'}), 200


# ============================================================================
# 7. 根路由
# ============================================================================

@app.route('/', methods=['GET'])
def index():
    """API 文档"""
    return jsonify({
        'name': '🎵 音乐扒谱应用 API',
        'version': '1.0',
        'endpoints': {
            '音乐源': {
                'GET /api/sources': '获取所有可用源',
                'POST /api/sources/switch': '切换音乐源'
            },
            '搜索': {
                'GET /api/search?q=xxx&limit=10': '搜索音乐'
            },
            '音乐文件': {
                'POST /api/music/upload': '上传本地文件',
                'GET /api/music/download/<source>/<music_id>': '下载音乐'
            },
            '扒谱': {
                'POST /api/transcribe/melody': '单旋律提取',
                'POST /api/transcribe/polyphonic': '多声部分离'
            },
            '下载': {
                'GET /api/download/<file_type>/<filename>': '下载输出文件'
            },
            '状态': {
                'GET /api/status': '应用状态',
                'GET /api/health': '健康检查'
            }
        }
    })


# ============================================================================
# 主函数
# ============================================================================

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("🎵 音乐扒谱应用 - 后端服务启动")
    logger.info("="*60)
    logger.info(f"上传文件夹: {UPLOAD_FOLDER}")
    logger.info(f"输出文件夹: {OUTPUT_FOLDER}")
    logger.info("访问 http://localhost:5000 查看 API 文档")
    logger.info("="*60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
