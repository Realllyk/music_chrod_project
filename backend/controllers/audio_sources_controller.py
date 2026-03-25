"""音源 Controller"""
from flask import Blueprint, jsonify, request
from services.audio_sources_service import AudioSourcesService

audio_sources_controller = Blueprint('audio_sources', __name__, url_prefix='/api/audio-sources')


@audio_sources_controller.route('/list', methods=['GET'])
def list_audio_sources():
    """获取音源列表"""
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    status = request.args.get('status', 'active')
    
    sources, total = AudioSourcesService.list_audio_sources(limit, offset, status)
    
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
    success = AudioSourcesService.delete_audio_source(audio_id)
    if success:
        return jsonify({'ok': True})
    return jsonify({'error': 'Delete failed'}), 400
