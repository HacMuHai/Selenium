"""
Nạp vector từ tiền huấn luyện (PhoW2V) cho LSTM.

File gốc `word2vec_vi_syllables_100dims.txt` nặng 1,18 GB / 979.460 từ - không thể để
trong repo và không cần thiết: corpus chỉ dùng ~7.000 từ. `trim()` cắt một lần ra file
`.npz` 1,9 MB, sau đó pipeline chỉ đọc file nhỏ này.

Dùng bản SYLLABLE chứ không phải WORD: `tokenize()` tách theo khoảng trắng, không có bộ
tách từ ghép tiếng Việt. Bản word-level cần "điện_thoại" - thả vào đây thì hầu hết token
trượt khỏi embedding mà KHÔNG báo lỗi, chỉ âm thầm cho kết quả kém.
"""
import logging
from pathlib import Path
from typing import Iterable, Optional

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path("vectors/phow2v_syllables_100.npz")
EMBEDDING_DIM = 100


def trim(source: str | Path, out_path: str | Path, vocab: Iterable[str]) -> int:
    """Đọc file word2vec dạng text, giữ lại các từ trong `vocab`, ghi ra `.npz`.

    Đọc theo dòng và chỉ parse vector khi từ đó cần: parse cả 979.460 dòng mất vài phút
    và ~800 MB RAM, trong khi chỉ ~5.000 dòng là có ích.
    """
    can = set(vocab)
    words: list[str] = []
    vecs: list[np.ndarray] = []
    with open(source, encoding="utf-8") as fh:
        next(fh)                                  # dòng đầu là "<số từ> <số chiều>"
        for line in fh:
            i = line.index(" ")
            if line[:i] in can:
                words.append(line[:i])
                vecs.append(np.fromstring(line[i + 1:], sep=" ", dtype=np.float32))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_path, words=np.array(words), vectors=np.vstack(vecs))
    logger.info("Cắt embedding: %d/%d từ -> %s", len(words), len(can), out_path)
    return len(words)


def load(path: str | Path = DEFAULT_PATH) -> Optional[dict[str, np.ndarray]]:
    """Trả `None` nếu chưa có file - gọi nơi dùng tự quyết định fallback, không ném lỗi."""
    path = Path(path)
    if not path.is_file():
        return None
    z = np.load(path, allow_pickle=True)
    return dict(zip(z["words"].tolist(), z["vectors"]))


def build_matrix(
    word_index: dict[str, int],
    vectors: dict[str, np.ndarray],
    vocab_size: int,
    dim: int = EMBEDDING_DIM,
    seed: int = 42,
) -> tuple[np.ndarray, int]:
    """Ma trận embedding khởi tạo từ `vectors`; từ không có thì giữ giá trị ngẫu nhiên.

    Ngẫu nhiên chứ không phải 0: hàng toàn 0 làm gradient của những từ đó chết cứng,
    từ hiếm sẽ không bao giờ học được gì.
    """
    matrix = np.random.RandomState(seed).normal(0, 0.1, (vocab_size, dim)).astype("float32")
    hit = 0
    for word, idx in word_index.items():
        if idx < vocab_size:
            vec = vectors.get(word)
            if vec is not None:
                matrix[idx] = vec
                hit += 1
    return matrix, hit
