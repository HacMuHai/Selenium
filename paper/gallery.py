"""
Sinh `out/index.html` - trang xem lại toàn bộ hình đã render.

`out/` phải TỰ CHỨA: gửi riêng mình nó cho người khác là xem được ngay, không cần
repo, không cần server. Vì vậy ảnh mẫu được COPY vào `out/anh-mau/` chứ không trỏ
ngược ra `../samples/` - link ra ngoài sẽ vỡ ngay khi folder rời khỏi máy này.
"""
import html
import shutil
from pathlib import Path

from paper import style

SAMPLES_DIR = Path(__file__).resolve().parent / "samples"

# Thư mục con trong `out/`.
DIR_ANH_MAU = "anh-mau"

# Ảnh mẫu lấy từ luận văn tham khảo, gắn với hình tương ứng của mình để so sánh.
# Mỗi ảnh mẫu chỉ xuất hiện MỘT lần, dưới hình nó giống nhất.
SAMPLE_MAP: dict[str, list[tuple[str, str]]] = {
    "bang-mau-du-lieu": [
        ("mau-hinh-4-3-du-lieu-thu-thap.jpg",
         "Hình 4.3: Dữ liệu sau khi thu thập"),
    ],
    "bang-comment-theo-lop": [
        ("mau-hinh-4-4-du-lieu-tho-tach-lop.jpg",
         "Hình 4.4: Dữ liệu thô tích cực sau khi được tách ra"),
    ],
    "bang-tien-xu-ly": [
        ("mau-hinh-4-6-du-lieu-tien-xu-ly.jpg",
         "Hình 4.6: Dữ liệu lớp tiêu cực đã qua tiền xử lý"),
    ],
    "bang-precision-recall": [
        ("mau-bang-5-2-ket-qua-huan-luyen.jpg",
         "Bảng 5.2: Kết quả huấn luyện với 3000 bình luận"),
    ],
    "bang-fscore": [
        ("mau-bieu-do-5-2-va-bang-5-5.jpg",
         "Bảng 5.5: Kết quả thực nghiệm với 3000 bình luận (kèm Biểu đồ 5.2)"),
    ],
    "bd-f1-tung-lop": [
        ("mau-bieu-do-5-3-fscore-3000.jpg",
         "Biểu đồ 5.3: Kết quả F-score với 3000 bình luận"),
        ("mau-bieu-do-5-1-va-bang-5-4.jpg",
         "Biểu đồ 5.1: F-score với 910 bình luận ngắn (kèm Bảng 5.4)"),
    ],
}

# Ảnh mẫu KHÔNG có hình tương ứng. Giữ danh sách này (dù đang rỗng) để lần sau thêm
# ảnh mẫu mới mà chưa dựng hình thì nó tự hiện ra thay vì bị bỏ quên.
SAMPLES_UNMATCHED: list[tuple[str, str]] = []

