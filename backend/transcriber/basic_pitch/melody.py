"""
基于 Spotify basic-pitch 的单旋律提取 backend
- 输入：已经分离好的人声音频（也可接受原始混音）
- 输出：与 LibrosaMelodyTranscriber 一致的 notes dict schema
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

import pretty_midi

from transcriber.base import MelodyTranscriberBase

logger = logging.getLogger(__name__)


class BasicPitchMelodyTranscriber(MelodyTranscriberBase):
    """基于 basic-pitch 的单旋律提取器"""

    @property
    def name(self) -> str:
        return "basic_pitch"

    def __init__(self, sr: int = 22050, hop_length: int = 512):
        self.sr = sr
        self.hop_length = hop_length
        self.audio_path = None
        self.notes = None
        self.midi_data = None
        self.raw_note_events = None
        self.tempo = None

        self.config = self._load_basic_pitch_config()
        self.onset_threshold = self.config.get('onset_threshold', 0.5)
        self.frame_threshold = self.config.get('frame_threshold', 0.3)
        self.minimum_note_length_ms = self.config.get('minimum_note_length_ms', 127.7)
        self.minimum_frequency = self.config.get('minimum_frequency', 65.0)
        self.maximum_frequency = self.config.get('maximum_frequency', 1100.0)
        self.melody_only = self.config.get('melody_only', True)
        self.midi_tempo = self.config.get('midi_tempo', 120)

    def _load_basic_pitch_config(self) -> Dict:
        config_path = Path(__file__).resolve().parents[2] / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('transcription', {}).get('basic_pitch', {})

    def extract_melody(self, audio_path: str) -> Dict:
        return self.transcribe(audio_path)

    def transcribe(self, audio_path: str) -> Dict:
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

        notes = self._convert_note_events(note_events)
        if self.melody_only:
            notes = self._filter_melody_only(notes)
        notes = self._dedup_and_sort(notes)

        self.notes = notes
        self.tempo = float(self.midi_tempo)
        logger.info(f"basic-pitch 最终音符数: {len(notes)}")
        return self.notes_to_dict()

    def _convert_note_events(self, note_events) -> List[Dict]:
        notes = []
        for event in note_events:
            start_time, end_time, pitch_midi, amplitude, _ = event
            if end_time <= start_time:
                continue
            duration = float(end_time - start_time)
            start_frame = int(round(start_time * self.sr / self.hop_length))
            end_frame = int(round(end_time * self.sr / self.hop_length))
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
        if not notes:
            return []

        sorted_notes = sorted(notes, key=lambda n: (n['start_frame'], -n['confidence']))
        kept: List[Dict] = []

        for note in sorted_notes:
            if not kept:
                kept.append(note.copy())
                continue

            last = kept[-1]
            overlap = note['start_frame'] < last['end_frame']

            if not overlap:
                kept.append(note.copy())
                continue

            if note['confidence'] > last['confidence']:
                last_new_end = note['start_frame']
                last_new_duration = (last_new_end - last['start_frame']) * self.hop_length / self.sr
                if last_new_duration >= (self.minimum_note_length_ms / 1000.0):
                    last['end_frame'] = last_new_end
                    last['duration'] = last_new_duration
                else:
                    kept.pop()
                kept.append(note.copy())
            else:
                continue

        return kept

    def _dedup_and_sort(self, notes: List[Dict]) -> List[Dict]:
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
