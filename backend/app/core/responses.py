from typing import Any, List


def api_response(data: Any = None, message: str = "操作成功") -> dict:
    return {
        "data": data,
        "message": message,
        "success": True
    }


def api_error(message: str, data: Any = None) -> dict:
    return {
        "data": data,
        "message": message,
        "success": False
    }


def paginated_response(total: int, items: List[Any]) -> dict:
    return {
        "total": total,
        "items": items
    }
