"""
歌手 Controller
处理歌手相关的 API 请求
"""

from flask import Blueprint

from pojo.dto import use_dto
from pojo.dto.artists_dto import (
    AddArtistDTO,
    ArtistIdPathDTO,
    AvatarUploadDTO,
    ListArtistsQueryDTO,
    UpdateArtistDTO,
)
from pojo.vo import PageVO, Result
from pojo.vo.artists_vo import ArtistVO
from services.artists_service import ArtistsService

artists_controller = Blueprint('artists', __name__, url_prefix='/api/artists')

# 允许的头像格式
ALLOWED_AVATAR_EXTS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}


def _save_avatar_to_oss(avatar_file):
    """
    将头像文件上传到 OSS，返回公网 URL
    """
    from pojo.vo.exceptions import BadRequestException
    from utils.aliyun_oss import upload_file

    ext = avatar_file.filename.rsplit('.', 1)[-1].lower() if '.' in avatar_file.filename else ''
    if ext not in ALLOWED_AVATAR_EXTS:
        raise BadRequestException(f'不支持的图片格式: {ext}')

    try:
        avatar_url = upload_file(avatar_file)
    except Exception as exc:
        raise RuntimeError(f'OSS upload failed: {exc}') from exc
    return avatar_url


# ============================================================================
# 歌手 API
# ============================================================================

@artists_controller.route('/list', methods=['GET'])
@use_dto(ListArtistsQueryDTO, source='query')
def list_artists(dto: ListArtistsQueryDTO):
    """获取歌手列表"""
    artists, total = ArtistsService.get_artists(dto.limit, dto.offset)
    artist_vos = [ArtistVO.from_domain(artist) for artist in artists]
    return Result.success(
        PageVO(items=artist_vos, total=total, limit=dto.limit, offset=dto.offset)
    ).to_response()


@artists_controller.route('/count', methods=['GET'])
def get_artists_count():
    count = ArtistsService.count_artists()
    return Result.success({'total': count}).to_response()


@artists_controller.route('/<int:artist_id>', methods=['GET'])
@use_dto(ArtistIdPathDTO, source='path')
def get_artist(dto: ArtistIdPathDTO):
    """获取单个歌手"""
    artist = ArtistsService.get_artist_by_id(dto.artist_id)
    return Result.success(ArtistVO.from_domain(artist)).to_response()


@artists_controller.route('/add', methods=['POST'])
@use_dto(AddArtistDTO)
def add_artist(dto: AddArtistDTO):
    """添加歌手（兼容 JSON / multipart）"""
    avatar_url = None
    if dto.avatar is not None and getattr(dto.avatar, 'filename', ''):
        avatar_url = _save_avatar_to_oss(dto.avatar)

    artist_id = ArtistsService.add_artist({
        'name': dto.name,
        'bio': dto.bio,
        'avatar': avatar_url,
    })
    artist = ArtistsService.get_artist_by_id(artist_id)
    return Result.success(ArtistVO.from_domain(artist)).to_response()


@artists_controller.route('/<int:artist_id>', methods=['PUT'])
@use_dto(ArtistIdPathDTO, source='path', arg_name='path_dto')
@use_dto(UpdateArtistDTO)
def update_artist(path_dto: ArtistIdPathDTO, dto: UpdateArtistDTO):
    """更新歌手文本信息"""
    artist = ArtistsService.update_artist(path_dto.artist_id, {
        'name': dto.name,
        'bio': dto.bio,
    })
    return Result.success(ArtistVO.from_domain(artist)).to_response()


@artists_controller.route('/<int:artist_id>', methods=['DELETE'])
@use_dto(ArtistIdPathDTO, source='path')
def delete_artist(dto: ArtistIdPathDTO):
    """删除歌手"""
    ArtistsService.delete_artist(dto.artist_id)
    return Result.success({'ok': True, 'message': 'Artist deleted'}).to_response()


# ============================================================================
# 头像 API
# ============================================================================

@artists_controller.route('/<int:artist_id>/avatar', methods=['PUT'])
@use_dto(ArtistIdPathDTO, source='path', arg_name='path_dto')
@use_dto(AvatarUploadDTO)
def update_artist_avatar(path_dto: ArtistIdPathDTO, dto: AvatarUploadDTO):
    """更新歌手头像（multipart/form-data，上传到 OSS）"""
    avatar_url = _save_avatar_to_oss(dto.avatar)
    ArtistsService.update_artist(path_dto.artist_id, {'avatar': avatar_url})
    return Result.success({'ok': True, 'avatar_url': avatar_url}).to_response()
