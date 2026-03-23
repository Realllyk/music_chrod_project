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
            'status': 'ready'
        }
        
        # 保存到数据库
        CaptureSessionsMapper.insert(session_data)
        
        # 返回完整会话信息
        session = CaptureSessionsMapper.find_by_session_id(session_id)
        return session
    
    @staticmethod
    def get_session(session_id):
        """获取会话"""
        return CaptureSessionsMapper.find_by_session_id(session_id)
    
    @staticmethod
    def get_active_session():
        """获取活跃会话"""
        return CaptureSessionsMapper.find_active()
    
    @staticmethod
    def list_sessions(limit=50, status_filter=None):
        """列出所有会话"""
        sessions, total = CaptureSessionsMapper.find_all(limit, 0)
        
        if status_filter:
            sessions = [s for s in sessions if s.get('status') == status_filter]
        
        return sessions, total
    
    @staticmethod
    def update_session(session_id, data):
        """更新会话"""
        return CaptureSessionsMapper.update(session_id, data)
    
    @staticmethod
    def register_file(session_id, file_data):
        """注册文件"""
        update_data = {
            'status': 'recorded',
            'file_name': file_data.get('file_name'),
            'file_path': file_data.get('file_path'),
            'sample_rate': file_data.get('sample_rate', 0),
            'channels': file_data.get('channels', 0),
            'duration_sec': file_data.get('duration_sec', 0),
            'ended_at': datetime.now()
        }
        
        # 可选：设备名称
        if file_data.get('meta', {}).get('device_name'):
            update_data['device_name'] = file_data['meta']['device_name']
        
        return CaptureSessionsMapper.update(session_id, update_data)
