"""
Ghi chú phiên bản — NGUỒN DUY NHẤT cho cả ba nơi:

  1. Khối "Có gì mới" đầu báo cáo (`paper/gallery.py`)
  2. Mô tả trên trang chọn phiên bản (`paper/publish.py`)
  3. Tham số `--label` của `deploy.sh` (bỏ trống thì lấy từ đây)

Chép tay ba chỗ thì chắc chắn sẽ lệch nhau sau vài lần deploy.

CÁCH THÊM PHIÊN BẢN MỚI: chèn một dict vào ĐẦU `VERSIONS`, `id` là "v4", "v5"...
(không kèm ngày — `publish.py` tự gắn ngày train vào thành "v4-20092026").
"""

# Mới nhất lên đầu. `VERSIONS[0]` chính là phiên bản báo cáo hiện tại.
VERSIONS: list[dict] = [
    {
        "id": "v3",
        "tom_tat": "Thêm mô hình LSTM + PhoW2V, bảng kết quả 2 lớp, "
                   "sửa lỗi Naive Bayes đoán ra lớp không có dữ liệu",
        "muc": [
            (
                "Thêm mô hình thứ tư: LSTM + PhoW2V",
                "LSTM cũ khởi tạo vector từ ngẫu nhiên rồi tự học nghĩa từ 3.229 câu — "
                "quá ít. Bản mới nạp sẵn vector đã học từ 20&nbsp;GB văn bản tiếng Việt. "
                "Đo trên 5 lần chia dữ liệu: macro-F1 <b>0,772</b> so với <b>0,763</b> "
                "của bản cũ. Nhỏ, nhưng riêng lớp <i>trung lập</i> tăng mạnh: "
                "<b>58,9% → 70,2%</b>.",
            ),
            (
                "Thêm bảng kết quả 2 lớp",
                "Phần lớn bài báo cùng chủ đề chỉ phân tích cực/tiêu cực, bỏ lớp trung "
                "lập, nên con số của họ cao hơn. Bảng mới cho thấy cùng bộ dữ liệu này "
                "đặt về 2 lớp thì SVM đạt <b>91,5%</b> — tương đương các bài đã công bố. "
                "Bảng chính vẫn là 3 lớp.",
            ),
            (
                "Sửa lỗi Naive Bayes đoán ra lớp không có dữ liệu",
                "Mô hình duyệt danh sách nhãn cố định nên một lớp <b>không có mẫu huấn "
                "luyện nào</b> vẫn có thể được đoán ra. Chỉ lộ khi chạy bảng 2 lớp: NB "
                "đoán ra <i>trung lập</i> 5 lần dù chưa từng thấy nhãn đó. Kết quả 3 lớp "
                "không bị ảnh hưởng.",
            ),
        ],
    },
    {
        "id": "v2",
        "tom_tat": "Gán nhãn thêm 909 bình luận loa Bluetooth: 3.128 → 4.037 mẫu",
        "muc": [
            (
                "Mở rộng dữ liệu huấn luyện",
                "Gán nhãn thêm 909 bình luận loa Bluetooth (90 sản phẩm, chọn ngẫu "
                "nhiên). Tập huấn luyện <b>3.128 → 4.037 mẫu</b>.",
            ),
            (
                "Cân bằng lại tỉ trọng danh mục",
                "Điện thoại giảm từ 55,7% xuống ~43%, thêm nhóm loa ~22%. Phân bố nhãn "
                "cũng đổi theo vì mỗi danh mục có thiên hướng khác nhau.",
            ),
        ],
    },
    {
        "id": "v1",
        "tom_tat": "Bản đầu — 3.128 mẫu điện thoại/laptop/máy in, "
                   "so sánh Naive Bayes · SVM · LSTM",
        "muc": [
            (
                "Bản đầu tiên",
                "3.128 mẫu từ điện thoại, laptop, máy tính bảng, máy in. So sánh ba mô "
                "hình Naive Bayes, SVM và LSTM trên bài toán 3 lớp.",
            ),
        ],
    },
]

# Thuật ngữ dễ gây khựng khi đọc. Chỉ giải thích cái KHÔNG tra một câu là ra.
THUAT_NGU: list[tuple[str, str]] = [
    (
        "PhoW2V",
        "Bộ vector từ tiếng Việt huấn luyện sẵn của VinAI trên 20&nbsp;GB văn bản. "
        "Mỗi từ thành một dãy 100 số sao cho từ nghĩa gần nhau thì dãy số gần nhau. "
        "Nạp sẵn vào mô hình để nó không phải học nghĩa từ đầu chỉ bằng vài nghìn câu.",
    ),
    (
        "macro-F1",
        "Trung bình điểm F1 của cả ba lớp, mỗi lớp tính ngang nhau bất kể nhiều hay ít "
        "mẫu. Nghiêm khắc hơn accuracy: bỏ rơi lớp <i>trung lập</i> (chỉ 9,3% dữ liệu) "
        "là điểm tụt ngay, trong khi accuracy gần như không đổi.",
    ),
]


def _tim(version_id: str) -> dict | None:
    goc = version_id.split("-")[0]        # "v3-12082026" -> "v3"
    return next((v for v in VERSIONS if v["id"] == goc), None)


def tom_tat(version_id: str) -> str:
    """Mô tả một dòng, dùng cho trang chọn phiên bản. Không có thì trả chuỗi rỗng."""
    ban = _tim(version_id)
    return ban["tom_tat"] if ban else ""


def hien_tai() -> dict:
    """Phiên bản đang build. Báo cáo không biết mình là vN nên lấy bản mới nhất."""
    return VERSIONS[0]
