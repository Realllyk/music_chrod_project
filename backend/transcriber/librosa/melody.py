"""
单旋律提取 - 自动识别和提取主旋律

================================================================================
输入格式
================================================================================

音频文件：
  - 格式：MP3, WAV, FLAC, OGG, M4A, WMA
  - 采样率：任意（自动重采样到 22050 Hz）
  - 声道：单声道或立体声（自动转换为单声道）
  - 时长：无限制（理论上支持任意长度）

================================================================================
输出格式
================================================================================

1. 基本返回值（transcribe() 方法）：
   {
       "notes": [
           {
               "start_frame": 0,
               "end_frame": 512,
               "midi": 60,              # MIDI 音号 (0-127)
               "freq": 261.63,          # 频率 (Hz)
               "duration": 0.5,         # 时长 (秒)
               "confidence": 0.95       # 置信度 (0-1)
           },
           ...
       ],
       "total_notes": 42,
       "duration_sec": 10.5
   }

2. MIDI 文件：
   - 格式：Standard MIDI File (.mid)
   - 轨道数：1
   - 乐器：长笛 (Flute, Channel 0)
   - 时值：四分音符为基准

3. 可视化数据（get_visualization_data() 方法）：
   {
       "pitch_curve": [0, 261.63, 293.66, ...],  # 基频曲线 (Hz)
       "midi_curve": [None, 60, 62, ...],        # MIDI 序列
       "confidence": [0, 0.95, 0.92, ...],       # 置信度曲线
       "notes": [...]                             # 同基本返回值
   }

================================================================================
算法详解
================================================================================

步骤 1: 音频加载
  输入：MP3/WAV 等音频文件
  输出：NumPy 数组 (1D, float32)
  采样率：22050 Hz (librosa 默认)

步骤 2: PYIN 基频提取
  输入：音频信号
  参数：fmin=80 Hz, fmax=400 Hz
  输出：基频曲线 (Hz)，NaN 表示无声部分
  
  PYIN 算法特点：
  - 高精度基频检测
  - 抗噪性强
  - 适合人声和旋律乐器
  - 输出置信度 (0-1)

步骤 3: 基频平滑
  输入：基频曲线
  方法：移动平均（窗口大小 7）
  输出：平滑后的基频曲线

步骤 4: 音符转换
  输入：基频曲线
  转换公式：MIDI = 69 + 12 * log2(freq/440)
  输出：离散音符列表（MIDI 号）

步骤 5: MIDI 生成
  输入：音符列表
  输出：Standard MIDI File (.mid)
  乐器：长笛
  速度：100 (固定)

================================================================================
参数说明
================================================================================

sr (采样率)：默认 22050 Hz
  - 更高的采样率：更好的高频精度，处理更慢
  - 22050 Hz 足以捕捉人声频率范围

hop_length (跳跃大小)：默认 512
  - 影响时间分辨率
  - 512 对应约 23 ms 的帧间隔
  
fmin, fmax：基频搜索范围
  - 女性人声：fmin=150, fmax=600
  - 男性人声：fmin=80, fmax=300
  - 乐器：fmin=200, fmax=800

================================================================================
"""

import numpy as np
import librosa
from transcriber.base import MelodyTranscriberBase, AnalysisType
import soundfile as sf
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional
import scipy.signal as signal

logger = logging.getLogger(__name__)


