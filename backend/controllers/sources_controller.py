"""
音乐源 Controller
处理音乐源切换、搜索等 API 请求
"""

import json
from pathlib import Path
from flask import Blueprint, request, jsonify

# 加载配置
_config_path = Path(__file__).parent.parent / 'config.json'
with open(_config_path) as f:
    _config = json.load(f)

sources_controller = Blueprint('sources', __name__, url_prefix='/api/sources')


# ============================================================================
# 音乐源管理 API
# ============================================================================

@sources_controller.route('', methods=['GET'])
def list_sources():
    """
    GET /api/sources
    获取可用的音乐源列表（local_file / spotify）
    """
    from sources import SourceFactory

    available = SourceFactory.get_available_sources()

    # 尝试获取当前源
    try:
        current = SourceFactory.get_current()
        current_name = current.__class__.__name__.replace('Source', '').lower()
    except RuntimeError:
        current_name = None

    sources = []
    for name in available:
        sources.append({
            'name': name,
            'label': _get_source_label(name),
            'is_current': (name == current_name)
        })

    return jsonify({
        'sources': sources,
        'current': current_name,
        'total': len(sources)
    })


@sources_controller.route('/switch', methods=['PUT'])
def switch_source():
    """
    PUT /api/sources/switch
    切换当前音乐源
    """
    from sources import SourceFactory

    data = request.get_json() or {}
    source_name = data.get('source')

    if not source_name:
        return jsonify({'error': 'source is required'}), 400

    # 检查源是否可用
    available = SourceFactory.get_available_sources()
    if source_name not in available:
        return jsonify({
            'error': f'Unknown source: {source_name}',
            'available': available
        }), 400

    try:
        # 构建配置（如果有）
        config = data.get('config', {})

        # 如果切换到 spotify 且没有传入 config，尝试从配置文件读取
        if source_name == 'spotify' and not config:
            spotify_config = _config.get('spotify', {})
            config = {
                'client_id': spotify_config.get('client_id', ''),
                'client_secret': spotify_config.get('client_secret', '')
            }

        source = SourceFactory.set_current(source_name, config)

        # 尝试认证
        auth_ok = source.authenticate()

        return jsonify({
            'ok': True,
            'source': source_name,
            'authenticated': auth_ok,
            'message': f'已切换到音乐源: {source_name}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# 搜索 API
# ============================================================================

@sources_controller.route('/search', methods=['GET'])
def search_music():
    """
    GET /api/sources/search
    搜索音乐（使用当前激活的音乐提供方）
    """
    from sources import SourceFactory

    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 20))

    if not query:
        return jsonify({'error': 'q (query) is required'}), 400

    try:
        source = SourceFactory.get_current()
    except RuntimeError:
        return jsonify({'error': 'No active music source. Please switch to a source first.'}), 400

    if not source.is_authenticated:
        return jsonify({'error': f'Source {source.__class__.__name__} not authenticated'}), 401

    try:
        results = source.search(query, limit=limit)
        return jsonify({
            'query': query,
            'results': results,
            'total': len(results),
            'source': source.__class__.__name__.replace('Source', '').lower()
        })
    except Exception as e:
        return jsonify({'error': f'Search failed: {e}'}), 500


def _get_source_label(name: str) -> str:
    """获取音乐源显示名称"""
    labels = {
        'spotify': 'Spotify',
        'local_file': '本地文件',
        'wav_file': 'WAV 文件',
    }
    return labels.get(name, name)
