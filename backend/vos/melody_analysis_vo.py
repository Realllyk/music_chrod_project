"""
旋律分析响应 VO
服务于 GET /api/songs/<song_id>/melody-analysis 接口的对外序列化
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class MelodyAnalysisVO:
    """旋律分析接口响应 VO。

    仅用于承载对外 JSON 结构的拼装；不做任何业务查询。
    领域对象（song / analysis 行）由 service 层提供，
    VO 负责将其转换为符合接口契约的响应体。
    """

    def __init__(self, song_section: Dict[str, Any], analysis_section: Dict[str, Any]):
        self._song_section = song_section
        self._analysis_section = analysis_section

    @classmethod
    def from_domain(
        cls,
        song: Optional[Dict[str, Any]],
        analysis: Optional[Dict[str, Any]],
    ) -> 'MelodyAnalysisVO':
        """根据 songs 行与 song_analysis 行构建 VO。"""
        song = song or {}
        analysis = analysis or {}
        result_json = analysis.get('result_json') or {}

        song_section = {
            'id': song.get('id'),
            'melody_key': song.get('melody_key') or analysis.get('analysis_key'),
        }

        # result_json 可能带有 type / midi_path；以外层 analysis 行为准覆盖
        analysis_section = {
            **result_json,
            'type': analysis.get('analysis_type') or 'melody',
            'midi_path': analysis.get('midi_path'),
        }

        return cls(song_section, analysis_section)

    def to_result(self) -> Dict[str, Any]:
        """返回接口 wrapper 内 result 字段内容。"""
        return {
            'song': self._song_section,
            'analysis': self._analysis_section,
        }

    def to_response(self) -> Dict[str, Any]:
        """兼容旧调用；仅返回 VO 自身内容，不包含通用 wrapper。"""
        return self.to_result()
