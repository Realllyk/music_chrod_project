"""直通分离器。

当真实分离器不可用，或者配置明确要求“不做人声分离”时，
用这个实现把原始混音直接挂到请求的 stem 键上，保持下游接口一致。
"""

from __future__ import annotations

import tempfile
from typing import FrozenSet

from .base import SeparationResult, VocalSeparatorBase


class PassthroughSeparator(VocalSeparatorBase):
    """不做实际分离，直接透传原始音频路径。"""

    @property
    def name(self) -> str:
        return 'passthrough'

    def separate(self, audio_path: str, stems: FrozenSet[str]) -> SeparationResult:
        # 这里仍然创建一个空工作目录，
        # 这样 Pipeline 可以统一执行 shutil.rmtree，而不需要特判 provider。
        work_dir = tempfile.mkdtemp(prefix='passthrough_')
        stems_dict = {stem: audio_path for stem in stems}
        return SeparationResult(stems=stems_dict, work_dir=work_dir, provider=self.name)
