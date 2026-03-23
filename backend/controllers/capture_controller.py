"""
采集 Controller
处理采集会话相关的 API 请求
"""

import os
from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
from services.capture_service import CaptureService
from services.songs_service import SongsService
from transcriber import MelodyTranscriber, PolyphonicTranscriber

# 创建 Blueprint
capture_controller = Blueprint('capture', __name__, url_prefix='/api/capture')

# 录音文件存储目录
AGENT_RECORDINGS_DIR = Path(__file__).parent.parent.parent / 'agent' / 'recordings'


def get_session_dir(date_str=None):
    """获取录音目录"""
    if date_str is None:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
    session_dir = AGENT_RECORDINGS_DIR / date_str
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


# ============================================================================
# 采集会话 API
# ============================================================================

@capture_controller.route('/start', methods=['POST'])
def start_session():
    """创建采集会话"""
    data = request.get_json() or {}
    source = data.get('source', 'system_loopback')
    
    session = CaptureService.create_session(source)
    
    return jsonify({
        'session_id': session['session_id'],
        'status': session['status'],
        'source': source,
        'created_at': session['created_at'].isoformat() if session.get('created_at') else None
    })


@capture_controller.route('/active', methods=['GET'])
def get_active_session():
    """获取活跃的采集会话"""
    session = CaptureService.get_active_session()
    if session:
        return jsonify({
            'session_id': session['session_id'],
            'status': session['status']
        })
    return jsonify({'session_id': None, 'status': None}), 404


@capture_controller.route('/request-recording', methods=['POST'])
def request_recording():
    """请求开始录制"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    
    session = CaptureService.get_session(session_id)
    if not session:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    CaptureService.update_session(session_id, {'status': 'recording_requested'})
    
    return jsonify({
        'session_id': session_id,
        'status': 'recording_requested'
    })


@capture_controller.route('/register-file', methods=['POST'])
def register_file():
    """注册已保存的文件"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    
    session = CaptureService.get_session(session_id)
    if not session:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    CaptureService.register_file(session_id, data)
    
    return jsonify({
        'ok': True,
        'status': 'recorded',
        'session_id': session_id,
        'message': '请使用 /api/capture/upload-file 上传 WAV 文件'
    })


@capture_controller.route('/upload-file', methods=['POST'])
def upload_file():
    """上传 WAV 文件"""
    session_id = request.form.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    # 保存文件
    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d")
    dest_dir = get_session_dir(date_str)
    
    filename = file.filename or f"{session_id}.wav"
    file_path = dest_dir / filename
    
    file.save(str(file_path))
    
    # 更新会话
    CaptureService.update_session(session_id, {
        'status': 'recorded',
        'file_name': filename,
        'file_path': str(file_path)
    })
    
    return jsonify({
        'ok': True,
        'status': 'uploaded',
        'session_id': session_id,
        'file_path': str(file_path)
    })


@capture_controller.route('/stop', methods=['POST'])
def stop_session():
    """停止采集会话"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    
    CaptureService.update_session(session_id, {'status': 'stopped'})
    
    return jsonify({
        'ok': True,
        'status': 'stopped',
        'session_id': session_id
    })


@capture_controller.route('/list', methods=['GET'])
def list_sessions():
    """获取会话列表"""
    limit = request.args.get('limit', 50, type=int)
    status_filter = request.args.get('status')
    
    sessions, total = CaptureService.list_sessions(limit, status_filter)
    
    result = []
    for s in sessions:
        created_at = s.get('created_at')
        result.append({
            'session_id': s.get('session_id'),
            'source': s.get('source'),
            'status': s.get('status'),
            'created_at': created_at.isoformat() if created_at else None,
            'duration_sec': s.get('duration_sec'),
            'file_name': s.get('file_name')
        })
    
    return jsonify({'sessions': result, 'total': total})


@capture_controller.route('/detail/<session_id>', methods=['GET'])
def get_session_detail(session_id):
    """获取会话详情"""
    session = CaptureService.get_session(session_id)
    if session:
        return jsonify(session)
    return jsonify({'error': 'Session not found'}), 404


# ============================================================================
# 识别 API
# ============================================================================

@capture_controller.route('/transcribe', methods=['POST'])
def transcribe_session():
    """对采集的音频进行识别"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    mode = data.get('mode', 'melody')
    
    session = CaptureService.get_session(session_id)
    if not session:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    # 检查文件是否存在
    file_path = session.get('file_path')
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Audio file not found'}), 404
    
    try:
        # 更新状态
        CaptureService.update_session(session_id, {'status': 'transcribing'})
        
        # 执行识别
        if mode == 'polyphonic':
            transcriber = PolyphonicTranscriber()
        else:
            transcriber = MelodyTranscriber()
        
        result = transcriber.transcribe(file_path)
        
        # 保存 MIDI
        midi_filename = f"{session_id}_{mode}.mid"
        midi_dir = Path(__file__).parent.parent / 'outputs'
        midi_dir.mkdir(exist_ok=True)
        midi_path = midi_dir / midi_filename
        transcriber.save_midi(str(midi_path))
        
        # 创建歌曲记录
        song_data = {
            'title': session.get('file_name', '未命名').replace('.wav', ''),
            'source': 'wasapi_loopback',
            'audio_path': file_path,
            'duration': int(session.get('duration_sec', 0) * 1000),
            'status': 'completed',
            'session_id': session_id
        }
        
        if mode == 'melody':
            song_data['melody_path'] = str(midi_path)
        else:
            song_data['chord_path'] = str(midi_path)
        
        song_id = SongsService.add_song(song_data)
        
        # 添加分析结果
        SongsService.add_analysis(song_id, mode, result, str(midi_path))
        
        # 关联歌曲到会话
        CaptureService.update_session(session_id, {'song_id': song_id})
        
        # 更新状态
        CaptureService.update_session(session_id, {'status': 'done'})
        
        return jsonify({
            'ok': True,
            'status': 'done',
            'mode': mode,
            'result': result,
            'midi_file': str(midi_path),
            'song_id': song_id
        })
        
    except Exception as e:
        CaptureService.update_session(session_id, {'status': 'failed'})
        return jsonify({'error': str(e)}), 500
