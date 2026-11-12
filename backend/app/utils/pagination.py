"""分页参数与响应结构。"""
from math import ceil


def page_params(page: int | None, page_size: int | None, default_size: int = 20, max_size: int = 100) -> tuple[int, int]:
    current = max(1, int(page or 1))
    size = max(1, min(int(page_size or default_size), max_size))
    return current, size


def paginated(items: list, total: int, page: int, page_size: int) -> dict:
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": ceil(total / page_size) if page_size else 0,
    }
