"""
采集会话管理模块
用于管理 WASAPI 音频采集会话
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify

# 创建采集 Blueprint
capture_bp = Blueprint('capture', __name__, url_prefix='/api/capture')

# 会话存储（内存中，生产环境可用数据库）
_sessions = {}

# 录音文件存储目录
AGENT_RECORDINGS_DIR = Path(__file__).parent.parent.parent / 'agent' / 'recordings'
AGENT_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 辅助函数
# ============================================================================

def generate_session_id():
    """生成会话 ID"""
    return f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


def get_session_dir(date_str=None):
    """获取当天的录音目录"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")
    session_dir = AGENT_RECORDINGS_DIR / date_str
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


# ============================================================================
# API 端点
# ============================================================================

@capture_bp.route('/start', methods=['POST'])
def start_session():
    """
    创建采集会话
    POST /api/capture/start
    
    请求：
    {
        "source": "system_loopback"  // 来源类型
    }
    
    响应：
    {
        "session_id": "sess_20260323_143025_abc123",
        "status": "ready",
        "source": "system_loopback",
        "created_at": "2026-03-23T14:30:25"
    }
    """
    data = request.get_json() or {}
    source = data.get('source', 'system_loopback')
    
    session_id = generate_session_id()
    session = {
        'session_id': session_id,
        'source': source,
        'status': 'ready',  # ready -> recording_requested -> recording -> recorded
        'created_at': datetime.now().isoformat(),
        'started_at': None,
        'ended_at': None,
        'file_name': None,
        'file_path': None,
        'duration_sec': 0,
        'sample_rate': 0,
        'channels': 0,
        'device_name': None,
        'error': None
    }
    
    _sessions[session_id] = session
    
    return jsonify({
        'session_id': session_id,
        'status': session['status'],
        'source': source,
        'created_at': session['created_at']
    })


@capture_bp.route('/active', methods=['GET'])
def get_active_session():
    """
    获取当前待采集会话
    GET /api/capture/active
    
    响应：
    {
        "session_id": "sess_20260323_143025_abc123",
        "status": "recording_requested"
    }
    
    如果没有活跃会话，返回 404
    """
    # 查找状态为 ready 或 recording_requested 的会话
    for session_id, session in _sessions.items():
        if session['status'] in ['ready', 'recording_requested']:
            return jsonify({
                'session_id': session_id,
                'status': session['status']
            })
    
    return jsonify({'session_id': None, 'status': None}), 404


@capture_bp.route('/request-recording', methods=['POST'])
def request_recording():
    """
    请求开始录制（网页点击开始采集后调用）
    POST /api/capture/request-recording
    
    请求：
    {
        "session_id": "sess_20260323_143025_abc123"
    }
    """
    data = request.get_json() or {}
    session_id = data.get('session_id')
    
    if not session_id or session_id not in _sessions:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    session = _sessions[session_id]
    session['status'] = 'recording_requested'
    
    return jsonify({
        'session_id': session_id,
        'status': session['status']
    })


@capture_bp.route('/register-file', methods=['POST'])
def register_file():
    """
    上报已保存音频文件（Agent 完成后调用）
    POST /api/capture/register-file
    
    请求：
    {
        "session_id": "sess_20260323_143025_abc123",
        "file_name": "sess_20260323_143025.wav",
        "file_path": "C:/project/agent/recordings/20260323/sess_20260323_143025.wav",
        "sample_rate": 48000,
        "channels": 2,
        "duration_sec": 37.2,
        "meta": {
            "encoding": "pcm16",
            "device_name": "Speakers (Realtek Audio)"
        }
    }
    """
    data = request.get_json() or {}
    session_id = data.get('session_id')
    
    if not session_id or session_id not in _sessions:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    session = _sessions[session_id]
    
    # 更新会话信息
    session['status'] = 'recorded'
    session['file_name'] = data.get('file_name')
    session['file_path'] = data.get('file_path')
    session['sample_rate'] = data.get('sample_rate', 0)
    session['channels'] = data.get('channels', 0)
    session['duration_sec'] = data.get('duration_sec', 0)
    session['device_name'] = data.get('meta', {}).get('device_name')
    session['ended_at'] = datetime.now().isoformat()
    
    # 如果是本地路径，尝试复制到服务器
    local_path = data.get('file_path')
    if local_path and os.path.exists(local_path):
        try:
            # 获取日期目录
            date_str = datetime.now().strftime("%Y%m%d")
            dest_dir = get_session_dir(date_str)
            
            # 复制文件到服务器
            import shutil
            dest_path = dest_dir / data.get('file_name')
            shutil.copy2(local_path, dest_path)
            
            # 更新路径为服务器路径
            session['file_path'] = str(dest_path)
            session['local_file_path'] = str(dest_path)
        except Exception as e:
            session['error'] = f"File copy failed: {str(e)}"
    
    return jsonify({
        'ok': True,
        'status': session['status'],
        'session_id': session_id
    })


