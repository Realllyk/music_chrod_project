"""旋律分析响应 VO。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pojo.vo.base import BaseVO


class MelodyAnalysisVO(BaseVO):
    song: Dict[str, Any]
    analysis: Dict[str, Any]

    @classmethod
    def from_domain(
        cls,
        song: Optional[Dict[str, Any]],
        analysis: Optional[Dict[str, Any]],
    ) -> 'MelodyAnalysisVO':
        song = song or {}
        analysis = analysis or {}
        result_json = analysis.get('result_json') or {}

        song_section = {
            'id': song.get('id'),
            'melody_key': song.get('melody_key') or analysis.get('analysis_key'),
        }

        analysis_section = {
            **result_json,
            'type': analysis.get('analysis_type') or 'melody',
            'midi_path': analysis.get('midi_path'),
        }

        return cls(song=song_section, analysis=analysis_section)

    def to_result(self) -> Dict[str, Any]:
        return self.model_dump(mode='json')

    def to_response(self) -> Dict[str, Any]:
        return self.to_result()
