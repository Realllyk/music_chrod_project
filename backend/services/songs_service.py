"""
歌曲 Service
负责歌曲业务的逻辑处理
"""

from __future__ import annotations

import uuid

from constants import SongStatus, AnalysisType
from database import get_db
from mappers.songs_mapper import SongsMapper
from mappers.song_analysis_mapper import SongAnalysisMapper
from pojo.dto.songs_dto import AddSongDTO
from pojo.vo.exceptions import BadRequestException
from services.file_service import FileService


class SongsService:
    """歌曲业务逻辑类"""

    @staticmethod
    def ensure_analysis_schema():
        """在运行期补齐本需求依赖字段与索引。"""
        conn = get_db()
        if not conn:
            return False

        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW COLUMNS FROM songs LIKE 'melody_key'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE songs ADD COLUMN melody_key VARCHAR(32) DEFAULT NULL COMMENT '旋律分析缓存key' AFTER chord_path")

                cursor.execute("SHOW COLUMNS FROM songs LIKE 'chord_key'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE songs ADD COLUMN chord_key VARCHAR(32) DEFAULT NULL COMMENT '和弦分析缓存key' AFTER melody_key")

                cursor.execute("SHOW COLUMNS FROM song_analysis LIKE 'analysis_key'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE song_analysis ADD COLUMN analysis_key VARCHAR(32) DEFAULT NULL COMMENT '分析记录唯一业务key' AFTER analysis_type")

                cursor.execute("SHOW COLUMNS FROM song_analysis LIKE 'updated_at'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE song_analysis ADD COLUMN updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间' AFTER created_at")

                cursor.execute("SHOW INDEX FROM song_analysis WHERE Key_name = 'uk_analysis_key'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE song_analysis ADD UNIQUE KEY uk_analysis_key (analysis_key)")

                cursor.execute("SHOW INDEX FROM song_analysis WHERE Key_name = 'idx_song_type'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE song_analysis ADD INDEX idx_song_type (song_id, analysis_type)")

                conn.commit()
            return True
        except Exception as e:
            print(f"补齐旋律分析表结构失败: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def add_song(song_data):
        if 'status' not in song_data:
            song_data['status'] = SongStatus.PENDING.value
        elif song_data['status'] not in SongStatus.values():
            song_data['status'] = SongStatus.PENDING.value

        SongsService.ensure_analysis_schema()
        return SongsMapper.insert(song_data)

    @staticmethod
    def create_song_from_dto(dto: AddSongDTO):
        from services.audio_sources_service import AudioSourcesService

        source = AudioSourcesService.get_audio_source(dto.audio_source_id)
        if not source:
            raise BadRequestException('Audio source not found')

        audio_path = source.get('file_path') if isinstance(source, dict) else source[4]
        if not audio_path:
            raise BadRequestException('Audio source file_path is empty')

        song_data = {
            'title': dto.title,
            'artist_id': dto.artist_id,
            'category': dto.category,
            'audio_path': audio_path,
            'source': 'recording',
            'source_id': str(dto.audio_source_id),
            'status': SongStatus.PENDING.value,
        }

        song_id = SongsService.add_song(song_data)
        if not song_id:
            raise RuntimeError('Failed to add song')

        song = SongsService.get_song_by_id(song_id)
        if not song:
            raise RuntimeError('Created song not found')

        return song, audio_path

    @staticmethod
    def get_songs(limit=100, offset=0):
        return SongsMapper.find_all(limit, offset)

    @staticmethod
    def count_songs():
        return SongsMapper.count()

    @staticmethod
    def get_song_by_id(song_id):
        return SongsMapper.find_by_id(song_id)

    @staticmethod
    def get_song_by_session(session_id):
        return SongsMapper.find_by_session_id(session_id)

    @staticmethod
    def update_song(song_id, song_data):
        if 'status' in song_data and song_data['status'] not in SongStatus.values():
            del song_data['status']
        return SongsMapper.update(song_id, song_data)

    @staticmethod
    def update_status(song_id, status):
        if status not in SongStatus.values():
            return False
        return SongsMapper.update(song_id, {'status': status})

    @staticmethod
    def delete_song(song_id):
        song = SongsMapper.find_by_id(song_id)
        if not song:
            return False

        SongAnalysisMapper.delete_by_song_id(song_id)

        for key in ['audio_path', 'melody_path', 'chord_path']:
            try:
                FileService.delete_path(song.get(key))
            except Exception:
                pass

        return SongsMapper.delete(song_id)

    @staticmethod
    def create_song_from_session(session_data, melody_path=None, chord_path=None):
        status = SongStatus.COMPLETED.value if (melody_path or chord_path) else SongStatus.PENDING.value

        song_data = {
            'title': session_data.get('file_name', '未命名').replace('.wav', ''),
            'source': 'wasapi_loopback',
            'source_id': session_data.get('session_id'),
            'audio_path': session_data.get('file_path'),
            'duration': int(session_data.get('duration_sec', 0) * 1000),
            'status': status,
            'session_id': session_data.get('session_id'),
            'melody_path': melody_path,
            'chord_path': chord_path
        }
        SongsService.ensure_analysis_schema()
        return SongsMapper.insert(song_data)

    @staticmethod
    def add_analysis(song_id, analysis_type, result_json, midi_path):
        if analysis_type not in AnalysisType.values():
            raise ValueError(f"Invalid analysis type: {analysis_type}")

        SongsService.ensure_analysis_schema()
        analysis_data = {
            'song_id': song_id,
            'analysis_type': analysis_type,
            'analysis_key': f'{analysis_type}_{song_id}_{uuid.uuid4().hex[:12]}',
            'result_json': result_json,
            'midi_path': midi_path
        }
        return SongAnalysisMapper.insert(analysis_data)

    @staticmethod
    def get_analyses(song_id):
        return SongAnalysisMapper.find_by_song_id(song_id)

    @staticmethod
    def get_melody_analysis(song_id):
        """返回旋律分析所需的原始领域对象。

        仅负责查询与业务判断，不做对外响应的 JSON 结构拼装；
        响应序列化由 VO 层 (pojo.vo.melody_analysis_vo.MelodyAnalysisVO) 完成。

        返回: (song, analysis, error)
            - song: songs 行（dict）或 None
            - analysis: song_analysis 行（dict）或 None
            - error: 'song_not_found' / 'melody_not_found' / None
        """
        SongsService.ensure_analysis_schema()
        song = SongsMapper.find_by_id(song_id)
        if not song:
            return None, None, 'song_not_found'

        analysis = SongAnalysisMapper.find_melody_analysis(song_id)
        if not analysis:
            return song, None, 'melody_not_found'

        return song, analysis, None

    @staticmethod
    def save_melody_analysis(song_id, analysis_payload, midi_path, melody_key):
        SongsService.ensure_analysis_schema()
        analysis_data = {
            'song_id': song_id,
            'analysis_type': AnalysisType.MELODY.value,
            'analysis_key': melody_key,
            'result_json': analysis_payload,
            'midi_path': midi_path,
        }
        saved = SongAnalysisMapper.upsert(analysis_data)
        if not saved:
            return False
        SongsMapper.update_melody_key(song_id, melody_key)
        return True

    @staticmethod
    def search_songs(keyword='', limit=20, offset=0):
        return SongsMapper.search(keyword, limit, offset)