_CSS = """
:root { --bg:#fff; --fg:#16202a; --mut:#63748a; --line:#dfe4ea; --card:#fff;
        --accent:#2471a3; --shadow:0 1px 3px rgba(16,32,48,.09); }
@media (prefers-color-scheme: dark) {
  :root { --bg:#14181d; --fg:#e6eaee; --mut:#93a1b0; --line:#2a3138; --card:#1b2027;
          --accent:#5fa8dd; --shadow:0 1px 3px rgba(0,0,0,.4); } }
* { box-sizing:border-box; }
body { margin:0; padding:2.5rem 1.5rem 4rem; background:var(--bg); color:var(--fg);
       font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
main { max-width:62rem; margin:0 auto; }
h1 { font-size:1.7rem; margin:0 0 .3rem; letter-spacing:-.01em; }
.sub { color:var(--mut); margin:0 0 1.5rem; }
h2 { font-size:1.15rem; margin:3rem 0 1rem; padding-bottom:.4rem;
     border-bottom:1px solid var(--line); }
.stats { display:flex; flex-wrap:wrap; gap:.6rem; margin:1.2rem 0 0; }
.stat { border:1px solid var(--line); border-radius:.55rem; padding:.55rem .85rem;
        background:var(--card); min-width:8rem; }
.stat b { display:block; font-size:1.25rem; line-height:1.3; }
.stat span { color:var(--mut); font-size:.78rem; }
.card { border:1px solid var(--line); border-radius:.7rem; background:var(--card);
        box-shadow:var(--shadow); margin:1.1rem 0; overflow:hidden; }
.card figure { margin:0; padding:1rem 1rem .5rem; text-align:center; }
.card img { max-width:100%; height:auto; border-radius:.3rem; background:#fff;
            cursor:zoom-in; transition:opacity .12s; }
.card img:hover { opacity:.85; }
/* Lightbox: ảnh trong trang bị thu nhỏ nên chữ khó đọc; bấm vào xem cỡ thật. */
/* Nền gần như đục hẳn: để trong hơn thì chữ của trang bên dưới lộ qua, đọc rối. */
#lb { position:fixed; inset:0; z-index:99; display:none; background:rgba(10,14,18,.985);
      padding:1.2rem 1rem 2rem; overflow:auto; }
#lb.on { display:block; }
#lb img { display:block; margin:0 auto; background:#fff; border-radius:.3rem;
          max-width:100%; height:auto; cursor:zoom-out; }
#lb.fit img { max-width:min(100%, 78rem); }
#lb.full img { max-width:none; width:auto; cursor:zoom-in; }
#lb .bar { position:sticky; top:0; display:flex; justify-content:space-between;
           align-items:center; gap:1rem; margin-bottom:.9rem; color:#e6eaee; }
#lb .bar span { font-size:.85rem; opacity:.85; min-width:0;
                overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
#lb .bar button { border-color:#4a5560; color:#e6eaee; background:rgba(0,0,0,.35); }
#lb .bar button:hover { border-color:#fff; color:#fff; }
/* Hai cột: hình của mình bên trái, ảnh mẫu bên phải. Dưới 60rem thì xếp dọc. */
/* align-items:start - nếu không, cột nào có 2 ảnh mẫu sẽ kéo cột kia cao bằng nó
   và để lại một mảng trắng lớn. */
.compare { display:grid; grid-template-columns:1fr 1fr; gap:.5rem; padding:.9rem .9rem 0;
           align-items:start; }
@media (max-width:60rem) { .compare { grid-template-columns:1fr; } }
.compare .side { min-width:0; border:1px solid var(--line); border-radius:.5rem;
                 padding:.5rem .5rem .2rem; background:var(--bg); }
.compare figure { padding:.4rem .2rem .2rem; }
.compare figcaption { color:var(--mut); font-size:.79rem; margin-top:.35rem;
                      line-height:1.4; }
.tag { display:inline-block; font-size:.72rem; font-weight:600; letter-spacing:.03em;
       text-transform:uppercase; padding:.2rem .5rem; border-radius:.3rem; }
.tag.mine { background:var(--accent); color:#fff; }
.tag.ref { background:transparent; color:var(--mut); border:1px solid var(--line); }
.ref img { opacity:.94; }
.meta { display:flex; flex-wrap:wrap; align-items:center; gap:.65rem;
        padding:.7rem 1rem .9rem; border-top:1px solid var(--line); }
.cap { flex:1 1 18rem; min-width:0; }
.cap b { font-weight:600; }
.cap i { display:block; color:var(--mut); font-size:.82rem; font-style:normal; }
code { font:.82rem ui-monospace,SFMono-Regular,Menlo,monospace; color:var(--mut); }
button, .btn { font:inherit; font-size:.83rem; padding:.35rem .8rem; border-radius:.4rem;
        border:1px solid var(--line); background:transparent; color:var(--fg);
        cursor:pointer; text-decoration:none; white-space:nowrap; }
button:hover, .btn:hover { border-color:var(--accent); color:var(--accent); }
button.done { border-color:var(--accent); color:var(--accent); }
.note { color:var(--mut); font-size:.86rem; border-left:3px solid var(--line);
        padding:.2rem 0 .2rem .8rem; margin:1.2rem 0; }
footer { margin-top:3.5rem; color:var(--mut); font-size:.82rem;
         border-top:1px solid var(--line); padding-top:1rem; }
"""

_LIGHTBOX_HTML = """
<div id="lb" class="fit" role="dialog" aria-modal="true" aria-label="Xem ảnh phóng to">
  <div class="bar">
    <span id="lb-name"></span>
    <span style="flex:0 0 auto">
      <button type="button" id="lb-zoom">Cỡ thật</button>
      <button type="button" id="lb-close">Đóng (Esc)</button>
    </span>
  </div>
  <img id="lb-img" alt="">
</div>"""

