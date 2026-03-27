"""
基于 demucs 的单旋律提取
使用 demucs 分离人声，然后使用 librosa 提取旋律
"""

import os
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
    
    @property
    def name(self) -> str:
        return "demucs"
    
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
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 1. 使用 demucs 分离
            # demucs.separate 会自动保存到 separated/{model}/{track_name}/
            demucs_separate.main([
                '--out', temp_dir,
                '--model', 'htdemucs',
                audio_path
            ])
            
            # 2. 找到人声文件
            basename = os.path.splitext(os.path.basename(audio_path))[0]
            vocals_path = os.path.join(temp_dir, 'htdemucs', basename, 'vocals.wav')
            
            if not os.path.exists(vocals_path):
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
                fmin=librosa.note_to_hz('C1'),
                fmax=librosa.note_to_hz('C8'),
                sr=sr,
                hop_length=self.hop_length
            )
            
            # 4. 转换为音符
            self.notes = []
            frame_times = librosa.times_like(f0, sr=sr, hop_length=self.hop_length)
            
            for i, (freq, voiced) in enumerate(zip(f0, voiced_flag)):
                if voiced and freq > 0:
                    midi = librosa.hz_to_midi(freq)
                    midi_quantized = round(midi * 12) / 12
                    note_name = librosa.midi_to_note(int(midi_quantized))
                    
                    self.notes.append({
                        'pitch': freq,
                        'midi': float(midi_quantized),
                        'note': note_name,
                        'start': float(frame_times[i]),
                        'duration': float(self.hop_length / sr)
                    })
            
            return {
                'notes': self.notes,
                'midi_path': None,
                'duration': len(y) / sr
            }
            
        except Exception as e:
            self.notes = []
            return {
                'notes': [],
                'midi_path': None,
                'error': str(e)
            }
    
    def save_midi(self, output_path: str = None):
        """保存为 MIDI 文件"""
        if output_path is None or not self.notes:
            return
        
        try:
            from music21 import stream, note
        except ImportError:
            return
        
        try:
            s = stream.Stream()
            s.metadata = stream.Metadata()
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
