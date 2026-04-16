"""
提取 Controller
处理单旋律提取和多声部分离任务
全程使用 OSS：下载音频 → 处理 → 上传结果
"""

import json
import uuid
import os
import threading
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify
from services.songs_service import SongsService
from database import get_db
from utils.aliyun_oss import download_file, upload_file

# 加载配置
_config_path = Path(__file__).parent.parent / 'config.json'
with open(_config_path) as f:
    _config = json.load(f)

ALGORITHM_CONFIG = _config.get('transcription', {}).get('algorithm', {})
VOCAL_SEPARATION_CONFIG = _config.get('transcription', {}).get('vocal_separation', {})
DEFAULT_CHORD_ALGO = ALGORITHM_CONFIG.get('chord', 'librosa')
DEFAULT_VOCAL_PROVIDER = VOCAL_SEPARATION_CONFIG.get('provider', 'demucs')
VOCAL_FALLBACK_ORDER = VOCAL_SEPARATION_CONFIG.get('fallback_order', ['spleeter', 'librosa'])
ALLOWED_ALGOS = {'librosa', 'spleeter', 'demucs'}

logger = logging.getLogger(__name__)

# 创建 Blueprint
transcribe_controller = Blueprint('transcribe', __name__, url_prefix='/api/transcribe')


# ============================================================================
# 任务管理
# ============================================================================

def create_task(song_id, mode):
    """创建任务并返回 task_id"""
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    
    conn = get_db()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO transcribe_tasks (task_id, song_id, mode, status) VALUES (%s, %s, %s, %s)",
                (task_id, song_id, mode, 'pending')
            )
            conn.commit()
        return task_id
    except Exception as e:
        print(f"创建任务失败: {e}")
        return None


def update_task(task_id, status, result_path=None, error=None):
    """更新任务状态"""
    conn = get_db()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cursor:
            if result_path:
                cursor.execute(
                    "UPDATE transcribe_tasks SET status=%s, result_path=%s WHERE task_id=%s",
                    (status, result_path, task_id)
                )
            elif error:
                cursor.execute(
                    "UPDATE transcribe_tasks SET status=%s, error=%s WHERE task_id=%s",
                    (status, error, task_id)
                )
            else:
                cursor.execute(
                    "UPDATE transcribe_tasks SET status=%s WHERE task_id=%s",
                    (status, task_id)
                )
            conn.commit()
        return True
    except Exception as e:
        print(f"更新任务失败: {e}")
        return False


def get_task(task_id):
    """获取任务信息"""
    conn = get_db()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM transcribe_tasks WHERE task_id=%s", (task_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"获取任务失败: {e}")
        return None


# ============================================================================
# 后台处理线程
# ============================================================================

def _serialize_task(task):
    if not task:
        return None
    payload = {
        'task_id': task.get('task_id'),
        'song_id': task.get('song_id'),
        'mode': task.get('mode'),
        'status': task.get('status'),
        'result_path': task.get('result_path'),
        'error': task.get('error'),
        'created_at': task.get('created_at').isoformat() if task.get('created_at') else None,
        'updated_at': task.get('updated_at').isoformat() if task.get('updated_at') else None,
    }
    if task.get('vocal_stem_path'):
        payload['vocal_stem_path'] = task.get('vocal_stem_path')
    return payload


def _create_melody_transcriber():
    """创建旋律提取器。优先使用人声分离方案，失败时逐级降级。"""
    provider_order = [DEFAULT_VOCAL_PROVIDER] + [item for item in VOCAL_FALLBACK_ORDER if item != DEFAULT_VOCAL_PROVIDER]
    last_error = None

    for provider in provider_order:
        if provider not in ALLOWED_ALGOS:
            continue

        try:
            if provider == 'demucs':
                from transcriber.demucs.melody import DemucsMelodyTranscriber
                logger.info("旋律提取使用 demucs 人声分离 + pitch 提取")
                return DemucsMelodyTranscriber()
            if provider == 'spleeter':
                from transcriber.spleeter.melody import SpleeterMelodyTranscriber
                logger.info("旋律提取使用 spleeter 人声分离 + pitch 提取")
                return SpleeterMelodyTranscriber()
            if provider == 'librosa':
                from transcriber.librosa.melody import LibrosaMelodyTranscriber
                logger.warning("旋律提取回退到 librosa 直接处理整首混音")
                return LibrosaMelodyTranscriber()
        except Exception as e:
            last_error = e
            logger.warning(f"初始化旋律提取器失败，provider={provider}, error={e}")

    raise RuntimeError(f"No available melody transcriber provider: {last_error}")


def _create_chord_transcriber(algo):
    if algo == 'librosa':
        from transcriber.librosa.chord import LibrosaChordTranscriber
        return LibrosaChordTranscriber()
    if algo == 'spleeter':
        from transcriber.spleeter.chord import SpleeterChordTranscriber
        return SpleeterChordTranscriber()
    if algo == 'demucs':
        from transcriber.demucs.chord import DemucsChordTranscriber
        return DemucsChordTranscriber()
    raise ValueError(f'Unsupported transcription algorithm: {algo}')


