#!/usr/bin/env python3
"""
basic-pitch 冒烟测试脚本

用途：
- 验证当前环境是否能成功 import basic_pitch
- 验证模型是否能对单个音频文件跑通推理
- 输出 MIDI 文件与基础结果摘要

示例：
python tmp/basic_pitch_smoke_test.py --input /path/to/test.wav
python tmp/basic_pitch_smoke_test.py --input /path/to/test.wav --output-dir /tmp/basic_pitch_smoke
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="basic-pitch smoke test")
    parser.add_argument("--input", required=True, help="输入音频文件路径")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="输出目录，默认在输入文件同级生成 basic_pitch_smoke_output",
    )
    parser.add_argument(
        "--onset-threshold",
        type=float,
        default=0.5,
        help="basic-pitch onset_threshold，默认 0.5",
    )
    parser.add_argument(
        "--frame-threshold",
        type=float,
        default=0.3,
        help="basic-pitch frame_threshold，默认 0.3",
    )
    parser.add_argument(
        "--minimum-note-length-ms",
        type=int,
        default=80,
        help="最小音符长度（毫秒），默认 80",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"[ERROR] 输入文件不存在: {input_path}")
        return 2

    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else input_path.parent / "basic_pitch_smoke_output"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print("[INFO] 开始 basic-pitch 冒烟测试")
    print(f"[INFO] 输入文件: {input_path}")
    print(f"[INFO] 输出目录: {output_dir}")

    try:
        from basic_pitch import ICASSP_2022_MODEL_PATH
        from basic_pitch.inference import predict
    except Exception as exc:
        print("[ERROR] 无法导入 basic_pitch")
        print(f"[ERROR] {exc}")
        traceback.print_exc()
        return 3

    try:
        print(f"[INFO] 模型路径: {ICASSP_2022_MODEL_PATH}")
        model_output, midi_data, note_events = predict(
            str(input_path),
            ICASSP_2022_MODEL_PATH,
            onset_threshold=args.onset_threshold,
            frame_threshold=args.frame_threshold,
            minimum_note_length=args.minimum_note_length_ms,
        )
    except Exception as exc:
        print("[ERROR] basic-pitch 推理失败")
        print(f"[ERROR] {exc}")
        traceback.print_exc()
        return 4

    midi_path = output_dir / f"{input_path.stem}_basic_pitch.mid"
    summary_path = output_dir / f"{input_path.stem}_basic_pitch_summary.json"

    try:
        midi_data.write(str(midi_path))
    except Exception as exc:
        print("[ERROR] MIDI 写出失败")
        print(f"[ERROR] {exc}")
        traceback.print_exc()
        return 5

    summary = {
        "input": str(input_path),
        "model_path": str(ICASSP_2022_MODEL_PATH),
        "midi_path": str(midi_path),
        "note_event_count": len(note_events) if note_events is not None else 0,
        "midi_instrument_count": len(midi_data.instruments) if midi_data is not None else 0,
        "onset_threshold": args.onset_threshold,
        "frame_threshold": args.frame_threshold,
        "minimum_note_length_ms": args.minimum_note_length_ms,
    }

    try:
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        print("[WARN] 摘要文件写出失败，但不影响冒烟测试结论")
        print(f"[WARN] {exc}")

    print("[SUCCESS] basic-pitch 冒烟测试通过")
    print(f"[SUCCESS] MIDI 输出: {midi_path}")
    print(f"[SUCCESS] 摘要文件: {summary_path}")
    print(f"[SUCCESS] note_events 数量: {summary['note_event_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
