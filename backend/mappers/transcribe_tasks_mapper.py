"""转录任务 Mapper。"""

from __future__ import annotations

import logging

from database import get_db

logger = logging.getLogger(__name__)


class TranscribeTasksMapper:
    """transcribe_tasks 表的数据访问层。"""

    @staticmethod
    def insert(task_id: str, song_id: int, mode: str) -> bool:
        conn = get_db()
        if not conn:
            return False

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO transcribe_tasks (task_id, song_id, mode, status) VALUES (%s, %s, %s, %s)",
                    (task_id, song_id, mode, 'pending'),
                )
                conn.commit()
            return True
        except Exception as exc:
            logger.exception(f'创建转录任务失败: {exc}')
            return False

    @staticmethod
    def update_status(task_id: str, status: str, result_path: str = None, error: str = None) -> bool:
        conn = get_db()
        if not conn:
            return False

        try:
            with conn.cursor() as cursor:
                if result_path:
                    cursor.execute(
                        "UPDATE transcribe_tasks SET status=%s, result_path=%s WHERE task_id=%s",
                        (status, result_path, task_id),
                    )
                elif error:
                    cursor.execute(
                        "UPDATE transcribe_tasks SET status=%s, error=%s WHERE task_id=%s",
                        (status, error, task_id),
                    )
                else:
                    cursor.execute(
                        "UPDATE transcribe_tasks SET status=%s WHERE task_id=%s",
                        (status, task_id),
                    )
                conn.commit()
            return True
        except Exception as exc:
            logger.exception(f'更新转录任务失败: {exc}')
            return False

    @staticmethod
    def find_by_task_id(task_id: str):
        conn = get_db()
        if not conn:
            return None

        try:
            with conn.cursor() as cursor:
                cursor.execute('SELECT * FROM transcribe_tasks WHERE task_id=%s', (task_id,))
                return cursor.fetchone()
        except Exception as exc:
            logger.exception(f'查询转录任务失败: {exc}')
            return None

    @staticmethod
    def find_by_song_id(song_id: int):
        conn = get_db()
        if not conn:
            return []

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    'SELECT * FROM transcribe_tasks WHERE song_id=%s ORDER BY created_at DESC',
                    (song_id,),
                )
                return cursor.fetchall() or []
        except Exception as exc:
            logger.exception(f'按歌曲查询转录任务失败: {exc}')
            return []
