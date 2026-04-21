"""
歌曲 Controller
处理歌曲相关的 API 请求
"""

from flask import Blueprint, jsonify, redirect, request, send_file

from pojo.dto import use_dto
from pojo.dto.songs_dto import AddSongDTO, ListSongsQueryDTO, SongIdPathDTO
from pojo.vo import PageVO, Result
from pojo.vo.melody_analysis_vo import MelodyAnalysisVO
from pojo.vo.songs_vo import AddSongVO, SongVO
from services.file_service import FileService
from services.songs_service import SongsService

songs_controller = Blueprint('songs', __name__, url_prefix='/api/songs')


@songs_controller.route('/list', methods=['GET'])
@use_dto(ListSongsQueryDTO, source='query')
def list_songs(dto: ListSongsQueryDTO):
    if dto.keyword:
        songs, total = SongsService.search_songs(dto.keyword, dto.limit, dto.offset)
    else:
        songs, total = SongsService.get_songs(dto.limit, dto.offset)

    songvos = [SongVO.from_domain(song) for song in songs]
    return Result.success(
        PageVO(items=songvos, total=total, limit=dto.limit, offset=dto.offset)
    ).to_response()


@songs_controller.route('/<int:song_id>', methods=['GET'])
def get_song(song_id):
    song = SongsService.get_song_by_id(song_id)
    if song:
        return jsonify(SongVO.from_domain(song).model_dump(mode='json'))
    return Result.not_found('Song not found').to_response()


@songs_controller.route('/<int:song_id>/melody-analysis', methods=['GET'])
@use_dto(SongIdPathDTO, source='path')
def get_song_melody_analysis(song_id: int, dto: SongIdPathDTO):
    song, analysis, error = SongsService.get_melody_analysis(dto.song_id)
    if error == 'song_not_found':
        return Result.not_found('Song not found').to_response()
    if error == 'melody_not_found':
        return Result.not_found('Melody analysis not found').to_response()

    vo_result = MelodyAnalysisVO.from_domain(song, analysis)
    return Result.success(vo_result).to_response()


@songs_controller.route('/add', methods=['POST'])
@use_dto(AddSongDTO)
def add_song(dto: AddSongDTO):
    song, audio_path = SongsService.create_song_from_dto(dto)
    vo = AddSongVO(song_id=song['id'], audio_path=audio_path)
    return Result.success(vo).to_response()


@songs_controller.route('/<int:song_id>', methods=['PUT'])
def update_song(song_id):
    data = request.json or {}

    if SongsService.update_song(song_id, data):
        return jsonify({'ok': True, 'message': 'Song updated'})
    return Result.server_error('Failed to update song').to_response()


@songs_controller.route('/<int:song_id>', methods=['DELETE'])
def delete_song(song_id):
    if SongsService.delete_song(song_id):
        return jsonify({'ok': True, 'message': 'Song deleted'})
    return Result.server_error('Failed to delete song').to_response()


@songs_controller.route("/uploads/audio/<filename>", methods=["GET"])
def serve_audio(filename):
    args = request.args.to_dict()
    song_id = int(args['song_id']) if args.get('song_id') else None
    song = SongsService.get_song_by_id(song_id) if song_id else None
    if song and song.get('audio_path'):
        return redirect(FileService.resolve_public_url(song.get('audio_path')))

    if filename.startswith('http://') or filename.startswith('https://'):
        return redirect(filename)

    audio_path = f"songs/{filename}"
    try:
        local_path = FileService.fetch_local_file(audio_path)
        return send_file(local_path)
    except Exception:
        return Result.not_found('File not found').to_response()