_JS = """
document.addEventListener('click', function (e) {
  var btn = e.target.closest('button[data-copy]');
  if (!btn) return;
  navigator.clipboard.writeText(btn.dataset.copy).then(function () {
    var old = btn.textContent;
    btn.textContent = 'Đã copy'; btn.classList.add('done');
    setTimeout(function () { btn.textContent = old; btn.classList.remove('done'); }, 1400);
  });
});

// --- Lightbox ---------------------------------------------------------------
var lb = document.getElementById('lb');
var lbImg = document.getElementById('lb-img');
var lbName = document.getElementById('lb-name');
var lbZoom = document.getElementById('lb-zoom');

function openLb(src, name) {
  lbImg.src = src;
  lbName.textContent = name;
  lb.className = 'on fit';          // mở ở cỡ vừa màn hình
  lbZoom.textContent = 'Cỡ thật';
  document.body.style.overflow = 'hidden';
}
function closeLb() {
  lb.className = 'fit';
  lbImg.src = '';                   // nhả ảnh, không giữ bộ nhớ
  document.body.style.overflow = '';
}
function toggleZoom() {
  var full = lb.classList.toggle('full');
  lb.classList.toggle('fit', !full);
  lbZoom.textContent = full ? 'Vừa màn hình' : 'Cỡ thật';
}

document.addEventListener('click', function (e) {
  var img = e.target.closest('.card img');
  if (img) {
    var cap = img.closest('.card').querySelector('.cap b');
    openLb(img.getAttribute('src'), cap ? cap.textContent : '');
    return;
  }
  if (e.target.id === 'lb-close') { closeLb(); return; }
  if (e.target.id === 'lb-zoom') { toggleZoom(); return; }
  if (e.target === lbImg) { toggleZoom(); return; }
  // Bấm ra nền tối thì đóng.
  if (lb.classList.contains('on') && e.target === lb) closeLb();
});

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape' && lb.classList.contains('on')) closeLb();
});
"""


def _copy_samples() -> dict[str, str]:
    """Copy ảnh mẫu vào `out/anh-mau/`, trả về {tên file: đường dẫn tương đối}.

    Chỉ copy ảnh thật sự tồn tại - thiếu một ảnh mẫu thì bỏ qua ảnh đó, không làm
    hỏng cả trang.
    """
    wanted = [f for entries in SAMPLE_MAP.values() for f, _ in entries]
    wanted += [f for f, _ in SAMPLES_UNMATCHED]

    out: dict[str, str] = {}
    dest_dir = style.OUT_DIR / DIR_ANH_MAU
    for name in wanted:
        src = SAMPLES_DIR / name
        if not src.is_file():
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_dir / name)
        out[name] = f"{DIR_ANH_MAU}/{name}"
    return out


def _figure(src: str, alt: str, *, caption: str = "", cls: str = "mine") -> str:
    cap = f"<figcaption>{html.escape(caption)}</figcaption>" if caption else ""
    return (f'<figure class="{cls}">'
            f'<img src="{html.escape(src)}" alt="{html.escape(alt)}" loading="lazy">'
            f"{cap}</figure>")


def _card(index: int, relpath: str, caption: str, samples: dict[str, str]) -> str:
    stem = Path(relpath).stem
    esc = html.escape(caption)
    mine = _figure(relpath, caption)

    refs = [(samples[f], c) for f, c in SAMPLE_MAP.get(stem, []) if f in samples]
    if refs:
        # Có ảnh mẫu -> xếp hai cột để mắt so trực tiếp, không phải cuộn qua lại.
        ref_figs = "".join(_figure(src, c, caption=c, cls="ref") for src, c in refs)
        body = f"""
  <div class="compare">
    <div class="side"><span class="tag mine">Kết quả của bạn</span>{mine}</div>
    <div class="side"><span class="tag ref">Ảnh mẫu để đối chiếu</span>{ref_figs}</div>
  </div>"""
    else:
        body = mine

    return f"""
<div class="card">
  {body}
  <div class="meta">
    <div class="cap"><b>Hình {index}: {esc}</b><i><code>{html.escape(relpath)}</code></i></div>
    <button type="button" data-copy="Hình {index}: {esc}">Copy caption</button>
    <button type="button" data-copy="{html.escape(relpath)}">Copy tên file</button>
    <a class="btn" href="{html.escape(relpath)}" download>Tải ảnh</a>
  </div>
</div>"""


