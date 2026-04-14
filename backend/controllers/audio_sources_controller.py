"""音源 Controller"""
from flask import Blueprint, jsonify, request
from services.audio_sources_service import AudioSourcesService
from utils.aliyun_oss import upload_file, list_files

audio_sources_controller = Blueprint('audio_sources', __name__, url_prefix='/api/audio-sources')


@audio_sources_controller.route('/list', methods=['GET'])
def list_audio_sources():
    """获取音源列表（不按状态过滤）"""
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))

    sources, total = AudioSourcesService.list_audio_sources(limit, offset)
    
    # 转换为字典列表
    result = []
    for s in sources:
        if isinstance(s, dict):
            result.append(s)
        else:
            # 元组情况
            result.append({
                'id': s[0],
                'source_type': s[1],
                'source_id': s[2],
                'audio_name': s[3],
                'file_path': s[4],
                'file_size': s[5],
                'duration_sec': s[6],
                'sample_rate': s[7],
                'channels': s[8],
                'format': s[9],
                'status': s[11],
                'created_at': str(s[13]) if s[13] else None
            })
    
    return jsonify({
        'sources': result,
        'total': total
    })


@audio_sources_controller.route('/oss-files', methods=['GET'])
def list_oss_audio_files():
    """从 OSS audio-sources/ 目录列出文件，返回公网 URL"""
    try:
        files = list_files("audio-sources/")
        return jsonify({
            'files': files,
            'total': len(files)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@audio_sources_controller.route('/<int:audio_id>', methods=['GET'])
def get_audio_source(audio_id):
    """获取音源详情"""
    source = AudioSourcesService.get_audio_source(audio_id)
    if not source:
        return jsonify({'error': 'Audio source not found'}), 404
    
    if isinstance(source, dict):
        return jsonify(source)
    
    return jsonify({
        'id': source[0],
        'source_type': source[1],
        'source_id': source[2],
        'audio_name': source[3],
        'file_path': source[4],
        'file_size': source[5],
        'duration_sec': source[6],
        'sample_rate': source[7],
        'channels': source[8],
        'format': source[9],
        'status': source[11],
        'created_at': str(source[13]) if source[13] else None
    })


@audio_sources_controller.route('/<int:audio_id>', methods=['DELETE'])
def delete_audio_source(audio_id):
    """删除音源"""
    success, error = AudioSourcesService.delete_audio_source(audio_id)
    if success:
        return jsonify({'ok': True})
    return jsonify({'error': error or 'Delete failed'}), 400



@audio_sources_controller.route('/upload', methods=['POST'])
def upload_audio_source():
    """上传音频文件"""
    audio_name = request.form.get('audio_name')
    audio_file = request.files.get('audio_file')
    
    if not audio_name:
        return jsonify({'error': '请输入音源名称'}), 400
    
    if not audio_file or audio_file.filename == '':
        return jsonify({'error': '请选择音频文件'}), 400
    
    # 上传到阿里云 OSS
    file_url = upload_file(audio_file, "audio-sources")
    
    # 获取文件大小
    import os
    file_size = audio_file.content_length if hasattr(audio_file, 'content_length') and audio_file.content_length else 0
    
    # 获取文件扩展名
    ext = audio_file.filename.rsplit('.', 1)[-1].lower() if '.' in audio_file.filename else 'wav'

    # 创建音源记录
    source_data = {
        'source_type': 'upload',
        'audio_name': audio_name,
        'file_path': file_url,
        'file_size': file_size,
        'format': ext,
        'status': 'active'
    }
    
    source_id = AudioSourcesService.create_audio_source(source_data)
    
    return jsonify({
        'ok': True,
        'audio_source_id': source_id,
        'audio_name': audio_name,
        'file_path': file_url
    })
