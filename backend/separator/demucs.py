"""Demucs 分离器实现。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, FrozenSet
import tempfile

from .base import SeparationResult, VocalSeparatorBase


class DemucsSeparator(VocalSeparatorBase):
    """基于 demucs 的 stem 分离器。"""

    SUPPORTED_STEMS = frozenset({'vocals', 'accompaniment', 'drums', 'bass', 'other'})

    def __init__(self):
        self.config = self._load_demucs_config()

    @property
    def name(self) -> str:
        return 'demucs'

    def _load_demucs_config(self) -> Dict:
        config_path = Path(__file__).resolve().parents[1] / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('transcription', {}).get('vocal_separation', {}).get('demucs', {})

    def separate(self, audio_path: str, stems: FrozenSet[str]) -> SeparationResult:
        if not stems or not stems.issubset(self.SUPPORTED_STEMS):
            raise ValueError(f'不支持的 stem 请求: {stems}')

        try:
            import demucs.separate as demucs_separate
        except ImportError as exc:
            raise RuntimeError('demucs not installed') from exc

        model_name = self.config.get('model_name', 'htdemucs')
        output_format = self.config.get('output_format', 'wav')
        work_dir = tempfile.mkdtemp(prefix='demucs_separator_')

        # melody 侧只请求 vocals/accompaniment，优先用 2-stems，速度更快。
        is_two_stems = stems.issubset({'vocals', 'accompaniment'})

        demucs_args = ['--out', work_dir, '-n', model_name]
        if is_two_stems:
            demucs_args.extend(['--two-stems', self.config.get('two_stems', 'vocals')])

        device = self.config.get('device')
        jobs = self.config.get('jobs')
        segment = self.config.get('segment')
        shifts = self.config.get('shifts')
        overlap = self.config.get('overlap')

        if device:
            demucs_args.extend(['-d', str(device)])
        if isinstance(jobs, int) and jobs >= 0:
            demucs_args.extend(['-j', str(jobs)])
        if segment is not None:
            demucs_args.extend(['--segment', str(segment)])
        if shifts is not None:
            demucs_args.extend(['--shifts', str(shifts)])
        if overlap is not None:
            demucs_args.extend(['--overlap', str(overlap)])

        if output_format == 'mp3':
            demucs_args.append('--mp3')
        elif output_format == 'flac':
            demucs_args.append('--flac')

        demucs_args.append(audio_path)
        demucs_separate.main(demucs_args)

        basename = os.path.splitext(os.path.basename(audio_path))[0]
        base_path = os.path.join(work_dir, model_name, basename)

        suffixes = ['wav', 'mp3', 'flac']
        stem_map: Dict[str, str] = {}

        # 这里保留原有 demucs 目录扫描语义，避免因为路径猜测错误影响回归。
        lookup = {
            'vocals': 'vocals',
            'accompaniment': 'no_vocals',
            'drums': 'drums',
            'bass': 'bass',
            'other': 'other',
        }
        for stem in lookup:
            filename = lookup[stem]
            for suffix in suffixes:
                candidate = os.path.join(base_path, f'{filename}.{suffix}')
                if os.path.exists(candidate):
                    stem_map[stem] = candidate
                    break

        missing = [stem for stem in stems if stem not in stem_map]
        if missing:
            raise RuntimeError(f'Failed to extract stems: {", ".join(missing)}')

        return SeparationResult(stems=stem_map, work_dir=work_dir, provider=self.name)
