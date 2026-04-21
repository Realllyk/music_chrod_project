"""
基于 demucs 的单旋律提取
使用 demucs 分离人声，然后复用 librosa 提取旋律
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

from transcriber.base import MelodyTranscriberBase


class DemucsMelodyTranscriber(MelodyTranscriberBase):
    """基于 demucs 的单旋律提取。

    职责边界：
    1. 使用 demucs 先把输入音频分离出人声 stem
    2. 按配置选择后续的旋律提取 backend（如 librosa / basic-pitch）
    3. 把人声文件交给下游 backend 提取旋律

    注意：
    - 这里不负责最终上传 OSS
    - 这里只负责产出可供后续提取的人声文件，并代理下游 backend 的 save_midi()
    """

    def __init__(self, sr: int = 22050, hop_length: int = 512):
        self.sample_rate = sr
        self.hop_length = hop_length
        self.notes = []
        self.demucs_config = self._load_demucs_config()
        self.melody_backend = self._load_melody_backend()
        self.preserved_vocals_path = None
        self._delegate = None

    @property
    def name(self) -> str:
        return "demucs"

    def _load_demucs_config(self) -> dict:
        """读取 demucs 自身配置。

        这里只读取“分离阶段”需要的参数，例如：
        - model_name
        - two_stems
        - output_format
        - device / jobs / segment / shifts / overlap
        """
        config_path = Path(__file__).resolve().parents[2] / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('transcription', {}).get('vocal_separation', {}).get('demucs', {})

    def _load_melody_backend(self) -> str:
        """读取旋律提取 backend 类型。

        这里读取的是“分离完成之后交给谁继续提取旋律”，
        例如：
        - librosa
        - basic_pitch
        """
        config_path = Path(__file__).resolve().parents[2] / 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('transcription', {}).get('melody', {}).get('backend', 'librosa')

    def _build_melody_delegate(self):
        """根据配置构造旋律提取 backend。

        这里的 delegate 只负责“对已经分离出的人声文件继续做旋律提取”。
        demucs 自己不关心后面是 librosa 还是 basic-pitch。
        """
        backend = self.melody_backend
        if backend == 'basic_pitch':
            from transcriber.basic_pitch import BasicPitchMelodyTranscriber
            return BasicPitchMelodyTranscriber(sr=self.sample_rate, hop_length=self.hop_length)
        if backend == 'librosa':
            from transcriber.librosa.melody import LibrosaMelodyTranscriber
            return LibrosaMelodyTranscriber(sr=self.sample_rate, hop_length=self.hop_length)
        raise ValueError(f"未知的 melody backend: '{backend}'，合法值：'librosa' | 'basic_pitch'")

    def _separate_vocals(self, audio_path: str, temp_dir: str) -> str:
        """调用 demucs 分离人声，并返回分离后的人声文件路径。

        工作机制：
        1. 组装 demucs 的命令参数
        2. 调用 demucs.separate.main(...) 真正执行分离
        3. demucs 自己把结果写到 temp_dir 下
        4. 我们再去输出目录中查找 vocals.wav / mp3 / flac

        注意：
        - 这里没有手动 open(...).write(...) 保存文件
        - “保存分离结果到磁盘”这件事是 demucs 内部完成的
        """
        try:
            import demucs.separate as demucs_separate
        except ImportError:
            raise RuntimeError('demucs not installed')

        # 读取 demucs 模型与输出策略配置
        model_name = self.demucs_config.get('model_name', 'htdemucs')
        two_stems = self.demucs_config.get('two_stems', 'vocals')
        output_format = self.demucs_config.get('output_format', 'mp3')

        # 这是传给 demucs CLI/API 的核心参数：
        # --out：输出目录
        # --two-stems vocals：只拆分为 vocals / no_vocals 两路
        # -n：指定使用的 demucs 模型名
        demucs_args = [
            '--out', temp_dir,
            '--two-stems', two_stems,
            '-n', model_name,
        ]

        # 这些参数主要控制 demucs 的运行方式：
        # -d：运行设备（cpu / cuda）
        # -j：并发 worker 数
        # --segment：长音频分段长度
        # --shifts：增强推理次数，越大越稳但越慢
        # --overlap：分段重叠比例
        device = self.demucs_config.get('device')
        jobs = self.demucs_config.get('jobs')
        segment = self.demucs_config.get('segment')
        shifts = self.demucs_config.get('shifts')
        overlap = self.demucs_config.get('overlap')

        if device:
            demucs_args.extend(['-d', str(device)])
        if isinstance(jobs, int) and jobs >= 0:
            demucs_args.extend(['-j', str(jobs)])
        if segment is not None:
            demucs_args.extend(['--segment', str(segment)])
        if shifts is not None:
            demucs_args.extend(['--shifts', str(shifts)])
        if overlap is not None:
            demucs_args.extend(['--overlap', str(overlap)])

        # 输出格式默认是 wav；如果显式指定 mp3 / flac，则附加对应开关
        if output_format == 'mp3':
            demucs_args.append('--mp3')
        elif output_format == 'flac':
            demucs_args.append('--flac')

        # 最后一个参数是输入音频路径
        demucs_args.append(audio_path)

        # 真正执行分离：demucs 会自己把结果写入 temp_dir
        demucs_separate.main(demucs_args)

        # demucs 的典型输出目录形如：
        # temp_dir/model_name/<输入文件名去后缀>/vocals.wav
        basename = os.path.splitext(os.path.basename(audio_path))[0]
        candidates = [
            os.path.join(temp_dir, model_name, basename, 'vocals.wav'),
            os.path.join(temp_dir, model_name, basename, 'vocals.mp3'),
            os.path.join(temp_dir, model_name, basename, 'vocals.flac'),
        ]
        vocals_path = next((path for path in candidates if os.path.exists(path)), None)
        if not vocals_path:
            raise RuntimeError('Failed to extract vocals')
        return vocals_path

    def extract_melody(self, audio_path: str) -> dict:
        """完整旋律提取入口。

        流程：
        1. 创建临时目录给 demucs 使用
        2. 先做人声分离，拿到 vocals_path
        3. 复制一份人声文件到系统临时目录，供后续上传 / 调试保留
        4. 构造下游旋律提取 backend（librosa / basic_pitch）
        5. 把分离后的人声文件交给下游 backend 提取旋律
        """
        temp_dir = tempfile.mkdtemp(prefix='demucs_melody_')

        try:
            vocals_path = self._separate_vocals(audio_path, temp_dir)

            # demucs 输出目录会在 finally 中清理，因此这里额外复制一份人声文件，
            # 避免后续上传 OSS 或手动试听时找不到原始 stem。
            preserved_suffix = Path(vocals_path).suffix or '.wav'
            preserved_vocals_path = os.path.join(
                tempfile.gettempdir(),
                f"vocals_{next(tempfile._get_candidate_names())}{preserved_suffix}"
            )
            shutil.copy2(vocals_path, preserved_vocals_path)
            self.preserved_vocals_path = preserved_vocals_path

            delegate = self._build_melody_delegate()
            result = delegate.extract_melody(vocals_path)

            # 保存 delegate，后续 save_midi() 直接复用下游 backend 的实现
            self._delegate = delegate
            self.notes = delegate.notes or []

            # 额外把保留的人声文件路径塞回结果，供上层决定是否上传 OSS
            if isinstance(result, dict):
                result['vocals_path'] = self.preserved_vocals_path
            return result

        except Exception as e:
            self.notes = []
            if self.preserved_vocals_path and os.path.exists(self.preserved_vocals_path):
                try:
                    os.remove(self.preserved_vocals_path)
                except Exception:
                    pass
            self.preserved_vocals_path = None
            return {
                'notes': [],
                'midi_path': None,
                'error': str(e)
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def save_midi(self, output_path: str = None):
        """保存为 MIDI 文件（复用 librosa 的 MIDI 生成逻辑）"""
        if self._delegate is not None:
            return self._delegate.save_midi(output_path)
        return None
