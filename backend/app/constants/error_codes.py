"""统一错误码。前端 src/constants/errorCodes.ts 只镜像展示用文案。"""


class ErrorCode:
    UNAUTHORIZED = "RFM-1001"
    FORBIDDEN = "RFM-1003"
    NOT_FOUND = "RFM-1004"
    VALIDATION = "RFM-2001"
    BAD_CREDENTIALS = "RFM-2002"
    SAMPLE_TOO_SMALL = "RFM-3001"
    BUDGET_INVALID = "RFM-3002"
    RUN_NOT_READY = "RFM-3003"
    RATE_LIMITED = "RFM-4001"
    QUOTA_EXCEEDED = "RFM-4002"
    INTERNAL = "RFM-5000"


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, detail=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail


def not_found(message: str) -> AppError:
    return AppError(ErrorCode.NOT_FOUND, message, 404)


def forbidden(message: str = "当前角色无权执行该操作") -> AppError:
    return AppError(ErrorCode.FORBIDDEN, message, 403)


def unauthorized(message: str = "未登录或登录已过期") -> AppError:
    return AppError(ErrorCode.UNAUTHORIZED, message, 401)


def validation(message: str, detail=None) -> AppError:
    return AppError(ErrorCode.VALIDATION, message, 422, detail)
