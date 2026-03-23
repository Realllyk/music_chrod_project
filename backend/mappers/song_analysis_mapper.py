"""
歌曲分析结果 Mapper
负责歌曲分析结果的数据库操作
"""

from database import get_db


class SongAnalysisMapper:
    """歌曲分析结果数据操作类"""
    
    @staticmethod
    def insert(analysis_data):
        """插入分析结果"""
        conn = get_db()
        if not conn:
            return None
        
        try:
            import json
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO song_analysis (song_id, analysis_type, result_json, midi_path)
                    VALUES (%s, %s, %s, %s)
                """
                result_json = analysis_data.get('result_json')
                if isinstance(result_json, dict):
                    result_json = json.dumps(result_json, ensure_ascii=False)
                
                cursor.execute(sql, (
                    analysis_data.get('song_id'),
                    analysis_data.get('analysis_type'),
                    result_json,
                    analysis_data.get('midi_path')
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"插入分析结果失败: {e}")
            return None
    
    @staticmethod
    def find_by_song_id(song_id):
        """根据歌曲ID查询所有分析结果"""
        conn = get_db()
        if not conn:
            return []
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM song_analysis 
                    WHERE song_id = %s
                    ORDER BY created_at DESC
                """, (song_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"查询分析结果失败: {e}")
            return []
    
    @staticmethod
    def find_by_song_and_type(song_id, analysis_type):
        """根据歌曲ID和分析类型查询"""
        conn = get_db()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM song_analysis 
                    WHERE song_id = %s AND analysis_type = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (song_id, analysis_type))
                return cursor.fetchone()
        except Exception as e:
            print(f"查询分析结果失败: {e}")
            return None
    
    @staticmethod
    def delete_by_song_id(song_id):
        """删除歌曲的所有分析结果"""
        conn = get_db()
        if not conn:
            return False
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM song_analysis WHERE song_id = %s", (song_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"删除分析结果失败: {e}")
            return False
