"""separator 包导出。"""

from .base import SeparationResult, VocalSeparatorBase
from .demucs import DemucsSeparator
from .passthrough import PassthroughSeparator
from .spleeter import SpleeterSeparator


def create_separator(provider: str) -> VocalSeparatorBase:
    """按 provider 创建分离器实例。

    这里不做复杂降级，只做名称到实现类的映射；
    降级顺序由 pipelines 层统一控制。
    """
    normalized = (provider or '').strip().lower()
    if normalized == 'demucs':
        return DemucsSeparator()
    if normalized == 'spleeter':
        return SpleeterSeparator()
    if normalized in {'passthrough', 'none', 'librosa'}:
        # 历史配置里 librosa 代表“不做人声分离，直接处理原混音”，
        # 这里把它兼容映射到 passthrough。
        return PassthroughSeparator()
    raise ValueError(f'未知分离器 provider: {provider}')


__all__ = [
    'SeparationResult',
    'VocalSeparatorBase',
    'DemucsSeparator',
    'SpleeterSeparator',
    'PassthroughSeparator',
    'create_separator',
]
