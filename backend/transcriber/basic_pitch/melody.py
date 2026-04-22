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

        # basic-pitch 默认 tempo 及可选 BPM 检测能力。
        self.midi_tempo = float(self.config.get('midi_tempo', 120))
        self.detect_tempo = self.config.get('detect_tempo', True)
        self.tempo_min = float(self.config.get('tempo_min', 60))
        self.tempo_max = float(self.config.get('tempo_max', 200))

        # MIDI 力度归一化范围。
        self.velocity_min = int(self.config.get('velocity_min', 50))
        self.velocity_max = int(self.config.get('velocity_max', 120))

        # 扫描线阶段的宽松预过滤阈值：比 minimum_note_length_ms 小，
        # 让尾音碎片有机会进入后续的 gap-merge，而不是在此阶段被整批丢弃。
        self.prefilter_min_ms = float(self.config.get('prefilter_min_ms', 40))

        # 同 midi、小 gap 合并的最大可容忍间隙。
        self.same_pitch_gap_ms = float(self.config.get('same_pitch_gap_ms', 50))

        # 转音（melisma）装饰音吸收的参数。
        self.melisma_merge_enabled = bool(self.config.get('melisma_merge_enabled', True))
        self.melisma_short_ms = float(self.config.get('melisma_short_ms', 120))
        self.melisma_gap_ms = float(self.config.get('melisma_gap_ms', 30))
        self.melisma_semitone_window = int(self.config.get('melisma_semitone_window', 1))

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

        # 第二步：如果要求单旋律，做扫描线去重叠。
        # 注意：此处只按 prefilter_min_ms 做宽松过滤，尾音碎片会被保留到后续合并阶段。
        if self.melody_only:
            notes = self._filter_melody_only(notes)

        # 第三步：尾音保留 —— 合并同 midi 且小 gap 的相邻段。
        notes = self._merge_same_pitch_gap(notes)

        # 第四步：转音合并 —— 短小音程装饰音吸收到相邻主音。
        notes = self._merge_melisma(notes)

        # 第五步：再次合并同 midi —— 因上一步改写 midi 后可能形成新的同 midi 相邻段。
        notes = self._merge_same_pitch_gap(notes)

        # 第六步：最终按 minimum_note_length_ms 过滤掉仍然过短的音符。
        notes = self._apply_min_length(notes)

        # 第七步：排序并去掉完全重复的音符。
        notes = self._dedup_and_sort(notes)

        # 第八步：按当前歌曲内相对强度归一化 velocity。
        notes = self._normalize_velocities(notes)

        self.notes = notes

        if self.detect_tempo:
            try:
                self.tempo = self._detect_tempo(audio_path)
            except Exception as e:
                logger.warning(f"BPM 检测失败，回退到固定 {self.midi_tempo}: {e}")
                self.tempo = float(self.midi_tempo)
        else:
            self.tempo = float(self.midi_tempo)

        logger.info(f"basic-pitch 最终音符数: {len(notes)}, tempo={self.tempo}")
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

        采用边界区间法：
        - 收集所有音符的 start/end 作为边界
        - 在每个基础区间内选择置信度最高的音符
        - 再合并相邻且 MIDI 相同的区间

        这样可以避免“低置信度音符和高置信度音符部分重叠时被整段误丢弃”的问题。
        """
        if not notes:
            return []

        boundaries = sorted({
            frame
            for note in notes
            for frame in (note['start_frame'], note['end_frame'])
        })
        if len(boundaries) < 2:
            return self._dedup_and_sort([note.copy() for note in notes])

        intervals = []
        for start_frame, end_frame in zip(boundaries[:-1], boundaries[1:]):
            if end_frame <= start_frame:
                continue

            active_notes = [
                note for note in notes
                if note['start_frame'] <= start_frame and note['end_frame'] >= end_frame
            ]
            if not active_notes:
                continue

            winner = max(active_notes, key=lambda note: note['confidence'])
            intervals.append({
                'midi': int(winner['midi']),
                'start_frame': int(start_frame),
                'end_frame': int(end_frame),
                'freq': float(winner['freq']),
                'confidence': float(winner['confidence']),
            })

        if not intervals:
            return []

        merged: List[Dict] = []
        for interval in intervals:
            if (
                merged
                and merged[-1]['midi'] == interval['midi']
                and merged[-1]['end_frame'] == interval['start_frame']
            ):
                merged[-1]['end_frame'] = interval['end_frame']
                merged[-1]['confidence'] = max(merged[-1]['confidence'], interval['confidence'])
            else:
                merged.append(interval.copy())

        # 这里使用较宽松的 prefilter 阈值，只过滤掉扫描线产生的极碎片段。
        # 真正按 minimum_note_length_ms 的最终过滤延迟到 gap-merge / 转音合并之后。
        min_frames = int(round((self.prefilter_min_ms / 1000.0) * self.sr / self.hop_length))
        min_frames = max(min_frames, 1)

        filtered = []
        for note in merged:
            frame_count = note['end_frame'] - note['start_frame']
            if frame_count < min_frames:
                continue

            duration = frame_count * self.hop_length / self.sr
            filtered.append({
                'midi': int(note['midi']),
                'start_frame': int(note['start_frame']),
                'end_frame': int(note['end_frame']),
                'duration': float(duration),
                'freq': float(note['freq']),
                'confidence': float(note['confidence']),
            })

        return filtered

    def _merge_same_pitch_gap(self, notes: List[Dict]) -> List[Dict]:
        """合并 midi 相同且时间间隙不超过阈值的相邻段。

        用途：
        - 尾音衰减被 basic-pitch 切成一串同 midi 的短碎片时，把它们重新粘回完整一段
        - 也用作 _merge_melisma 之后的收尾：转音装饰音的 midi 被改写为主音后，
          相邻段出现同 midi，再做一次合并即可形成连贯主音
        """
        if len(notes) < 2:
            return [note.copy() for note in notes]

        gap_frames = int(round((self.same_pitch_gap_ms / 1000.0) * self.sr / self.hop_length))
        sorted_notes = sorted([note.copy() for note in notes], key=lambda n: n['start_frame'])

        merged: List[Dict] = []
        for cur in sorted_notes:
            if (
                merged
                and merged[-1]['midi'] == cur['midi']
                and 0 <= cur['start_frame'] - merged[-1]['end_frame'] <= gap_frames
            ):
                prev = merged[-1]
                prev['end_frame'] = max(prev['end_frame'], cur['end_frame'])
                prev['confidence'] = float(max(prev['confidence'], cur['confidence']))
                prev['duration'] = (prev['end_frame'] - prev['start_frame']) * self.hop_length / self.sr
            else:
                merged.append(cur)
        return merged

    def _merge_melisma(self, notes: List[Dict]) -> List[Dict]:
        """把转音段内的短小音程装饰音吸收到相邻主音。

        策略：
        - 只改写短音的 midi/freq/confidence，不合并、不删除
        - 合并交给随后 _merge_same_pitch_gap 统一处理

        吸收条件（需全部满足）：
        - 当前音 duration < melisma_short_ms
        - 与左邻或右邻的 gap ≤ melisma_gap_ms
        - 与该邻音的 |Δmidi| ≤ melisma_semitone_window
        - 邻音本身足够长（视 duration 判定 anchor）
        """
        if len(notes) < 2 or not self.melisma_merge_enabled:
            return [note.copy() for note in notes]

        short_frames = int(round((self.melisma_short_ms / 1000.0) * self.sr / self.hop_length))
        gap_frames = int(round((self.melisma_gap_ms / 1000.0) * self.sr / self.hop_length))
        semitone = int(self.melisma_semitone_window)

        sorted_notes = sorted([note.copy() for note in notes], key=lambda n: n['start_frame'])

        for i, cur in enumerate(sorted_notes):
            cur_frames = cur['end_frame'] - cur['start_frame']
            if cur_frames >= short_frames:
                continue

            candidates = []
            if i > 0:
                left = sorted_notes[i - 1]
                gap_l = cur['start_frame'] - left['end_frame']
                if 0 <= gap_l <= gap_frames and abs(int(cur['midi']) - int(left['midi'])) <= semitone:
                    candidates.append(left)
            if i < len(sorted_notes) - 1:
                right = sorted_notes[i + 1]
                gap_r = right['start_frame'] - cur['end_frame']
                if 0 <= gap_r <= gap_frames and abs(int(cur['midi']) - int(right['midi'])) <= semitone:
                    candidates.append(right)

            if not candidates:
                continue

            # anchor 选择：持续时间更长的邻音
            anchor = max(candidates, key=lambda n: n['end_frame'] - n['start_frame'])
            # 仅吸收到“比自己更长”的 anchor，避免两个都很短的音互相改写
            if (anchor['end_frame'] - anchor['start_frame']) <= cur_frames:
                continue

            cur['midi'] = int(anchor['midi'])
            cur['freq'] = float(anchor['freq'])
            cur['confidence'] = float(max(cur['confidence'], anchor['confidence']))

        return sorted_notes

    def _apply_min_length(self, notes: List[Dict]) -> List[Dict]:
        """按 minimum_note_length_ms 做最终最小长度过滤。

        位置：gap-merge 与转音合并之后，确保被合并的尾音碎片不会被错误丢弃，
        同时仍然剔除合并后依旧过短的杂音。
        """
        min_frames = int(round((self.minimum_note_length_ms / 1000.0) * self.sr / self.hop_length))
        min_frames = max(min_frames, 1)
        return [n for n in notes if (n['end_frame'] - n['start_frame']) >= min_frames]

    def _detect_tempo(self, audio_path: str) -> float:
        """检测输入音频的 BPM，失败由调用方负责兜底。"""
        import librosa

        y, sr = librosa.load(audio_path, sr=self.sr, mono=True)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=self.hop_length)

        if hasattr(tempo, '__len__'):
            tempo = float(tempo[0]) if len(tempo) else float(self.midi_tempo)
        tempo = float(tempo) if tempo else float(self.midi_tempo)

        if tempo < self.tempo_min:
            doubled = tempo * 2
            if doubled <= self.tempo_max:
                tempo = doubled
        elif tempo > self.tempo_max:
            halved = tempo / 2
            if halved >= self.tempo_min:
                tempo = halved

        return float(min(max(tempo, self.tempo_min), self.tempo_max))

    def _normalize_velocities(self, notes: List[Dict]) -> List[Dict]:
        """按当前歌曲内的相对强度归一化 MIDI velocity。"""
        if not notes:
            return notes

        velocity_min = max(1, min(int(self.velocity_min), 127))
        velocity_max = max(1, min(int(self.velocity_max), 127))
        if velocity_max < velocity_min:
            velocity_min, velocity_max = velocity_max, velocity_min

        confidences = [float(note.get('confidence', 0.0)) for note in notes]
        conf_min = min(confidences)
        conf_max = max(confidences)

        if conf_max - conf_min < 1e-6:
            fallback_velocity = int(round((velocity_min + velocity_max) / 2))
            for note in notes:
                note['velocity'] = fallback_velocity
            return notes

        for note in notes:
            ratio = (float(note.get('confidence', 0.0)) - conf_min) / (conf_max - conf_min)
            note['velocity'] = int(round(velocity_min + ratio * (velocity_max - velocity_min)))
        return notes

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

        midi = pretty_midi.PrettyMIDI(initial_tempo=float(self.tempo or self.midi_tempo or 120))
        midi.time_signature_changes.append(pretty_midi.TimeSignature(4, 4, 0))
        instrument = pretty_midi.Instrument(program=0, name='Melody')

        for note_info in self.notes:
            start_time = note_info['start_frame'] * self.hop_length / self.sr
            end_time = start_time + note_info['duration']
            if end_time <= start_time:
                continue

            midi_note = pretty_midi.Note(
                velocity=min(127, max(1, int(note_info.get('velocity', 90)))),
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
