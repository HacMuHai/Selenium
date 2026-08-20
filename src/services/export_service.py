"""
ExportService - xuất product + comment ra Excel, TÁCH THƯ MỤC THEO SÀN.

Nhận repository từ ngoài nên chạy y hệt cho cả Mongo lẫn in-memory (`--no-db`).
Duyệt bằng cursor để không nạp toàn bộ collection vào RAM.

Cấu trúc file: `<output_dir>/<site>/<base>_<n>.xlsx`, mỗi sàn đếm số thứ tự riêng.
Sàn lấy từ field `site`; document cũ chưa có field này thì suy ra từ hostname của `link`.

Header giữ nguyên 4 cột đầu (`link, name_item, comments_id, comments_content`) vì tầng
phân tích ở `paper/analysis/dataset.py` đọc theo TÊN cột. Ba cột `site, user_name, rating`
thêm vào cuối để `src/import_excel.py` dựng lại đúng document Mongo từ Excel.
"""
import logging
from pathlib import Path
from typing import Optional

from openpyxl import Workbook

from src.services.sites import UnknownSiteError, site_class_for

logger = logging.getLogger(__name__)

HEADER = [
    "link",
    "name_item",
    "comments_id",
    "comments_content",
    "site",
    "user_name",
    "rating",
]
EXPORT_PROJECTION = {"link": 1, "name": 1, "site": 1, "comments": 1}

# Sàn không xác định (document cũ, link lạ) vẫn phải xuất ra chứ không được rơi mất.
UNKNOWN_SITE = "khac"


def site_of(product: dict) -> str:
    """Tên sàn của product: ưu tiên field `site`, không có thì suy từ link."""
    site = (product.get("site") or "").strip()
    if site:
        return site
    try:
        return site_class_for(product.get("link") or "").name
    except UnknownSiteError:
        return UNKNOWN_SITE


class _SiteWriter:
    """Trạng thái ghi của MỘT sàn: workbook đang mở, số dòng, số thứ tự file."""

    def __init__(self, directory: Path, base_file_name: str, max_rows: int) -> None:
        self.directory = directory
        self.base_file_name = base_file_name
        self.max_rows = max_rows
        self.workbook: Optional[Workbook] = None
        self.sheet = None
        self.rows_in_file = 0
        self.file_index = 1
        self.written: list[Path] = []

    def append(self, row: list) -> None:
        if self.workbook is None:
            self.workbook = Workbook()
            self.sheet = self.workbook.active
            self.sheet.title = "Comments"
            self.sheet.append(HEADER)
        self.sheet.append(row)
        self.rows_in_file += 1
        if self.rows_in_file >= self.max_rows:
            self.flush()

    def flush(self) -> None:
        """Lưu workbook đang dở (nếu có) và mở vòng file mới."""
        if self.workbook is None or self.rows_in_file == 0:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"{self.base_file_name}_{self.file_index}.xlsx"
        self.workbook.save(str(path))
        logger.info("Đã xuất %s (%d dòng)", path, self.rows_in_file)
        self.written.append(path)
        self.workbook = None
        self.sheet = None
        self.rows_in_file = 0
        self.file_index += 1


class ExportService:
    """Ghi dữ liệu ra `<output_dir>/<site>/<base>_<n>.xlsx`, mỗi file tối đa `max_rows_per_file` dòng."""

    def __init__(
        self,
        repository,
        output_dir: str,
        max_rows_per_file: int = 2000,
    ) -> None:
        if max_rows_per_file < 1:
            raise ValueError("max_rows_per_file phải >= 1")
        self.repository = repository
        self.output_dir = Path(output_dir)
        self.max_rows_per_file = max_rows_per_file

    def export(self, base_file_name: str = "comments_export") -> list[Path]:
        """Xuất toàn bộ và trả danh sách file đã ghi (mọi sàn)."""
        logger.info("Lưu file vào: %s/<sàn>/", self.output_dir.resolve())

        total_products = self.repository.count_products()
        logger.info("Tổng số product: %d", total_products)

        writers: dict[str, _SiteWriter] = {}
        product_count = 0

        try:
            for product in self.repository.iter_products(EXPORT_PROJECTION):
                product_count += 1
                if product_count % 100 == 0:
                    logger.info("Đang xử lý product %d/%d", product_count, total_products)

                site = site_of(product)
                writer = writers.get(site)
                if writer is None:
                    writer = _SiteWriter(
                        self.output_dir / site, base_file_name, self.max_rows_per_file
                    )
                    writers[site] = writer

                link = product.get("link", "")
                name_item = product.get("name", "")
                is_first_row_of_product = True

                for idx, comment in enumerate(product.get("comments") or []):
                    content = comment.get("content", "")
                    if not content:
                        continue
                    comment_id = comment.get("id", str(idx))
                    tail = [site, comment.get("name", ""), comment.get("rating", 0)]
                    if is_first_row_of_product:
                        writer.append([link, name_item, comment_id, content, *tail])
                    else:
                        # Các dòng sau để trống 2 cột đầu cho dễ đọc (import forward-fill lại).
                        writer.append(["", "", comment_id, content, *tail])
                    # rows_in_file về 0 nghĩa là vừa sang file mới: file mới phải mở đầu
                    # bằng dòng có link + tên, nếu không import sẽ mất product.
                    is_first_row_of_product = writer.rows_in_file == 0
        finally:
            # Luôn flush workbook đang dở, kể cả khi cursor ném lỗi giữa chừng.
            for writer in writers.values():
                writer.flush()

        written = [path for writer in writers.values() for path in writer.written]
        logger.info(
            "Hoàn thành: %d product -> %d file Excel trên %d sàn (%s)",
            product_count,
            len(written),
            len(writers),
            ", ".join(sorted(writers)) or "không có",
        )
        return written
