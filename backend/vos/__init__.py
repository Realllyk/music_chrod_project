"""
VO (View Object) 层
专门负责对外响应的序列化，隔离 controller/service 中与接口响应拼装相关的逻辑
"""

from vos.melody_analysis_vo import MelodyAnalysisVO

__all__ = ['MelodyAnalysisVO']
