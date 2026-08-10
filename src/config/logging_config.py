"""
Cấu hình logging tập trung. Chỉ gọi `setup_logging()` tại ENTRYPOINT
(`src/main.py::main`, `src/app.py` lifespan) - thư viện/service chỉ dùng
`logger = logging.getLogger(__name__)`.
"""
import logging

_configured = False


def setup_logging(level: str = "INFO") -> None:
    """Cấu hình root logger. Gọi nhiều lần là no-op."""
    global _configured
    if _configured:
        return

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s",
    )
    # Các thư viện bên thứ 3 quá ồn ở mức DEBUG/INFO
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)

    _configured = True
