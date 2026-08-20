"""
Registry các sàn. Sàn được chọn theo hostname của URL nên `--links` và `--category`
đều dùng chung một đường: đưa URL vào, nhận đúng scraper ra.
"""
from typing import Optional
from urllib.parse import urlparse

from src.services.sites.base import SiteScraper
from src.services.sites.cellphones import CellphonesScraper
from src.services.sites.fptshop import FptShopScraper
from src.services.sites.tgdd import TgddScraper

SITE_CLASSES: tuple[type[SiteScraper], ...] = (
    TgddScraper,
    CellphonesScraper,
    FptShopScraper,
)


class UnknownSiteError(ValueError):
    """URL không thuộc sàn nào đã hỗ trợ."""


def site_class_for(url: str) -> type[SiteScraper]:
    host = (urlparse(url).hostname or "").lower()
    for site_class in SITE_CLASSES:
        if any(host == h or host.endswith("." + h) for h in site_class.hosts):
            return site_class
    supported = ", ".join(h for c in SITE_CLASSES for h in c.hosts)
    raise UnknownSiteError(f"Chưa hỗ trợ sàn của URL {url!r}. Đang hỗ trợ: {supported}")


def get_site(url: str, wait_timeout: Optional[float] = None) -> SiteScraper:
    return site_class_for(url)(wait_timeout=wait_timeout)


__all__ = ["SiteScraper", "UnknownSiteError", "get_site", "site_class_for"]
