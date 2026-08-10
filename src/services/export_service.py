"""
ExportService - xuất product + comment ra nhiều file Excel.

Nhận repository từ ngoài nên chạy y hệt cho cả Mongo lẫn in-memory (`--no-db`).
Duyệt bằng cursor để không nạp toàn bộ collection vào RAM.
"""
import logging
from pathlib import Path
from typing import Optional

from openpyxl import Workbook

logger = logging.getLogger(__name__)

HEADER = ["link", "name_item", "comments_id", "comments_content"]
EXPORT_PROJECTION = {"link": 1, "name": 1, "comments": 1}


class ExportService:
    """Ghi dữ liệu ra `<output_dir>/<base>_<n>.xlsx`, mỗi file tối đa `max_rows_per_file` dòng."""

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
        """Xuất toàn bộ và trả danh sách file đã ghi."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Lưu file vào: %s", self.output_dir.resolve())

        total_products = self.repository.count_products()
        logger.info("Tổng số product: %d", total_products)

        written: list[Path] = []
        workbook: Optional[Workbook] = None
        sheet = None
        rows_in_file = 0
        file_index = 1
        product_count = 0

        try:
            for product in self.repository.iter_products(EXPORT_PROJECTION):
                product_count += 1
                if product_count % 100 == 0:
                    logger.info("Đang xử lý product %d/%d", product_count, total_products)

                link = product.get("link", "")
                name_item = product.get("name", "")
                comments = product.get("comments") or []

                is_first_row_of_product = True
                for idx, comment in enumerate(comments):
                    content = comment.get("content", "")
                    if not content:
                        continue

                    if workbook is None:
                        workbook = Workbook()
                        sheet = workbook.active
                        sheet.title = "Comments"
                        sheet.append(HEADER)

                    comment_id = comment.get("id", str(idx))
                    if is_first_row_of_product:
                        sheet.append([link, name_item, comment_id, content])
                        is_first_row_of_product = False
                    else:
                        # Các dòng sau để trống 2 cột đầu cho dễ đọc.
                        sheet.append(["", "", comment_id, content])

                    rows_in_file += 1
                    if rows_in_file >= self.max_rows_per_file:
                        written.append(
                            self._save(workbook, base_file_name, file_index, rows_in_file)
                        )
                        workbook = None
                        sheet = None
                        rows_in_file = 0
                        file_index += 1
                        is_first_row_of_product = True
        finally:
            # Luôn flush workbook đang dở, kể cả khi cursor ném lỗi giữa chừng.
            if workbook is not None and rows_in_file > 0:
                written.append(
                    self._save(workbook, base_file_name, file_index, rows_in_file)
                )

        logger.info(
            "Hoàn thành: %d product -> %d file Excel", product_count, len(written)
        )
        return written

    def _save(
        self, workbook: Workbook, base_file_name: str, index: int, rows: int
    ) -> Path:
        path = self.output_dir / f"{base_file_name}_{index}.xlsx"
        workbook.save(str(path))
        logger.info("Đã xuất %s (%d dòng)", path, rows)
        return path