def _unmatched_block(samples: dict[str, str]) -> str:
    """Ảnh mẫu chưa có hình tương ứng - nói thẳng ra thay vì giấu đi."""
    entries = [(samples[f], c) for f, c in SAMPLES_UNMATCHED if f in samples]
    if not entries:
        return ""
    cards = "".join(
        f"""
<div class="card">
  <figure class="mine"><img src="{html.escape(f)}" alt="{html.escape(c)}" loading="lazy"></figure>
  <div class="meta"><div class="cap"><b>{html.escape(c)}</b>
  <i>Ảnh mẫu — bộ hình này chưa có hình tương ứng</i></div></div>
</div>"""
        for f, c in entries
    )
    return f"""<h2>Ảnh mẫu chưa có hình tương ứng ({len(entries)})</h2>
<p class="note">Hai hình này trong bài mẫu là ảnh chụp màn hình Notepad chứa dữ liệu
thô và dữ liệu đã tiền xử lý. Bộ hình hiện tại chưa dựng phần đó — nói mình nếu
bạn cần.</p>{cards}"""


def render(items: list[tuple[str, str, str]], metadata: dict) -> Path:
    """`items` là [(nhóm, đường dẫn tương đối trong out/, caption)] theo thứ tự hiện."""
    samples = _copy_samples()
    data = metadata.get("dataset", {})
    split = metadata.get("split", {})
    models = metadata.get("models", {})
    best = max(models, key=lambda n: models[n]["metrics"]["macro_f1"], default=None)

    stats = [
        (f"{data.get('final_rows', 0):,}".replace(",", "."), "bình luận sau làm sạch"),
        (f"{split.get('train', 0):,}".replace(",", ".") + " / "
         + f"{split.get('test', 0):,}".replace(",", "."), "train / test"),
        (str(len(models)), "mô hình so sánh"),
    ]
    if best:
        stats.append((f"{models[best]['metrics']['macro_f1']:.3f}",
                      f"macro-F1 tốt nhất ({style.MODEL_VI.get(best, best)})"))
    stat_html = "".join(
        f'<div class="stat"><b>{html.escape(v)}</b><span>{html.escape(k)}</span></div>'
        for v, k in stats
    )

    body: list[str] = []
    index = 0
    for group in ("Bảng", "Biểu đồ"):
        rows = [it for it in items if it[0] == group]
        if not rows:
            continue
        body.append(f"<h2>{html.escape(group)} ({len(rows)})</h2>")
        for _, relpath, caption in rows:
            index += 1
            body.append(_card(index, relpath, caption, samples))
    body.append(_unmatched_block(samples))

    trained = html.escape(str(metadata.get("trained_at", "")))
    page = f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hình cho bài báo – Phân tích cảm xúc bình luận</title>
<style>{_CSS}</style>
</head>
<body>
<main>
<h1>Hình cho bài báo</h1>
<p class="sub">Phân tích cảm xúc bình luận sản phẩm tiếng Việt · kết quả huấn luyện
lúc {trained}</p>
<div class="stats">{stat_html}</div>
<p class="note">Toàn bộ ảnh là PNG 300&nbsp;dpi, chèn thẳng vào Word được. Mỗi bảng có
thêm một file <code>.csv</code> cùng tên nếu bạn muốn tự định dạng lại trong Excel.
Số thứ tự hình ở đây chỉ để tham chiếu nhanh — khi đưa vào bài, đánh số lại theo
bố cục chương của bạn. <b>Bấm vào ảnh</b> để phóng to, bấm tiếp để xem cỡ thật.</p>
<p class="note">Hình nào có ảnh mẫu tương ứng thì xếp <b>hai cột</b>: kết quả của bạn
bên trái, ảnh mẫu từ bài tham khảo bên phải. Ảnh mẫu chỉ để đối chiếu bố cục và
cách trình bày — <b>số liệu hai bên không so trực tiếp được</b> vì khác tập dữ liệu
và khác số lớp (bài mẫu 2 lớp, bài của bạn 3 lớp).</p>
{''.join(body)}
<footer>Sinh tự động bởi <code>python -m paper.figures</code> · font <b>{html.escape(style.FONT)}</b><br>
Thư mục: <code>bang/</code> bảng · <code>bieu-do/</code> biểu đồ ·
<code>csv/</code> số liệu thô · <code>anh-mau/</code> ảnh mẫu đối chiếu</footer>
</main>
{_LIGHTBOX_HTML}
<script>{_JS}</script>
</body>
</html>
"""
    path = style.OUT_DIR / "index.html"
    path.write_text(page, encoding="utf-8")
    return path
