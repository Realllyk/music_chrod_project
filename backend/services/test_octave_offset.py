"""一次性验证脚本：_build_notation_notes 的 octave_offset 正确性。

对应方案：docs/plan/202604/旋律简谱八度错修复/方案.md
验证通过后删除。

覆盖第四节两张表：
  - C 大调（tonic_pc=0, tonic_reference_midi=60）
  - A 小调（tonic_pc=9, tonic_reference_midi=69）
"""
import os
import sys

# 让脚本能以 backend 作为根找到 services 包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.melody_analysis_service import MelodyAnalysisService


class FakeNote:
    """最小替身：只暴露 start / end / pitch 三个字段，绕开 pretty_midi 依赖。"""

    def __init__(self, start, end, pitch):
        self.start = float(start)
        self.end = float(end)
        self.pitch = int(pitch)


def run(tonic_pc, mode, pitches):
    notes = [FakeNote(i * 0.5, i * 0.5 + 0.4, p) for i, p in enumerate(pitches)]
    return MelodyAnalysisService._build_notation_notes(
        notes=notes,
        tonic_pc=tonic_pc,
        mode=mode,
        tempo_bpm=120.0,
    )


def assert_cases(label, tonic_pc, mode, cases):
    pitches = [p for p, _ in cases]
    out = run(tonic_pc, mode, pitches)
    for (pitch, expect), got in zip(cases, out):
        actual = got['octave_offset']
        assert actual == expect, (
            f"{label} MIDI={pitch}: expect octave_offset={expect}, got {actual}"
        )
    print(f"{label} OK ({len(cases)} cases)")


def test_c_major():
    """C 大调：旧代码下 G4、B4 会被错判为 +1 八度。"""
    assert_cases(
        'C 大调',
        tonic_pc=0,
        mode='major',
        cases=[
            (48, -1),  # C3
            (55, -1),  # G3
            (59, -1),  # B3
            (60, 0),   # C4
            (67, 0),   # G4  <- 旧 round() 错成 1
            (71, 0),   # B4  <- 旧 round() 错成 1
            (72, 1),   # C5
            (79, 1),   # G5
            (84, 2),   # C6
        ],
    )


def test_a_minor():
    """A 小调：旧代码下 E5 会被错判为 +1 八度。"""
    assert_cases(
        'A 小调',
        tonic_pc=9,
        mode='minor',
        cases=[
            (57, -1),  # A3
            (69, 0),   # A4
            (76, 0),   # E5  <- 旧 round() 错成 1
            (81, 1),   # A5
        ],
    )


def test_degree_still_correct():
    """回归：级数（1~7）计算不应受影响。

    C 大调中 C4=1、E4=3、G4=5 等。
    """
    out = run(0, 'major', [60, 64, 67, 72])
    expected_degrees = ['1', '3', '5', '1']
    for got, expect in zip(out, expected_degrees):
        assert got['degree'] == expect, (
            f"C 大调 MIDI={got['midi']}: expect degree={expect}, got {got['degree']}"
        )
    print('degree 回归 OK')


if __name__ == '__main__':
    test_c_major()
    test_a_minor()
    test_degree_still_correct()
    print('All tests passed.')
