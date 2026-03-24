"""
采集会话 Mapper
负责采集会话数据的数据库操作
"""

from database import get_db


class CaptureSessionsMapper:
    """采集会话数据操作类"""
    
    @staticmethod
    def insert(session_data):
        """插入采集会话"""
        conn = get_db()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO capture_sessions 
                    (session_id, source, status, file_name, file_path, 
                     sample_rate, channels, duration_sec, device_name, ended_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    session_data.get('session_id'),
                    session_data.get('source'),
                    session_data.get('status', 'ready'),
                    session_data.get('file_name'),
                    session_data.get('file_path'),
                    session_data.get('sample_rate', 0),
                    session_data.get('channels', 0),
                    session_data.get('duration_sec', 0),
                    session_data.get('device_name'),
                    session_data.get('ended_at')
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"插入采集会话失败: {e}")
            return None
    
    @staticmethod
    def find_all(limit=100, offset=0):
        """查询所有采集会话"""
        conn = get_db()
        if not conn:
            return [], 0
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as total FROM capture_sessions")
                total = cursor.fetchone()['total']
                
                cursor.execute("""
                    SELECT * FROM capture_sessions 
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s
                """, (limit, offset))
                sessions = cursor.fetchall()
                
                return sessions, total
        except Exception as e:
            print(f"查询采集会话失败: {e}")
            return [], 0
    
    @staticmethod
    def find_by_session_id(session_id):
        """根据会话ID查询"""
        conn = get_db()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM capture_sessions WHERE session_id = %s", (session_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"查询采集会话失败: {e}")
            return None
    
    @staticmethod
    def find_active():
        """查询活跃的采集会话"""
        conn = get_db()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM capture_sessions 
                    WHERE status IN ('ready', 'recording_requested', 'recording')
                    ORDER BY created_at DESC 
                    LIMIT 1
                """)
                return cursor.fetchone()
        except Exception as e:
            print(f"查询活跃会话失败: {e}")
            return None
    
    @staticmethod
    def update(session_id, session_data):
        """更新采集会话"""
        conn = get_db()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                fields = []
                values = []
                for key in ['status', 'file_name', 'file_path', 'duration_sec', 'ended_at']:
                    if key in session_data and session_data[key] is not None:
                        fields.append(f"{key} = %s")
                        values.append(session_data[key])
                
                if fields:
                    values.append(session_id)
                    sql = f"UPDATE capture_sessions SET {', '.join(fields)} WHERE session_id = %s"
                    cursor.execute(sql, values)
                    conn.commit()
                    return True
                return False
        except Exception as e:
            print(f"更新采集会话失败: {e}")
            return False
    
    @staticmethod
    def delete(session_id):
        """删除采集会话"""
        conn = get_db()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM capture_sessions WHERE session_id = %s", (session_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"删除采集会话失败: {e}")
            return False
