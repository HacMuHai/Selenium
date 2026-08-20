"""
CLI nạp Excel đã export trở lại MongoDB. Chạy từ repo root.

Dùng khi crawl bằng `--no-db --export` (Excel là nơi lưu duy nhất) và sau này mới dựng
được Mongo. Đọc đệ quy nên trỏ vào `data/` là nạp cả các thư mục con theo sàn.

Ví dụ:
    python -m src.import_excel --input data --dry-run      # xem trước, không ghi
    python -m src.import_excel --input data                # nạp, product đã có thì bỏ qua
    python -m src.import_excel --input data/cellphones --mode replace
"""
import argparse
import logging
import sys
from typing import Optional

from src.config.database import ensure_indexes
from src.config.logging_config import setup_logging
from src.config.settings import get_settings
from src.repositories.product_repository import ProductRepository
from src.services.import_service import ImportService

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        prog="python -m src.import_excel",
        description="Nạp Excel đã export (data/<sàn>/*.xlsx) trở lại MongoDB.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input", default=settings.export_dir, metavar="DIR",
        help="Thư mục chứa .xlsx (quét cả thư mục con)",
    )
    parser.add_argument(
        "--mode", choices=("skip", "replace"), default="skip",
        help="Product đã có trong DB: bỏ qua hay ghi đè",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Chỉ đọc và thống kê, không ghi Mongo",
    )
    parser.add_argument("--log-level", default=settings.log_level)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)

    try:
        repository = ProductRepository()
        if not args.dry_run:
            ensure_indexes(repository.collection)
        stats = ImportService(repository, mode=args.mode).import_dir(
            args.input, dry_run=args.dry_run
        )
        logger.info("Kết quả: %s", stats)
        return 0
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    except KeyboardInterrupt:
        logger.warning("Đã dừng theo yêu cầu người dùng")
        return 130
    except Exception:
        logger.exception("Import thất bại")
        return 1


if __name__ == "__main__":
    sys.exit(main())
