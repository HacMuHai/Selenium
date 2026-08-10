# Research — Tiền xử lý tiếng Việt & xử lý lệch lớp

## 1. Vì sao preprocessing gốc sai với tiếng Việt

`NaiveBayesModel.preprocess_tweet` hiện làm 3 việc, cả 3 đều hỏng với tiếng Việt:

| Bước gốc | Vấn đề |
|---|---|
| `PorterStemmer().stem(token)` | Thuật toán cắt hậu tố tiếng Anh (-ing, -ed, -s). Tiếng Việt không biến hình → cắt bừa, làm hỏng từ ("dùng" → "dùng" may mắn không đổi, nhưng "sạc" / "sac" thì tuỳ token) |
| `stopwords.words("english")` | Không chứa một từ tiếng Việt nào → lọc được 0 từ |
| `str.maketrans("", "", string.punctuation)` | Giữ được, nhưng bỏ luôn emoji/ký tự lặp vốn mang tín hiệu cảm xúc mạnh trong comment |

Ngoài ra `stemmer`/`stopwords_set` được **khởi tạo lại trong mỗi lần gọi** → chậm khi chạy
hàng trăm nghìn dòng.

## 2. Phương án thay thế (không thêm thư viện)

Quyết định: viết `src/analysis/preprocessing.py` thuần Python + `unicodedata`.

```
normalize_text(s):
    NFC normalize (tiếng Việt có 2 cách gõ dấu: tổ hợp vs dựng sẵn -> phải chuẩn hoá,
                   nếu không "tốt" gõ 2 kiểu sẽ thành 2 token khác nhau)
    lowercase
    thu gọn ký tự lặp:  "tốtttttt" -> "tốtt"   (giữ 2 ký tự, vẫn phân biệt được nhấn mạnh)
    tách emoji ra thành token riêng (giữ, không xoá)
    bỏ dấu câu, gom khoảng trắng
tokenize(s) -> list[str]  # tách theo khoảng trắng
```

**Stopword tiếng Việt**: danh sách ~200 từ tự viết trong module (`và, là, của, thì, mà, ở, cho,
những, các, được, ...`). Cố ý **KHÔNG** đưa vào danh sách các từ phủ định/mức độ
(`không, chẳng, chưa, rất, quá, hơi, lắm`) — đây chính là tín hiệu cảm xúc, lọc đi là tự bắn vào chân.

**Bù cho việc không tách được từ ghép**: tiếng Việt "điện thoại" là 2 âm tiết. Không dùng
underthesea thì bù bằng **n-gram (1,2)** ở `TfidfVectorizer` → bigram "điện thoại" tự xuất hiện.
Với Naive Bayes cũng dùng bigram tương tự.

*Đánh đổi đã chấp nhận*: tách từ kém chính xác hơn underthesea/pyvi, đổi lại không thêm
dependency (underthesea kéo theo torch ở bản mới) và chạy nhanh hơn nhiều khi predict 250k dòng.

## 3. Lệch lớp — vì sao accuracy là chỉ số sai

Phân bố: neutral 76% · negative 15.7% · positive 8.3%.

- Model "luôn trả neutral" đạt **accuracy 76%**, macro-F1 chỉ **0.288**.
- Quan sát thực tế khi chạy thử: LSTM giữ `val_accuracy` đứng yên 0.8684 suốt 5 epoch — đúng
  hành vi của model đã sụp về lớp đa số.

**Chỉ số phải báo cáo**:
- `macro-F1` (chỉ số chính để so sánh model)
- `precision/recall/F1` từng lớp
- confusion matrix 3×3
- accuracy (giữ, nhưng luôn kèm baseline "luôn đoán neutral" để đối chiếu)

**Xử lý khi train**:
- SVM: `SVC(class_weight="balanced")` — sklearn tự nhân trọng số nghịch đảo tần suất
- LSTM: truyền `class_weight` vào `model.fit()`
- Naive Bayes: log prior đã phản ánh tần suất; thêm cờ `balanced_prior` để dùng prior đều
  (`log(1/3)`) thay vì prior theo tần suất

Cố ý **KHÔNG** oversample: 3160 mẫu duy nhất, lớp positive chỉ vài trăm — nhân bản sẽ overfit.

## 4. Chống rò rỉ dữ liệu (data leakage)

3160 nội dung duy nhất / 4600 dòng. Nếu split trước khi khử trùng, cùng một câu comment sẽ
nằm ở CẢ train lẫn test → điểm số ảo cao.

**Bắt buộc**: khử trùng theo nội dung đã chuẩn hoá **TRƯỚC** khi `train_test_split`,
và dùng `stratify=y` để giữ tỷ lệ lớp ở cả 2 tập.

62 nội dung mâu thuẫn nhãn: bỏ hẳn (không đoán bừa nhãn nào đúng), ghi log số lượng đã bỏ.

## 5. Ghi chú kỹ thuật cho LSTM

Code gốc: `self.max_length = max(len(x) for x in X_train)`.

Text dài nhất **2246 ký tự** → mọi chuỗi bị pad tới độ dài đó. Hệ quả: ma trận khổng lồ,
train chậm, và phần lớn là số 0 vô nghĩa.

Sửa: `max_length = percentile(lengths, 95)`, cắt bớt phần dư. Ghi giá trị vào metadata để
lúc predict dùng đúng con số đã train.

`num_words=5000` giữ nguyên; vốn từ tiếng Việt của 3160 comment không vượt quá nhiều.
