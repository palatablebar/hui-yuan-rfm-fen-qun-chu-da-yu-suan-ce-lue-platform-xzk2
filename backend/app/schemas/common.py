"""统一错误信封与通用输出结构。"""


def error_envelope(code: str, message: str, request_id: str | None = None, detail=None) -> dict:
    payload = {"code": code, "message": message}
    if request_id:
        payload["request_id"] = request_id
    if detail is not None:
        payload["detail"] = detail
    return {"error": payload}
