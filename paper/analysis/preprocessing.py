"""
Chuẩn hoá và tách từ cho comment TIẾNG VIỆT.

Thuần Python + `unicodedata` - KHÔNG import sklearn/tensorflow, để module này nạp được
ở mọi tiến trình (kể cả API chỉ hiển thị metrics đã lưu).

QUAN TRỌNG: sửa logic trong file này thì PHẢI tăng `PREPROCESSING_VERSION`. Nếu không,
model cũ vẫn nạp được nhưng predict sai âm thầm.
"""
import re
import unicodedata

PREPROCESSING_VERSION = "1.0"

# Chữ cái tiếng Việt (đã NFC) + chữ/số ASCII. Dùng để XOÁ mọi thứ KHÔNG thuộc nhóm này.
# Cố ý không dùng `string.punctuation` hay `[^a-z0-9]`: cách đó xoá sạch chữ có dấu.
_VN_CHARS = "a-z0-9àáâãèéêìíòóôõùúăđĩũơưăạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹý"
_PUNCT_RE = re.compile(rf"[^{_VN_CHARS}\s]+", re.UNICODE)

# Emoji mang tín hiệu cảm xúc mạnh nên KHÔNG xoá. Đổi thành token ascii `emj<hex>` để
# sống sót qua bước bỏ dấu câu bên dưới (bước đó chỉ giữ chữ tiếng Việt + a-z0-9).
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF❤⭐]",
    re.UNICODE,
)

_REPEAT_RE = re.compile(r"(.)\1{2,}", re.UNICODE)
_SPACE_RE = re.compile(r"\s+", re.UNICODE)

# Stopword tiếng Việt. CỐ Ý KHÔNG chứa từ phủ định / mức độ / đánh giá:
# không, chẳng, chưa, đừng, rất, quá, hơi, lắm, nhất, hơn, kém, tệ, tốt, ổn...
# Bỏ "không" khỏi "không tốt" là đảo ngược nhãn.
VI_STOPWORDS = frozenset(
    """
    và với của cho từ tại về theo trong ngoài trên dưới giữa cùng như là thì mà rồi
    nên nếu vì bởi do nhưng còn hay hoặc cũng đã đang sẽ vẫn cứ lại nữa mới
    này kia đó ấy nào gì ai đâu vậy nhé nha nhỉ ạ ừ à ơi
    tôi tao mình tớ ta chúng bạn cậu mày nó họ anh chị em con ông bà cô chú
    các những mọi từng mỗi một hai ba bốn năm sáu bảy tám chín mười
    được bị có thấy làm đi đến ra vào lên xuống qua
    khi lúc giờ ngày tháng hôm nay mai bữa
    ơ ờ ừm dạ vâng
    cái chiếc bên phía chỗ nơi
    để thôi luôn ngay đều toàn
    """.split()
)


def normalize_text(value: object) -> str:
    """Chuẩn hoá 1 comment về dạng so sánh/tách từ được.

    NFC là bắt buộc: tiếng Việt gõ được bằng tổ hợp (e + dấu) hoặc dựng sẵn (é);
    không chuẩn hoá thì cùng một chữ ra hai token khác nhau.
    """
    text = unicodedata.normalize("NFC", str(value) if value is not None else "")
    text = text.lower()
    text = _EMOJI_RE.sub(lambda m: f" emj{ord(m.group(0)):x} ", text)
    text = _REPEAT_RE.sub(r"\1\1", text)     # "tốtttt" -> "tốtt", vẫn giữ sắc thái nhấn mạnh
    text = _PUNCT_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def tokenize(value: object, remove_stopwords: bool = True) -> list[str]:
    """Tách từ theo khoảng trắng sau khi chuẩn hoá."""
    tokens = normalize_text(value).split()
    if remove_stopwords:
        tokens = [t for t in tokens if t not in VI_STOPWORDS]
    return tokens


def add_bigrams(tokens: list[str]) -> list[str]:
    """Bù cho việc không tách được từ ghép: "điện thoại" xuất hiện dưới dạng bigram.

    Trả unigram + bigram nối bằng "_".
    """
    return tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
