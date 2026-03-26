"""
基于 spleeter 的和弦分离
"""

import os
import tempfile
from pathlib import Path
import numpy as np
from transcriber.base import ChordTranscriberBase, AnalysisType


class SpleeterChordTranscriber(ChordTranscriberBase):
    """基于 spleeter 的和弦分离"""
    
    def __init__(self, sr: int = 22050, hop_length: int = 512):
        self.sample_rate = sr
        self.hop_length = hop_length
        self.chords = []  # 存储提取的和弦
    
    @property
    def name(self) -> str:
        return "spleeter"
    
    def extract_chords(self, audio_path: str) -> dict:
        """使用 spleeter 分离，然后分析和弦"""
        
        try:
            from spleeter.separator import Separator
        except ImportError:
            return {
                'chords': [],
                'midi_path': None,
                'error': 'spleeter not installed'
            }
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 1. 使用 4stems 分离
            separator = Separator('spleeter:4stems')
            separator.separate_to_file(audio_path, temp_dir)
            
            # 2. 获取各轨道路径
            basename = os.path.splitext(os.path.basename(audio_path))[0]
            
            track_paths = {}
            possible_names = ['vocals', 'drums', 'bass', 'other']
            
            for name in possible_names:
                path = os.path.join(temp_dir, basename, f'{name}.wav')
                if os.path.exists(path):
                    track_paths[name] = path
            
            # 3. 加载伴奏（排除人声）
            import librosa
            
            harmonic = None
            if 'bass' in track_paths:
                y_bass, _ = librosa.load(track_paths['bass'], sr=self.sample_rate)
                harmonic = y_bass
            if 'other' in track_paths:
                y_other, _ = librosa.load(track_paths['other'], sr=self.sample_rate)
                if harmonic is not None:
                    min_len = min(len(harmonic), len(y_other))
                    harmonic = harmonic[:min_len] + y_other[:min_len]
                else:
                    harmonic = y_other
            
            if harmonic is None:
                return {
                    'chords': [],
                    'midi_path': None,
                    'error': 'No accompaniment tracks found'
                }
            
            # 4. 分析和弦并存储
            self.chords = self._analyze_chords(harmonic)
            
            return {
                'chords': self.chords,
                'midi_path': None,
                'duration': len(harmonic) / self.sample_rate
            }
            
        except Exception as e:
            self.chords = []
            return {
                'chords': [],
                'midi_path': None,
                'error': str(e)
            }
    
    def _analyze_chords(self, y):
        """分析和弦"""
        import librosa
        
        CHORD_TYPES = {
            (0, 4, 7): 'C',
            (0, 3, 7): 'Dm',
            (0, 4, 7, 11): 'CMaj7',
            (0, 3, 7, 10): 'Dm7',
            (0, 4, 7, 10): 'C7',
            (0, 5, 7): 'G',
            (0, 5, 7, 10): 'G7',
            (0, 5, 7, 11): 'GMaj7',
            (0, 4, 9): 'Em',
            (0, 3, 5): 'Am',
            (0, 4, 6): 'Eb',
            (0, 3, 6): 'Bdim',
            (0, 4, 5): 'F',
        }
        
        chords = []
        window_sec = 2.0
        hop_sec = 1.0
        
        chroma = librosa.feature.chroma_cqt(y=y, sr=self.sample_rate, hop_length=self.hop_length)
        
        n_frames = chroma.shape[1]
        frames_per_window = int(window_sec * self.sample_rate / self.hop_length)
        hop_frames = int(hop_sec * self.sample_rate / self.hop_length)
        
        for start_frame in range(0, n_frames - frames_per_window, hop_frames):
            end_frame = start_frame + frames_per_window
            window = chroma[:, start_frame:end_frame]
            
            mean_chroma = np.mean(window, axis=1)
            root_idx = np.argmax(mean_chroma)
            
            if mean_chroma[root_idx] < 0.5:
                continue
            
            sorted_indices = np.argsort(mean_chroma)[::-1]
            intervals = []
            for idx in sorted_indices[1:4]:
                diff = (idx - root_idx) % 12
                if diff > 0:
                    intervals.append(diff)
            
            intervals = tuple(sorted(intervals))
            
            chord_name = None
            for chord_intervals, name in CHORD_TYPES.items():
                if intervals == chord_intervals:
                    chord_name = name
                    break
            
            if chord_name:
                root_note = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][root_idx]
                chords.append({
                    'root': root_note,
                    'chord': f"{root_note}{chord_name}",
                    'start': start_frame * self.hop_length / self.sample_rate,
                    'duration': window_sec
                })
        
        return chords
    
    def save_midi(self, output_path: str = None):
        """保存和弦为 MIDI"""
        if output_path is None or not self.chords:
            return
        
        try:
            from music21 import stream, note, instrument
        except ImportError:
            return
        
        s = stream.Stream()
        s.append(instrument.fromString("piano"))
        
        for c in self.chords:
            try:
                n = note.Note()
                n.name = c['chord']
                n.duration.quarterLength = c.get('duration', 2.0) * 4
                s.append(n)
            except:
                pass
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        s.write('midi', fp=output_path)
