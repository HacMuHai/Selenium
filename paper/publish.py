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
import re
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


def ma_phien_ban(version: str, trained_at: str) -> str:
    """'v3' + '2026-08-12T...' -> 'v3-12082026'.

    Ngày lấy từ metadata lúc train, không phải ngày deploy: deploy lại một bản cũ
    tháng sau vẫn phải ra đúng mã cũ, nếu không sẽ mọc thêm thư mục trùng nội dung.
    Truyền sẵn mã đầy đủ thì giữ nguyên, để deploy đè đúng một phiên bản.
    """
    if re.fullmatch(r"v\d+-\d{8}", version):
        return version
    nam, thang, ngay = trained_at[:4], trained_at[5:7], trained_at[8:10]
    return f"{version}-{ngay}{thang}{nam}"


def sinh_index(site: Path, versions: list[dict]) -> None:
    """Trang gốc: thanh chọn phiên bản + báo cáo, mặc định mở bản mới nhất.

    Báo cáo hiện qua `<iframe>` chứ không nhúng thẳng nội dung vào. Nhúng thẳng thì
    phải viết lại đường dẫn ảnh (`bang/x.png` -> `v2/bang/x.png`) và khởi động lại
    script lightbox của trang con - hai chỗ dễ hỏng âm thầm khi báo cáo đổi cấu trúc.
    Iframe giữ mỗi phiên bản đã lưu chạy y như lúc build, không đụng vào.
    """
    # Nhúng thẳng dữ liệu vào trang, không fetch versions.json: mở bằng file:// vẫn chạy.
    data = json.dumps([
        {
            "id": v["id"], "label": v["label"], "ngay": v["trained_at"][:10],
            "final_rows": so(v["final_rows"]), "total_rows": so(v["total_rows"]),
            # Thanh đầu trang hẹp -> viết tắt tên model. Tên đầy đủ có trong báo cáo.
            "f1": " · ".join(f"{k.upper()} {s:.3f}".replace(".", ",")
                             for k, s in v["models"].items()),
        }
        for v in versions
    ], ensure_ascii=False)

    site.joinpath("index.html").write_text(f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Phân tích cảm xúc bình luận – báo cáo</title>
<style>
:root {{ --bg:#fff; --fg:#16202a; --mut:#63748a; --line:#dfe4ea; --card:#fbfcfd;
        --accent:#2471a3; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#14181d; --fg:#e6eaee; --mut:#93a1b0; --line:#2a3138; --card:#1b2027;
          --accent:#5fa8dd; }} }}
* {{ box-sizing:border-box; }}
html, body {{ height:100%; }}
body {{ margin:0; display:flex; flex-direction:column; background:var(--bg); color:var(--fg);
       font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
header {{ flex:none; border-bottom:1px solid var(--line); background:var(--card);
         padding:.7rem 1.1rem; display:flex; align-items:center; gap:1rem;
         flex-wrap:wrap; }}
.title {{ font-weight:600; font-size:.95rem; margin-right:auto; }}
.title span {{ display:block; font-weight:400; font-size:.78rem; color:var(--mut); }}
.pick {{ display:flex; align-items:center; gap:.45rem; font-size:.85rem; color:var(--mut); }}
select {{ font:inherit; font-size:.88rem; color:var(--fg); background:var(--bg);
         border:1px solid var(--line); border-radius:.4rem; padding:.32rem 1.9rem .32rem .55rem;
         appearance:none; cursor:pointer;
         background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' \
width='10' height='6' viewBox='0 0 10 6'><path d='M1 1l4 4 4-4' fill='none' \
stroke='%2363748a' stroke-width='1.6' stroke-linecap='round'/></svg>");
         background-repeat:no-repeat; background-position:right .6rem center; }}
select:focus-visible {{ outline:2px solid var(--accent); outline-offset:1px; }}
.meta {{ font-size:.8rem; color:var(--mut); font-variant-numeric:tabular-nums; }}
.meta b {{ color:var(--fg); font-weight:600; }}
a.open {{ font-size:.8rem; color:var(--accent); text-decoration:none; white-space:nowrap; }}
a.open:hover {{ text-decoration:underline; }}
iframe {{ flex:1 1 auto; width:100%; border:0; min-height:0; }}
@media (max-width:34rem) {{ .meta {{ width:100%; order:9; }} }}
</style>
</head>
<body>
<header>
  <div class="title">Phân tích cảm xúc bình luận thương mại điện tử
    <span id="nhan"></span></div>
  <label class="pick">Phiên bản
    <select id="chon"></select>
  </label>
  <div class="meta" id="so"></div>
  <a class="open" id="rieng" href="#" target="_blank" rel="noopener">Mở riêng ↗</a>
</header>
<iframe id="khung" title="Báo cáo"></iframe>

<script>
const BAN = {data};
const chon = document.getElementById('chon');
const khung = document.getElementById('khung');

BAN.forEach((v, i) => chon.add(new Option(
  v.id + ' — ' + v.ngay + (i === 0 ? ' (mới nhất)' : ''), v.id)));

function mo(id, ghiLichSu) {{
  const v = BAN.find(x => x.id === id) || BAN[0];
  chon.value = v.id;
  khung.src = v.id + '/';
  document.getElementById('rieng').href = v.id + '/';
  document.getElementById('nhan').textContent = v.label;
  document.getElementById('so').innerHTML =
    '<b>' + v.final_rows + '</b> mẫu · ' + v.f1;
  document.title = 'Báo cáo ' + v.id + ' – Phân tích cảm xúc bình luận';
  // replaceState: đổi phiên bản không nên chèn thêm một bước vào nút Back.
  if (ghiLichSu) history.replaceState(null, '', v.id === BAN[0].id ? './' : '?v=' + v.id);
}}

chon.addEventListener('change', () => mo(chon.value, true));
// Mặc định bản mới nhất; ?v=v1 để chia sẻ link mở thẳng một phiên bản cũ.
mo(new URLSearchParams(location.search).get('v') || BAN[0].id, false);
</script>
</body>
</html>
""")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--site", required=True, help="Thư mục bản sao nhánh gh-pages")
    p.add_argument("--out", default="paper/out", help="Thư mục hình vừa build")
    p.add_argument("--metadata", default="paper/data/metadata.json")
    p.add_argument("--version", required=True, help="Mã phiên bản, ví dụ v3 (ngày tự thêm)")
    p.add_argument("--label", default="", help="Mô tả ngắn phiên bản")
    p.add_argument("--id-file", help="Ghi mã phiên bản đầy đủ ra file, cho deploy.sh đọc")
    a = p.parse_args()

    site, out = Path(a.site), Path(a.out)
    ban = doc_metadata(Path(a.metadata))
    ma = ma_phien_ban(a.version, ban["trained_at"])

    dich = site / ma
    if dich.exists():
        shutil.rmtree(dich)          # deploy lại cùng mã version = ghi đè có chủ ý
    shutil.copytree(out, dich)

    ban["id"] = ma
    ban["label"] = a.label
    if a.id_file:
        Path(a.id_file).write_text(ma)

    versions = [v for v in nap_versions(site) if v["id"] != ma]
    versions.insert(0, ban)
    # Mới nhất lên đầu. Sắp theo trained_at chứ không theo thứ tự thêm vào, để
    # deploy bù một bản cũ không đẩy nó lên đầu bảng.
    versions.sort(key=lambda v: v["trained_at"], reverse=True)

    site.joinpath("versions.json").write_text(
        json.dumps(versions, ensure_ascii=False, indent=2)
    )
    sinh_index(site, versions)
    print(f"  {ma}: {ban['final_rows']} mẫu, {len(versions)} phiên bản trên site")


if __name__ == "__main__":
    main()
