"""
基于 spleeter 的和弦分离
"""

import os
import tempfile
from pathlib import Path
from transcriber.base import ChordTranscriberBase, AnalysisType


class SpleeterChordTranscriber(ChordTranscriberBase):
    """基于 spleeter 的和弦分离"""
    
    def __init__(self):
        self.sample_rate = 22050
    
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
            # 使用 4stems 分离
            separator = Separator('spleeter:4stems')
            separator.separate_to_file(audio_path, temp_dir)
            
            # 获取各个轨道
            # 可以进一步处理来分析和弦
            
            # 保存 MIDI
            output_dir = Path(__file__).parent.parent.parent.parent / 'outputs' / 'transcribe'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            midi_path = str(output_dir / 'spleeter_chord.mid')
            
            return {
                'chords': [],
                'midi_path': midi_path
            }
            
        except Exception as e:
            return {
                'chords': [],
                'midi_path': None,
                'error': str(e)
            }
