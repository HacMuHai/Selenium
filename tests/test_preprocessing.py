"""
Test chuẩn hoá tiếng Việt. Ca quan trọng nhất: KHÔNG được xoá mất chữ có dấu, và
KHÔNG được lọc mất từ phủ định.
"""
import unicodedata

import pytest

from src.analysis.preprocessing import (
    VI_STOPWORDS,
    add_bigrams,
    normalize_text,
    tokenize,
)


def test_giu_nguyen_chu_co_dau():
    # "!!!" bị thu gọn còn "!!" rồi bị xoá ở bước bỏ dấu câu
    assert normalize_text("Sản phẩm TỐT!!!") == "sản phẩm tốt"


def test_giu_du_bo_chu_cai_tieng_viet():
    """Lỗi kinh điển: regex bỏ dấu câu xoá luôn ă â ê ô ơ ư đ và 5 thanh."""
    text = "ăn âm ê ô ơ ư đủ à á ả ã ạ"
    assert normalize_text(text) == text


def test_hai_cach_go_dau_cho_cung_ket_qua():
    """Tổ hợp (NFD) và dựng sẵn (NFC) phải ra cùng token, nếu không là lỗi âm thầm."""
    assert normalize_text("tốt") == normalize_text(unicodedata.normalize("NFD", "tốt"))


def test_thu_gon_ky_tu_lap():
    assert normalize_text("tốtttttt") == "tốtt"
    assert normalize_text("oke") == "oke"          # không đụng vào chữ bình thường


def test_bo_dau_cau_va_gom_khoang_trang():
    assert normalize_text("Máy   ok,  giá rẻ!!!") == "máy ok giá rẻ"


def test_emoji_thanh_token_rieng_khong_bi_xoa():
    out = normalize_text("sản phẩm tốt 👍")
    assert "sản phẩm tốt" in out
    assert "emj" in out, "emoji phải sống sót dưới dạng token, không bị xoá"


def test_none_va_so_khong_lam_no():
    assert normalize_text(None) == ""
    assert normalize_text(12345) == "12345"


@pytest.mark.parametrize("word", ["không", "chẳng", "chưa", "rất", "quá", "lắm", "tệ", "tốt"])
def test_tu_phu_dinh_va_muc_do_khong_phai_stopword(word):
    """Bỏ 'không' khỏi 'không tốt' là đảo ngược nhãn."""
    assert word not in VI_STOPWORDS


def test_tokenize_giu_tu_phu_dinh():
    tokens = tokenize("sản phẩm này không tốt")
    assert "không" in tokens and "tốt" in tokens


def test_tokenize_loc_stopword():
    tokens = tokenize("máy của tôi và bạn")
    assert "máy" in tokens
    assert "của" not in tokens and "tôi" not in tokens


def test_tokenize_giu_stopword_khi_tat():
    assert "của" in tokenize("máy của tôi", remove_stopwords=False)


def test_add_bigrams():
    assert add_bigrams(["điện", "thoại", "tốt"]) == [
        "điện", "thoại", "tốt", "điện_thoại", "thoại_tốt",
    ]


def test_add_bigrams_mot_token():
    assert add_bigrams(["tốt"]) == ["tốt"]
