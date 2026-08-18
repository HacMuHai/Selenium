"""
CLI crawler. Chạy từ repo root: `python -m src.main [flags]`.

Ví dụ:
    python -m src.main --category phu-kien
    python -m src.main --links https://www.thegioididong.com/sac-cap --limit 1 --no-db --export
    python -m src.main --export-only
"""
import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from src.config import version as version_module
from src.config.database import ensure_indexes
from src.config.driver import get_driver, quit_all, set_attach_address
from src.config.logging_config import setup_logging
from src.config.settings import get_settings
from src.config.targets import CATEGORIES, DEFAULT_CATEGORY
from src.repositories.memory_repository import InMemoryProductRepository
from src.repositories.product_repository import ProductRepository
from src.services.export_service import ExportService
from src.services.scraper_service import ScraperService, summarize
from src.services.sites import UnknownSiteError, site_class_for

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="Crawl comment sản phẩm thegioididong và lưu vào MongoDB / Excel.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--links", nargs="+", metavar="URL",
        help="Ghi đè danh sách link danh mục (bỏ qua --category)",
    )
    parser.add_argument(
        "--category", choices=sorted(CATEGORIES), default=DEFAULT_CATEGORY,
        help="Nhóm danh mục định nghĩa trong src/config/targets.py",
    )
    parser.add_argument(
        "--no-db", action="store_true",
        help="Không đọc & không ghi Mongo (giữ trong RAM). Vì không đọc DB nên sẽ "
             "crawl lại cả sản phẩm đã có trong Mongo.",
    )
    parser.add_argument(
        "--max-pages", type=int, default=15,
        help="Số trang danh mục tối đa mỗi link",
    )
    parser.add_argument(
        "--workers", type=int, default=settings.max_workers,
        help="Số thread crawl song song (mỗi thread 1 Chrome, ~200-400MB)",
    )
    parser.add_argument(
        "--export", nargs="?", const=settings.export_dir, metavar="DIR",
        help="Xuất Excel sau khi crawl vào thư mục DIR",
    )
    parser.add_argument(
        "--export-only", action="store_true",
        help="Chỉ export từ DB, không mở Chrome và không crawl",
    )
    parser.add_argument(
        "--limit", type=int, help="Chỉ crawl N sản phẩm đầu mỗi danh mục (smoke test)"
    )
    headless = parser.add_mutually_exclusive_group()
    headless.add_argument(
        "--headless", dest="headless", action="store_true", default=settings.headless
    )
    headless.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument(
        "--attach", metavar="HOST:PORT",
        help="Attach vào Chrome đang chạy với --remote-debugging-port. Chỉ bind "
             "127.0.0.1, KHÔNG bind 0.0.0.0. Khi attach, quit_all() không đóng browser.",
    )
    parser.add_argument(
        "--version-tag", help="Ghi đè config.version.version cho lần chạy này"
    )
    parser.add_argument("--log-level", default=settings.log_level)
    return parser


def resolve_links(args: argparse.Namespace) -> list[str]:
    """--links > --category. Chặn sớm URL không thuộc sàn nào để khỏi mở Chrome vô ích."""
    links = args.links if args.links else CATEGORIES[args.category]
    for link in links:
        site_class_for(link)  # ném UnknownSiteError kèm danh sách sàn hỗ trợ
    return links


def build_repository(no_db: bool):
    """Mongo hay in-memory - tầng service không phân biệt."""
    if no_db:
        logger.info("Chế độ --no-db: không đọc/ghi MongoDB")
        return InMemoryProductRepository()
    repository = ProductRepository()
    ensure_indexes(repository.collection)
    return repository


def run_crawl(args: argparse.Namespace, repository) -> None:
    settings = get_settings()
    scraper = ScraperService(repository, wait_timeout=settings.wait_timeout)
    all_results: list[list] = []
    links = resolve_links(args)  # validate trước khi mở Chrome

    try:
        driver = get_driver()
        for category_url in links:
            logger.info("Danh mục: %s", category_url)
            product_links = scraper.collect_product_links(
                driver, category_url, max_pages=args.max_pages, limit=args.limit
            )
            if not product_links:
                logger.warning("Không thu được sản phẩm nào từ %s", category_url)
                continue
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                all_results.extend(executor.map(scraper.crawl_product, product_links))
    finally:
        quit_all()

    stats = summarize(all_results)
    logger.info(
        "Tổng kết: %d sản phẩm, %d comment, %d sản phẩm không có comment",
        stats["products"], stats["comments"], stats["empty_products"],
    )


def run_export(repository, output_dir: str) -> None:
    settings = get_settings()
    service = ExportService(
        repository, output_dir, max_rows_per_file=settings.max_rows_per_file
    )
    files = service.export()
    logger.info("Đã ghi %d file Excel", len(files))


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)

    if args.version_tag:
        version_module.version = args.version_tag
    if args.attach:
        set_attach_address(args.attach)

    settings = get_settings()
    # --headless chỉ có tác dụng qua Settings vì driver đọc từ đó.
    settings.headless = args.headless

    try:
        if args.export_only:
            if args.no_db:
                logger.error("--export-only cần MongoDB, không dùng được với --no-db")
                return 2
            run_export(ProductRepository(), args.export or settings.export_dir)
            return 0

        repository = build_repository(args.no_db)
        run_crawl(args, repository)
        if args.export:
            run_export(repository, args.export)
        return 0
    except UnknownSiteError as exc:
        logger.error("%s", exc)
        return 2
    except KeyboardInterrupt:
        logger.warning("Đã dừng theo yêu cầu người dùng")
        return 130
    except Exception:
        logger.exception("Chạy thất bại")
        return 1


if __name__ == "__main__":
    sys.exit(main())
