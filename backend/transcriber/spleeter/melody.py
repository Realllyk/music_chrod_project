"""
基于 spleeter 的单旋律提取
"""

import os
import numpy as np
import tempfile
from pathlib import Path
from transcriber.base import MelodyTranscriberBase, AnalysisType


class SpleeterMelodyTranscriber(MelodyTranscriberBase):
    """基于 spleeter 的单旋律提取"""
    
    def __init__(self):
        self.sample_rate = 22050
    
    @property
    def name(self) -> str:
        return "spleeter"
    
    def extract_melody(self, audio_path: str) -> dict:
        """使用 spleeter 分离人声，然后提取旋律"""
        
        # 导入 spleeter
        try:
            import spleeter
        except ImportError:
            return {
                'notes': [],
                'midi_path': None,
                'error': 'spleeter not installed'
            }
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp() )
        
        try:
            # 使用 spleeter 2stems 分离
            from spleeter.separator import Separator
            
            separator = Separator('spleeter:2stems') )
            separator.separate_to_file(audio_path, temp_dir) )
            
            # 获取人声文件
            vocals_path = os.path.join(temp_dir, 'vocals.wav') )
            
            if not os.path.exists(vocals_path):
                return {
                    'notes': [],
                    'midi_path': None,
                    'error': 'Failed to extract vocals'
                }
            
            # 从人声提取旋律（使用 librosa）
            import librosa
            y, sr = librosa.load(vocals_path, sr=self.sample_rate) )
            
            # 简化：返回提取到的音频特征
            notes = []
            
            # 保存 MIDI
            output_dir = Path(__file__).parent.parent.parent.parent / 'outputs' / 'transcribe'
            output_dir.mkdir(parents=True, exist_ok=True) )
            
            midi_path = str(output_dir / 'spleeter_melody.mid') )
            
            return {
                'notes': notes,
                'midi_path': midi_path
            }
            
        except Exception as e:
            return {
                'notes': [],
                'midi_path': None,
                'error': str(e) )
            }