class LibrosaMelodyTranscriber(MelodyTranscriberBase):
    """单旋律提取器"""
    
    @property
    def name(self) -> str:
        return "librosa"
    
    def __init__(self, sr: int = 22050, hop_length: int = 512):
        """
        初始化
        
        Args:
            sr: 采样率
            hop_length: 跳跃大小
        """
        self.sr = sr
        self.hop_length = hop_length
        self.audio = None
        self.S = None  # 幅度谱
        self.pitch = None  # 基频
        self.confidence = None  # 置信度
        self.notes = None  # 识别的音符
    
    def load_audio(self, audio_path: str) -> np.ndarray:
        """加载音频文件"""
        logger.info(f"加载音频: {audio_path}")
        self.audio, _ = librosa.load(audio_path, sr=self.sr, mono=True)
        logger.info(f"音频加载完成，时长: {len(self.audio) / self.sr:.2f}s")
        return self.audio
    
    def compute_spectrogram(self) -> np.ndarray:
        """计算频谱图"""
        logger.info("计算频谱图...")
        self.S = librosa.stft(self.audio, n_fft=2048, hop_length=self.hop_length)
        self.S = np.abs(self.S)
        logger.info(f"频谱图形状: {self.S.shape}")
        return self.S
    
    def extract_pitch_pyin(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        使用 PYIN 算法提取基频
        
        Returns:
            (pitch, confidence) - 基频和置信度
        """
        logger.info("使用 PYIN 提取基频...")
        
        # PYIN 基频提取
        f0, voiced_flag, voiced_probs = librosa.pyin(
            self.audio,
            fmin=80,    # 最小频率 (80 Hz)
            fmax=400,   # 最大频率 (400 Hz)
            sr=self.sr
        )
        
        # 将 NaN 替换为 0
        f0 = np.nan_to_num(f0, nan=0.0)
        
        self.pitch = f0
        self.confidence = voiced_probs
        
        logger.info(f"基频提取完成，有效基频点: {np.sum(f0 > 0)}/{len(f0)}")
        return f0, voiced_probs
    
    def smooth_pitch(self, window_size: int = 5) -> np.ndarray:
        """
        平滑基频曲线（移动平均）
        
        Args:
            window_size: 窗口大小
        
        Returns:
            平滑后的基频
        """
        logger.info(f"平滑基频曲线 (window_size={window_size})...")
        
        if self.pitch is None:
            raise ValueError("请先提取基频")
        
        # 创建平滑窗口（只在有效点上平滑）
        smoothed = np.copy(self.pitch)
        
        for i in range(len(smoothed)):
            if smoothed[i] > 0:  # 只平滑有效点
                start = max(0, i - window_size // 2)
                end = min(len(smoothed), i + window_size // 2 + 1)
                
                # 计算有效点的平均值
                valid_points = smoothed[start:end]
                valid_points = valid_points[valid_points > 0]
                
                if len(valid_points) > 0:
                    smoothed[i] = np.mean(valid_points)
        
        self.pitch = smoothed
        logger.info("基频平滑完成")
        return smoothed
    
    def pitch_to_notes(self, cent_threshold: float = 50) -> List[Dict]:
        """
        将基频转换为音符
        
        Args:
            cent_threshold: 音分阈值（用于量化）
        
        Returns:
            音符列表
        """
        logger.info("将基频转换为音符...")
        
        if self.pitch is None:
            raise ValueError("请先提取基频")
        
        # A4 = 440 Hz 作为参考
        A4_freq = 440
        A4_midi = 69
        
        notes = []
        current_note = None
        current_start = 0
        
        for i, freq in enumerate(self.pitch):
            if freq <= 0:  # 无声部分
                if current_note is not None:
                    # 保存当前音符
                    current_note['end_frame'] = i
                    current_note['duration'] = (i - current_note['start_frame']) * self.hop_length / self.sr
                    notes.append(current_note)
                    current_note = None
            else:
                # 频率转 MIDI 音号
                midi = A4_midi + 12 * np.log2(freq / A4_freq)
                midi_rounded = round(midi)  # 量化到最近的半音
                
                if current_note is None:
                    # 开始新音符
                    current_note = {
                        'start_frame': i,
                        'midi': midi_rounded,
                        'freq': freq,
                        'confidence': self.confidence[i] if self.confidence is not None else 0.8
                    }
                elif current_note['midi'] != midi_rounded:
                    # 音符改变
                    current_note['end_frame'] = i
                    current_note['duration'] = (i - current_note['start_frame']) * self.hop_length / self.sr
                    notes.append(current_note)
                    
                    current_note = {
                        'start_frame': i,
                        'midi': midi_rounded,
                        'freq': freq,
                        'confidence': self.confidence[i] if self.confidence is not None else 0.8
                    }
        
        # 保存最后一个音符
        if current_note is not None:
            current_note['end_frame'] = len(self.pitch)
            current_note['duration'] = (len(self.pitch) - current_note['start_frame']) * self.hop_length / self.sr
            notes.append(current_note)
        
        self.notes = notes
        logger.info(f"识别音符数: {len(notes)}")
        return notes
    
    def notes_to_dict(self) -> Dict:
        """将音符转换为字典格式"""
        if self.notes is None:
            return {}
        
        return {
            'notes': self.notes,
            'total_notes': len(self.notes),
            'duration_sec': len(self.pitch) * self.hop_length / self.sr
        }
    
    def save_midi(self, output_path: str = None):
        """
        保存为 MIDI 文件
        
        Args:
            output_path: 输出文件路径
        """
        if self.notes is None or len(self.notes) == 0:
            logger.warning("没有音符，无法生成 MIDI")
            return
        
        try:
            from music21 import stream, note, instrument
        except ImportError:
            logger.error("需要安装 music21: pip install music21")
            return
        
        logger.info(f"生成 MIDI 文件: {output_path}")
        
        # 创建乐谱
        s = stream.Score()
        part = stream.Part()
        part.instrument = instrument.Flute()
        
        # 添加音符
        for note_info in self.notes:
            midi_num = note_info['midi']
            duration = note_info['duration']
            
            # 音符时值（简化处理）
            if duration < 0.25:
                quarter_length = 0.25
            elif duration < 0.5:
                quarter_length = 0.5
            elif duration < 1:
                quarter_length = 1
            else:
                quarter_length = duration
            
            # 创建音符对象
            n = note.Note(midi=midi_num)
            n.quarterLength = quarter_length
            part.append(n)
        
        s.append(part)
        
        # 保存文件
        if output_path:
            s.write('midi', fp=output_path)
            logger.info(f"MIDI 文件已保存: {output_path}")
        
        return s
    
    def extract_melody(self, audio_path: str) -> Dict:
        """提取单旋律"""
        return self.transcribe(audio_path)
    
    def transcribe(self, audio_path: str) -> Dict:
        """
        完整的扒谱流程
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            扒谱结果
        """
        try:
            # 1. 加载音频
            self.load_audio(audio_path)
            
            # 2. 提取基频
            self.extract_pitch_pyin()
            
            # 3. 平滑基频
            self.smooth_pitch(window_size=7)
            
            # 4. 转换为音符
            self.pitch_to_notes()
            
            # 5. 返回结果
            result = self.notes_to_dict()
            logger.info(f"扒谱完成: {result['total_notes']} 个音符")
            
            return result
        
        except Exception as e:
            logger.error(f"扒谱失败: {e}")
            raise
    
    def get_visualization_data(self) -> Dict:
        """获取可视化数据"""
        if self.pitch is None:
            return {}
        
        # 将基频转换为 MIDI
        A4_freq = 440
        A4_midi = 69
        
        midi_curve = []
        for freq in self.pitch:
            if freq > 0:
                midi = A4_midi + 12 * np.log2(freq / A4_freq)
                midi_curve.append(round(midi))
            else:
                midi_curve.append(None)
        
        return {
            'pitch_curve': self.pitch.tolist(),
            'midi_curve': midi_curve,
            'confidence': self.confidence.tolist() if self.confidence is not None else None,
            'notes': self.notes
        }
