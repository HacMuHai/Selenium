"""
Naive Bayes tự cài đặt (port từ repo gốc), sửa 3 điểm:

1. Preprocessing tiếng Việt thay cho PorterStemmer + stopwords tiếng Anh (vốn vô dụng
   với tiếng Việt: stemmer cắt hậu tố tiếng Anh, stopword list không chứa từ tiếng Việt nào).
2. Thêm bigram để bù việc không tách được từ ghép ("điện thoại").
3. **Sửa bug từ chưa từng thấy**: bản gốc dùng `.get(token, 0)`. `log(p)` luôn ÂM, nên
   token lạ được điểm 0 hoá ra "tốt hơn" mọi token đã biết -> câu càng lạ càng được ưu ái.
   Bản này trả về log-prob của Laplace smoothing cho token lạ.
"""
import math
from collections import defaultdict
from pathlib import Path

import joblib
import pandas as pd

from paper.analysis.metrics import LABELS
from paper.analysis.models.base import SentimentModel
from paper.analysis.preprocessing import PREPROCESSING_VERSION, add_bigrams, tokenize

ARTIFACT = "naive_bayes.joblib"
SMOOTHING = 1.0


class NaiveBayesModel(SentimentModel):
    name = "nb"

    def __init__(self) -> None:
        # Các lớp THỰC SỰ có trong dữ liệu train. Duyệt hằng LABELS toàn cục thay cho
        # danh sách này khiến một lớp không có mẫu nào vẫn được đoán ra: lớp rỗng có
        # `default_log_likelihood = log(1/|V|)` cao hơn mọi lớp có dữ liệu, nên câu
        # toàn từ lạ sẽ rơi vào nó. Chỉ lộ ra khi train trên tập bỏ bớt lớp.
        self.labels: tuple[str, ...] = LABELS
        self.log_prior: dict[str, float] = {}
        self.log_likelihood: dict[str, dict[str, float]] = {}
        self.default_log_likelihood: dict[str, float] = {}

    # ----- huấn luyện -----

    @staticmethod
    def _features(text: object) -> list[str]:
        return add_bigrams(tokenize(text))

    def train(self, train_df: pd.DataFrame, class_weight: bool = True) -> None:
        total_docs = len(train_df)
        present = set(train_df["sentiment"])
        self.labels = tuple(label for label in LABELS if label in present)

        # Đếm token theo lớp, đồng thời dựng VOCAB TOÀN CỤC.
        per_label_counts: dict[str, dict[str, int]] = {}
        vocabulary: set[str] = set()
        for label in self.labels:
            counts: dict[str, int] = defaultdict(int)
            for text in train_df[train_df["sentiment"] == label]["text"]:
                for token in self._features(text):
                    counts[token] += 1
            per_label_counts[label] = counts
            vocabulary.update(counts)

        # |V| PHẢI là vocab toàn cục, giống nhau cho mọi lớp. Dùng vocab riêng từng lớp
        # làm mẫu số lệch nhau -> lớp ít dữ liệu (vocab nhỏ) được ưu ái token lạ và
        # nuốt hết dự đoán. Đây chính là bug đã quan sát được: NB dồn 303/328 negative
        # vào neutral.
        vocab_size = max(len(vocabulary), 1)

        for label in self.labels:
            counts = per_label_counts[label]
            subset = train_df[train_df["sentiment"] == label]["text"]
            total_tokens = sum(counts.values())
            denominator = total_tokens + SMOOTHING * vocab_size

            self.log_likelihood[label] = {
                token: math.log((count + SMOOTHING) / denominator)
                for token, count in counts.items()
            }
            # Token chưa từng thấy: vẫn là một số ÂM, không phải 0.
            self.default_log_likelihood[label] = math.log(SMOOTHING / denominator)

            if class_weight:
                # Prior đều -> không để lớp đa số nuốt hết
                self.log_prior[label] = math.log(1.0 / len(self.labels))
            else:
                n_docs = len(subset)
                self.log_prior[label] = math.log(n_docs / total_docs) if n_docs else -1e9

    # ----- dự đoán -----

    def predict(self, text: str) -> tuple[str, dict[str, float]]:
        tokens = self._features(text)
        scores: dict[str, float] = {}
        for label in self.labels:
            likelihood = self.log_likelihood.get(label, {})
            fallback = self.default_log_likelihood.get(label, -1e9)
            scores[label] = self.log_prior.get(label, -1e9) + sum(
                likelihood.get(token, fallback) for token in tokens
            )
        best = max(scores, key=lambda k: scores[k])
        return best, scores

    # ----- lưu / nạp -----

    def save(self, models_dir: Path) -> None:
        models_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "version": PREPROCESSING_VERSION,
                "labels": list(self.labels),
                "log_prior": self.log_prior,
                "log_likelihood": self.log_likelihood,
                "default_log_likelihood": self.default_log_likelihood,
            },
            models_dir / ARTIFACT,
        )

    @classmethod
    def load(cls, models_dir: Path) -> "NaiveBayesModel":
        payload = joblib.load(models_dir / ARTIFACT)
        cls._check_version(payload.get("version"))
        model = cls()
        model.labels = tuple(payload.get("labels", LABELS))
        model.log_prior = payload["log_prior"]
        model.log_likelihood = payload["log_likelihood"]
        model.default_log_likelihood = payload["default_log_likelihood"]
        return model
