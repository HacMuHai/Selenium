"""
Test phần chọn sàn theo URL và phần parse dữ liệu API của CellphoneS / FPT Shop.

Không đụng mạng: chỉ kiểm tra logic thuần. Selector DOM vẫn phải smoke-test thủ công
vì phụ thuộc HTML của sàn (xem README).
"""
import pytest

from src.services.sites import (
    UnknownSiteError,
    site_class_for,
)
from src.services.sites.cellphones import CellphonesScraper
from src.services.sites.fptshop import FptShopScraper
from src.services.sites.tgdd import TgddScraper


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.thegioididong.com/sac-cap", TgddScraper),
        ("https://thegioididong.com/dtdd", TgddScraper),
        ("https://cellphones.com.vn/mobile.html", CellphonesScraper),
        ("https://cellphones.com.vn/dien-thoai-samsung-galaxy-a17-5g.html", CellphonesScraper),
        ("https://fptshop.com.vn/dien-thoai", FptShopScraper),
        ("https://fptshop.com.vn/dien-thoai/samsung-galaxy-s25-ultra", FptShopScraper),
    ],
)
def test_chon_dung_san_theo_hostname(url, expected):
    assert site_class_for(url) is expected


def test_url_la_de_khong_bi_nham_thanh_san_da_ho_tro():
    # "fptshop.com.vn.evil.com" kết thúc bằng chuỗi khác nên không được khớp.
    with pytest.raises(UnknownSiteError):
        site_class_for("https://fptshop.com.vn.evil.com/dien-thoai")


def test_url_khong_thuoc_san_nao_bao_loi_kem_danh_sach_ho_tro():
    with pytest.raises(UnknownSiteError, match="cellphones.com.vn"):
        site_class_for("https://shopee.vn/abc")


# ----- CellphoneS -----


def test_cps_parse_review_lay_sao_tu_rating_id():
    parsed = CellphonesScraper()._parse_review(
        {"content": "Máy chạy mượt", "rating_id": 4, "customer": {"fullname": "An"}}
    )

    assert parsed["name"] == "An"
    assert parsed["content"] == "Máy chạy mượt"
    assert parsed["rating"] == 4
    assert parsed["id"]


def test_cps_parse_review_thieu_customer_va_rating():
    parsed = CellphonesScraper()._parse_review({"content": "Tạm ổn"})

    assert parsed["name"] == ""
    assert parsed["rating"] == 0


def test_cps_parse_review_bo_qua_noi_dung_rong():
    assert CellphonesScraper()._parse_review({"content": "   ", "rating_id": 5}) is None


# ----- FPT Shop -----


def test_fpt_parse_comment_giu_diem_va_ten():
    parsed = FptShopScraper()._parse_comment(
        {"content": "Pin trâu", "score": 5, "fullName": "Bình", "isAdministrator": False}
    )

    assert parsed == {
        "id": parsed["id"],
        "name": "Bình",
        "content": "Pin trâu",
        "rating": 5,
    }


def test_fpt_parse_comment_score_null_thanh_0():
    parsed = FptShopScraper()._parse_comment({"content": "Giá bao nhiêu ạ", "score": None})

    assert parsed["rating"] == 0


def test_fpt_parse_comment_bo_phan_hoi_cua_nhan_vien():
    item = {"content": "Chào anh", "isAdministrator": True, "fullName": "FPT Shop"}

    assert FptShopScraper()._parse_comment(item) is None


def test_fpt_parse_comment_go_the_html():
    parsed = FptShopScraper()._parse_comment(
        {"content": "<p>Máy <strong>đẹp</strong></p>", "score": 5}
    )

    assert "<" not in parsed["content"]
    assert "đẹp" in parsed["content"]
