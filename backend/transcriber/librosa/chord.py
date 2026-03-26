"""
多声部分离 - 分离和识别多个声部

================================================================================
输入格式
================================================================================

音频文件：
  - 格式：MP3, WAV, FLAC, OGG, M4A, WMA
  - 采样率：任意（自动重采样到 22050 Hz）
  - 声道：单声道或立体声（自动转换为单声道）
  - 类型：
    * 最佳：钢琴、弦乐、合唱等多声部
    * 可用：人声 + 伴奏
    * 困难：混响过多、压缩过度
  - 时长：无限制

================================================================================
输出格式
================================================================================

1. 基本返回值（transcribe() 方法）：
   {
       "voices": [
           [  # 第 1 声部
               {
                   "start_frame": 0,
                   "end_frame": 512,
                   "midi": 60,
                   "freq": 261.63,
                   "duration": 0.5
               },
               ...
           ],
           [  # 第 2 声部
               {
                   "start_frame": 100,
                   "end_frame": 612,
                   "midi": 72,
                   "freq": 392.00,
                   "duration": 0.5
               },
               ...
           ]
       ],
       "total_voices": 2,
       "duration_sec": 10.5
   }

2. 多轨 MIDI 文件：
   - 格式：Standard MIDI File (.mid)
   - 轨道数：N（等于声部数）
   - 乐器分配：
     * 轨道 1：长笛 (Flute)
     * 轨道 2：小提琴 (Violin)
     * 轨道 3：大提琴 (Cello)
     * 轨道 4：低音提琴 (Contrabass)
   - 时值：四分音符为基准

3. 可视化数据（get_visualization_data() 方法）：
   {
       "voices": [...],              # 同基本返回值
       "harmonic_spectrogram": [],   # 谐波分量频谱图
       "percussive_spectrogram": []  # 打击分量频谱图
   }

================================================================================
算法详解
================================================================================

步骤 1: 音频加载
  输入：MP3/WAV 等音频文件
  输出：NumPy 数组 (1D, float32)
  采样率：22050 Hz

步骤 2: HPSS 分离（Harmonic-Percussive Source Separation）
  输入：音频信号
  输出：
    - 谐波分量（harmonic）：旋律和和弦
    - 打击分量（percussive）：鼓、打击乐
  
  HPSS 原理：
  - 分析短时傅里叶变换 (STFT) 谱图
  - 检测中位数过滤后的谐波性（平滑）
  - 打击成分保留尖锐变化
  - 参数 margin=4.0 控制分离程度

步骤 3: 多旋律提取
  输入：谐波分量频谱图
  方法：
    1. 对每一帧找最强频率峰值
    2. 记录为第 1 旋律
    3. 抑制该频率（避免重复）
    4. 再找次强频率
    5. 重复 N 次（N=n_voices）
  
  输出：N 条频率轨迹

步骤 4: 频率转音符
  输入：频率轨迹
  方法：与单旋律提取相同
  输出：离散音符列表

步骤 5: 多轨 MIDI 生成
  输入：多条音符列表
  分配：
    - 每条旋律分配不同乐器
    - 在 MIDI 中对应不同轨道
  输出：标准多轨 MIDI 文件

================================================================================
参数说明
================================================================================

n_voices：预期声部数
  默认：2
  范围：1-4（取决于音乐复杂度）
  建议：
    - 1: 纯人声或单旋律
    - 2: 人声 + 伴奏、双声部
    - 3: 三声部（如弦乐三重奏）
    - 4: 四声部（如弦乐四重奏或合唱）

hpss_margin：HPSS 分离程度
  默认：4.0
  范围：1-10
  建议：
    - 低值（1-2）：分离不彻底，可能混合
    - 中值（4-5）：平衡，推荐
    - 高值（8-10）：激进分离，可能断裂

================================================================================
局限性和注意事项
================================================================================

1. 和弦识别
   - 当前：分离为独立音符
   - 不识别：特定和弦类型（大、小、七等）
   - 改进方向：使用 chroma 特性识别

2. 打击乐
   - HPSS 会将鼓、打击乐分离为 percussive 分量
   - 当前不处理打击乐
   - 改进方向：单独的打击乐识别模块

3. 时间准确性
   - 用 hop_length=512 导致 ~23ms 的时间误差
   - 足以捕捉音乐节奏但不适合精确编辑

4. 贝司线
   - 可能被识别为低音声部
   - 对节奏的处理：需要单独模块

5. 混响和延迟
   - 高混响环境会降低分离精度
   - 压缩的音频质量下降明显

================================================================================
"""

import numpy as np
import librosa
from transcriber.base import ChordTranscriberBase, AnalysisType
import logging
from typing import Dict, List, Tuple
# from .melody import MelodyTranscriber

logger = logging.getLogger(__name__)


