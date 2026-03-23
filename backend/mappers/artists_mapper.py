"""
歌手 Mapper
负责歌手数据的数据库操作
"""

from database import get_db


class ArtistsMapper:
    """歌手数据操作类"""
    
    @staticmethod
    def insert(artist_data):
        """插入歌手"""
        conn = get_db()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO artists (name, avatar, bio)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(sql, (
                    artist_data.get('name'),
                    artist_data.get('avatar'),
                    artist_data.get('bio')
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"插入歌手失败: {e}")
            return None
    
    @staticmethod
    def find_all(limit=100, offset=0):
        """查询所有歌手"""
        conn = get_db()
        if not conn:
            return [], 0
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as total FROM artists WHERE deleted_at IS NULL")
                total = cursor.fetchone()['total']
                
                cursor.execute("""
                    SELECT * FROM artists 
                    WHERE deleted_at IS NULL
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s
                """, (limit, offset))
                artists = cursor.fetchall()
                
                return artists, total
        except Exception as e:
            print(f"查询歌手失败: {e}")
            return [], 0
    
    @staticmethod
    def find_by_id(artist_id):
        """根据ID查询歌手"""
        conn = get_db()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM artists WHERE id = %s AND deleted_at IS NULL", 
                    (artist_id,)
                )
                return cursor.fetchone()
        except Exception as e:
            print(f"查询歌手失败: {e}")
            return None
    
    @staticmethod
    def find_by_name(name):
        """根据名字查询歌手"""
        conn = get_db()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM artists WHERE name = %s AND deleted_at IS NULL", 
                    (name,)
                )
                return cursor.fetchone()
        except Exception as e:
            print(f"查询歌手失败: {e}")
            return None
    
    @staticmethod
    def update(artist_id, artist_data):
        """更新歌手"""
        conn = get_db()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                fields = []
                values = []
                for key in ['name', 'avatar', 'bio']:
                    if key in artist_data and artist_data[key] is not None:
                        fields.append(f"{key} = %s")
                        values.append(artist_data[key])
                
                if fields:
                    values.append(artist_id)
                    sql = f"UPDATE artists SET {', '.join(fields)} WHERE id = %s"
                    cursor.execute(sql, values)
                    conn.commit()
                    return True
                return False
        except Exception as e:
            print(f"更新歌手失败: {e}")
            return False
    
    @staticmethod
    def delete(artist_id):
        """删除歌手（软删除）"""
        conn = get_db()
        if not conn:
            return False
        
        try:
            from datetime import datetime
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE artists SET deleted_at = %s WHERE id = %s",
                    (datetime.now(), artist_id)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"删除歌手失败: {e}")
            return False
