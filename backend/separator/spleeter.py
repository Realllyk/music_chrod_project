"""Spleeter 分离器实现。"""

from __future__ import annotations

import os
import tempfile
from typing import Dict, FrozenSet

from .base import SeparationResult, VocalSeparatorBase


class SpleeterSeparator(VocalSeparatorBase):
    """基于 spleeter 的 stem 分离器。"""

    SUPPORTED_STEMS = frozenset({'vocals', 'accompaniment', 'drums', 'bass', 'other'})

    @property
    def name(self) -> str:
        return 'spleeter'

    def separate(self, audio_path: str, stems: FrozenSet[str]) -> SeparationResult:
        if not stems or not stems.issubset(self.SUPPORTED_STEMS):
            raise ValueError(f'不支持的 stem 请求: {stems}')

        try:
            from spleeter.separator import Separator
        except ImportError as exc:
            raise RuntimeError('spleeter not installed') from exc

        work_dir = tempfile.mkdtemp(prefix='spleeter_separator_')
        is_two_stems = stems.issubset({'vocals', 'accompaniment'})
        separator = Separator('spleeter:2stems' if is_two_stems else 'spleeter:4stems')
        separator.separate_to_file(audio_path, work_dir)

        basename = os.path.splitext(os.path.basename(audio_path))[0]
        base_path = os.path.join(work_dir, basename)

        lookup = {
            'vocals': 'vocals.wav',
            'accompaniment': 'accompaniment.wav',
            'drums': 'drums.wav',
            'bass': 'bass.wav',
            'other': 'other.wav',
        }
        stem_map: Dict[str, str] = {}
        for stem, filename in lookup.items():
            candidate = os.path.join(base_path, filename)
            if os.path.exists(candidate):
                stem_map[stem] = candidate

        missing = [stem for stem in stems if stem not in stem_map]
        if missing:
            raise RuntimeError(f'Failed to extract stems: {", ".join(missing)}')

        return SeparationResult(stems=stem_map, work_dir=work_dir, provider=self.name)
