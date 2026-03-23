"""
歌曲 Mapper
负责歌曲数据的数据库操作
"""

from database import get_db


class SongsMapper:
    """歌曲数据操作类"""
    
    @staticmethod
    def insert(song_data):
        """插入歌曲"""
        conn = get_db()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO songs 
                    (title, artist, album, duration, source, source_id, audio_path, status, session_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    song_data.get('title'),
                    song_data.get('artist'),
                    song_data.get('album'),
                    song_data.get('duration', 0),
                    song_data.get('source'),
                    song_data.get('source_id'),
                    song_data.get('audio_path'),
                    song_data.get('status', 'pending'),
                    song_data.get('session_id')
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"插入歌曲失败: {e}")
            return None
    
    @staticmethod
    def find_all(limit=100, offset=0):
        """查询所有歌曲"""
        conn = get_db()
        if not conn:
            return [], 0
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as total FROM songs")
                total = cursor.fetchone()['total']
                
                cursor.execute("""
                    SELECT * FROM songs 
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s
                """, (limit, offset))
                songs = cursor.fetchall()
                
                return songs, total
        except Exception as e:
            print(f"查询歌曲失败: {e}")
            return [], 0
    
    @staticmethod
    def find_by_id(song_id):
        """根据ID查询歌曲"""
        conn = get_db()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM songs WHERE id = %s", (song_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"查询歌曲失败: {e}")
            return None
    
    @staticmethod
    def find_by_session_id(session_id):
        """根据会话ID查询歌曲"""
        conn = get_db()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM songs WHERE session_id = %s", (session_id,))
                return cursor.fetchone()
        except Exception as e:
            print(f"查询歌曲失败: {e}")
            return None
    
    @staticmethod
    def update(song_id, song_data):
        """更新歌曲"""
        conn = get_db()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                fields = []
                values = []
                for key in ['title', 'artist', 'album', 'duration', 'midi_path', 'status', 'transcription_mode']:
                    if key in song_data and song_data[key] is not None:
                        fields.append(f"{key} = %s")
                        values.append(song_data[key])
                
                if fields:
                    values.append(song_id)
                    sql = f"UPDATE songs SET {', '.join(fields)} WHERE id = %s"
                    cursor.execute(sql, values)
                    conn.commit()
                    return True
                return False
        except Exception as e:
            print(f"更新歌曲失败: {e}")
            return False
    
    @staticmethod
    def delete(song_id):
        """删除歌曲"""
        conn = get_db()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM songs WHERE id = %s", (song_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"删除歌曲失败: {e}")
            return False
