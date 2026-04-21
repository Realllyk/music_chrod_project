class BizException(Exception):
    """业务异常基类。"""

    code: int = 500
    description: str = 'Internal server error'

    def __init__(self, description: str | None = None, code: int | None = None):
        self.description = description or self.description
        if code is not None:
            self.code = code
        super().__init__(self.description)


class NotFoundException(BizException):
    code = 404
    description = 'Not found'


class BadRequestException(BizException):
    code = 400
    description = 'Bad request'


class ConflictException(BizException):
    code = 409
    description = 'Conflict'
