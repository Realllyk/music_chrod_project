"""旋律 MIDI 结构化分析服务"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np


KRUMHANSL_MAJOR_PROFILE = np.array([
    6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
    2.52, 5.19, 2.39, 3.66, 2.29, 2.88,
], dtype=float)

KRUMHANSL_MINOR_PROFILE = np.array([
    6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
    2.54, 4.75, 3.98, 2.69, 3.34, 3.17,
], dtype=float)

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
DEGREE_MAP_MAJOR = {
    0: '1', 1: '#1', 2: '2', 3: '#2', 4: '3', 5: '4',
    6: '#4', 7: '5', 8: '#5', 9: '6', 10: '#6', 11: '7',
}
DEGREE_MAP_MINOR = {
    0: '1', 1: '#1', 2: '2', 3: 'b3', 4: '3', 5: '4',
    6: '#4', 7: '5', 8: 'b6', 9: '6', 10: 'b7', 11: '7',
}


class MelodyAnalysisService:
    @staticmethod
    def build_melody_analysis(midi_path: str) -> Dict:
        try:
            import pretty_midi
        except ImportError as exc:
            raise RuntimeError('pretty_midi is required for melody analysis') from exc

        if not midi_path:
            raise ValueError('midi_path is required')

        midi = pretty_midi.PrettyMIDI(midi_path)
        notes = MelodyAnalysisService._collect_notes(midi)
        tonic_pc, mode, confidence = MelodyAnalysisService._detect_key(notes)
        tonic_name = NOTE_NAMES[tonic_pc]
        time_signature = MelodyAnalysisService._detect_time_signature(midi)
        tempo_bpm = MelodyAnalysisService._detect_tempo(midi)
        duration_sec = float(midi.get_end_time() or 0.0)
        notation_notes = MelodyAnalysisService._build_notation_notes(
            notes=notes,
            tonic_pc=tonic_pc,
            mode=mode,
            tempo_bpm=tempo_bpm,
        )
        measures = MelodyAnalysisService._build_measures(
            notation_notes=notation_notes,
            tempo_bpm=tempo_bpm,
            time_signature=time_signature,
        )

        return {
            'type': 'melody',
            'midi_path': midi_path,
            'key': {
                'tonic': tonic_name,
                'mode': mode,
                'display': f'{tonic_name} {mode}',
                'confidence': round(confidence, 4),
            },
            'time_signature': time_signature,
            'tempo': {
                'bpm': round(tempo_bpm, 3),
            },
            'duration': {
                'seconds': round(duration_sec, 3),
            },
            'notation': {
                'mode': 'numbered',
                'notes': notation_notes,
                'measures': measures,
            },
        }

    @staticmethod
    def _collect_notes(midi) -> List:
        notes = []
        for instrument in midi.instruments:
            notes.extend(instrument.notes)
        return sorted(notes, key=lambda item: (item.start, item.pitch, item.end))

    @staticmethod
    def _detect_key(notes: List) -> Tuple[int, str, float]:
        if not notes:
            return 0, 'major', 0.0

        histogram = np.zeros(12, dtype=float)
        for note in notes:
            duration = max(float(note.end - note.start), 0.0)
            weight = duration if duration > 0 else 1e-6
            histogram[int(note.pitch) % 12] += weight

        if float(histogram.sum()) <= 0:
            return 0, 'major', 0.0

        best_score = -2.0
        second_score = -2.0
        best_pc = 0
        best_mode = 'major'

        for tonic in range(12):
            major_score = MelodyAnalysisService._safe_corrcoef(histogram, np.roll(KRUMHANSL_MAJOR_PROFILE, tonic))
            minor_score = MelodyAnalysisService._safe_corrcoef(histogram, np.roll(KRUMHANSL_MINOR_PROFILE, tonic))
            for mode, score in [('major', major_score), ('minor', minor_score)]:
                if score > best_score:
                    second_score = best_score
                    best_score = score
                    best_pc = tonic
                    best_mode = mode
                elif score > second_score:
                    second_score = score

        confidence = max(0.0, min(1.0, (best_score + 1.0) / 2.0))
        if second_score > -2.0:
            confidence = max(confidence, min(1.0, max(0.0, best_score - second_score)))
        return best_pc, best_mode, confidence

    @staticmethod
    def _safe_corrcoef(left: np.ndarray, right: np.ndarray) -> float:
        if np.allclose(left.std(), 0) or np.allclose(right.std(), 0):
            return -1.0
        return float(np.corrcoef(left, right)[0, 1])

    @staticmethod
    def _detect_time_signature(midi) -> Dict:
        changes = getattr(midi, 'time_signature_changes', None) or []
        if changes:
            ts = changes[0]
            return {
                'numerator': int(ts.numerator),
                'denominator': int(ts.denominator),
                'source': 'midi',
            }
        return {
            'numerator': 4,
            'denominator': 4,
            'source': 'midi_default',
        }

    @staticmethod
    def _detect_tempo(midi) -> float:
        try:
            tempo_times, tempi = midi.get_tempo_changes()
            if len(tempi) > 0:
                return float(tempi[0])
        except Exception:
            pass
        estimate = midi.estimate_tempo()
        return float(estimate or 120.0)

    @staticmethod
    def _build_notation_notes(notes: List, tonic_pc: int, mode: str, tempo_bpm: float) -> List[Dict]:
        """把 MIDI note 列表转换成简谱渲染所需的结构化数据。

        简谱的基本写法：
          - 每个音用 1~7 表示「相对调性主音的级数」，可能带 # / b
          - 数字头上加点 = 高八度；数字脚下加点 = 低八度；不加点 = 中央八度
          - 每个音还要给出时长（秒 / 拍），用于渲染与播放

        参数：
            notes:     已按 start 排序的 MIDI note 对象（pretty_midi.Note）
            tonic_pc:  调性主音的「音级」（pitch class），0=C、1=C#、…、9=A、11=B。
                       只表示主音是哪个音名，不带八度。
            mode:      'major' / 'minor'，决定级数到半音的映射表
            tempo_bpm: BPM，用来把秒换算成拍

        返回：每个音符的 dict 列表，字段含 degree / octave_offset / midi / 时长等。
        """
        # 按大调 / 小调选择「相对主音的半音差 -> 级数数字」映射表
        degree_map = DEGREE_MAP_MINOR if mode == 'minor' else DEGREE_MAP_MAJOR

        # tonic_reference_midi：把抽象的 tonic_pc（不带八度）锚定到一个具体的 MIDI 号，
        # 作为判定「中央八度」的参考点。
        #   - MIDI 协议里 C4 = 60，每升 12 表示升一个八度
        #   - 60 + tonic_pc 得到「以 C4 那一组为基准八度」的主音 MIDI
        #     例：C 大调 -> 60 (C4)、A 小调 -> 69 (A4)
        #   - 随后每个音符与它相除，得到相对这个基准偏了几个八度
        tonic_reference_midi = 60 + tonic_pc

        # 一拍的时长（秒）= 60 / BPM；BPM 异常时用 0.5s 兜底（相当于 120 BPM）
        beat_duration = 60.0 / tempo_bpm if tempo_bpm and tempo_bpm > 0 else 0.5

        serialized = []
        for index, note in enumerate(notes):
            start = float(note.start)
            end = float(note.end)
            duration = max(end - start, 0.0)

            # midi_pitch：当前音符的 MIDI 音高号（0~127），如 C4=60、G4=67、C5=72
            midi_pitch = int(note.pitch)

            # delta：当前音符相对主音的半音差，压回 [0, 11) 内（忽略八度）
            # 查 degree_map 即得简谱级数：C 大调里 C=1 / D=2 / … / B=7
            delta = (midi_pitch - tonic_pc) % 12

            # octave_offset：当前音符相对「中央八度」偏了几个八度
            #   0  = 中央八度（数字不加点）
            #   +1 = 高一个八度（数字头上加一个点）
            #   -1 = 低一个八度（数字脚下加一个点）
            # 用 floor division 而非 round()：简谱的「中央八度」是半开区间
            # [tonic_reference_midi, tonic_reference_midi + 12)，凡落入此区间的音
            # octave_offset 都应为 0，而 round() 会把相差 7~11 个半音的音
            # （例如 C 大调里的 G4、B4）错误抛到高一个八度。
            octave_offset = (int(midi_pitch) - int(tonic_reference_midi)) // 12

            serialized.append({
                'index': index,
                'start': round(start, 4),
                'end': round(end, 4),
                'midi': midi_pitch,
                'pitch_name': MelodyAnalysisService._pitch_name(midi_pitch),
                'degree': degree_map.get(delta, '?'),
                'octave_offset': octave_offset,
                'duration_seconds': round(duration, 4),
                'duration_beats': round(duration / beat_duration, 4) if beat_duration > 0 else 0.0,
            })
        return serialized

    @staticmethod
    def _build_measures(notation_notes: List[Dict], tempo_bpm: float, time_signature: Dict) -> List[Dict]:
        if not notation_notes:
            return []

        numerator = int(time_signature.get('numerator') or 4)
        denominator = int(time_signature.get('denominator') or 4)
        beat_duration = 60.0 / tempo_bpm if tempo_bpm and tempo_bpm > 0 else 0.5
        measure_duration = numerator * beat_duration * (4.0 / denominator)
        if measure_duration <= 0:
            measure_duration = 2.0

        buckets: Dict[int, Dict] = {}
        for note in notation_notes:
            measure_index = int(math.floor(note['start'] / measure_duration))
            bucket = buckets.setdefault(measure_index, {
                'index': measure_index,
                'start': round(measure_index * measure_duration, 4),
                'end': round((measure_index + 1) * measure_duration, 4),
                'degrees': [],
                'notes': [],
            })
            bucket['degrees'].append(note['degree'])
            bucket['notes'].append(note['index'])

        return [buckets[index] for index in sorted(buckets.keys())]

    @staticmethod
    def _pitch_name(midi_pitch: int) -> Optional[str]:
        try:
            import pretty_midi
            return pretty_midi.note_number_to_name(int(midi_pitch))
        except Exception:
            octave = midi_pitch // 12 - 1
            return f"{NOTE_NAMES[midi_pitch % 12]}{octave}"
