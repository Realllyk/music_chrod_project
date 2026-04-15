"""
基于 spleeter 的单旋律提取
"""

import os
import shutil
import tempfile
from pathlib import Path
import numpy as np
from transcriber.base import MelodyTranscriberBase, AnalysisType


class SpleeterMelodyTranscriber(MelodyTranscriberBase):
    """基于 spleeter 的单旋律提取"""
    
    def __init__(self, sr: int = 22050, hop_length: int = 512):
        self.sample_rate = sr
        self.hop_length = hop_length
        self.notes = []  # 存储提取的音符
    
    @property
    def name(self) -> str:
        return "spleeter"
    
    def extract_melody(self, audio_path: str) -> dict:
        """使用 spleeter 分离人声，然后提取旋律"""
        print(f"[SpleeterMelody] 开始提取: {audio_path}")
        
        try:
            from spleeter.separator import Separator
            print(f"[SpleeterMelody] spleeter 已导入")
        except ImportError:
            print(f"[SpleeterMelody] spleeter 未安装")
            return {
                'notes': [],
                'midi_path': None,
                'error': 'spleeter not installed'
            }
        
        temp_dir = tempfile.mkdtemp(prefix='spleeter_melody_')
        print(f"[SpleeterMelody] 临时目录: {temp_dir}")
        
        try:
            # 1. 使用 spleeter 2stems 分离人声
            print(f"[SpleeterMelody] 开始分离...")
            separator = Separator('spleeter:2stems')
            separator.separate_to_file(audio_path, temp_dir)
            print(f"[SpleeterMelody] 分离完成")
            
            # 2. 找到人声文件
            basename = os.path.splitext(os.path.basename(audio_path))[0]
            vocals_path = os.path.join(temp_dir, basename, 'vocals.wav')
            
            if not os.path.exists(vocals_path):
                # 尝试其他路径格式
                vocals_path = os.path.join(temp_dir, 'vocals.wav')
            
            print(f"[SpleeterMelody] 人声文件: {vocals_path}, 存在: {os.path.exists(vocals_path)}")
            
            if not os.path.exists(vocals_path):
                return {
                    'notes': [],
                    'midi_path': None,
                    'error': 'Failed to extract vocals'
                }
            
            # 3. 从人声提取旋律（使用 librosa）
            import librosa
            print(f"[SpleeterMelody] 加载音频...")
            y, sr = librosa.load(vocals_path, sr=self.sample_rate)
            print(f"[SpleeterMelody] 音频长度: {len(y)} samples, 时长: {len(y)/sr:.2f}s")
            
            # 使用 pyin 提取基频
            print(f"[SpleeterMelody] 使用 pyin 提取基频...")
            f0, voiced_flag, voiced_probs = librosa.pyin(
                y, 
                fmin=librosa.note_to_hz('C1'),
                fmax=librosa.note_to_hz('C8'),
                sr=sr,
                hop_length=self.hop_length
            )
            print(f"[SpleeterMelody] pyin 完成, f0 形状: {f0.shape}")
            
            # 4. 转换为音符并存储
            self.notes = []
            frame_times = librosa.times_like(f0, sr=sr, hop_length=self.hop_length)
            
            voiced_count = sum(1 for v in voiced_flag if v)
            print(f"[SpleeterMelody] 有声帧数: {voiced_count}/{len(voiced_flag)}")
            
            for i, (freq, voiced) in enumerate(zip(f0, voiced_flag)):
                if voiced and freq > 0:
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
            
            print(f"[SpleeterMelody] 提取到 {len(self.notes)} 个音符")
            
            return {
                'notes': self.notes,
                'midi_path': None,
                'duration': len(y) / sr
            }
            
        except Exception as e:
            self.notes = []
            print(f"[SpleeterMelody] Exception: {e}")
            import traceback
            traceback.print_exc()
            return {
                'notes': [],
                'midi_path': None,
                'error': str(e)
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def save_midi(self, output_path: str = None):
        """保存为 MIDI 文件"""
        if output_path is None:
            print(f"[SpleeterMelody] output_path is None, skipping save")
            return
        
        if not self.notes:
            print(f"[SpleeterMelody] self.notes is empty ({len(self.notes)}), skipping save")
            return
        
        try:
            from music21 import stream, note, metadata
        except ImportError:
            print(f"[SpleeterMelody] music21 not installed")
            return
        
        try:
            s = stream.Stream()
            s.metadata = metadata.Metadata()
            s.metadata.title = 'Spleeter Melody'
            
            for n in self.notes:
                try:
                    pitch = note.Note()
                    pitch.midi = n['midi']
                    pitch.duration.quarterLength = 0.25
                    s.append(pitch)
                except Exception as e:
                    print(f"[SpleeterMelody] Error creating note: {e}")
            
            # 确保目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            print(f"[SpleeterMelody] Saving MIDI to: {output_path}")
            s.write('midi', fp=output_path)
            print(f"[SpleeterMelody] MIDI saved successfully")
        except Exception as e:
            print(f"[SpleeterMelody] Error saving MIDI: {e}")
            import traceback
            traceback.print_exc()
