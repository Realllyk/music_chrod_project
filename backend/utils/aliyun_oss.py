"""
阿里云 OSS 上传工具类
"""

import json
import uuid
import os
from pathlib import Path

try:
    import oss2
    HAS_OSS2 = True
except ImportError:
    HAS_OSS2 = False


def _load_config():
    """从 config.json 加载 OSS 配置"""
    config_path = Path(__file__).parent.parent / 'config.json'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config.get('aliyunoss', {})


def get_oss_url(object_name):
    """
    生成 OSS 公网 URL

    Args:
        object_name: OSS 对象名称（如 'avatars/xxx.jpg', 'audio-sources/yyy.mp3'）

    Returns:
        str: OSS 公网 URL
    """
    config = _load_config()
    endpoint = config.get('endpoint')
    bucket_name = config.get('bucket')

    if not endpoint or endpoint == 'your-endpoint':
        raise ValueError("OSS endpoint 未配置，请检查 config.json")
    if not bucket_name or bucket_name == 'your-bucket-name':
        raise ValueError("OSS bucket 未配置，请检查 config.json")

    clean_endpoint = endpoint.replace('http://', '').replace('https://', '')
    return f"https://{bucket_name}.{clean_endpoint}/{object_name.lstrip('/')}"


def upload_file(file_obj, directory="avatars", object_name=None):
    """
    上传文件到阿里云 OSS

    Args:
        file_obj: 文件对象（FileStorage 或文件路径）
        directory: OSS 存储目录，如 "avatars/", "songs/", "audio-sources/" 等
        object_name: OSS 存储路径（完整路径），优先级高于 directory

    Returns:
        str: OSS 公网访问 URL
    """
    if not HAS_OSS2:
        raise RuntimeError("oss2 库未安装，请运行: pip install oss2")

    config = _load_config()
    endpoint = config.get('endpoint')
    bucket_name = config.get('bucket')

    # 从环境变量读取 AccessKey
    import os
    access_key_id = os.environ.get('OSS_ACCESS_KEY_ID')
    access_key_secret = os.environ.get('OSS_ACCESS_KEY_SECRET')

    # 验证配置
    if not endpoint or endpoint == 'your-endpoint':
        raise ValueError(f"OSS endpoint 未配置，请检查 config.json")
    if not bucket_name or bucket_name == 'your-bucket-name':
        raise ValueError(f"OSS bucket 未配置，请检查 config.json")
    if not access_key_id:
        raise ValueError("请设置环境变量 OSS_ACCESS_KEY_ID")
    if not access_key_secret:
        raise ValueError("请设置环境变量 OSS_ACCESS_KEY_SECRET")

    # 自动生成 object_name
    if not object_name:
        if hasattr(file_obj, 'filename'):
            ext = Path(file_obj.filename).suffix.lower()
        else:
            ext = os.path.splitext(getattr(file_obj, 'name', ''))[-1].lower()
        # 确保 directory 末尾有 /
        directory = directory.rstrip('/') + '/'
        object_name = f"{directory}{uuid.uuid4().hex}{ext}"

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # 支持 FileStorage 或本地文件路径
    if hasattr(file_obj, 'read'):
        content = file_obj.read()
        bucket.put_object(object_name, content)
    else:
        bucket.put_object_from_file(object_name, file_obj)

    # 返回公网 URL
    return get_oss_url(object_name)


def _get_bucket():
    """获取 OSS Bucket 实例（内部复用）"""
    if not HAS_OSS2:
        raise RuntimeError("oss2 库未安装，请运行: pip install oss2")

    config = _load_config()
    endpoint = config.get('endpoint')
    bucket_name = config.get('bucket')

    import os
    access_key_id = os.environ.get('OSS_ACCESS_KEY_ID')
    access_key_secret = os.environ.get('OSS_ACCESS_KEY_SECRET')

    if not endpoint or endpoint == 'your-endpoint':
        raise ValueError(f"OSS endpoint 未配置，请检查 config.json")
    if not bucket_name or bucket_name == 'your-bucket-name':
        raise ValueError(f"OSS bucket 未配置，请检查 config.json")
    if not access_key_id:
        raise ValueError("请设置环境变量 OSS_ACCESS_KEY_ID")
    if not access_key_secret:
        raise ValueError("请设置环境变量 OSS_ACCESS_KEY_SECRET")

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)
    return bucket, bucket_name, endpoint


def download_file(object_name):
    """
    从 OSS 下载文件到本地临时目录

    Args:
        object_name: OSS 存储路径（相对路径），如 "audio-sources/song.mp3"

    Returns:
        str: 本地文件路径
    """
    bucket, bucket_name, endpoint = _get_bucket()

    # 下载到 uploads/oss_cache/ 下
    base_dir = Path(__file__).parent.parent
    cache_dir = base_dir / 'uploads' / 'oss_cache'
    cache_dir.mkdir(parents=True, exist_ok=True)

    local_filename = os.path.basename(object_name)
    local_path = cache_dir / local_filename

    bucket.get_object_to_file(object_name, str(local_path))
    return str(local_path)


def file_exists(object_name):
    """
    检查 OSS 文件是否存在

    Args:
        object_name: OSS 存储路径（相对路径）

    Returns:
        bool: 文件是否存在
    """
    bucket, _, _ = _get_bucket()
    return bucket.object_exists(object_name)


def list_files(directory):
    """
    列出 OSS 目录下的文件

    Args:
        directory: OSS 存储目录，如 "audio-sources/"

    Returns:
        list: 文件信息列表，每个元素为 dict，包含 key, size, last_modified
    """
    if not HAS_OSS2:
        raise RuntimeError("oss2 库未安装，请运行: pip install oss2")

    config = _load_config()
    endpoint = config.get('endpoint')
    bucket_name = config.get('bucket')

    import os
    access_key_id = os.environ.get('OSS_ACCESS_KEY_ID')
    access_key_secret = os.environ.get('OSS_ACCESS_KEY_SECRET')

    if not endpoint or endpoint == 'your-endpoint':
        raise ValueError(f"OSS endpoint 未配置，请检查 config.json")
    if not bucket_name or bucket_name == 'your-bucket-name':
        raise ValueError(f"OSS bucket 未配置，请检查 config.json")
    if not access_key_id:
        raise ValueError("请设置环境变量 OSS_ACCESS_KEY_ID")
    if not access_key_secret:
        raise ValueError("请设置环境变量 OSS_ACCESS_KEY_SECRET")

    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # 确保 directory 末尾有 /
    directory = directory.rstrip('/') + '/'

    files = []
    for obj in oss2.ObjectIterator(bucket, prefix=directory):
        if obj.key != directory:
            files.append({
                'key': obj.key,
                'name': obj.key.split('/')[-1],
                'size': obj.size,
                'last_modified': obj.last_modified,
                'url': get_oss_url(obj.key)
            })

    return files
