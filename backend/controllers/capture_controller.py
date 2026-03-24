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
    # 返回 200 而不是 404，避免日志刷屏
    return jsonify({'session_id': None, 'status': None})


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
    
    # 保存文件到 backend 自己的目录
    from datetime import datetime
    import uuid
    date_str = datetime.now().strftime("%Y%m%d")
    dest_dir = Path(__file__).parent.parent / 'uploads' / 'recordings' / date_str
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # 使用原始文件名或生成唯一文件名
    original_name = file.filename or f"{session_id}.wav"
    filename = f"{uuid.uuid4().hex[:8]}_{original_name}"
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

@capture_controller.route('/transcribe', methods=['PUT'])
def transcribe_session():
    """对采集的音频进行识别"""
    data = request.get_json() or {}
    song_id = data.get('song_id')
    session_id = data.get('session_id')
    mode = data.get('mode', 'melody')
    
    # 获取歌曲信息
    song = SongsService.get_song_by_id(song_id)
    if not song:
        # 如果没有 song_id，尝试通过 session_id 获取
        if session_id:
            session = CaptureService.get_session(session_id)
            if session:
                file_path = session.get('file_path')
                session_id = session_id
        else:
            return jsonify({'error': 'Invalid song_id or session_id'}), 400
    else:
        file_path = song.get('audio_path')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Audio file not found'}), 404
    
    try:
        # 执行识别
        if mode == 'polyphonic':
            transcriber = PolyphonicTranscriber()
        else:
            transcriber = MelodyTranscriber()
        
        result = transcriber.transcribe(file_path)
        
        # 保存 MIDI
        import uuid
        midi_filename = f"song_{song_id}_{mode}_{uuid.uuid4().hex[:6]}.mid"
        midi_dir = Path(__file__).parent.parent / 'outputs'
        midi_dir.mkdir(exist_ok=True)
        midi_path = midi_dir / midi_filename
        transcriber.save_midi(str(midi_path))
        
        # 更新歌曲记录
        update_data = {'status': 'completed'}
        if mode == 'melody':
            update_data['melody_path'] = str(midi_path)
        else:
            update_data['chord_path'] = str(midi_path)
        
        SongsService.update_song(song_id, update_data)
        
        # 添加分析结果
        analysis_type = 'chord' if mode == 'polyphonic' else mode
        SongsService.add_analysis(song_id, analysis_type, result, str(midi_path))
        
        return jsonify({
            'ok': True,
            'status': 'done',
            'mode': mode,
            'result': result,
            'midi_file': str(midi_path),
            'song_id': song_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# 简化后的录音接口
# ============================================================================

@capture_controller.route('/start-recording', methods=['POST'])
def start_recording():
    """开始录音（创建会话+请求录制）"""
    data = request.get_json() or {}
    source = data.get('source', 'system_loopback')
    
    # 创建会话
    session = CaptureService.create_session(source)
    session_id = session['session_id']
    
    # 请求开始录制
    CaptureService.update_status(session_id, 'recording')
    
    return jsonify({
        'ok': True,
        'session_id': session_id,
        'status': 'recording',
        'message': '已开始录音'
    })


@capture_controller.route('/stop-recording', methods=['PUT'])
def stop_recording():
    """停止录音"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    
    # 如果没有指定 session_id，获取当前活跃的
    if not session_id:
        session = CaptureService.get_active_session()
        if session:
            session_id = session['session_id']
    
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
    
    CaptureService.update_status(session_id, 'stopped')
    
    return jsonify({
        'ok': True,
        'status': 'stopped',
        'message': '已停止录音'
    })


@capture_controller.route('/save', methods=['POST'])
def save_recording():
    """保存录音文件名"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    file_name = data.get('file_name', '未命名')
    
    if not session_id:
        return jsonify({'error': 'session_id is required'}), 400
    
    # 获取会话信息
    session = CaptureService.get_session(session_id)
    if not session:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    # 添加 .wav 后缀
    if not file_name.endswith('.wav'):
        file_name = file_name + '.wav'
    
    # 更新文件名
    CaptureService.update_session(session_id, {'file_name': file_name})
    
    return jsonify({
        'ok': True,
        'session_id': session_id,
        'file_name': file_name,
        'message': '保存成功'
    })


@capture_controller.route('/recordings', methods=['GET'])
def get_recordings():
    """获取录音文件列表（用于创建歌曲时选择音源）"""
    result = CaptureService.list_sessions(limit=100)
    sessions = result[0] if isinstance(result, tuple) else result
    
    recordings = []
    for s in sessions:
        if isinstance(s, dict) and s.get('file_path'):
            recordings.append({
                'session_id': s.get('session_id'),
                'file_name': s.get('file_name'),
                'file_path': s.get('file_path'),
                'duration_sec': s.get('duration_sec')
            })
    
    return jsonify({'recordings': recordings})


@capture_controller.route('/upload-wav', methods=['POST'])
def upload_wav():
    """上传 WAV 录音文件"""
    session_id = request.form.get('session_id')
    wav_file = request.files.get('file')
    
    if not session_id or not wav_file:
        return jsonify({'error': 'session_id and file are required'}), 400
    
    # 保存文件
    import uuid
    from pathlib import Path
    
    ext = Path(wav_file.filename).suffix.lower()
    if ext not in ['.wav', '.mp3']:
        return jsonify({'error': 'only wav/mp3 files allowed'}), 400
    
    filename = f"{session_id}_{uuid.uuid4().hex[:6]}{ext}"
    upload_dir = Path(__file__).parent.parent / 'uploads' / 'recordings'
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename
    wav_file.save(str(file_path))
    
    # 更新会话
    CaptureService.update_session(session_id, {
        'file_path': f"/api/uploads/recordings/{filename}",
        'file_name': wav_file.filename,
        'status': 'stopped'
    })
    
    return jsonify({
        'ok': True,
        'session_id': session_id,
        'file_path': f"/api/uploads/recordings/{filename}"
    })


@capture_controller.route('/uploads/recordings/<filename>', methods=['GET'])
def serve_recording(filename):
    """服务录音文件"""
    from pathlib import Path
    recordings_dir = Path(__file__).parent.parent / 'uploads' / 'recordings'
    file_path = recordings_dir / filename
    if file_path.exists():
        return send_file(file_path)
    return jsonify({'error': 'File not found'}), 404
