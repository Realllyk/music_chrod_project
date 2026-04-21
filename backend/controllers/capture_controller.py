"""
采集 Controller
处理采集会话相关的 API 请求
"""

from pathlib import Path

from flask import Blueprint, send_file

from pojo.dto import use_dto
from pojo.dto.capture_dto import (
    ListRecordingsQueryDTO,
    ListSessionsQueryDTO,
    RecordingFilePathDTO,
    RegisterFileDTO,
    RequestRecordingDTO,
    SaveRecordingDTO,
    SessionIdDTO,
    SessionIdPathDTO,
    StartRecordingDTO,
    StartSessionDTO,
    StopRecordingDTO,
    UpdateSessionDTO,
    UploadFileDTO,
)
from pojo.vo import PageVO, Result
from pojo.vo.capture_vo import (
    ActiveCaptureSessionVO,
    CaptureSessionVO,
    DeleteSessionVO,
    RecordingActionVO,
    RecordingVO,
    RegisterFileVO,
    SaveRecordingVO,
    StartSessionVO,
    UpdateSessionResultVO,
)
from services.audio_sources_service import AudioSourcesService
from services.capture_service import CaptureService
from services.file_service import FileService
from utils.aliyun_oss import download_file, upload_file as upload_to_oss

# 创建 Blueprint
capture_controller = Blueprint('capture', __name__, url_prefix='/api/capture')

# 录音文件存储目录
AGENT_RECORDINGS_DIR = Path(__file__).parent.parent.parent / 'agent' / 'recordings'


def get_session_dir(date_str=None):
    """获取录音目录"""
    if date_str is None:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
    session_dir = AGENT_RECORDINGS_DIR / date_str
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


@capture_controller.route('/start', methods=['POST'])
@use_dto(StartSessionDTO)
def start_session(dto: StartSessionDTO):
    """创建采集会话"""
    session = CaptureService.create_session(dto.source)
    vo = StartSessionVO(
        session_id=session['session_id'],
        status=session['status'],
        source=session.get('source') or dto.source,
        created_at=session['created_at'].isoformat() if session.get('created_at') else None,
    )
    return Result.success(vo).to_response()


@capture_controller.route('/active', methods=['GET'])
def get_active_session():
    """获取活跃的采集会话"""
    session = CaptureService.get_active_session()
    vo = ActiveCaptureSessionVO(
        session_id=session.get('session_id') if session else None,
        status=session.get('status') if session else None,
        source=session.get('source') if session else None,
    )
    return Result.success(vo).to_response()


@capture_controller.route('/request-recording', methods=['PUT'])
@use_dto(RequestRecordingDTO)
def request_recording(dto: RequestRecordingDTO):
    """请求开始录制"""
    session = CaptureService.get_session(dto.session_id)
    if not session:
        return Result.bad_request('Invalid session_id').to_response()

    CaptureService.update_session(dto.session_id, {'status': 'recording_requested'})
    return Result.success(
        RecordingActionVO(session_id=dto.session_id, status='recording_requested')
    ).to_response()


@capture_controller.route('/register-file', methods=['PUT'])
@use_dto(RegisterFileDTO)
def register_file(dto: RegisterFileDTO):
    """注册已保存的文件"""
    session = CaptureService.get_session(dto.session_id)
    if not session:
        return Result.bad_request('Invalid session_id').to_response()

    payload = dto.model_dump(exclude_none=True)
    CaptureService.register_file(dto.session_id, payload)
    refreshed = CaptureService.get_session(dto.session_id)
    return Result.success(
        RegisterFileVO(
            session_id=dto.session_id,
            status='recorded',
            audio_name=refreshed.get('audio_name') if refreshed else dto.audio_name,
            file_path=refreshed.get('file_path') if refreshed else dto.file_path,
        )
    ).to_response()


@capture_controller.route('/upload-file', methods=['POST'])
@use_dto(UploadFileDTO, source='form')
def upload_file(dto: UploadFileDTO):
    """上传 WAV 文件到 OSS"""
    session = CaptureService.get_session(dto.session_id)
    if not session:
        return Result.bad_request('Invalid session_id').to_response()

    file = dto.audio_file
    try:
        oss_url = upload_to_oss(file, directory='recordings')
    except Exception as e:
        return Result.server_error(f'OSS upload failed: {str(e)}').to_response()

    resolved_audio_name = dto.audio_name or session.get('audio_name') or file.filename or f'{dto.session_id}.wav'
    update_data = {
        'status': 'uploaded',
        'file_path': oss_url,
        'audio_name': resolved_audio_name,
    }
    CaptureService.update_session(dto.session_id, update_data)

    AudioSourcesService.create_from_session({
        'session_id': dto.session_id,
        'audio_name': resolved_audio_name,
        'file_path': oss_url,
        'sample_rate': 48000,
        'channels': 2,
    })

    return Result.success({
        'ok': True,
        'session_id': dto.session_id,
        'file_path': oss_url,
    }).to_response()


@capture_controller.route('/stop', methods=['PUT'])
@use_dto(SessionIdDTO)
def stop_session(dto: SessionIdDTO):
    """停止采集会话"""
    session = CaptureService.get_session(dto.session_id)
    if not session:
        return Result.not_found('Session not found').to_response()

    CaptureService.update_session(dto.session_id, {'status': 'stopped'})
    return Result.success(
        RecordingActionVO(session_id=dto.session_id, status='stopped')
    ).to_response()


