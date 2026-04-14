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
                    (title, artist_id, category, duration, source, source_id, audio_path, melody_path, chord_path, status, session_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    song_data.get('title'),
                    song_data.get('artist_id'),
                    song_data.get('category'),
                    song_data.get('duration', 0),
                    song_data.get('source'),
                    song_data.get('source_id'),
                    song_data.get('audio_path'),
                    song_data.get('melody_path'),
                    song_data.get('chord_path'),
                    song_data.get('status', 'pending'),
                    song_data.get('session_id')
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"插入歌曲失败: {e}")
            return None
    
    @staticmethod
    def get_all(limit=20, offset=0):
        """获取所有歌曲（兼容方法）"""
        return SongsMapper.find_all(limit, offset)
    
    @staticmethod
    def search(keyword, limit=20, offset=0):
        """搜索歌曲（按歌曲名或歌手名）"""
        conn = get_db()
        if not conn:
            return [], 0
        
        try:
            with conn.cursor() as cursor:
                # 先搜索歌手ID
                cursor.execute("SELECT id FROM artists WHERE name LIKE %s", (f'%{keyword}%',))
                artist_ids = [row['id'] for row in cursor.fetchall()]
                
                # 搜索歌曲
                if artist_ids:
                    placeholders = ','.join(['%s'] * len(artist_ids))
                    cursor.execute(f"""
                        SELECT COUNT(*) as total FROM songs 
                        WHERE title LIKE %s OR artist_id IN ({placeholders})
                    """, (f'%{keyword}%',) + tuple(artist_ids))
                else:
                    cursor.execute("""
                        SELECT COUNT(*) as total FROM songs 
                        WHERE title LIKE %s
                    """, (f'%{keyword}%',))
                total = cursor.fetchone()['total']
                
                if artist_ids:
                    placeholders = ','.join(['%s'] * len(artist_ids))
                    cursor.execute(f"""
                        SELECT s.*, a.name as artist_name 
                        FROM songs s 
                        LEFT JOIN artists a ON s.artist_id = a.id
                        WHERE s.title LIKE %s OR s.artist_id IN ({placeholders})
                        ORDER BY s.created_at DESC 
                        LIMIT %s OFFSET %s
                    """, (f'%{keyword}%',) + tuple(artist_ids) + (limit, offset))
                else:
                    cursor.execute("""
                        SELECT s.*, a.name as artist_name 
                        FROM songs s 
                        LEFT JOIN artists a ON s.artist_id = a.id
                        WHERE s.title LIKE %s
                        ORDER BY s.created_at DESC 
                        LIMIT %s OFFSET %s
                    """, (f'%{keyword}%', limit, offset))
                songs = cursor.fetchall()
                
                return songs, total
        except Exception as e:
            print(f"搜索歌曲失败: {e}")
            return [], 0
    
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
                for key in ['title', 'artist_id', 'category', 'duration', 'source', 'source_id', 'audio_path', 'session_id', 'melody_path', 'chord_path', 'status']:
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
