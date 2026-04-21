"""
采集 Service
负责采集会话的逻辑处理
"""

import uuid
from datetime import datetime

from constants import CaptureStatus
from mappers.capture_mapper import CaptureSessionsMapper


class CaptureService:
    """采集会话业务逻辑类"""

    @staticmethod
    def generate_session_id():
        """生成会话ID"""
        return f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    @staticmethod
    def create_session(source='system_loopback'):
        """创建采集会话"""
        session_id = CaptureService.generate_session_id()
        session_data = {
            'session_id': session_id,
            'source': source,
            'status': CaptureStatus.READY.value,
        }

        CaptureSessionsMapper.insert(session_data)
        return CaptureSessionsMapper.find_by_session_id(session_id)

    @staticmethod
    def get_session(session_id):
        """获取会话"""
        return CaptureSessionsMapper.find_by_session_id(session_id)

    @staticmethod
    def get_active_session():
        """获取活跃会话"""
        return CaptureSessionsMapper.find_active()

    @staticmethod
    def list_sessions(limit=50, status_filter=None, offset=0, source_filter=None):
        """列出所有会话"""
        sessions, total = CaptureSessionsMapper.find_all(limit, offset)

        if status_filter:
            if status_filter not in CaptureStatus.values():
                sessions = []
            else:
                sessions = [s for s in sessions if s.get('status') == status_filter]

        if source_filter:
            sessions = [s for s in sessions if s.get('source') == source_filter]

        filtered_total = len(sessions) if (status_filter or source_filter) else total
        return sessions, filtered_total

    @staticmethod
    def list_recordings(limit=100, offset=0, session_id=None, audio_name=None):
        """列出带文件路径的录音会话"""
        sessions, _ = CaptureSessionsMapper.find_all(1000, 0)
        recordings = [s for s in sessions if isinstance(s, dict) and s.get('file_path')]

        if session_id:
            recordings = [s for s in recordings if s.get('session_id') == session_id]
        if audio_name:
            keyword = audio_name.lower()
            recordings = [s for s in recordings if keyword in (s.get('audio_name') or '').lower()]

        total = len(recordings)
        return recordings[offset:offset + limit], total

    @staticmethod
    def update_session(session_id, data):
        """更新会话"""
        if 'status' in data and data['status'] not in CaptureStatus.values():
            del data['status']

        return CaptureSessionsMapper.update(session_id, data)

    @staticmethod
    def update_status(session_id, status):
        """更新会话状态"""
        if status not in CaptureStatus.values():
            return False
        return CaptureSessionsMapper.update(session_id, {'status': status})

    @staticmethod
    def register_file(session_id, file_data):
        """注册文件"""
        update_data = {
            'status': CaptureStatus.RECORDED.value,
            'audio_name': file_data.get('audio_name'),
            'file_path': file_data.get('file_path'),
            'sample_rate': file_data.get('sample_rate', 0),
            'channels': file_data.get('channels', 0),
            'duration_sec': file_data.get('duration_sec', 0),
            'ended_at': datetime.now(),
        }

        if file_data.get('meta', {}).get('device_name'):
            update_data['device_name'] = file_data['meta']['device_name']

        return CaptureSessionsMapper.update(session_id, update_data)

    @staticmethod
    def delete_session(session_id):
        """删除会话"""
        return CaptureSessionsMapper.delete(session_id)
