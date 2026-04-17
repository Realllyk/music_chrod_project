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

import json
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
        self.config = self._load_melody_config()
        self.fmin = self.config.get('fmin', 65)
        self.fmax = self.config.get('fmax', 1047)
        self.window_size = self.config.get('window_size', 7)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.5)
        self.min_note_duration = self.config.get('min_note_duration', 0.12)
        self.midi_median_kernel_size = self.config.get('midi_median_kernel_size', 7)
        self.merge_gap_threshold = self.config.get('merge_gap_threshold', 0.10)
        self.pitch_backend = self.config.get('pitch_backend', 'torchcrepe')
        self.torchcrepe_model = self.config.get('torchcrepe_model', 'full')
        self.torchcrepe_batch_size = self.config.get('torchcrepe_batch_size', 2048)
        self.torchcrepe_viterbi = self.config.get('torchcrepe_viterbi', True)
        self.tempo = self.config.get('default_tempo', 120)
    
    def _load_melody_config(self) -> Dict:
        config_path = Path(__file__).resolve().parents[2] / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('transcription', {}).get('melody', {})

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
        logger.info(f"使用 PYIN 提取基频... fmin={self.fmin}, fmax={self.fmax}")
        
        # PYIN 基频提取
        f0, voiced_flag, voiced_probs = librosa.pyin(
            self.audio,
            fmin=self.fmin,
            fmax=self.fmax,
            sr=self.sr,
            hop_length=self.hop_length
        )
        
        # 将 NaN 替换为 0
        f0 = np.nan_to_num(f0, nan=0.0)
        
        self.pitch = f0
        self.confidence = voiced_probs
        
        logger.info(f"基频提取完成，有效基频点: {np.sum(f0 > 0)}/{len(f0)}")
        return f0, voiced_probs
    
    def extract_pitch_torchcrepe(self) -> Tuple[np.ndarray, np.ndarray]:
        """使用 torchcrepe 算法提取基频。"""
        logger.info(
            f"使用 torchcrepe 提取基频... model={self.torchcrepe_model}, "
            f"batch_size={self.torchcrepe_batch_size}, viterbi={self.torchcrepe_viterbi}"
        )

        try:
            import torch
            import torchcrepe
        except ImportError as e:
            raise RuntimeError('torchcrepe not installed') from e

        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        audio = torch.tensor(self.audio, dtype=torch.float32).unsqueeze(0).to(device)

        decoder = torchcrepe.decode.viterbi if self.torchcrepe_viterbi else None
        pitch, periodicity = torchcrepe.predict(
            audio,
            sample_rate=self.sr,
            hop_length=self.hop_length,
            fmin=float(self.fmin),
            fmax=float(self.fmax),
            model=self.torchcrepe_model,
            batch_size=int(self.torchcrepe_batch_size),
            device=device,
            decoder=decoder,
            return_periodicity=True,
        )

        if self.torchcrepe_viterbi:
            periodicity = torchcrepe.filter.median(periodicity, 3)
            pitch = torchcrepe.filter.mean(pitch, 3)

        frequency = pitch.squeeze(0).detach().cpu().numpy()
        confidence = periodicity.squeeze(0).detach().cpu().numpy()
        frequency = np.nan_to_num(frequency, nan=0.0)
        confidence = np.nan_to_num(confidence, nan=0.0)
        frequency[confidence < self.confidence_threshold] = 0.0
        frequency[frequency < self.fmin] = 0.0
        frequency[frequency > self.fmax] = 0.0

        self.pitch = frequency
        self.confidence = confidence
        logger.info(f"torchcrepe 基频提取完成，有效基频点: {np.sum(frequency > 0)}/{len(frequency)}")
        return frequency, confidence

    def detect_tempo(self) -> float:
        """检测音频 BPM。"""
        tempo, _ = librosa.beat.beat_track(y=self.audio, sr=self.sr, hop_length=self.hop_length)
        if hasattr(tempo, '__len__'):
            tempo = float(tempo[0]) if len(tempo) else float(self.tempo)
        self.tempo = float(tempo) if tempo else float(self.tempo)
        logger.info(f"检测到 BPM: {self.tempo}")
        return self.tempo

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
    
    def merge_adjacent_same_notes(self, notes: List[Dict], gap_threshold: float) -> List[Dict]:
        """合并间隔很短的相邻同音符。"""
        if not notes:
            return []

        merged = [notes[0].copy()]
        for note in notes[1:]:
            prev = merged[-1]
            prev_end = prev['start_frame'] * self.hop_length / self.sr + prev['duration']
            current_start = note['start_frame'] * self.hop_length / self.sr
            gap = current_start - prev_end

            if prev['midi'] == note['midi'] and gap < gap_threshold:
                prev['end_frame'] = note['end_frame']
                prev['duration'] = (note['end_frame'] - prev['start_frame']) * self.hop_length / self.sr
                prev['confidence'] = max(prev.get('confidence', 0), note.get('confidence', 0))
            else:
                merged.append(note.copy())

        return merged

    def pitch_to_notes(self, cent_threshold: float = 50) -> List[Dict]:
        """
        将基频转换为音符
        
        Args:
            cent_threshold: 音分阈值（用于量化）
        
        Returns:
            音符列表
        """
        logger.info(
            f"将基频转换为音符... confidence_threshold={self.confidence_threshold}, "
            f"min_note_duration={self.min_note_duration}, midi_median_kernel_size={self.midi_median_kernel_size}, "
            f"merge_gap_threshold={self.merge_gap_threshold}"
        )
        
        if self.pitch is None:
            raise ValueError("请先提取基频")
        
        # A4 = 440 Hz 作为参考
        A4_freq = 440
        A4_midi = 69

        midi_sequence = np.zeros(len(self.pitch), dtype=float)
        freq_sequence = np.zeros(len(self.pitch), dtype=float)
        confidence_sequence = np.zeros(len(self.pitch), dtype=float)

        for i, freq in enumerate(self.pitch):
            confidence = self.confidence[i] if self.confidence is not None else 0.8
            if freq > 0 and confidence >= self.confidence_threshold:
                midi_sequence[i] = round(A4_midi + 12 * np.log2(freq / A4_freq))
                freq_sequence[i] = freq
                confidence_sequence[i] = confidence

        voiced_mask = midi_sequence > 0
        voiced_count = int(np.sum(voiced_mask))
        if np.any(voiced_mask):
            voiced_midi = midi_sequence[voiced_mask]
            kernel_size = int(self.midi_median_kernel_size)
            if kernel_size % 2 == 0:
                kernel_size += 1
            if kernel_size > len(voiced_midi):
                kernel_size = len(voiced_midi) if len(voiced_midi) % 2 == 1 else max(1, len(voiced_midi) - 1)
            if kernel_size >= 3:
                midi_sequence[voiced_mask] = signal.medfilt(voiced_midi, kernel_size=kernel_size)

        logger.info(f"MIDI 序列中值滤波完成，有声帧数={voiced_count}")

        notes = []
        current_note = None

        for i, midi_value in enumerate(midi_sequence):
            if midi_value <= 0:
                if current_note is not None:
                    current_note['end_frame'] = i
                    current_note['duration'] = (i - current_note['start_frame']) * self.hop_length / self.sr
                    notes.append(current_note)
                    current_note = None
                continue

            if current_note is None:
                current_note = {
                    'start_frame': i,
                    'midi': int(midi_value),
                    'freq': float(freq_sequence[i]) if freq_sequence[i] > 0 else 0.0,
                    'confidence': float(confidence_sequence[i]) if confidence_sequence[i] > 0 else 0.8
                }
            elif current_note['midi'] != int(midi_value):
                current_note['end_frame'] = i
                current_note['duration'] = (i - current_note['start_frame']) * self.hop_length / self.sr
                notes.append(current_note)
                current_note = {
                    'start_frame': i,
                    'midi': int(midi_value),
                    'freq': float(freq_sequence[i]) if freq_sequence[i] > 0 else 0.0,
                    'confidence': float(confidence_sequence[i]) if confidence_sequence[i] > 0 else 0.8
                }

        if current_note is not None:
            current_note['end_frame'] = len(midi_sequence)
            current_note['duration'] = (len(midi_sequence) - current_note['start_frame']) * self.hop_length / self.sr
            notes.append(current_note)

        raw_note_count = len(notes)
        notes = [note for note in notes if note.get('duration', 0) >= self.min_note_duration]
        short_filtered_count = raw_note_count - len(notes)
        merged_notes = self.merge_adjacent_same_notes(notes, self.merge_gap_threshold)
        merge_reduced_count = len(notes) - len(merged_notes)

        self.notes = merged_notes
        logger.info(
            f"识别音符数: 原始={raw_note_count}, 过滤后={len(notes)}, 合并后={len(merged_notes)}, "
            f"过滤掉过短音符={short_filtered_count}, 合并减少={merge_reduced_count}"
        )
        return merged_notes
    
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
            import pretty_midi
        except ImportError:
            logger.error("需要安装 pretty_midi: pip install pretty_midi")
            return

        logger.info(f"生成 MIDI 文件: {output_path}, tempo={self.tempo}")

        midi = pretty_midi.PrettyMIDI(initial_tempo=float(self.tempo))
        instrument = pretty_midi.Instrument(program=0, name='Melody')

        for note_info in self.notes:
            start_time = note_info['start_frame'] * self.hop_length / self.sr
            end_time = start_time + note_info['duration']
            if end_time <= start_time:
                continue
            midi_note = pretty_midi.Note(
                velocity=100,
                pitch=int(note_info['midi']),
                start=float(start_time),
                end=float(end_time),
            )
            instrument.notes.append(midi_note)

        midi.instruments.append(instrument)

        if output_path:
            midi.write(output_path)
            logger.info(f"MIDI 文件已保存: {output_path}, tempo={self.tempo}")

        return midi
    
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
            if self.pitch_backend == 'torchcrepe':
                self.extract_pitch_torchcrepe()
            else:
                self.extract_pitch_pyin()
            
            # 3. 平滑基频
            self.smooth_pitch(window_size=self.window_size)
            
            # 4. 检测 BPM
            self.detect_tempo()

            # 5. 转换为音符
            self.pitch_to_notes()
            
            # 6. 返回结果
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
