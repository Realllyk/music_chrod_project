"""
采集 Service
负责采集会话的逻辑处理
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from mappers.capture_mapper import CaptureSessionsMapper
from database import DatabaseConnection


class CaptureService:
    """采集会话业务逻辑类"""
    
    # 内存存储（作为缓存）
    _memory_sessions = {}
    
    # 会话持久化文件
    _sessions_file = None
    
    @classmethod
    def _get_sessions_file(cls):
        """获取会话文件路径"""
        if cls._sessions_file is None:
            cls._sessions_file = Path(__file__).parent.parent.parent / 'agent' / 'sessions.json'
        return cls._sessions_file
    
    @classmethod
    def _load_sessions(cls):
        """从文件加载会话"""
        sessions_file = cls._get_sessions_file()
        if sessions_file.exists():
            try:
                with open(sessions_file, 'r', encoding='utf-8') as f:
                    cls._memory_sessions = json.load(f)
                print(f"✓ 已加载 {len(cls._memory_sessions)} 个会话")
            except Exception as e:
                print(f"加载会话失败: {e}")
    
    @classmethod
    def _save_sessions(cls):
        """保存会话到文件"""
        try:
            sessions_file = cls._get_sessions_file()
            sessions_file.parent.mkdir(parents=True, exist_ok=True)
            with open(sessions_file, 'w', encoding='utf-8') as f:
                json.dump(cls._memory_sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存会话失败: {e}")
    
    @classmethod
    def init(cls):
        """初始化"""
        cls._load_sessions()
        # 尝试同步到数据库
        cls._sync_to_database()
    
    @classmethod
    def _sync_to_database(cls):
        """同步到数据库"""
        for session_id, session in cls._memory_sessions.items():
            existing = CaptureSessionsMapper.find_by_session_id(session_id)
            if not existing:
                CaptureSessionsMapper.insert(session)
    
    @staticmethod
    def generate_session_id():
        """生成会话ID"""
        return f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    @classmethod
    def create_session(cls, source='system_loopback'):
        """创建采集会话"""
        session_id = cls.generate_session_id()
        session = {
            'session_id': session_id,
            'source': source,
            'status': 'ready',
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
        
        cls._memory_sessions[session_id] = session
        cls._save_sessions()
        
        # 同步到数据库
        CaptureSessionsMapper.insert(session)
        
        return session
    
    @classmethod
    def get_session(cls, session_id):
        """获取会话"""
        return cls._memory_sessions.get(session_id)
    
    @classmethod
    def get_active_session(cls):
        """获取活跃会话"""
        for session_id, session in cls._memory_sessions.items():
            if session.get('status') in ['ready', 'recording_requested']:
                return session
        return None
    
    @classmethod
    def list_sessions(cls, limit=50, status_filter=None):
        """列出所有会话"""
        sessions = list(cls._memory_sessions.values())
        
        if status_filter:
            sessions = [s for s in sessions if s.get('status') == status_filter]
        
        sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return sessions[:limit]
    
    @classmethod
    def update_session(cls, session_id, data):
        """更新会话"""
        if session_id in cls._memory_sessions:
            cls._memory_sessions[session_id].update(data)
            cls._save_sessions()
            
            # 同步到数据库
            CaptureSessionsMapper.update(session_id, data)
            return True
        return False
    
    @classmethod
    def register_file(cls, session_id, file_data):
        """注册文件"""
        if session_id in cls._memory_sessions:
            session = cls._memory_sessions[session_id]
            session['status'] = 'recorded'
            session['file_name'] = file_data.get('file_name')
            session['file_path'] = file_data.get('file_path')
            session['sample_rate'] = file_data.get('sample_rate', 0)
            session['channels'] = file_data.get('channels', 0)
            session['duration_sec'] = file_data.get('duration_sec', 0)
            session['device_name'] = file_data.get('meta', {}).get('device_name')
            session['ended_at'] = datetime.now().isoformat()
            
            cls._save_sessions()
            
            # 同步到数据库
            CaptureSessionsMapper.update(session_id, session)
            return True
        return False
