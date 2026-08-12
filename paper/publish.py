"""
Ghép `paper/out/` vào site nhiều phiên bản và sinh lại trang chọn phiên bản.

Vì sao cần: `deploy.sh pages` cũ ĐÈ nguyên nhánh `gh-pages`, nên mỗi lần deploy là
bản trước biến mất. Khi bài báo đã gửi đi kèm một link, số liệu trên link đó không
được phép đổi dưới chân người phản biện. Ở đây mỗi lần deploy ghi vào `vN/` riêng,
link cũ giữ nguyên số cũ, còn `/` là trang liệt kê để chia sẻ một link duy nhất.

Không gọi trực tiếp; `deploy.sh pages` gọi hộ.
"""
import argparse
import json
import shutil
from pathlib import Path

# Số của từng phiên bản đọc từ metadata.json lúc train, KHÔNG chép tay: chép tay là
# nguồn số liệu thứ hai, và nó sẽ lệch với hình ngay lần deploy vội đầu tiên.
MODEL_TEN = {"svm": "SVM", "lstm": "LSTM", "nb": "Naive Bayes"}


def doc_metadata(path: Path) -> dict:
    meta = json.loads(path.read_text())
    ds, models = meta["dataset"], meta.get("models", {})
    return {
        "trained_at": meta.get("trained_at", ""),
        "total_rows": ds["total_rows"],
        "final_rows": ds["final_rows"],
        "label_counts": ds["label_counts"],
        "split": {k: meta["split"][k] for k in ("train", "test") if k in meta["split"]},
        "models": {
            k: round(v["metrics"]["macro_f1"], 3)
            for k, v in sorted(models.items(), key=lambda kv: -kv[1]["metrics"]["macro_f1"])
        },
    }


def nap_versions(site: Path) -> list[dict]:
    f = site / "versions.json"
    return json.loads(f.read_text()) if f.is_file() else []


def so(n: int) -> str:
    """4725 -> '4.725'. Dấu chấm ngăn hàng nghìn theo cách viết tiếng Việt."""
    return f"{n:,}".replace(",", ".")


def sinh_index(site: Path, versions: list[dict]) -> None:
    """Trang gốc: bảng các phiên bản, mới nhất trên cùng, kèm số liệu chính."""
    moi_nhat = versions[0]["id"] if versions else ""
    hang = []
    for i, v in enumerate(versions):
        # Thay dấu thập phân TỪNG SỐ MỘT. Thay trên cả dòng HTML thì dấu chấm
        # hàng nghìn của `so()` cũng bị đổi ngược lại thành dấu phẩy.
        f1 = " · ".join(f"{MODEL_TEN.get(k, k)} {s:.3f}".replace(".", ",")
                        for k, s in v["models"].items())
        nhan = '<span class="badge">mới nhất</span>' if i == 0 else ""
        ngay = v["trained_at"][:10]
        hang.append(f"""    <tr>
      <td><a href="{v['id']}/">{v['id']}</a> {nhan}<div class="mut">{v['label']}</div></td>
      <td>{ngay}</td>
      <td class="num">{so(v['final_rows'])}</td>
      <td class="num">{so(v['total_rows'])}</td>
      <td class="f1">{f1}</td>
    </tr>""")

    site.joinpath("index.html").write_text(f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phân tích cảm xúc bình luận – các phiên bản báo cáo</title>
<style>
:root {{ --bg:#fff; --fg:#16202a; --mut:#63748a; --line:#dfe4ea; --card:#fff;
        --accent:#2471a3; --shadow:0 1px 3px rgba(16,32,48,.09); }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#14181d; --fg:#e6eaee; --mut:#93a1b0; --line:#2a3138; --card:#1b2027;
          --accent:#5fa8dd; --shadow:0 1px 3px rgba(0,0,0,.4); }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; padding:2.5rem 1.5rem 4rem; background:var(--bg); color:var(--fg);
       font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
main {{ max-width:56rem; margin:0 auto; }}
h1 {{ font-size:1.7rem; margin:0 0 .3rem; letter-spacing:-.01em; }}
.sub {{ color:var(--mut); margin:0 0 2rem; }}
.wrap {{ border:1px solid var(--line); border-radius:.7rem; background:var(--card);
        box-shadow:var(--shadow); overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; min-width:38rem; }}
th, td {{ text-align:left; padding:.8rem 1rem; border-bottom:1px solid var(--line);
         vertical-align:top; }}
th {{ font-size:.78rem; text-transform:uppercase; letter-spacing:.04em; color:var(--mut);
     font-weight:600; }}
tr:last-child td {{ border-bottom:none; }}
td a {{ color:var(--accent); font-weight:600; font-size:1.05rem; text-decoration:none; }}
td a:hover {{ text-decoration:underline; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.f1 {{ font-size:.85rem; color:var(--mut); }}
.mut {{ color:var(--mut); font-size:.83rem; margin-top:.15rem; }}
.badge {{ display:inline-block; font-size:.68rem; font-weight:600; letter-spacing:.03em;
         text-transform:uppercase; padding:.15rem .45rem; border-radius:.3rem;
         background:var(--accent); color:#fff; vertical-align:.15em; }}
.note {{ color:var(--mut); font-size:.87rem; margin-top:1.5rem; }}
</style>
</head>
<body>
<main>
<h1>Phân tích cảm xúc bình luận thương mại điện tử</h1>
<p class="sub">Các phiên bản báo cáo. Mỗi phiên bản là một lần huấn luyện,
số liệu và hình đóng băng tại thời điểm đó.</p>

<div class="wrap">
<table>
  <thead><tr>
    <th>Phiên bản</th><th>Ngày train</th><th class="num">Mẫu huấn luyện</th>
    <th class="num">Dòng thô</th><th>macro-F1</th>
  </tr></thead>
  <tbody>
{chr(10).join(hang)}
  </tbody>
</table>
</div>

<p class="note">Link phiên bản (ví dụ <code>/{moi_nhat}/</code>) không thay đổi khi có
phiên bản mới &mdash; dùng nó khi cần trích dẫn số liệu cố định.</p>
</main>
</body>
</html>
""")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--site", required=True, help="Thư mục bản sao nhánh gh-pages")
    p.add_argument("--out", default="paper/out", help="Thư mục hình vừa build")
    p.add_argument("--metadata", default="paper/data/metadata.json")
    p.add_argument("--version", required=True, help="Mã phiên bản, ví dụ v3")
    p.add_argument("--label", default="", help="Mô tả ngắn phiên bản")
    a = p.parse_args()

    site, out = Path(a.site), Path(a.out)
    dich = site / a.version
    if dich.exists():
        shutil.rmtree(dich)          # deploy lại cùng mã version = ghi đè có chủ ý
    shutil.copytree(out, dich)

    ban = doc_metadata(Path(a.metadata))
    ban["id"] = a.version
    ban["label"] = a.label

    versions = [v for v in nap_versions(site) if v["id"] != a.version]
    versions.insert(0, ban)
    # Mới nhất lên đầu. Sắp theo trained_at chứ không theo thứ tự thêm vào, để
    # deploy bù một bản cũ không đẩy nó lên đầu bảng.
    versions.sort(key=lambda v: v["trained_at"], reverse=True)

    site.joinpath("versions.json").write_text(
        json.dumps(versions, ensure_ascii=False, indent=2)
    )
    sinh_index(site, versions)
    print(f"  {a.version}: {ban['final_rows']} mẫu, {len(versions)} phiên bản trên site")


if __name__ == "__main__":
    main()
