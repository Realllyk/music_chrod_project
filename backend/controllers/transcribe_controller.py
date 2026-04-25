"""提取 Controller。

当前职责刻意收敛为三件事：
1. DTO 校验
2. 调用 Service
3. 包装统一响应

不再承担：
- 数据库读写
- Pipeline / Transcriber 组装
- 后台线程编排
- OSS 上传下载
"""

import logging

from flask import Blueprint

from pojo.dto import use_dto
from pojo.dto.transcribe_dto import SongTasksQueryDTO, StartTranscribeDTO, TranscribeTaskQueryDTO
from pojo.vo import Result
from pojo.vo.transcribe_vo import SongTranscribeTasksVO, StartTranscribeVO, TranscribeTaskVO
from services.transcribe_service import TranscribeService

logger = logging.getLogger(__name__)

transcribe_controller = Blueprint('transcribe', __name__, url_prefix='/api/transcribe')


@transcribe_controller.route('/start', methods=['POST'])
@use_dto(StartTranscribeDTO)
def start_transcribe(dto: StartTranscribeDTO):
    """启动提取任务。"""
    task_id = TranscribeService.start(dto.song_id, dto.mode)
    vo = StartTranscribeVO(task_id=task_id, status='pending')
    return Result.success(vo).to_response()


@transcribe_controller.route('/status/<task_id>', methods=['GET'])
@use_dto(TranscribeTaskQueryDTO, source='path')
def get_task_status(dto: TranscribeTaskQueryDTO):
    """查询任务状态。"""
    task = TranscribeService.get_task_status(dto.task_id)
    return Result.success(TranscribeTaskVO.from_domain(task)).to_response()


@transcribe_controller.route('/song/<int:song_id>', methods=['GET'])
@use_dto(SongTasksQueryDTO, source='path')
def get_song_tasks(dto: SongTasksQueryDTO):
    """按歌曲查询所有转录任务。"""
    tasks = TranscribeService.list_tasks_by_song(dto.song_id)
    vo = SongTranscribeTasksVO(
        song_id=dto.song_id,
        tasks=[TranscribeTaskVO.from_domain(task) for task in tasks],
    )
    return Result.success(vo).to_response()
