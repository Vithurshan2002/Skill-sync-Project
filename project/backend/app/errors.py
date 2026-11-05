class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, fields: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields


def invalid(field: str, message: str) -> None:
    raise ApiError(422, "validation_error", "Please check your input.", {field: [message]})


def conflict(message: str) -> None:
    raise ApiError(409, "conflict", message)


def missing() -> None:
    raise ApiError(404, "not_found", "The requested record was not found.")
