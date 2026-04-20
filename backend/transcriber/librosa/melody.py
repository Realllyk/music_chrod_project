"""
单旋律提取 - 自动识别和提取主旋律
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import librosa
import numpy as np
import pretty_midi
import scipy.signal as signal
import soundfile as sf
import torch
import torchcrepe
from transcriber.base import MelodyTranscriberBase, AnalysisType

logger = logging.getLogger(__name__)


class LibrosaMelodyTranscriber(MelodyTranscriberBase):
    """单旋律提取器"""

    @property
    def name(self) -> str:
        return "librosa"

    def __init__(self, sr: int = 22050, hop_length: int = 512):
        self.sr = sr
        self.hop_length = hop_length
        self.audio = None
        self.S = None
        self.pitch = None
        self.confidence = None
        self.notes = None
        self.onset_frames = np.array([], dtype=int)
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
        self.preprocess_highpass_hz = self.config.get('preprocess_highpass_hz', 80)
        self.preprocess_normalize = self.config.get('preprocess_normalize', True)
        self.onset_delta = self.config.get('onset_delta', 0.07)
        self.onset_wait = self.config.get('onset_wait', 10)
        self.onset_pre_max = self.config.get('onset_pre_max', 20)
        self.onset_post_max = self.config.get('onset_post_max', 20)
        self.onset_pre_avg = self.config.get('onset_pre_avg', 100)
        self.onset_post_avg = self.config.get('onset_post_avg', 100)
        self.segment_min_voiced_frames = self.config.get('segment_min_voiced_frames', 5)

    def _load_melody_config(self) -> Dict:
        config_path = Path(__file__).resolve().parents[2] / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('transcription', {}).get('melody', {})

    def load_audio(self, audio_path: str) -> np.ndarray:
        logger.info(f"加载音频: {audio_path}")
        self.audio, _ = librosa.load(audio_path, sr=self.sr, mono=True)
        logger.info(f"音频加载完成，时长: {len(self.audio) / self.sr:.2f}s")
        return self.audio

    def preprocess_audio(self, audio: np.ndarray) -> np.ndarray:
        logger.info(
            f"开始人声预处理... highpass_hz={self.preprocess_highpass_hz}, normalize={self.preprocess_normalize}"
        )
        processed = np.copy(audio)

        if self.preprocess_highpass_hz and self.preprocess_highpass_hz > 0:
            sos = signal.butter(
                4,
                self.preprocess_highpass_hz / (self.sr / 2),
                btype='highpass',
                output='sos',
            )
            processed = signal.sosfilt(sos, processed)

        if self.preprocess_normalize:
            processed = librosa.util.normalize(processed)

        logger.info("人声预处理完成")
        return processed

    def compute_spectrogram(self) -> np.ndarray:
        logger.info("计算频谱图...")
        self.S = librosa.stft(self.audio, n_fft=2048, hop_length=self.hop_length)
        self.S = np.abs(self.S)
        logger.info(f"频谱图形状: {self.S.shape}")
        return self.S

    def extract_pitch_pyin(self) -> Tuple[np.ndarray, np.ndarray]:
        logger.info(f"使用 PYIN 提取基频... fmin={self.fmin}, fmax={self.fmax}")
        f0, voiced_flag, voiced_probs = librosa.pyin(
            self.audio,
            fmin=self.fmin,
            fmax=self.fmax,
            sr=self.sr,
            hop_length=self.hop_length,
        )
        f0 = np.nan_to_num(f0, nan=0.0)
        self.pitch = f0
        self.confidence = voiced_probs
        logger.info(f"基频提取完成，有效基频点: {np.sum(f0 > 0)}/{len(f0)}")
        return f0, voiced_probs

    def extract_pitch_torchcrepe(self) -> Tuple[np.ndarray, np.ndarray]:
        logger.info(
            f"使用 torchcrepe 提取基频... model={self.torchcrepe_model}, "
            f"batch_size={self.torchcrepe_batch_size}, viterbi={self.torchcrepe_viterbi}"
        )

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

    def detect_onsets(self) -> np.ndarray:
        onset_frames = librosa.onset.onset_detect(
            y=self.audio,
            sr=self.sr,
            hop_length=self.hop_length,
            backtrack=True,
            units='frames',
            pre_max=self.onset_pre_max,
            post_max=self.onset_post_max,
            pre_avg=self.onset_pre_avg,
            post_avg=self.onset_post_avg,
            delta=self.onset_delta,
            wait=self.onset_wait,
        )
        self.onset_frames = onset_frames.astype(int)
        logger.info(f"检测到 {len(self.onset_frames)} 个 onset")
        return self.onset_frames

    def detect_tempo(self) -> float:
        tempo, _ = librosa.beat.beat_track(y=self.audio, sr=self.sr, hop_length=self.hop_length)
        if hasattr(tempo, '__len__'):
            tempo = float(tempo[0]) if len(tempo) else float(self.tempo)
        self.tempo = float(tempo) if tempo else float(self.tempo)
        logger.info(f"检测到 BPM: {self.tempo}")
        return self.tempo

    def smooth_pitch(self, window_size: int = 5) -> np.ndarray:
        logger.info(f"平滑基频曲线 (window_size={window_size})...")
        if self.pitch is None:
            raise ValueError("请先提取基频")

        smoothed = np.copy(self.pitch)
        for i in range(len(smoothed)):
            if smoothed[i] > 0:
                start = max(0, i - window_size // 2)
                end = min(len(smoothed), i + window_size // 2 + 1)
                valid_points = smoothed[start:end]
                valid_points = valid_points[valid_points > 0]
                if len(valid_points) > 0:
                    smoothed[i] = np.mean(valid_points)

        self.pitch = smoothed
        logger.info("基频平滑完成")
        return smoothed

    def build_midi_sequence(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        logger.info(
            f"构建 MIDI 序列... confidence_threshold={self.confidence_threshold}, "
            f"midi_median_kernel_size={self.midi_median_kernel_size}"
        )
        if self.pitch is None:
            raise ValueError("请先提取基频")

        a4_freq = 440
        a4_midi = 69
        midi_sequence = np.zeros(len(self.pitch), dtype=float)
        freq_sequence = np.zeros(len(self.pitch), dtype=float)
        confidence_sequence = np.zeros(len(self.pitch), dtype=float)

        for i, freq in enumerate(self.pitch):
            confidence = self.confidence[i] if self.confidence is not None else 0.8
            if freq > 0 and confidence >= self.confidence_threshold:
                midi_sequence[i] = round(a4_midi + 12 * np.log2(freq / a4_freq))
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
        return midi_sequence, freq_sequence, confidence_sequence

    def segment_notes_by_onset(
        self,
        midi_sequence: np.ndarray,
        freq_sequence: np.ndarray,
        confidence_sequence: np.ndarray,
    ) -> List[Dict]:
        boundaries = np.concatenate([[0], self.onset_frames, [len(midi_sequence)]])
        boundaries = np.unique(boundaries.astype(int))
        notes = []

        for start, end in zip(boundaries[:-1], boundaries[1:]):
            segment = midi_sequence[start:end]
            voiced = segment[segment > 0].astype(int)
            if len(voiced) < self.segment_min_voiced_frames:
                continue

            pitch = int(np.bincount(voiced).argmax())
            voiced_indices = np.where(segment > 0)[0]
            real_start = start + int(voiced_indices[0])
            real_end = start + int(voiced_indices[-1]) + 1
            duration = (real_end - real_start) * self.hop_length / self.sr
            voiced_confidence = confidence_sequence[real_start:real_end]
            voiced_freq = freq_sequence[real_start:real_end]
            voiced_freq = voiced_freq[voiced_freq > 0]

            notes.append({
                'midi': pitch,
                'start_frame': real_start,
                'end_frame': real_end,
                'duration': duration,
                'freq': float(np.median(voiced_freq)) if len(voiced_freq) > 0 else 0.0,
                'confidence': float(np.max(voiced_confidence)) if len(voiced_confidence) > 0 else 0.8,
            })

        logger.info(f"基于 onset 分段完成，生成段数={len(notes)}")
        return notes

    def merge_adjacent_same_notes(self, notes: List[Dict], gap_threshold: float) -> List[Dict]:
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

    def finalize_notes(self, notes: List[Dict]) -> List[Dict]:
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
        if self.notes is None:
            return {}
        return {
            'notes': self.notes,
            'total_notes': len(self.notes),
            'duration_sec': len(self.pitch) * self.hop_length / self.sr if self.pitch is not None else 0,
        }

    def save_midi(self, output_path: str = None):
        if self.notes is None or len(self.notes) == 0:
            logger.warning("没有音符，无法生成 MIDI")
            return

        logger.info(f"生成 MIDI 文件: {output_path}, tempo={self.tempo}")
        midi = pretty_midi.PrettyMIDI(initial_tempo=float(self.tempo))
        midi.time_signature_changes.append(pretty_midi.TimeSignature(4, 4, 0))
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
        return self.transcribe(audio_path)

    def transcribe(self, audio_path: str) -> Dict:
        try:
            self.load_audio(audio_path)
            self.audio = self.preprocess_audio(self.audio)

            if self.pitch_backend == 'torchcrepe':
                self.extract_pitch_torchcrepe()
            else:
                self.extract_pitch_pyin()

            self.smooth_pitch(window_size=self.window_size)
            midi_sequence, freq_sequence, confidence_sequence = self.build_midi_sequence()
            self.detect_onsets()
            notes = self.segment_notes_by_onset(midi_sequence, freq_sequence, confidence_sequence)
            self.finalize_notes(notes)
            self.detect_tempo()

            result = self.notes_to_dict()
            logger.info(f"扒谱完成: {result['total_notes']} 个音符")
            return result
        except Exception as e:
            logger.error(f"扒谱失败: {e}")
            raise

    def get_visualization_data(self) -> Dict:
        if self.pitch is None:
            return {}

        a4_freq = 440
        a4_midi = 69
        midi_curve = []
        for freq in self.pitch:
            if freq > 0:
                midi = a4_midi + 12 * np.log2(freq / a4_freq)
                midi_curve.append(round(midi))
            else:
                midi_curve.append(None)

        return {
            'pitch_curve': self.pitch.tolist(),
            'midi_curve': midi_curve,
            'confidence': self.confidence.tolist() if self.confidence is not None else None,
            'onset_frames': self.onset_frames.tolist() if self.onset_frames is not None else [],
            'notes': self.notes,
        }
