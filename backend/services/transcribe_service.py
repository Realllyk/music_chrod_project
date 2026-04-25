"""转录任务 Service。

职责：
1. 启动 melody/chord 转录任务
2. 编排后台线程内的完整处理流程
3. 调用 Pipeline / Mapper / SongsService / OSS 工具链
4. 对 controller 暴露清晰的业务入口
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from pathlib import Path

from mappers.transcribe_tasks_mapper import TranscribeTasksMapper
from pipelines import create_chord_pipeline, create_melody_pipeline
from pojo.vo import BadRequestException, NotFoundException
from services.melody_analysis_service import MelodyAnalysisService
from services.songs_service import SongsService
from utils.aliyun_oss import download_file, upload_file

logger = logging.getLogger(__name__)

ALLOWED_MODES = ('melody', 'chord')


class TranscribeService:
    """转录任务业务逻辑层。"""

    @staticmethod
    def start(song_id: int, mode: str) -> str:
        """创建任务并异步启动后台转录。"""
        if mode not in ALLOWED_MODES:
            raise BadRequestException('mode must be melody or chord')

        song = SongsService.get_song_by_id(song_id)
        if not song:
            raise NotFoundException('Song not found')

        task_id = f'task_{uuid.uuid4().hex[:12]}'
        created = TranscribeTasksMapper.insert(task_id, song_id, mode)
        if not created:
            raise RuntimeError('Failed to create task')

        thread = threading.Thread(
            target=TranscribeService.run_transcription,
            args=(task_id, song_id, mode),
            daemon=True,
        )
        thread.start()
        return task_id

    @staticmethod
    def get_task_status(task_id: str):
        task = TranscribeTasksMapper.find_by_task_id(task_id)
        if not task:
            raise NotFoundException('Task not found')
        return task

    @staticmethod
    def list_tasks_by_song(song_id: int):
        return TranscribeTasksMapper.find_by_song_id(song_id)

    @staticmethod
    def run_transcription(task_id: str, song_id: int, mode: str):
        """后台执行转录任务，全程使用 OSS 与本地临时文件。"""
        full_audio_path = None
        midi_path = None
        vocals_upload_path = None
        local_vocals_path = None

        try:
            logger.info(f'[task_id={task_id}] 提取任务启动, song_id={song_id}, mode={mode}')
            TranscribeTasksMapper.update_status(task_id, 'processing')
            SongsService.update_status(song_id, 'processing')

            song = SongsService.get_song_by_id(song_id)
            if not song:
                TranscribeTasksMapper.update_status(task_id, 'failed', error='Song not found')
                return

            audio_path = song.get('audio_path')
            if not audio_path:
                TranscribeTasksMapper.update_status(task_id, 'failed', error='Audio file not found')
                return

            logger.info(f'[task_id={task_id}] 开始下载原始音频')
            full_audio_path = download_file(audio_path)
            logger.info(f'[task_id={task_id}] 原始音频下载完成: {full_audio_path}')

            if mode == 'melody':
                pipeline = create_melody_pipeline()
                logger.info(f'[task_id={task_id}] 开始旋律提取, pipeline={pipeline.name}')
                result = pipeline.extract_melody(full_audio_path)
            else:
                pipeline = create_chord_pipeline()
                logger.info(f'[task_id={task_id}] 开始和弦提取, pipeline={pipeline.name}')
                result = pipeline.extract_chords(full_audio_path)

            if isinstance(result, dict) and result.get('error'):
                raise RuntimeError(result.get('error'))

            # melody 链路下，人声 stem 仍需保留并上传 OSS。
            if mode == 'melody' and isinstance(result, dict) and result.get('vocals_path'):
                local_vocals_path = result.get('vocals_path')
                vocals_ext = os.path.splitext(local_vocals_path)[1] or '.wav'
                vocals_object_name = f'transcribe/vocals/{song_id}_{task_id}{vocals_ext}'
                logger.info(f'[task_id={task_id}] 开始上传人声文件到 OSS: {vocals_object_name}')
                vocals_upload_path = upload_file(local_vocals_path, directory='', object_name=vocals_object_name)
                logger.info(f'[task_id={task_id}] 人声文件已上传: {vocals_upload_path}')

            midi_path, result_path = TranscribeService._save_and_upload_midi(pipeline, song_id, mode, task_id)

            update_data = {'status': 'completed'}
            update_data['melody_path' if mode == 'melody' else 'chord_path'] = result_path
            SongsService.update_song(song_id, update_data)

            if mode == 'melody':
                logger.info(f'[task_id={task_id}] 开始构建旋律分析缓存')
                analysis_payload = MelodyAnalysisService.build_melody_analysis(midi_path)
                melody_key = f'melody_{song_id}_{task_id[-8:]}'
                saved = SongsService.save_melody_analysis(
                    song_id=song_id,
                    analysis_payload=analysis_payload,
                    midi_path=result_path,
                    melody_key=melody_key,
                )
                if not saved:
                    raise RuntimeError('Failed to save melody analysis cache')
                logger.info(f'[task_id={task_id}] 旋律分析缓存已写入, melody_key={melody_key}')

            TranscribeTasksMapper.update_status(task_id, 'completed', result_path=result_path)
            if vocals_upload_path:
                logger.info(f'[task_id={task_id}] 人声文件保留地址: {vocals_upload_path}')
            logger.info(f'[task_id={task_id}] 提取任务完成: {result_path}')

        except Exception as exc:
            logger.exception(f'[task_id={task_id}] 提取失败: {exc}')
            SongsService.update_status(song_id, 'failed')
            TranscribeTasksMapper.update_status(task_id, 'failed', error=str(exc))
        finally:
            for path in (full_audio_path, midi_path, local_vocals_path):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

    @staticmethod
    def _save_and_upload_midi(pipeline, song_id: int, mode: str, task_id: str):
        """保存本地 MIDI，再上传到 OSS。"""
        base_dir = Path(__file__).resolve().parents[1]
        output_dir = base_dir / 'outputs' / 'transcribe'
        output_dir.mkdir(parents=True, exist_ok=True)

        midi_filename = f'{song_id}_{mode}_{task_id}.mid'
        midi_path = str(output_dir / midi_filename)

        logger.info(f'[task_id={task_id}] 开始生成 MIDI: {midi_path}')
        pipeline.save_midi(midi_path)
        if not os.path.exists(midi_path):
            raise RuntimeError('MIDI file was not generated')

        oss_object_name = f'transcribe/{midi_filename}'
        logger.info(f'[task_id={task_id}] 开始上传 MIDI 到 OSS: {oss_object_name}')
        result_path = upload_file(midi_path, directory='', object_name=oss_object_name)
        return midi_path, result_path