class LibrosaChordTranscriber(ChordTranscriberBase):
    """多声部分离器"""
    
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
        self.harmonic = None  # 谐波分量
        self.percussive = None  # 打击分量
        self.voices = None  # 分离的声部
        self.notes = None  # 识别的音符
    
    def load_audio(self, audio_path: str) -> np.ndarray:
        """加载音频文件"""
        logger.info(f"加载音频: {audio_path}")
        self.audio, _ = librosa.load(audio_path, sr=self.sr, mono=True)
        logger.info(f"音频加载完成，时长: {len(self.audio) / self.sr:.2f}s")
        return self.audio
    
    def separate_harmonic_percussive(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        分离谐波和打击分量
        使用 HPSS (Harmonic-Percussive Source Separation)
        
        Returns:
            (harmonic, percussive) - 谐波和打击分量的幅度谱
        """
        logger.info("进行谐波-打击分离 (HPSS)...")
        
        # STFT 分解
        S = librosa.stft(self.audio, n_fft=2048, hop_length=self.hop_length)
        
        # HPSS 分离
        harmonic, percussive = librosa.decompose.hpss(S, margin=4.0)
        
        self.S = np.abs(S)
        self.harmonic = np.abs(harmonic)
        self.percussive = np.abs(percussive)
        
        logger.info("谐波-打击分离完成")
        return self.harmonic, self.percussive
    
    def extract_multiple_melodies(self, n_voices: int = 2) -> List[List[Dict]]:
        """
        从谐波分量中提取多条旋律
        
        Args:
            n_voices: 预期的声部数量
        
        Returns:
            多条旋律列表
        """
        logger.info(f"提取 {n_voices} 条旋律...")
        
        if self.harmonic is None:
            raise ValueError("请先进行 HPSS 分离")
        
        # 对每个频率时间点进行峰值检测
        voices = []
        
        # 简化方案：提取前 n_voices 个最强的频率分量
        for voice_idx in range(n_voices):
            logger.info(f"提取第 {voice_idx + 1} 条旋律...")
            
            # 复制谐波谱
            S_copy = np.copy(self.harmonic)
            
            # 提取主要频率
            freqs = []
            for t in range(S_copy.shape[1]):
                col = S_copy[:, t]
                if np.sum(col) > 0:
                    # 找最强频率
                    peak_freq = np.argmax(col)
                    freqs.append(peak_freq)
                    
                    # 抑制已提取的频率（为下一条旋律服务）
                    S_copy[max(0, peak_freq-3):min(len(col), peak_freq+4), t] = 0
                else:
                    freqs.append(0)
            
            # 将频率转换为基频
            pitches = librosa.core.frames_to_time(np.array(freqs), sr=self.sr)
            
            # 转换为音符
            notes = self._freq_to_notes(pitches)
            voices.append(notes)
        
        self.voices = voices
        logger.info(f"提取完成，共 {len(voices)} 条旋律")
        return voices
    
    def _freq_to_notes(self, frequencies: np.ndarray) -> List[Dict]:
        """将频率转换为音符"""
        A4_freq = 440
        A4_midi = 69
        
        notes = []
        current_note = None
        
        for i, freq in enumerate(frequencies):
            if freq <= 0:
                if current_note is not None:
                    current_note['end_frame'] = i
                    current_note['duration'] = (i - current_note['start_frame']) * self.hop_length / self.sr
                    notes.append(current_note)
                    current_note = None
            else:
                midi = A4_midi + 12 * np.log2(freq / A4_freq)
                midi_rounded = round(midi)
                
                if current_note is None or current_note['midi'] != midi_rounded:
                    if current_note is not None:
                        current_note['end_frame'] = i
                        current_note['duration'] = (i - current_note['start_frame']) * self.hop_length / self.sr
                        notes.append(current_note)
                    
                    current_note = {
                        'start_frame': i,
                        'midi': midi_rounded,
                        'freq': freq
                    }
        
        if current_note is not None:
            current_note['end_frame'] = len(frequencies)
            current_note['duration'] = (len(frequencies) - current_note['start_frame']) * self.hop_length / self.sr
            notes.append(current_note)
        
        return notes
    
    def save_midi_multitrack(self, output_path: str = None):
        """
        保存为多轨 MIDI 文件
        
        Args:
            output_path: 输出文件路径
        """
        if self.voices is None or len(self.voices) == 0:
            logger.warning("没有声部，无法生成 MIDI")
            return
        
        try:
            from music21 import stream, note, instrument, midi
        except ImportError:
            logger.error("需要安装 music21: pip install music21")
            return
        
        logger.info(f"生成多轨 MIDI 文件: {output_path}")
        
        # 创建乐谱
        s = stream.Score()
        
        # 乐器列表
        instruments_list = [
            instrument.Flute(),
            instrument.Violin(),
            instrument.fromString("cello"),
            instrument.Contrabass()
        ]
        
        # 为每个声部创建 part
        for voice_idx, voice_notes in enumerate(self.voices):
            part = stream.Part()
            part.instrument = instruments_list[voice_idx % len(instruments_list)]
            
            for note_info in voice_notes:
                midi_num = note_info['midi']
                duration = note_info.get('duration', 0.5)
                
                # 音符时值
                if duration < 0.25:
                    quarter_length = 0.25
                elif duration < 0.5:
                    quarter_length = 0.5
                elif duration < 1:
                    quarter_length = 1
                else:
                    quarter_length = duration
                
                n = note.Note(midi=midi_num)
                n.quarterLength = quarter_length
                part.append(n)
            
            s.append(part)
        
        # 保存文件
        if output_path:
            s.write('midi', fp=output_path)
            logger.info(f"MIDI 文件已保存: {output_path}")
        
        return s
    
    def extract_chords(self, audio_path: str) -> Dict:
        """提取和弦"""
        return self.transcribe(audio_path)
    
    def transcribe(self, audio_path: str, n_voices: int = 2) -> Dict:
        """
        完整的多声部扒谱流程
        
        Args:
            audio_path: 音频文件路径
            n_voices: 预期的声部数量
        
        Returns:
            扒谱结果
        """
        try:
            # 1. 加载音频
            self.load_audio(audio_path)
            
            # 2. HPSS 分离
            self.separate_harmonic_percussive()
            
            # 3. 提取多条旋律
            self.extract_multiple_melodies(n_voices=n_voices)
            
            # 5. 返回结果
            result = {
                'voices': self.voices,
                'total_voices': len(self.voices),
                'duration_sec': len(self.audio) / self.sr
            }
            
            logger.info(f"多声部扒谱完成: {result['total_voices']} 个声部")
            return result
        
        except Exception as e:
            logger.error(f"多声部扒谱失败: {e}")
            raise
    
    def save_midi(self, output_path: str = None):
        """保存 MIDI（兼容接口）"""
        return self.save_midi_multitrack(output_path)
    
    def get_visualization_data(self) -> Dict:
        """获取可视化数据"""
        return {
            'voices': self.voices,
            'harmonic_spectrogram': self.harmonic.tolist() if self.harmonic is not None else None,
            'percussive_spectrogram': self.percussive.tolist() if self.percussive is not None else None
        }


# 和弦类型映射
CHORD_TYPES = {
    # 大三和弦
    (0, 4, 7): 'C',
    (0, 4, 7, 11): 'CMaj7',
    (0, 4, 7, 10): 'C7',
    (0, 4, 7, 14): 'C9',
    # 小三和弦
    (0, 3, 7): 'Dm',
    (0, 3, 7, 10): 'Dm7',
    (0, 3, 7, 11): 'DmMaj7',
    # 其他常用和弦
    (0, 5, 7): 'G',
    (0, 5, 7, 10): 'G7',
    (0, 5, 7, 11): 'GMaj7',
    (0, 7, 12): 'G',
    (0, 7, 14): 'G9',
    (0, 4, 6): 'Bb',
    (0, 3, 6): 'Bdim',
    (0, 4, 5): 'F',
    (0, 3, 5): 'Am',
    (0, 4, 9): 'Em',
    (0, 5, 9): 'B',
}

def _get_chord_name(pitches):
    """根据音程获取和弦名称"""
    if not pitches or len(pitches) < 2:
        return None
    
    # 计算相对于根音的音程
    root = min(pitches)
    intervals = tuple(sorted([p - root for p in pitches if p > root]))
    
    # 精确匹配
    if intervals in CHORD_TYPES:
        return CHORD_TYPES[intervals]
    
    # 近似匹配
    for chord_intervals, name in CHORD_TYPES.items():
        if len(chord_intervals) == len(intervals):
            diff = sum(1 for a, b in zip(chord_intervals, intervals) if abs(a - b) <= 1)
            if diff >= len(intervals) * 0.7:
                return name
    
    return 'X'

def _analyze_chords(self, midi_notes):
    """分析和弦类型"""
    chords = []
    
    # 按时间窗口分组
    window_size = 22050 * 4  # 约4秒窗口
    
    for i in range(0, len(midi_notes), window_size):
        window = midi_notes[i:i+window_size]
        if not window:
            continue
        
        # 获取窗口内的音高
        pitches = [n.get('midi') for n in window if n.get('midi')]
        if len(pitches) >= 3:
            chord_name = _get_chord_name(pitches)
            if chord_name:
                chords.append({
                    'chord': chord_name,
                    'start': i / self.sr,
                    'duration': window_size / self.sr
                })
    
    return chords
