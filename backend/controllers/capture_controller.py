"""
采集 Controller
处理采集会话相关的 API 请求
"""

import os
from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
from services.capture_service import CaptureService
from services.audio_sources_service import AudioSourcesService
from services.file_service import FileService
from utils.aliyun_oss import upload_file as upload_to_oss, download_file

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


@capture_controller.route('/request-recording', methods=['PUT'])
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


@capture_controller.route('/register-file', methods=['PUT'])
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
    """上传 WAV 文件到 OSS"""
    session_id = request.form.get('session_id')

    if not session_id:
        return jsonify({'error': 'Invalid session_id'}), 400

    if 'audio_file' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    # 上传到 OSS，目录为 recordings
    try:
        oss_url = upload_to_oss(file, directory="recordings")
    except Exception as e:
        return jsonify({'error': f'OSS upload failed: {str(e)}'}), 500

    # 更新会话
    update_data = {'status': 'uploaded', 'file_path': oss_url}
    session = CaptureService.get_session(session_id)
    if not session or not session.get('audio_name'):
        update_data['audio_name'] = file.filename or f"{session_id}.wav"

    CaptureService.update_session(session_id, update_data)

    # 上传完成后自动创建音源
    session = CaptureService.get_session(session_id)
    user_audio_name = session.get('audio_name') if session else None
    final_audio_name = user_audio_name if user_audio_name else file.filename

    AudioSourcesService.create_from_session({
        'session_id': session_id,
        'audio_name': final_audio_name,
        'file_path': oss_url,
        'sample_rate': 48000,
        'channels': 2
    })

    return jsonify({
        'ok': True,
        'status': 'uploaded',
        'session_id': session_id,
        'file_path': oss_url
    })


@capture_controller.route('/stop', methods=['PUT'])
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
            'audio_name': s.get('audio_name')
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
# 简化后的录音接口
# ============================================================================

@capture_controller.route('/start-recording', methods=['POST'])
def start_recording():
    """兼容接口：开始录音（创建会话+请求录制）。正式流程请使用 /start + /request-recording。"""
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
    """兼容接口：停止录音。正式流程请使用 /stop。"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    audio_name = data.get('audio_name')  # 接收文件名
    
    # 如果没有指定 session_id，获取当前活跃的
    if not session_id:
        session = CaptureService.get_active_session()
        if session:
            session_id = session['session_id']
    
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
    
    # 更新状态和文件名
    update_data = {'status': 'stopped'}
    if audio_name:
        update_data['audio_name'] = audio_name
    
    CaptureService.update_session(session_id, update_data)
    
    return jsonify({
        'ok': True,
        'status': 'stopped',
        'session_id': session_id,
        'message': '已停止录音'
    })


@capture_controller.route('/save', methods=['PUT'])
def save_recording():
    """保存录音文件名"""
    data = request.get_json() or {}
    session_id = data.get('session_id')
    audio_name = data.get('audio_name', '未命名')
    
    if not session_id:
        return jsonify({'error': 'session_id is required'}), 400
    
    # 获取会话信息
    session = CaptureService.get_session(session_id)
    if not session:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    # 添加 .wav 后缀
    if not audio_name.endswith('.wav'):
        audio_name = audio_name + '.wav'
    
    # 更新文件名
    CaptureService.update_session(session_id, {'audio_name': audio_name})
    
    return jsonify({
        'ok': True,
        'session_id': session_id,
        'audio_name': audio_name,
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
                'audio_name': s.get('audio_name'),
                'file_path': s.get('file_path'),
                'duration_sec': s.get('duration_sec')
            })
    
    return jsonify({'recordings': recordings})


@capture_controller.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """删除录音会话"""
    session = CaptureService.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # 删除文件：本地文件走本地删除，OSS URL/object key 走 OSS 删除
    file_path = session.get('file_path')
    try:
        FileService.delete_path(file_path)
    except Exception:
        pass
    
    # 删除数据库记录
    CaptureService.delete_session(session_id)
    
    return jsonify({'ok': True})


@capture_controller.route('/sessions/<session_id>', methods=['PUT'])
def update_session_info(session_id):
    """更新会话信息（文件名等）"""
    data = request.get_json() or {}
    audio_name = data.get('audio_name')
    
    if not audio_name:
        return jsonify({'error': 'audio_name is required'}), 400
    
    session = CaptureService.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    CaptureService.update_session(session_id, {'audio_name': audio_name})
    
    return jsonify({'ok': True, 'audio_name': audio_name})


@capture_controller.route('/uploads/recordings/<filename>', methods=['GET'])
def serve_recording(filename):
    """服务录音文件（从 OSS 或本地）"""
    from pathlib import Path
    # 先尝试本地
    recordings_dir = Path(__file__).parent.parent / 'uploads' / 'recordings'
    file_path = recordings_dir / filename
    if file_path.exists():
        return send_file(file_path)
    # 再尝试从 OSS 下载
    try:
        object_name = f"recordings/{filename}"
        local_path = download_file(object_name)
        return send_file(local_path)
    except Exception:
        return jsonify({'error': 'File not found'}), 404
