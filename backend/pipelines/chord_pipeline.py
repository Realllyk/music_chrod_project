"""和弦提取编排器。"""

from __future__ import annotations

import os
import shutil
import tempfile

import librosa
import numpy as np
import soundfile as sf

from separator import SeparationResult, VocalSeparatorBase
from transcriber.base import ChordTranscriberBase


class ChordPipeline:
    """把“音轨分离 → 伴奏合成 → 和弦提取”串起来的 chord 编排器。"""

    ACCOMPANIMENT_STEMS = ('bass', 'other', 'drums')

    def __init__(self, separator: VocalSeparatorBase, transcriber: ChordTranscriberBase, sr: int = 22050):
        self.separator = separator
        self.transcriber = transcriber
        self.sample_rate = sr

    @property
    def name(self) -> str:
        return f'{self.separator.name}+{self.transcriber.name}'

    def extract_chords(self, audio_path: str) -> dict:
        # 直通模式下，不再强求 4-stems，直接让现有 librosa 和弦提取器吃整轨混音。
        if self.separator.name == 'passthrough':
            return self.transcriber.extract_chords(audio_path)

        sep_result = self.separator.separate(audio_path, frozenset({'vocals', 'drums', 'bass', 'other'}))
        try:
            accompaniment_path = self._mix_accompaniment(sep_result)
            return self.transcriber.extract_chords(accompaniment_path)
        finally:
            shutil.rmtree(sep_result.work_dir, ignore_errors=True)

    def save_midi(self, output_path: str = None):
        return self.transcriber.save_midi(output_path)

    def _mix_accompaniment(self, sep_result: SeparationResult) -> str:
        """把 bass / other / drums 混合成一路伴奏。

        这里沿用旧 demucs/spleeter chord 实现的思路：
        - 各 stem 统一重采样加载
        - 按最短长度截断
        - 逐轨相加
        - 输出到当前 work_dir 下，供后续 chord transcriber 读取
        """
        mixed_tracks = []
        for stem in self.ACCOMPANIMENT_STEMS:
            path = sep_result.stems.get(stem)
            if not path or not os.path.exists(path):
                continue
            y, _ = librosa.load(path, sr=self.sample_rate)
            mixed_tracks.append(y)

        if not mixed_tracks:
            raise RuntimeError('No accompaniment tracks found')

        min_len = min(len(track) for track in mixed_tracks)
        accompaniment = np.zeros(min_len, dtype=np.float32)
        for track in mixed_tracks:
            accompaniment += track[:min_len]

        output_path = os.path.join(sep_result.work_dir, 'accompaniment_mix.wav')
        sf.write(output_path, accompaniment, self.sample_rate)
        return output_path