def run_transcription(task_id, song_id, mode):
    """后台执行提取任务，全程使用 OSS"""
    full_audio_path = None
    midi_path = None
    vocals_upload_path = None
    local_vocals_path = None

    try:
        logger.info(f"[task_id={task_id}] 提取任务启动, song_id={song_id}, mode={mode}")

        # 更新状态为处理中
        update_task(task_id, 'processing')
        SongsService.update_status(song_id, 'processing')

        # 获取歌曲信息
        song = SongsService.get_song_by_id(song_id)
        if not song:
            update_task(task_id, 'failed', error='Song not found')
            return

        audio_path = song.get('audio_path')
        if not audio_path:
            update_task(task_id, 'failed', error='Audio file not found')
            return

        logger.info(f"[task_id={task_id}] 开始下载原始音频")
        full_audio_path = download_file(audio_path)
        logger.info(f"[task_id={task_id}] 原始音频下载完成: {full_audio_path}")

        # 根据配置选择实现类
        if mode == 'melody':
            transcriber = _create_melody_transcriber()
            logger.info(f"[task_id={task_id}] 开始旋律提取")
            result = transcriber.extract_melody(full_audio_path)
        else:
            algo = DEFAULT_CHORD_ALGO
            if algo not in ALLOWED_ALGOS:
                raise ValueError(f'Unsupported transcription algorithm: {algo}')
            transcriber = _create_chord_transcriber(algo)
            logger.info(f"[task_id={task_id}] 开始和弦提取")
            result = transcriber.extract_chords(full_audio_path)

        if isinstance(result, dict) and result.get('error'):
            raise RuntimeError(result.get('error'))

        if mode == 'melody' and isinstance(result, dict) and result.get('vocals_path'):
            local_vocals_path = result.get('vocals_path')
            vocals_ext = os.path.splitext(local_vocals_path)[1] or '.wav'
            vocals_object_name = f"transcribe/vocals/{song_id}_{task_id}{vocals_ext}"
            logger.info(f"[task_id={task_id}] 开始上传人声文件到 OSS: {vocals_object_name}")
            vocals_upload_path = upload_file(local_vocals_path, directory="", object_name=vocals_object_name)
            logger.info(f"[task_id={task_id}] 人声文件已上传: {vocals_upload_path}")

        # 保存 MIDI 到本地临时目录
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, 'outputs', 'transcribe')
        os.makedirs(output_dir, exist_ok=True)

        midi_filename = f"{song_id}_{mode}_{task_id}.mid"
        midi_path = os.path.join(output_dir, midi_filename)

        logger.info(f"[task_id={task_id}] 开始生成 MIDI: {midi_path}")
        transcriber.save_midi(midi_path)
        if not os.path.exists(midi_path):
            raise RuntimeError('MIDI file was not generated')

        # 上传 MIDI 到 OSS
        oss_object_name = f"transcribe/{midi_filename}"
        logger.info(f"[task_id={task_id}] 开始上传 MIDI 到 OSS: {oss_object_name}")
        result_path = upload_file(midi_path, directory="", object_name=oss_object_name)

        # 更新歌曲
        update_data = {}
        if mode == 'melody':
            update_data['melody_path'] = result_path
        else:
            update_data['chord_path'] = result_path

        update_data['status'] = 'completed'
        SongsService.update_song(song_id, update_data)

        # 更新任务状态
        update_task(task_id, 'completed', result_path=result_path)
        if vocals_upload_path:
            logger.info(f"[task_id={task_id}] 人声文件保留地址: {vocals_upload_path}")
        logger.info(f"[task_id={task_id}] 提取任务完成: {result_path}")

    except Exception as e:
        logger.exception(f"[task_id={task_id}] 提取失败: {e}")
        SongsService.update_status(song_id, 'failed')
        update_task(task_id, 'failed', error=str(e))
    finally:
        # 清理临时下载的 OSS 文件和本地 MIDI
        if full_audio_path and os.path.exists(full_audio_path):
            try:
                os.remove(full_audio_path)
            except Exception:
                pass
        if midi_path and os.path.exists(midi_path):
            try:
                os.remove(midi_path)
            except Exception:
                pass
        if local_vocals_path and os.path.exists(local_vocals_path):
            try:
                os.remove(local_vocals_path)
            except Exception:
                pass


# ============================================================================
# API 接口
# ============================================================================

@transcribe_controller.route('/start', methods=['POST'])
def start_transcribe():
    """启动提取任务"""
    data = request.get_json() or {}
    song_id = data.get('song_id')
    mode = data.get('mode', 'melody')
    
    if not song_id:
        return jsonify({'error': 'song_id is required'}), 400
    
    if mode not in ['melody', 'chord']:
        return jsonify({'error': 'mode must be melody or chord'}), 400
    
    # 创建任务
    task_id = create_task(song_id, mode)
    if not task_id:
        return jsonify({'error': 'Failed to create task'}), 500
    
    # 启动后台线程处理
    thread = threading.Thread(target=run_transcription, args=(task_id, song_id, mode))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'ok': True,
        'task_id': task_id,
        'message': 'Task submitted'
    })


@transcribe_controller.route('/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取任务状态"""
    task = get_task(task_id)
    
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify(_serialize_task(task))


@transcribe_controller.route('/song/<song_id>', methods=['GET'])
def get_song_tasks(song_id):
    """获取歌曲的所有任务"""
    conn = get_db()
    if not conn:
        return jsonify({'tasks': []})
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM transcribe_tasks WHERE song_id=%s ORDER BY created_at DESC",
                (song_id,)
            )
            tasks = cursor.fetchall()
        return jsonify({'tasks': [_serialize_task(task) for task in tasks]})
    except Exception as e:
        return jsonify({'tasks': [], 'error': str(e)})
