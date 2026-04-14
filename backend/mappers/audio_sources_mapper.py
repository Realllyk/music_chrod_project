"""音源 Mapper"""
from database import get_db


class AudioSourcesMapper:
    
    @staticmethod
    def insert(data):
        """插入音源"""
        conn = get_db()
        if not conn:
            return None
        
        try:
            fields = list(data.keys())
            values = list(data.values())
            placeholders = ', '.join(['%s'] * len(fields))
            columns = ', '.join(fields)
            
            sql = f"INSERT INTO audio_sources ({columns}) VALUES ({placeholders})"
            
            with conn.cursor() as cursor:
                cursor.execute(sql, values)
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"插入音源失败: {e}")
            return None
    
    @staticmethod
    def find_by_id(audio_id):
        """根据ID查询"""
        conn = get_db()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM audio_sources WHERE id = %s", (audio_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"查询音源失败: {e}")
            return None
    
    @staticmethod
    def find_all(limit=100, offset=0, status=None):
        """查询所有音源"""
        conn = get_db()
        if not conn:
            return [], 0
        
        try:
            with conn.cursor() as cursor:
                if status:
                    cursor.execute("SELECT COUNT(*) as total FROM audio_sources WHERE status = %s", (status,))
                    total_row = cursor.fetchone()
                    total = total_row['total'] if isinstance(total_row, dict) else total_row[0]
                    cursor.execute(
                        "SELECT * FROM audio_sources WHERE status = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
                        (status, limit, offset)
                    )
                else:
                    cursor.execute("SELECT COUNT(*) as total FROM audio_sources")
                    total_row = cursor.fetchone()
                    total = total_row['total'] if isinstance(total_row, dict) else total_row[0]
                    cursor.execute(
                        "SELECT * FROM audio_sources ORDER BY created_at DESC LIMIT %s OFFSET %s",
                        (limit, offset)
                    )
                results = cursor.fetchall()
                return results, total
        except Exception as e:
            print(f"查询音源列表失败: {e}")
            return [], 0
    
    @staticmethod
    def update(audio_id, data):
        """更新音源"""
        conn = get_db()
        if not conn:
            return False
        
        try:
            sets = []
            values = []
            for key, value in data.items():
                sets.append(f"{key} = %s")
                values.append(value)
            
            values.append(audio_id)
            
            with conn.cursor() as cursor:
                cursor.execute(
                    f"UPDATE audio_sources SET {', '.join(sets)} WHERE id = %s",
                    values
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"更新音源失败: {e}")
            return False
    
    @staticmethod
    def delete(audio_id):
        """删除音源"""
        conn = get_db()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE audio_sources SET status='deleted' WHERE id = %s", (audio_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"删除音源失败: {e}")
            return False
