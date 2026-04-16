"""
基于 demucs 的单旋律提取
使用 demucs 分离人声，然后复用 librosa 提取旋律
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

from transcriber.base import MelodyTranscriberBase


class DemucsMelodyTranscriber(MelodyTranscriberBase):
    """基于 demucs 的单旋律提取"""

    def __init__(self, sr: int = 22050, hop_length: int = 512):
        self.sample_rate = sr
        self.hop_length = hop_length
        self.notes = []
        self.demucs_config = self._load_demucs_config()
        self.preserved_vocals_path = None
        self._delegate = None

    @property
    def name(self) -> str:
        return "demucs"

    def _load_demucs_config(self) -> dict:
        config_path = Path(__file__).resolve().parents[2] / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('transcription', {}).get('vocal_separation', {}).get('demucs', {})

    def _separate_vocals(self, audio_path: str, temp_dir: str) -> str:
        try:
            import demucs.separate as demucs_separate
        except ImportError:
            raise RuntimeError('demucs not installed')

        model_name = self.demucs_config.get('model_name', 'htdemucs')
        two_stems = self.demucs_config.get('two_stems', 'vocals')
        output_format = self.demucs_config.get('output_format', 'mp3')

        demucs_args = [
            '--out', temp_dir,
            '--two-stems', two_stems,
            '-n', model_name,
        ]

        device = self.demucs_config.get('device')
        jobs = self.demucs_config.get('jobs')
        segment = self.demucs_config.get('segment')
        shifts = self.demucs_config.get('shifts')
        overlap = self.demucs_config.get('overlap')

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
        candidates = [
            os.path.join(temp_dir, model_name, basename, 'vocals.wav'),
            os.path.join(temp_dir, model_name, basename, 'vocals.mp3'),
            os.path.join(temp_dir, model_name, basename, 'vocals.flac'),
        ]
        vocals_path = next((path for path in candidates if os.path.exists(path)), None)
        if not vocals_path:
            raise RuntimeError('Failed to extract vocals')
        return vocals_path

    def extract_melody(self, audio_path: str) -> dict:
        """使用 demucs 分离人声，然后复用 librosa 提取旋律"""
        temp_dir = tempfile.mkdtemp(prefix='demucs_melody_')

        try:
            vocals_path = self._separate_vocals(audio_path, temp_dir)

            preserved_suffix = Path(vocals_path).suffix or '.wav'
            preserved_vocals_path = os.path.join(
                tempfile.gettempdir(),
                f"vocals_{next(tempfile._get_candidate_names())}{preserved_suffix}"
            )
            shutil.copy2(vocals_path, preserved_vocals_path)
            self.preserved_vocals_path = preserved_vocals_path

            from transcriber.librosa.melody import LibrosaMelodyTranscriber
            delegate = LibrosaMelodyTranscriber(sr=self.sample_rate, hop_length=self.hop_length)
            result = delegate.extract_melody(vocals_path)

            self._delegate = delegate
            self.notes = delegate.notes or []

            if isinstance(result, dict):
                result['vocals_path'] = self.preserved_vocals_path
            return result

        except Exception as e:
            self.notes = []
            if self.preserved_vocals_path and os.path.exists(self.preserved_vocals_path):
                try:
                    os.remove(self.preserved_vocals_path)
                except Exception:
                    pass
            self.preserved_vocals_path = None
            return {
                'notes': [],
                'midi_path': None,
                'error': str(e)
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def save_midi(self, output_path: str = None):
        """保存为 MIDI 文件（复用 librosa 的 MIDI 生成逻辑）"""
        if self._delegate is not None:
            return self._delegate.save_midi(output_path)
        return None
