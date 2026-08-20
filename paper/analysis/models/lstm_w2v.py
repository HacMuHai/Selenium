"""
LSTM khởi tạo bằng vector PhoW2V thay vì ngẫu nhiên.

Chỉ khác `LSTMModel` ở lớp Embedding - mọi thứ còn lại giữ nguyên để phép so sánh
"random init vs tiền huấn luyện" đo đúng một biến.

Embedding để TINH CHỈNH TIẾP (`trainable=True`), không đóng băng. Đo thực tế trên bộ
này: đóng băng cho macro-F1 0,584 so với 0,799 khi tinh chỉnh - 5 epoch không đủ để
phần còn lại của mạng học bù cho lớp embedding đứng yên.

Thiếu file vector thì tự lùi về khởi tạo ngẫu nhiên và ghi WARNING, không ném lỗi:
người clone repo về mà chưa tải PhoW2V vẫn train được cả pipeline.
"""
import logging

import pandas as pd

from paper.analysis import embeddings
from paper.analysis.models.lstm import EMBEDDING_DIM, VOCAB_SIZE, LSTMModel

logger = logging.getLogger(__name__)

ARTIFACT_MODEL = "lstm_w2v.keras"
ARTIFACT_META = "lstm_w2v_meta.joblib"


class LSTMW2VModel(LSTMModel):
    name = "lstm_w2v"
    artifact_model = ARTIFACT_MODEL
    artifact_meta = ARTIFACT_META

    def __init__(self, epochs: int = 5, seed: int = 42, vectors_path=None) -> None:
        super().__init__(epochs=epochs, seed=seed)
        self.vectors_path = vectors_path or embeddings.DEFAULT_PATH
        self._matrix = None

    def train(self, train_df: pd.DataFrame, class_weight: bool = True) -> None:
        # Ma trận phải dựng SAU khi tokenizer có word_index, mà tokenizer chỉ tồn tại
        # bên trong train() của lớp cha. Nạp vector trước, ghép trong _embedding_layer().
        self._vectors = embeddings.load(self.vectors_path)
        if self._vectors is None:
            logger.warning(
                "Không thấy %s - lstm_w2v sẽ khởi tạo ngẫu nhiên như lstm thường. "
                "Tải PhoW2V rồi chạy: python -m src.analyze embeddings <file.txt>",
                self.vectors_path,
            )
        super().train(train_df, class_weight=class_weight)

    def _embedding_layer(self):
        import tensorflow as tf

        if not getattr(self, "_vectors", None):
            return super()._embedding_layer()

        matrix, hit = embeddings.build_matrix(
            self.tokenizer.word_index, self._vectors, VOCAB_SIZE, EMBEDDING_DIM, self.seed
        )
        dung = min(len(self.tokenizer.word_index), VOCAB_SIZE)
        logger.info("lstm_w2v: nạp %d/%d từ từ PhoW2V (%.1f%%)", hit, dung, hit / dung * 100)
        return tf.keras.layers.Embedding(
            VOCAB_SIZE, EMBEDDING_DIM, weights=[matrix], trainable=True
        )
