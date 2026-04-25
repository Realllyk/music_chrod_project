"""Pipeline 工厂。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from separator import create_separator
from .chord_pipeline import ChordPipeline
from .melody_pipeline import MelodyPipeline

logger = logging.getLogger(__name__)
_CONFIG_CACHE = None


def _load_config() -> dict:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        config_path = Path(__file__).resolve().parents[1] / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            _CONFIG_CACHE = json.load(f)
    return _CONFIG_CACHE


def _resolve_separator_order() -> List[str]:
    cfg = _load_config().get('transcription', {}).get('vocal_separation', {})
    primary = cfg.get('provider', 'demucs')
    fallback = cfg.get('fallback_order', ['spleeter', 'librosa'])
    order = [primary] + [item for item in fallback if item != primary]
    if not any(item in order for item in ('passthrough', 'none', 'librosa')):
        order.append('passthrough')
    return order


def _create_melody_transcriber():
    backend = _load_config().get('transcription', {}).get('melody', {}).get('backend', 'librosa')
    if backend == 'basic_pitch':
        from transcriber.basic_pitch.melody import BasicPitchMelodyTranscriber
        return BasicPitchMelodyTranscriber()
    if backend == 'librosa':
        from transcriber.librosa.melody import LibrosaMelodyTranscriber
        return LibrosaMelodyTranscriber()
    raise ValueError(f'未知 melody backend: {backend}')


def _create_chord_transcriber():
    algo = _load_config().get('transcription', {}).get('algorithm', {}).get('chord', 'librosa')
    if algo == 'librosa':
        from transcriber.librosa.chord import LibrosaChordTranscriber
        return LibrosaChordTranscriber()
    raise ValueError(f'未知 chord algorithm: {algo}')


def create_melody_pipeline() -> MelodyPipeline:
    transcriber = _create_melody_transcriber()
    last_error = None
    for provider in _resolve_separator_order():
        try:
            separator = create_separator(provider)
            logger.info(f'melody pipeline: separator={separator.name}, transcriber={transcriber.name}')
            return MelodyPipeline(separator, transcriber)
        except Exception as exc:
            last_error = exc
            logger.warning(f'分离器初始化失败 provider={provider}: {exc}')
    raise RuntimeError(f'No available separator: {last_error}')


def create_chord_pipeline() -> ChordPipeline:
    transcriber = _create_chord_transcriber()
    last_error = None
    for provider in _resolve_separator_order():
        try:
            separator = create_separator(provider)
            logger.info(f'chord pipeline: separator={separator.name}, transcriber={transcriber.name}')
            return ChordPipeline(separator, transcriber)
        except Exception as exc:
            last_error = exc
            logger.warning(f'分离器初始化失败 provider={provider}: {exc}')
    raise RuntimeError(f'No available separator: {last_error}')


__all__ = ['create_melody_pipeline', 'create_chord_pipeline', 'MelodyPipeline', 'ChordPipeline']
