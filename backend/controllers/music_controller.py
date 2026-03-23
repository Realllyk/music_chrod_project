"""
音乐 Controller
处理音乐搜索、上传等 API 请求
"""

import os
from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
from sources import SourceFactory
from transcriber import MelodyTranscriber, PolyphonicTranscriber

# 创建 Blueprint
music_controller = Blueprint('music', __name__, url_prefix='/api')


# ============================================================================
# 音乐源 API
# ============================================================================

@music_controller.route('/sources', methods=['GET'])
def get_sources():
    """获取所有可用的音乐源"""
    sources = SourceFactory.get_available_sources()
    return jsonify({
        'sources': sources,
        'current': type(SourceFactory.get_current()).__name__ if SourceFactory._current_source else None
    })


@music_controller.route('/sources/switch', methods=['POST'])
def switch_source():
    """切换音乐源"""
    data = request.get_json() or {}
    source_name = data.get('source_name')
    source_config = data.get('config', {})
    
    try:
        source = SourceFactory.set_current(source_name, source_config)
        # 认证
        source.authenticate()
        return jsonify({
            'ok': True,
            'source': source_name,
            'message': f'Switched to {source_name}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# 搜索 API
# ============================================================================

@music_controller.route('/search', methods=['GET'])
def search_music():
    """搜索音乐"""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)
    
    try:
        source = SourceFactory.get_current()
        results = source.search(query, limit)
        return jsonify({
            'results': results,
            'total': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# 文件上传 API
# ============================================================================

@music_controller.route('/music/upload', methods=['POST'])
def upload_music():
    """上传音乐文件"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    # 检查文件类型
    allowed_ext = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.wma'}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_ext:
        return jsonify({'error': f'Invalid file type. Allowed: {allowed_ext}'}), 400
    
    # 保存文件
    from datetime import datetime
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    upload_dir = Path(__file__).parent.parent / 'uploads'
    upload_dir.mkdir(exist_ok=True)
    file_path = upload_dir / filename
    file.save(str(file_path))
    
    return jsonify({
        'ok': True,
        'file_id': filename,
        'file_name': file.filename,
        'file_path': str(file_path),
        'size': os.path.getsize(file_path)
    })


# ============================================================================
# 识别 API
# ============================================================================

@music_controller.route('/transcribe/melody', methods=['POST'])
def transcribe_melody():
    """提取单旋律"""
    data = request.get_json() or {}
    audio_file = data.get('audio_file')
    
    if not audio_file:
        return jsonify({'error': 'No audio_file specified'}), 400
    
    file_path = Path(__file__).parent.parent / 'uploads' / audio_file
    if not file_path.exists():
        file_path = Path(audio_file)
    
    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404
    
    try:
        transcriber = MelodyTranscriber()
        result = transcriber.transcribe(str(file_path))
        
        # 保存 MIDI
        midi_filename = f"{audio_file.rsplit('.', 1)[0]}_melody.mid"
        midi_dir = Path(__file__).parent.parent / 'outputs'
        midi_dir.mkdir(exist_ok=True)
        midi_path = midi_dir / midi_filename
        transcriber.save_midi(str(midi_path))
        
        return jsonify({
            'ok': True,
            'result': result,
            'midi_file': str(midi_path)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@music_controller.route('/transcribe/polyphonic', methods=['POST'])
def transcribe_polyphonic():
    """多声部分离"""
    data = request.get_json() or {}
    audio_file = data.get('audio_file')
    
    if not audio_file:
        return jsonify({'error': 'No audio_file specified'}), 400
    
    file_path = Path(__file__).parent.parent / 'uploads' / audio_file
    if not file_path.exists():
        file_path = Path(audio_file)
    
    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404
    
    try:
        transcriber = PolyphonicTranscriber()
        result = transcriber.transcribe(str(file_path))
        
        # 保存 MIDI
        midi_filename = f"{audio_file.rsplit('.', 1)[0]}_polyphonic.mid"
        midi_dir = Path(__file__).parent.parent / 'outputs'
        midi_dir.mkdir(exist_ok=True)
        midi_path = midi_dir / midi_filename
        transcriber.save_midi(str(midi_path))
        
        return jsonify({
            'ok': True,
            'result': result,
            'midi_file': str(midi_path)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# 下载 API
# ============================================================================

@music_controller.route('/download/midi/<filename>', methods=['GET'])
def download_midi(filename):
    """下载 MIDI 文件"""
    midi_dir = Path(__file__).parent.parent / 'outputs'
    midi_path = midi_dir / filename
    
    if not midi_path.exists():
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(midi_path, as_attachment=True, download_name=filename)
