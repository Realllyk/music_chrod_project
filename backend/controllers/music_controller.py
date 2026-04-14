"""
音乐 Controller
处理音乐文件上传、MIDI 下载等 API 请求
"""

import os
import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file
from utils.aliyun_oss import upload_file, download_file, list_files, get_oss_url
from services.file_service import FileService

music_controller = Blueprint('music', __name__, url_prefix='/api/music')


# ============================================================================
# 音乐文件上传
# ============================================================================

@music_controller.route('/upload', methods=['POST'])
def upload_music():
    """
    POST /api/music/upload
    上传音乐文件到 OSS（支持 multipart/form-data）
    """
    audio_name = request.form.get('audio_name')
    audio_file = request.files.get('audio_file')

    if not audio_name:
        return jsonify({'error': 'audio_name is required'}), 400

    if not audio_file or audio_file.filename == '':
        return jsonify({'error': 'audio_file is required'}), 400

    # 检查文件扩展名
    ext = audio_file.filename.rsplit('.', 1)[-1].lower() if '.' in audio_file.filename else ''
    allowed = {'mp3', 'wav', 'flac', 'ogg', 'm4a', 'wma'}
    if ext not in allowed:
        return jsonify({'error': f'Unsupported format: {ext}. Allowed: {", ".join(allowed)}'}), 400

    try:
        # 上传到 OSS，目录为 music
        oss_url = upload_file(audio_file, directory="music")
        return jsonify({
            'ok': True,
            'audio_name': audio_name,
            'filename': oss_url.split('/')[-1],
            'file_path': oss_url,
            'format': ext
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# MIDI 文件下载
# ============================================================================

@music_controller.route('/download/midi/<filename>', methods=['GET'])
def download_midi(filename):
    """
    GET /api/music/download/midi/<filename>
    从 OSS 下载 MIDI 文件
    """
    # 安全检查：只允许 .mid 和 .midi 扩展名
    if not filename.endswith(('.mid', '.midi')):
        return jsonify({'error': 'Invalid file type'}), 400

    # 防止路径遍历
    filename = os.path.basename(filename)

    try:
        # 统一从当前提取结果目录 transcribe/ 获取；兼容旧 outputs/
        try:
            local_path = download_file(f"transcribe/{filename}")
        except Exception:
            local_path = download_file(f"outputs/{filename}")
        return send_file(
            local_path,
            mimetype='audio/midi',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': f'File not found: {str(e)}'}), 404
