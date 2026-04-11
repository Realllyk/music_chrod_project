"""
音乐 Controller
处理音乐文件上传、MIDI 下载等 API 请求
"""

import os
import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file

music_controller = Blueprint('music', __name__, url_prefix='/api/music')


# ============================================================================
# 音乐文件上传
# ============================================================================

@music_controller.route('/upload', methods=['POST'])
def upload_music():
    """
    POST /api/music/upload
    上传音乐文件（支持 multipart/form-data）
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

    # 生成唯一文件名
    filename = f"{uuid.uuid4().hex[:8]}_{audio_name}.{ext}"

    # 保存到 uploads/music 目录
    upload_dir = Path(__file__).parent.parent / 'uploads' / 'music'
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename
    audio_file.save(str(file_path))

    file_size = os.path.getsize(file_path)

    return jsonify({
        'ok': True,
        'audio_name': audio_name,
        'filename': filename,
        'file_path': str(file_path),
        'file_size': file_size,
        'format': ext
    })


# ============================================================================
# MIDI 文件下载
# ============================================================================

@music_controller.route('/download/midi/<filename>', methods=['GET'])
def download_midi(filename):
    """
    GET /api/music/download/midi/<filename>
    下载 MIDI 文件
    """
    # 安全检查：只允许 .mid 和 .midi 扩展名
    if not filename.endswith(('.mid', '.midi')):
        return jsonify({'error': 'Invalid file type'}), 400

    # 防止路径遍历
    filename = os.path.basename(filename)

    # 查找文件：优先 outputs 目录
    output_dir = Path(__file__).parent.parent / 'outputs'
    file_path = output_dir / filename

    if not file_path.exists():
        # 尝试 uploads 目录
        upload_dir = Path(__file__).parent.parent / 'uploads'
        file_path = upload_dir / filename
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404

    return send_file(
        file_path,
        mimetype='audio/midi',
        as_attachment=True,
        download_name=filename
    )
