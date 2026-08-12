"""
ENTRYPOINT RIÊNG cho phân tích cảm xúc. Chạy từ repo root:

    python -m src.analyze train    [--models nb,svm,lstm]
    python -m src.analyze evaluate [--report report.html] [--csv metrics.csv]
    python -m src.analyze predict   --text "Sản phẩm dùng rất tốt"
    python -m src.analyze predict   --input data --output data_predicted --model svm

Độc lập hoàn toàn với crawler (`src/main.py`) và với MongoDB - không import, không kết nối.
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from src.analysis import metrics
from src.analysis.dataset import describe_split, load_tagged_dataset, split_dataset
from src.analysis.predictor import ModelNotTrained, Predictor
from src.analysis.registry import available_names, parse_model_list
from src.analysis.report import render_csv, render_html
from src.analysis.trainer import Trainer, load_metadata
from src.config.logging_config import setup_logging
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        prog="python -m src.analyze",
        description="Phân tích cảm xúc comment tiếng Việt: Naive Bayes / SVM / LSTM.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--log-level", default=settings.log_level)
    parser.add_argument("--models-dir", default=settings.models_dir)
    sub = parser.add_subparsers(dest="command", required=True)

    p_train = sub.add_parser("train", help="Huấn luyện và đánh giá model")
    p_train.add_argument("--models", default=",".join(available_names()),
                         help="Danh sách model, phân tách bằng dấu phẩy")
    p_train.add_argument("--tag-dir", default=settings.tag_dir,
                         help="Thư mục Excel đã gán nhãn")
    p_train.add_argument("--test-size", type=float, default=settings.test_size)
    p_train.add_argument("--seed", type=int, default=settings.random_seed)
    p_train.add_argument("--epochs", type=int, default=5, help="Số epoch của LSTM")
    p_train.add_argument("--no-class-weight", dest="class_weight", action="store_false",
                         help="Tắt cân bằng trọng số lớp")
    p_train.add_argument("--report", nargs="?", const="report.html",
                         help="Xuất luôn HTML sau khi train")

    p_eval = sub.add_parser("evaluate", help="Xuất báo cáo từ metadata đã có, không train lại")
    p_eval.add_argument("--report", default="report.html")
    p_eval.add_argument("--csv", help="Xuất thêm bảng metrics dạng CSV")

    p_pred = sub.add_parser("predict", help="Dự đoán 1 đoạn text hoặc cả thư mục Excel")
    p_pred.add_argument("--model", default=settings.default_model)
    group = p_pred.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="Dự đoán một đoạn text")
    group.add_argument("--input", help="Thư mục Excel chưa gán nhãn")
    p_pred.add_argument("--output", help="Thư mục ghi kết quả (bắt buộc khi dùng --input)")
    return parser


def _print_summary(evaluations: dict, results: dict, baseline: dict) -> None:
    print()
    print(f"{'model':<10}{'macro-F1':>10}{'accuracy':>10}{'train(s)':>10}")
    print("-" * 40)
    for name in sorted(evaluations, key=lambda n: -evaluations[n]["macro_f1"]):
        m = evaluations[name]
        secs = results[name].train_seconds if name in results else 0.0
        print(f"{name:<10}{m['macro_f1']:>10.3f}{m['accuracy']:>10.3f}{secs:>10.1f}")
    print("-" * 40)
    print(f"{'baseline':<10}{baseline['macro_f1']:>10.3f}{baseline['accuracy']:>10.3f}"
          f"{'-':>10}   (luôn đoán \"{baseline['label']}\")")
    print()


def cmd_train(args: argparse.Namespace) -> int:
    names = parse_model_list(args.models)
    frame, stats = load_tagged_dataset(args.tag_dir)
    train_df, test_df = split_dataset(frame, args.test_size, args.seed)
    split_info = describe_split(train_df, test_df)
    logger.info("Chia dữ liệu: train=%d test=%d", len(train_df), len(test_df))

    trainer = Trainer(args.models_dir, seed=args.seed)
    results = trainer.train(names, train_df, class_weight=args.class_weight, epochs=args.epochs)
    evaluations = trainer.evaluate(names, test_df)
    baseline = metrics.majority_baseline(list(test_df["sentiment"]))

    path = trainer.write_metadata(
        stats, split_info, results, evaluations, baseline, args.test_size
    )
    logger.info("Đã ghi %s", path)
    _print_summary(evaluations, results, baseline)

    if args.report:
        metadata = load_metadata(args.models_dir)
        Path(args.report).write_text(render_html(metadata), encoding="utf-8")
        logger.info("Đã ghi %s", args.report)
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    metadata = load_metadata(args.models_dir)
    if metadata is None:
        logger.error("Chưa có model. Chạy trước: python -m src.analyze train")
        return 2

    Path(args.report).write_text(render_html(metadata), encoding="utf-8")
    logger.info("Đã ghi %s", args.report)
    if args.csv:
        Path(args.csv).write_text(render_csv(metadata), encoding="utf-8")
        logger.info("Đã ghi %s", args.csv)

    baseline = metadata.get("baseline", {})
    print()
    for name, info in sorted(
        metadata.get("models", {}).items(),
        key=lambda kv: -kv[1].get("metrics", {}).get("macro_f1", 0),
    ):
        m = info.get("metrics", {})
        print(f"{name:<10} macro-F1={m.get('macro_f1', 0):.3f}  accuracy={m.get('accuracy', 0):.3f}")
    print(f"{'baseline':<10} macro-F1={baseline.get('macro_f1', 0):.3f}  "
          f"accuracy={baseline.get('accuracy', 0):.3f}")
    print()
    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    predictor = Predictor(args.models_dir)

    if args.text:
        result = predictor.predict_text(args.text, args.model)
        print(f"\n  model     : {result['model']}")
        print(f"  sentiment : {result['sentiment']}")
        for label, score in sorted(result["scores"].items(), key=lambda kv: -kv[1]):
            print(f"    {label:<10}{score:>10.4f}")
        print()
        return 0

    if not args.output:
        logger.error("--input phải đi kèm --output")
        return 2
    files = predictor.predict_dir(args.input, args.output, args.model)
    logger.info("Đã ghi %d file vào %s", len(files), args.output)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)
    try:
        if args.command == "train":
            return cmd_train(args)
        if args.command == "evaluate":
            return cmd_evaluate(args)
        return cmd_predict(args)
    except (ValueError, FileNotFoundError, ModelNotTrained) as exc:
        logger.error("%s", exc)
        return 2
    except KeyboardInterrupt:
        logger.warning("Đã dừng theo yêu cầu người dùng")
        return 130
    except Exception:
        logger.exception("Chạy thất bại")
        return 1


if __name__ == "__main__":
    sys.exit(main())