@capture_controller.route('/list', methods=['GET'])
@use_dto(ListSessionsQueryDTO, source='query')
def list_sessions(dto: ListSessionsQueryDTO):
    """获取会话列表"""
    sessions, total = CaptureService.list_sessions(dto.limit, dto.status, dto.offset, dto.source)
    items = [CaptureSessionVO.from_domain(session) for session in sessions]
    return Result.success(
        PageVO(items=items, total=total, limit=dto.limit, offset=dto.offset)
    ).to_response()


@capture_controller.route('/detail/<session_id>', methods=['GET'])
@use_dto(SessionIdPathDTO, source='path')
def get_session_detail(dto: SessionIdPathDTO):
    """获取会话详情"""
    session = CaptureService.get_session(dto.session_id)
    if not session:
        return Result.not_found('Session not found').to_response()
    return Result.success(CaptureSessionVO.from_domain(session)).to_response()


@capture_controller.route('/start-recording', methods=['POST'])
@use_dto(StartRecordingDTO)
def start_recording(dto: StartRecordingDTO):
    """兼容接口：开始录音（创建会话+请求录制）。"""
    session = CaptureService.create_session(dto.source)
    session_id = session['session_id']
    CaptureService.update_status(session_id, 'recording')
    refreshed = CaptureService.get_session(session_id) or {}
    return Result.success(
        RecordingActionVO(session_id=session_id, status=refreshed.get('status', 'recording'))
    ).to_response()


@capture_controller.route('/stop-recording', methods=['PUT'])
@use_dto(StopRecordingDTO)
def stop_recording(dto: StopRecordingDTO):
    """兼容接口：停止录音。"""
    session_id = dto.session_id
    if not session_id:
        session = CaptureService.get_active_session()
        if session:
            session_id = session['session_id']

    if not session_id:
        return Result.bad_request('No active session').to_response()

    session = CaptureService.get_session(session_id)
    if not session:
        return Result.not_found('Session not found').to_response()

    update_data = {'status': 'stopped'}
    if dto.audio_name:
        update_data['audio_name'] = dto.audio_name
    CaptureService.update_session(session_id, update_data)
    return Result.success(RecordingActionVO(session_id=session_id, status='stopped')).to_response()


@capture_controller.route('/save', methods=['PUT'])
@use_dto(SaveRecordingDTO)
def save_recording(dto: SaveRecordingDTO):
    """保存录音文件名"""
    session = CaptureService.get_session(dto.session_id)
    if not session:
        return Result.bad_request('Invalid session_id').to_response()

    audio_name = dto.audio_name if dto.audio_name.endswith('.wav') else f'{dto.audio_name}.wav'
    CaptureService.update_session(dto.session_id, {'audio_name': audio_name})
    return Result.success(SaveRecordingVO(session_id=dto.session_id, audio_name=audio_name)).to_response()


@capture_controller.route('/recordings', methods=['GET'])
@use_dto(ListRecordingsQueryDTO, source='query')
def get_recordings(dto: ListRecordingsQueryDTO):
    """获取录音文件列表（用于创建歌曲时选择音源）"""
    sessions, total = CaptureService.list_recordings(
        limit=dto.limit,
        offset=dto.offset,
        session_id=dto.session_id,
        audio_name=dto.audio_name,
    )
    items = [RecordingVO.from_domain(session) for session in sessions]
    return Result.success(
        PageVO(items=items, total=total, limit=dto.limit, offset=dto.offset)
    ).to_response()


@capture_controller.route('/sessions/<session_id>', methods=['DELETE'])
@use_dto(SessionIdPathDTO, source='path')
def delete_session(dto: SessionIdPathDTO):
    """删除录音会话"""
    session = CaptureService.get_session(dto.session_id)
    if not session:
        return Result.not_found('Session not found').to_response()

    file_path = session.get('file_path')
    try:
        FileService.delete_path(file_path)
    except Exception:
        pass

    deleted = CaptureService.delete_session(dto.session_id)
    return Result.success(DeleteSessionVO(session_id=dto.session_id, deleted=bool(deleted))).to_response()


@capture_controller.route('/sessions/<session_id>', methods=['PUT'])
@use_dto(SessionIdPathDTO, source='path', arg_name='path_dto')
@use_dto(UpdateSessionDTO, arg_name='body_dto')
def update_session_info(path_dto: SessionIdPathDTO, body_dto: UpdateSessionDTO):
    """更新会话信息（文件名等）"""
    session = CaptureService.get_session(path_dto.session_id)
    if not session:
        return Result.not_found('Session not found').to_response()

    payload = body_dto.model_dump(exclude_none=True)
    CaptureService.update_session(path_dto.session_id, payload)
    refreshed = CaptureService.get_session(path_dto.session_id) or {}
    return Result.success(
        UpdateSessionResultVO(
            session_id=path_dto.session_id,
            audio_name=refreshed.get('audio_name'),
            source=refreshed.get('source'),
            status=refreshed.get('status'),
        )
    ).to_response()


@capture_controller.route('/uploads/recordings/<filename>', methods=['GET'])
@use_dto(RecordingFilePathDTO, source='path')
def serve_recording(dto: RecordingFilePathDTO):
    """服务录音文件（从 OSS 或本地）"""
    recordings_dir = Path(__file__).parent.parent / 'uploads' / 'recordings'
    file_path = recordings_dir / dto.filename
    if file_path.exists():
        return send_file(file_path)

    try:
        object_name = f'recordings/{dto.filename}'
        local_path = download_file(object_name)
        return send_file(local_path)
    except Exception:
        return Result.not_found('File not found').to_response()
