"""统一文件解析/删除服务"""

from pathlib import Path
from urllib.parse import urlparse

from utils.aliyun_oss import extract_object_name, delete_file as delete_oss_file, download_file, get_oss_url


class FileService:
    @staticmethod
    def is_remote_path(path_or_url):
        value = str(path_or_url or '')
        return value.startswith('http://') or value.startswith('https://')

    @staticmethod
    def resolve_public_url(path_or_url):
        if not path_or_url:
            return None
        if FileService.is_remote_path(path_or_url):
            return path_or_url
        return get_oss_url(extract_object_name(path_or_url))

    @staticmethod
    def fetch_local_file(path_or_url):
        if not path_or_url:
            return None

        if FileService.is_remote_path(path_or_url):
            return download_file(extract_object_name(path_or_url))

        candidate = Path(path_or_url)
        if candidate.exists():
            return str(candidate)

        object_name = extract_object_name(path_or_url)
        if object_name:
            return download_file(object_name)
        return None

    @staticmethod
    def delete_path(path_or_url):
        if not path_or_url:
            return False

        if FileService.is_remote_path(path_or_url):
            return delete_oss_file(path_or_url)

        candidate = Path(path_or_url)
        if candidate.exists() and candidate.is_file():
            candidate.unlink()
            return True

        object_name = extract_object_name(path_or_url)
        if object_name and '/' in object_name:
            return delete_oss_file(object_name)
        return False
