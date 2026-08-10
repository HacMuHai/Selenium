"""
Exception nghiệp vụ. Tầng service ném, tầng app map sang HTTP status.
Repository KHÔNG biết gì về HTTP.
"""


class AppError(Exception):
    """Lỗi nghiệp vụ có status code tương ứng."""

    status_code = 500

    def __init__(self, message: str = "Lỗi hệ thống") -> None:
        super().__init__(message)
        self.message = message


class InvalidIdError(AppError):
    status_code = 400


class EmptyPayloadError(AppError):
    status_code = 400


class NotFoundError(AppError):
    status_code = 404


class DuplicateError(AppError):
    status_code = 409


class ModelNotTrainedError(AppError):
    """Chưa chạy `python -m src.analyze train`."""

    status_code = 503


class UnknownModelError(AppError):
    status_code = 400


class DatabaseUnavailableError(AppError):
    """MongoDB không kết nối được - app vẫn chạy, chỉ router /products là hỏng."""

    status_code = 503
