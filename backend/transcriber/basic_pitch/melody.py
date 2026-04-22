"""
基于 Spotify basic-pitch 的单旋律提取 backend

职责：
1. 接收已经分离好的人声音频（也可直接接受原始混音）
2. 调用 basic-pitch 做音符级推理
3. 把 basic-pitch 的原始输出转换成项目内部统一的 notes dict 结构
4. 生成 MIDI 并提供可视化所需的数据

设计目标：
- 与 LibrosaMelodyTranscriber 的输出结构保持一致
- 让上层代码在切换 backend 时尽量无感
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

import pretty_midi

from transcriber.base import MelodyTranscriberBase

logger = logging.getLogger(__name__)


class BasicPitchMelodyTranscriber(MelodyTranscriberBase):
    """基于 basic-pitch 的单旋律提取器。"""

    @property
    def name(self) -> str:
        return "basic_pitch"

    def __init__(self, sr: int = 22050, hop_length: int = 512):
        # 采样率与 hop_length 保持与现有旋律提取链路一致，
        # 这样 start_frame / end_frame 的语义能与现有系统对齐。
        self.sr = sr
        self.hop_length = hop_length

        # 输入音频路径，仅用于记录当前正在处理的文件。
        self.audio_path = None

        # 项目统一的音符输出结构。
        # 每个元素是一个 dict，包含 midi / start_frame / end_frame / duration / freq / confidence。
        self.notes = None

        # basic-pitch 原生返回的 pretty_midi 对象，便于调试和对照。
        self.midi_data = None

        # basic-pitch 原始 note_events，用于排查模型原始输出。
        self.raw_note_events = None

        # 输出 MIDI 时使用的 tempo。
        self.tempo = None

        # 读取 basic-pitch 专属配置。
        self.config = self._load_basic_pitch_config()
        self.onset_threshold = self.config.get('onset_threshold', 0.5)
        self.frame_threshold = self.config.get('frame_threshold', 0.3)
        self.minimum_note_length_ms = self.config.get('minimum_note_length_ms', 127.7)
        self.minimum_frequency = self.config.get('minimum_frequency', 65.0)
        self.maximum_frequency = self.config.get('maximum_frequency', 1100.0)

        # melody_only=True 表示：如果同一时刻出现多个重叠音符，
        # 会通过后处理只保留一个“主旋律音”。
        self.melody_only = self.config.get('melody_only', True)

        # basic-pitch 本身不做 BPM 检测，这里使用配置中的默认 tempo。
        self.midi_tempo = self.config.get('midi_tempo', 120)

    def _load_basic_pitch_config(self) -> Dict:
        """读取 config.json 中 transcription.basic_pitch 配置。"""
        config_path = Path(__file__).resolve().parents[2] / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('transcription', {}).get('basic_pitch', {})

    def extract_melody(self, audio_path: str) -> Dict:
        """对外统一入口，保持与其他 backend 的调用方式一致。"""
        return self.transcribe(audio_path)

    def transcribe(self, audio_path: str) -> Dict:
        """执行 basic-pitch 推理，并转换为项目内部统一结构。"""
        try:
            from basic_pitch import ICASSP_2022_MODEL_PATH
            from basic_pitch.inference import predict
        except ImportError as e:
            raise RuntimeError(
                'basic-pitch 未安装。请在主环境执行：pip install basic-pitch onnxruntime'
            ) from e

        self.audio_path = audio_path
        logger.info(
            f"使用 basic-pitch 提取旋律... onset_threshold={self.onset_threshold}, "
            f"frame_threshold={self.frame_threshold}, min_note_length={self.minimum_note_length_ms}ms, "
            f"melody_only={self.melody_only}"
        )

        try:
            # basic-pitch 的核心推理入口。
            # 返回：模型原始输出、pretty_midi 对象、note_events 列表。
            model_output, midi_data, note_events = predict(
                audio_path,
                ICASSP_2022_MODEL_PATH,
                onset_threshold=self.onset_threshold,
                frame_threshold=self.frame_threshold,
                minimum_note_length=self.minimum_note_length_ms,
                minimum_frequency=self.minimum_frequency,
                maximum_frequency=self.maximum_frequency,
            )
        except Exception as e:
            logger.error(f"basic-pitch 推理失败: {e}")
            raise

        self.midi_data = midi_data
        self.raw_note_events = note_events
        logger.info(f"basic-pitch 原始音符数: {len(note_events)}")

        # 第一步：把 basic-pitch 原始 note_events 转换成项目统一 notes 结构。
        notes = self._convert_note_events(note_events)

        # 第二步：如果要求单旋律，则做一次“重叠音去多留一”的后处理。
        if self.melody_only:
            notes = self._filter_melody_only(notes)

        # 第三步：排序并去掉完全重复的音符。
        notes = self._dedup_and_sort(notes)

        self.notes = notes
        self.tempo = float(self.midi_tempo)
        logger.info(f"basic-pitch 最终音符数: {len(notes)}")
        return self.notes_to_dict()

    def _convert_note_events(self, note_events) -> List[Dict]:
        """将 basic-pitch 原始 note_events 转成项目统一的 notes dict。

        basic-pitch 的 note_events 每个元素通常为：
            (start_time_s, end_time_s, pitch_midi, amplitude, pitch_bends)

        这里会把它映射成系统统一格式：
        - midi: MIDI 音高号
        - start_frame / end_frame: 按当前 hop_length 计算出的帧位置
        - duration: 秒级时长
        - freq: 对应频率（Hz）
        - confidence: 这里使用 amplitude 近似表示置信度 / 强度
        """
        notes = []
        for event in note_events:
            start_time, end_time, pitch_midi, amplitude, _ = event
            if end_time <= start_time:
                continue

            duration = float(end_time - start_time)
            start_frame = int(round(start_time * self.sr / self.hop_length))
            end_frame = int(round(end_time * self.sr / self.hop_length))

            # MIDI 音高转频率：A4=440Hz, MIDI=69。
            freq = 440.0 * (2 ** ((int(pitch_midi) - 69) / 12.0))

            notes.append({
                'midi': int(pitch_midi),
                'start_frame': start_frame,
                'end_frame': end_frame,
                'duration': duration,
                'freq': float(freq),
                'confidence': float(amplitude),
            })
        return notes

    def _filter_melody_only(self, notes: List[Dict]) -> List[Dict]:
        """把多音输出压缩成单旋律。

        basic-pitch 本质上是多音模型，同一时刻可能识别出多个重叠音。
        而当前项目目标是“主旋律”，所以这里做一个贪心后处理：

        - 如果两个音符不重叠：都保留
        - 如果重叠：优先保留 confidence（amplitude）更高的那个
        - 如果后来的音更强，会把前一个音的尾部裁剪到新音起点

        这是启发式策略，不是严格的音乐理论规则，但足以用于当前单旋律场景。
        """
        if not notes:
            return []

        # 先按起始帧排序；如果同起点，则把 confidence 更高的排前面。
        sorted_notes = sorted(notes, key=lambda n: (n['start_frame'], -n['confidence']))
        kept: List[Dict] = []

        for note in sorted_notes:
            if not kept:
                kept.append(note.copy())
                continue

            last = kept[-1]
            overlap = note['start_frame'] < last['end_frame']

            # 不重叠则直接保留。
            if not overlap:
                kept.append(note.copy())
                continue

            # 重叠时，如果当前音更“强”，则尝试让它替换前一个音的后半段。
            if note['confidence'] > last['confidence']:
                last_new_end = note['start_frame']
                last_new_duration = (last_new_end - last['start_frame']) * self.hop_length / self.sr

                # 如果裁剪后的前一个音仍有足够长度，则保留缩短后的版本；
                # 否则直接丢弃前一个音。
                if last_new_duration >= (self.minimum_note_length_ms / 1000.0):
                    last['end_frame'] = last_new_end
                    last['duration'] = last_new_duration
                else:
                    kept.pop()

                kept.append(note.copy())
            else:
                # 当前音更弱，则认为它更可能是伴随音或次要音，直接丢弃。
                continue

        return kept

    def _dedup_and_sort(self, notes: List[Dict]) -> List[Dict]:
        """排序并去重。

        去重规则：
        - start_frame
        - end_frame
        - midi

        三者完全相同则视为重复音符。
        """
        seen = set()
        deduped = []
        for note in sorted(notes, key=lambda n: (n['start_frame'], n['midi'])):
            key = (note['start_frame'], note['end_frame'], note['midi'])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(note)
        return deduped

    def notes_to_dict(self) -> Dict:
        """转换成项目统一的返回结构。"""
        if self.notes is None:
            return {}

        total_duration = 0.0
        if self.notes:
            last = self.notes[-1]
            total_duration = (last['start_frame'] * self.hop_length / self.sr) + last['duration']

        return {
            'notes': self.notes,
            'total_notes': len(self.notes),
            'duration_sec': total_duration,
        }

    def save_midi(self, output_path: str = None):
        """根据 self.notes 重新构建并保存 MIDI。

        这里不直接复用 basic-pitch 原始返回的 midi_data，
        而是用当前 self.notes 重新构建 pretty_midi，原因是：
        - self.notes 可能已经经过 melody_only 后处理
        - 这样写出的 MIDI 才与最终输出结果保持一致
        """
        if self.notes is None or len(self.notes) == 0:
            logger.warning('没有音符，无法生成 MIDI')
            return None

        midi = pretty_midi.PrettyMIDI(initial_tempo=float(self.tempo or 120))
        midi.time_signature_changes.append(pretty_midi.TimeSignature(4, 4, 0))
        instrument = pretty_midi.Instrument(program=0, name='Melody')

        for note_info in self.notes:
            start_time = note_info['start_frame'] * self.hop_length / self.sr
            end_time = start_time + note_info['duration']
            if end_time <= start_time:
                continue

            # confidence 这里映射到 MIDI velocity，范围压到 1~127。
            midi_note = pretty_midi.Note(
                velocity=min(127, max(1, int(note_info['confidence'] * 127))),
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

    def get_visualization_data(self) -> Dict:
        """构造与现有前端兼容的可视化数据。

        basic-pitch 本身不是直接返回帧级 pitch 曲线，
        所以这里按最终 notes 反推出一条“阶梯状”的 pitch / midi 曲线，
        用于兼容现有可视化字段。
        """
        if self.notes is None:
            return {}

        max_end_frame = max((n['end_frame'] for n in self.notes), default=0)
        pitch_curve: List[float] = [0.0] * max_end_frame
        midi_curve: List = [None] * max_end_frame
        confidence: List[float] = [0.0] * max_end_frame

        for note in self.notes:
            for frame in range(note['start_frame'], min(note['end_frame'], max_end_frame)):
                pitch_curve[frame] = note['freq']
                midi_curve[frame] = note['midi']
                confidence[frame] = note['confidence']

        return {
            'pitch_curve': pitch_curve,
            'midi_curve': midi_curve,
            'confidence': confidence,
            'onset_frames': [n['start_frame'] for n in self.notes],
            'notes': self.notes,
        }
