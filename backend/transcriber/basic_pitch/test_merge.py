"""一次性验证脚本：转音合并与尾音合并正确性。

对应方案：docs/plan/202604/basic-pitch连音与尾音修复/方案.md
验证通过后删除。

默认参数（sr=22050, hop=512）下关键阈值转换为帧：
    prefilter_min_ms=40  -> 2 frames
    same_pitch_gap_ms=50 -> 2 frames
    melisma_gap_ms=30    -> 1 frame
    melisma_short_ms=120 -> 5 frames
    minimum_note_length_ms=80 -> 3 frames
"""
import os
import sys

# 让脚本能以 backend 作为根找到 transcriber 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from transcriber.basic_pitch.melody import BasicPitchMelodyTranscriber


def make_note(start_frame, end_frame, midi, confidence):
    sr, hop = 22050, 512
    return {
        'midi': int(midi),
        'start_frame': int(start_frame),
        'end_frame': int(end_frame),
        'duration': float((end_frame - start_frame) * hop / sr),
        'freq': 440.0 * (2 ** ((midi - 69) / 12.0)),
        'confidence': float(confidence),
    }


def run_pipeline(t, notes):
    notes = t._merge_same_pitch_gap(notes)
    notes = t._merge_melisma(notes)
    notes = t._merge_same_pitch_gap(notes)
    notes = t._apply_min_length(notes)
    return notes


def test_melisma():
    """转音用例：[C5 0-9][B4 10-13 短][C5 14-23] -> 合并为一段 C5"""
    t = BasicPitchMelodyTranscriber()
    notes = [
        make_note(0, 9, 72, 0.9),
        make_note(10, 13, 71, 0.5),
        make_note(14, 23, 72, 0.9),
    ]
    out = run_pipeline(t, notes)
    assert len(out) == 1, f"expected 1 note, got {len(out)}: {out}"
    assert out[0]['midi'] == 72
    assert out[0]['start_frame'] == 0
    assert out[0]['end_frame'] == 23
    print("melisma OK:", out)


def test_tail_gap_merge():
    """尾音用例：[C5 0-13][C5 14-17 短][C5 19-22 短] -> 合并为 [C5 0-22]"""
    t = BasicPitchMelodyTranscriber()
    notes = [
        make_note(0, 13, 72, 0.9),
        make_note(14, 17, 72, 0.5),
        make_note(19, 22, 72, 0.4),
    ]
    out = run_pipeline(t, notes)
    assert len(out) == 1, f"expected 1 note, got {len(out)}: {out}"
    assert out[0]['midi'] == 72
    assert out[0]['start_frame'] == 0
    assert out[0]['end_frame'] == 22
    print("tail OK:", out)


def test_no_merge_when_gap_too_large():
    """gap 超过阈值不应合并：[C5 0-13][C5 20-30]，gap=7 frames (~162ms)"""
    t = BasicPitchMelodyTranscriber()
    notes = [
        make_note(0, 13, 72, 0.9),
        make_note(20, 30, 72, 0.5),
    ]
    out = run_pipeline(t, notes)
    assert len(out) == 2, f"expected 2 notes (gap too large), got {len(out)}: {out}"
    print("no-merge (big gap) OK:", out)


def test_no_merge_when_semitone_too_large():
    """音程超过半音阈值不应吸收：[C5 0-9][A4 10-13 短][C5 14-23]，ΔMIDI=3"""
    t = BasicPitchMelodyTranscriber()
    notes = [
        make_note(0, 9, 72, 0.9),
        make_note(10, 13, 69, 0.5),   # A4，距 C5 三个半音
        make_note(14, 23, 72, 0.9),
    ]
    out = run_pipeline(t, notes)
    assert len(out) == 3, f"expected 3 notes (semitone too wide), got {len(out)}: {out}"
    print("no-merge (wide semitone) OK:", out)


if __name__ == '__main__':
    test_melisma()
    test_tail_gap_merge()
    test_no_merge_when_gap_too_large()
    test_no_merge_when_semitone_too_large()
    print("All tests passed.")
