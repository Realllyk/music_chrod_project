"""
歌曲分析结果 Mapper
负责歌曲分析结果的数据库操作
"""

import json
from database import get_db


class SongAnalysisMapper:
    """歌曲分析结果数据操作类"""

    @staticmethod
    def _deserialize_row(row):
        if not row:
            return None
        result_json = row.get('result_json')
        if isinstance(result_json, str):
            try:
                row['result_json'] = json.loads(result_json)
            except Exception:
                pass
        return row

    @staticmethod
    def insert(analysis_data):
        """插入分析结果"""
        conn = get_db()
        if not conn:
            return None

        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO song_analysis (song_id, analysis_type, analysis_key, result_json, midi_path)
                    VALUES (%s, %s, %s, %s, %s)
                """
                result_json = analysis_data.get('result_json')
                if isinstance(result_json, dict):
                    result_json = json.dumps(result_json, ensure_ascii=False)

                cursor.execute(sql, (
                    analysis_data.get('song_id'),
                    analysis_data.get('analysis_type'),
                    analysis_data.get('analysis_key'),
                    result_json,
                    analysis_data.get('midi_path')
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"插入分析结果失败: {e}")
            return None

    @staticmethod
    def upsert(analysis_data):
        """按 song_id + analysis_type 覆盖写入分析结果"""
        conn = get_db()
        if not conn:
            return None

        try:
            with conn.cursor() as cursor:
                result_json = analysis_data.get('result_json')
                if isinstance(result_json, dict):
                    result_json = json.dumps(result_json, ensure_ascii=False)

                cursor.execute(
                    """
                    SELECT id FROM song_analysis
                    WHERE song_id = %s AND analysis_type = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (analysis_data.get('song_id'), analysis_data.get('analysis_type')),
                )
                existing = cursor.fetchone()

                if existing:
                    cursor.execute(
                        """
                        UPDATE song_analysis
                        SET analysis_key = %s,
                            result_json = %s,
                            midi_path = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (
                            analysis_data.get('analysis_key'),
                            result_json,
                            analysis_data.get('midi_path'),
                            existing['id'],
                        ),
                    )
                    conn.commit()
                    return existing['id']

                cursor.execute(
                    """
                    INSERT INTO song_analysis (song_id, analysis_type, analysis_key, result_json, midi_path)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        analysis_data.get('song_id'),
                        analysis_data.get('analysis_type'),
                        analysis_data.get('analysis_key'),
                        result_json,
                        analysis_data.get('midi_path')
                    ),
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Upsert 分析结果失败: {e}")
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
                return [SongAnalysisMapper._deserialize_row(row) for row in cursor.fetchall()]
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
                    ORDER BY updated_at DESC, created_at DESC
                    LIMIT 1
                """, (song_id, analysis_type))
                return SongAnalysisMapper._deserialize_row(cursor.fetchone())
        except Exception as e:
            print(f"查询分析结果失败: {e}")
            return None

    @staticmethod
    def find_melody_analysis(song_id):
        return SongAnalysisMapper.find_by_song_and_type(song_id, 'melody')

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