@capture_bp.route('/stop', methods=['POST'])
def stop_session():
    """
    结束采集会话
    POST /api/capture/stop
    
    请求：
    {
        "session_id": "sess_20260323_143025_abc123"
    }
    """
    data = request.get_json() or {}
    session_id = data.get('session_id')
    
    if not session_id or session_id not in _sessions:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    session = _sessions[session_id]
    session['status'] = 'stopped'
    
    return jsonify({
        'ok': True,
        'status': session['status'],
        'session_id': session_id
    })


@capture_bp.route('/list', methods=['GET'])
def list_sessions():
    """
    获取所有采集会话
    GET /api/capture/list
    
    查询参数：
    - limit: 返回数量限制
    - status: 按状态过滤
    """
    limit = request.args.get('limit', 50, type=int)
    status_filter = request.args.get('status')
    
    sessions = list(_sessions.values())
    
    # 按状态过滤
    if status_filter:
        sessions = [s for s in sessions if s['status'] == status_filter]
    
    # 按时间倒序
    sessions.sort(key=lambda x: x['created_at'], reverse=True)
    
    # 限制数量
    sessions = sessions[:limit]
    
    # 简化返回
    result = []
    for s in sessions:
        result.append({
            'session_id': s['session_id'],
            'source': s['source'],
            'status': s['status'],
            'created_at': s['created_at'],
            'duration_sec': s['duration_sec'],
            'file_name': s['file_name']
        })
    
    return jsonify({'sessions': result, 'total': len(result)})


@capture_bp.route('/detail/<session_id>', methods=['GET'])
def get_session_detail(session_id):
    """
    获取会话详情
    GET /api/capture/detail/<session_id>
    """
    if session_id not in _sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify(_sessions[session_id])


# ============================================================================
# 识别接口
# ============================================================================

@capture_bp.route('/transcribe', methods=['POST'])
def transcribe_session():
    """
    对采集的音频进行识别
    POST /api/capture/transcribe
    
    请求：
    {
        "session_id": "sess_20260323_143025_abc123",
        "mode": "melody"  // 或 "polyphonic"
    }
    """
    data = request.get_json() or {}
    session_id = data.get('session_id')
    mode = data.get('mode', 'melody')
    
    if not session_id or session_id not in _sessions:
        return jsonify({'error': 'Invalid session_id'}), 400
    
    session = _sessions[session_id]
    
    # 检查文件是否存在
    if not session.get('file_path') or not os.path.exists(session['file_path']):
        return jsonify({'error': 'Audio file not found'}), 404
    
    # 导入识别模块
    try:
        from transcriber import MelodyTranscriber, PolyphonicTranscriber
        
        # 更新状态
        session['status'] = 'transcribing'
        
        # 选择识别模式
        if mode == 'polyphonic':
            transcriber = PolyphonicTranscriber()
        else:
            transcriber = MelodyTranscriber()
        
        # 执行识别
        result = transcriber.transcribe(session['file_path'])
        
        # 生成 MIDI
        midi_filename = f"{session_id}_{mode}.mid"
        midi_dir = Path(__file__).parent.parent / 'outputs'
        midi_dir.mkdir(exist_ok=True)
        midi_path = midi_dir / midi_filename
        transcriber.save_midi(str(midi_path))
        
        # 更新状态
        session['status'] = 'done'
        session['transcription_mode'] = mode
        session['midi_file'] = str(midi_path)
        session['result'] = result
        
        return jsonify({
            'ok': True,
            'status': 'done',
            'mode': mode,
            'result': result,
            'midi_file': str(midi_path)
        })
        
    except Exception as e:
        session['status'] = 'failed'
        session['error'] = str(e)
        return jsonify({'error': str(e)}), 500


# ============================================================================
# 导出
# ============================================================================

def register_blueprint(app):
    """注册 Blueprint 到 Flask 应用"""
    app.register_blueprint(capture_bp)