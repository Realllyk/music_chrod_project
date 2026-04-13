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
    public_url = f"https://{bucket_name}.{endpoint.replace('http://', '').replace('https://', '')}/{object_name}"
    return public_url
