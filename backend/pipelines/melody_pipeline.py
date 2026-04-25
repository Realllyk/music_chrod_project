"""旋律提取编排器。"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from separator import VocalSeparatorBase
from transcriber.base import MelodyTranscriberBase


class MelodyPipeline:
    """把“人声分离”和“旋律提取”串起来的 melody 编排器。"""

    def __init__(self, separator: VocalSeparatorBase, transcriber: MelodyTranscriberBase):
        self.separator = separator
        self.transcriber = transcriber
        self.preserved_vocals_path: Optional[str] = None

    @property
    def name(self) -> str:
        return f'{self.separator.name}+{self.transcriber.name}'

    def extract_melody(self, audio_path: str) -> dict:
        sep_result = self.separator.separate(audio_path, frozenset({'vocals'}))
        try:
            vocals_path = sep_result.stems['vocals']

            # 原有实现里会额外复制一份 vocals，避免临时目录清理后无法上传 OSS。
            # 这个语义现在统一下沉到 Pipeline，避免分离器/提取器重复处理。
            if self.separator.name != 'passthrough':
                self.preserved_vocals_path = self._preserve(vocals_path)

            result = self.transcriber.extract_melody(vocals_path)
            if isinstance(result, dict) and self.preserved_vocals_path:
                result['vocals_path'] = self.preserved_vocals_path
            return result
        finally:
            shutil.rmtree(sep_result.work_dir, ignore_errors=True)

    def save_midi(self, output_path: str = None):
        return self.transcriber.save_midi(output_path)

    def _preserve(self, vocals_path: str) -> str:
        suffix = Path(vocals_path).suffix or '.wav'
        preserved = os.path.join(
            tempfile.gettempdir(),
            f"vocals_{next(tempfile._get_candidate_names())}{suffix}",
        )
        shutil.copy2(vocals_path, preserved)
        return preserved
