"""
基于 demucs 的单旋律提取
使用 demucs 分离人声，然后使用 librosa 提取旋律
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
import numpy as np
from transcriber.base import MelodyTranscriberBase, AnalysisType


class DemucsMelodyTranscriber(MelodyTranscriberBase):
    """基于 demucs 的单旋律提取"""
    
    def __init__(self, sr: int = 22050, hop_length: int = 512):
        self.sample_rate = sr
        self.hop_length = hop_length
        self.notes = []
        self.demucs_config = self._load_demucs_config()
    
    @property
    def name(self) -> str:
        return "demucs"

    def _load_demucs_config(self) -> dict:
        config_path = Path(__file__).resolve().parents[2] / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('transcription', {}).get('vocal_separation', {}).get('demucs', {})
    
    def extract_melody(self, audio_path: str) -> dict:
        """使用 demucs 分离人声，然后提取旋律"""

        try:
            import demucs.separate as demucs_separate
        except ImportError:
            return {
                'notes': [],
                'midi_path': None,
                'error': 'demucs not installed'
            }

        temp_dir = tempfile.mkdtemp(prefix='demucs_melody_')

        try:
            # 1. 使用 demucs 分离人声
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

            # 2. 找到人声文件
            basename = os.path.splitext(os.path.basename(audio_path))[0]
            candidates = [
                os.path.join(temp_dir, model_name, basename, 'vocals.wav'),
                os.path.join(temp_dir, model_name, basename, 'vocals.mp3'),
                os.path.join(temp_dir, model_name, basename, 'vocals.flac'),
            ]
            vocals_path = next((path for path in candidates if os.path.exists(path)), None)

            if not vocals_path:
                return {
                    'notes': [],
                    'midi_path': None,
                    'error': 'Failed to extract vocals'
                }

            # 3. 使用 librosa 提取旋律
            import librosa
            y, sr = librosa.load(vocals_path, sr=self.sample_rate)

            f0, voiced_flag, voiced_probs = librosa.pyin(
                y,
                fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C7'),
                sr=sr,
                hop_length=self.hop_length
            )

            # 4. 转换为音符
            self.notes = []
            frame_times = librosa.times_like(f0, sr=sr, hop_length=self.hop_length)

            for i, (freq, voiced) in enumerate(zip(f0, voiced_flag)):
                if voiced and freq and freq > 0:
                    midi = librosa.hz_to_midi(freq)
                    midi_quantized = int(round(midi))
                    note_name = librosa.midi_to_note(midi_quantized)

                    self.notes.append({
                        'pitch': float(freq),
                        'midi': midi_quantized,
                        'note': note_name,
                        'start': float(frame_times[i]),
                        'duration': float(self.hop_length / sr)
                    })

            return {
                'notes': self.notes,
                'midi_path': None,
                'duration': len(y) / sr,
                'vocals_path': vocals_path
            }

        except Exception as e:
            self.notes = []
            return {
                'notes': [],
                'midi_path': None,
                'error': str(e)
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def save_midi(self, output_path: str = None):
        """保存为 MIDI 文件"""
        if output_path is None or not self.notes:
            return
        
        try:
            from music21 import stream, note, metadata
        except ImportError:
            return
        
        try:
            s = stream.Stream()
            s.metadata = metadata.Metadata()
            s.metadata.title = 'Demucs Melody'
            
            for n in self.notes:
                try:
                    pitch = note.Note()
                    pitch.midi = n['midi']
                    pitch.duration.quarterLength = 0.25
                    s.append(pitch)
                except:
                    pass
            
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            s.write('midi', fp=output_path)
        except Exception as e:
            print(f"[DemucsMelody] Error saving MIDI: {e}")
