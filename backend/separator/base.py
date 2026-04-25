"""
分离器抽象定义。

这一层只负责：
1. 接收一段混音音频
2. 产出若干 stem 的本地文件路径
3. 把临时工作目录信息交给上层 Pipeline 清理

注意：
- 不负责旋律/和弦提取
- 不负责 OSS 上传
- 不负责数据库写入
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, FrozenSet


@dataclass
class SeparationResult:
    """一次音轨分离的结果描述。"""

    stems: Dict[str, str]
    work_dir: str
    provider: str


class VocalSeparatorBase(ABC):
    """音轨分离器抽象基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """分离器名称，用于日志与排障。"""

    @abstractmethod
    def separate(self, audio_path: str, stems: FrozenSet[str]) -> SeparationResult:
        """执行音轨分离。

        Args:
            audio_path: 输入混音文件路径
            stems: 期望输出的 stem 集合

        Returns:
            SeparationResult: 包含分离结果与临时目录信息
        """
