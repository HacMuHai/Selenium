"""
Trang HTML so sánh model - TỰ CHỨA hoàn toàn (CSS inline + SVG thuần, không CDN).

Không dùng Streamlit: đã có sẵn FastAPI, dựng thêm một server chỉ để hiện một trang
so sánh là thừa. File này mở trực tiếp bằng trình duyệt hoặc serve qua `/analyze/report`.

Trang phải trả lời được ĐÚNG MỘT câu hỏi: *model có thực sự học được gì, hay chỉ đoán
lớp đa số?* → luôn vẽ đường baseline lên cùng biểu đồ.
"""
import csv
import html
import io

from src.analysis.metrics import LABELS

_CSS = """
:root { color-scheme: light dark; --fg:#111; --bg:#fff; --mut:#666; --line:#e5e5e5;
        --bar:#2563eb; --base:#dc2626; --ok:#16a34a; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#e8e8e8; --bg:#141414; --mut:#9a9a9a; --line:#333;
          --bar:#60a5fa; --base:#f87171; --ok:#4ade80; } }
* { box-sizing: border-box; }
body { margin:0; padding:2rem 1.25rem; background:var(--bg); color:var(--fg);
       font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
main { max-width: 60rem; margin: 0 auto; }
h1 { font-size:1.6rem; margin:0 0 .25rem; }
h2 { font-size:1.15rem; margin:2.5rem 0 .75rem; padding-bottom:.3rem;
     border-bottom:1px solid var(--line); }
h3 { font-size:1rem; margin:1.5rem 0 .5rem; }
.sub { color:var(--mut); margin:0 0 1.5rem; font-size:.9rem; }
.scroll { overflow-x:auto; }
table { border-collapse:collapse; width:100%; font-size:.9rem; }
th,td { padding:.45rem .6rem; text-align:right; border-bottom:1px solid var(--line);
        white-space:nowrap; }
th:first-child, td:first-child { text-align:left; }
thead th { color:var(--mut); font-weight:600; }
tr.best td { font-weight:700; color:var(--ok); }
tr.baseline td { color:var(--base); font-style:italic; }
.cards { display:flex; flex-wrap:wrap; gap:.75rem; margin:1rem 0; }
.card { border:1px solid var(--line); border-radius:.5rem; padding:.6rem .9rem; min-width:9rem; }
.card b { display:block; font-size:1.35rem; }
.card span { color:var(--mut); font-size:.8rem; }
.err { border-left:3px solid var(--base); padding:.35rem .7rem; margin:.4rem 0;
       color:var(--mut); font-size:.87rem; }
.err b { color:var(--fg); }
footer { margin-top:3rem; color:var(--mut); font-size:.82rem; }
textarea { width:100%; min-height:5rem; padding:.6rem; border-radius:.4rem;
           border:1px solid var(--line); background:var(--bg); color:var(--fg);
           font:inherit; resize:vertical; }
button { margin-top:.6rem; padding:.5rem 1.1rem; border:0; border-radius:.4rem;
         background:var(--bar); color:#fff; font:inherit; font-weight:600; cursor:pointer; }
button:disabled { opacity:.5; cursor:default; }
.chips { display:flex; flex-wrap:wrap; gap:.4rem; margin:.6rem 0 0; }
.chips button { margin:0; padding:.3rem .7rem; font-size:.82rem; font-weight:400;
                background:transparent; color:var(--mut); border:1px solid var(--line); }
.res { margin-top:1rem; }
.res td b { font-size:1rem; }
.pos { color:var(--ok); font-weight:700; }
.neg { color:var(--base); font-weight:700; }
.neu { color:var(--mut); font-weight:700; }
.note { color:var(--mut); font-size:.85rem; margin:.5rem 0 0; }
"""

# Ô thử nghiệm: chỉ hoạt động khi trang được serve qua API (`/analyze/report`).
# Mở file .html trực tiếp thì không có backend để gọi -> ẩn đi kèm ghi chú.
_TRY_IT = """
<h2>Thử ngay</h2>
<div id="try" hidden>
  <textarea id="inp" placeholder="Nhập một comment tiếng Việt..."></textarea>
  <div class="chips">
    <button type="button" data-s="Máy dùng rất tốt, pin trâu, nhân viên nhiệt tình">mẫu tích cực</button>
    <button type="button" data-s="Mua 2 ngày đã hỏng loa, bảo hành thì đùn đẩy, quá tệ">mẫu tiêu cực</button>
    <button type="button" data-s="Cho mình hỏi máy này có hỗ trợ 2 sim không ạ">mẫu trung tính</button>
  </div>
  <button id="go" type="button">Phân loại</button>
  <div class="res" id="out"></div>
</div>
<p class="note" id="offline">Ô thử nghiệm cần chạy qua API. Mở bằng:
<code>uvicorn src.app:app --reload</code> rồi vào <code>/analyze/report</code>.</p>
<script>
(function () {
  if (!location.protocol.startsWith('http')) return;
  document.getElementById('try').hidden = false;
  document.getElementById('offline').hidden = true;

  var inp = document.getElementById('inp');
  var go = document.getElementById('go');
  var out = document.getElementById('out');
  var CLS = { positive: 'pos', negative: 'neg', neutral: 'neu' };

  document.querySelectorAll('.chips button').forEach(function (b) {
    b.onclick = function () { inp.value = b.dataset.s; run(); };
  });

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function run() {
    var text = inp.value.trim();
    if (!text) { out.innerHTML = ''; return; }
    go.disabled = true;
    out.innerHTML = '<p class="note">Đang chạy...</p>';

    fetch('compare', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ text: text })
    })
      .then(function (r) { return r.json(); })
      .then(function (body) {
        if (!body.success) throw new Error(body.message || 'lỗi');
        var rows = body.data.map(function (d) {
          var top = Object.keys(d.scores).sort(function (a, b) {
            return d.scores[b] - d.scores[a];
          });
          return '<tr><td>' + esc(d.model) + '</td>'
            + '<td><b class="' + (CLS[d.sentiment] || '') + '">'
            + esc(d.sentiment) + '</b></td>'
            + top.map(function (k) {
                return '<td>' + esc(k) + ' ' + d.scores[k].toFixed(3) + '</td>';
              }).join('')
            + '</tr>';
        }).join('');
        out.innerHTML = '<div class="scroll"><table><thead><tr><th>Model</th>'
          + '<th>Kết quả</th><th colspan="3">Điểm số (cao → thấp)</th></tr></thead>'
          + '<tbody>' + rows + '</tbody></table></div>';
      })
      .catch(function (e) {
        out.innerHTML = '<p class="note">Lỗi: ' + esc(e.message) + '</p>';
      })
      .finally(function () { go.disabled = false; });
  }

  go.onclick = run;
  inp.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') run();
  });
})();
</script>
"""


def _fmt(value, digits: int = 3) -> str:
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else "-"


def _bar_chart(models: dict, baseline: dict) -> str:
    """Bar chart macro-F1 bằng SVG thuần + đường baseline."""
    names = list(models)
    if not names:
        return "<p>Chưa có model nào.</p>"

    row_h, pad_l, width = 34, 90, 640
    height = row_h * len(names) + 46
    base_f1 = baseline.get("macro_f1") or 0.0
    scale = width - pad_l - 60

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'role="img" aria-label="So sánh macro-F1">'
    ]
    for i, name in enumerate(names):
        f1 = models[name].get("metrics", {}).get("macro_f1", 0.0) or 0.0
        y = i * row_h + 8
        bar_w = max(1, f1 * scale)
        parts.append(
            f'<text x="0" y="{y + 16}" font-size="13" fill="currentColor">{html.escape(name)}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{bar_w:.1f}" height="22" rx="3" fill="var(--bar)"/>'
            f'<text x="{pad_l + bar_w + 8:.1f}" y="{y + 16}" font-size="12" '
            f'fill="currentColor">{f1:.3f}</text>'
        )
    base_x = pad_l + base_f1 * scale
    top, bottom = 4, row_h * len(names) + 6
    parts.append(
        f'<line x1="{base_x:.1f}" y1="{top}" x2="{base_x:.1f}" y2="{bottom}" '
        f'stroke="var(--base)" stroke-width="2" stroke-dasharray="5 4"/>'
        f'<text x="{pad_l}" y="{height - 12}" font-size="12" fill="var(--base)">'
        f'baseline (luôn đoán "{html.escape(str(baseline.get("label")))}"): '
        f'macro-F1 {base_f1:.3f}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _confusion_table(confusion: dict) -> str:
    total = sum(sum(r.values()) for r in confusion.values()) or 1
    head = "".join(f"<th>đoán {html.escape(l)}</th>" for l in LABELS)
    rows = []
    for true in LABELS:
        cells = []
        for pred in LABELS:
            n = confusion.get(true, {}).get(pred, 0)
            alpha = min(0.75, n / total * 3)
            tone = "22,163,74" if true == pred else "220,38,38"
            cells.append(f'<td style="background:rgba({tone},{alpha:.3f})">{n}</td>')
        rows.append(f"<tr><td>thật {html.escape(true)}</td>{''.join(cells)}</tr>")
    return (
        f'<div class="scroll"><table><thead><tr><th></th>{head}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )


def _per_class_table(per_class: dict) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(label)}</td>"
        f"<td>{_fmt(m.get('precision'))}</td><td>{_fmt(m.get('recall'))}</td>"
        f"<td>{_fmt(m.get('f1'))}</td><td>{int(m.get('support', 0))}</td></tr>"
        for label, m in per_class.items()
    )
    return (
        '<div class="scroll"><table><thead><tr><th>Lớp</th><th>Precision</th>'
        f"<th>Recall</th><th>F1</th><th>Support</th></tr></thead><tbody>{rows}</tbody></table></div>"
    )


def render_html(metadata: dict) -> str:
    models = metadata.get("models", {})
    baseline = metadata.get("baseline", {})
    dataset = metadata.get("dataset", {})
    split = metadata.get("split", {})

    best = ""
    if models:
        best = max(models, key=lambda n: models[n].get("metrics", {}).get("macro_f1", 0.0))

    summary_rows = []
    for name, info in sorted(
        models.items(), key=lambda kv: kv[1].get("metrics", {}).get("macro_f1", 0.0), reverse=True
    ):
        m = info.get("metrics", {})
        cls = ' class="best"' if name == best else ""
        summary_rows.append(
            f"<tr{cls}><td>{html.escape(name)}</td>"
            f"<td>{_fmt(m.get('macro_f1'))}</td><td>{_fmt(m.get('accuracy'))}</td>"
            f"<td>{_fmt(info.get('train_seconds'), 1)}s</td>"
            f"<td>{_fmt(m.get('predict_seconds'), 2)}s</td></tr>"
        )
    summary_rows.append(
        f'<tr class="baseline"><td>baseline (đoán "{html.escape(str(baseline.get("label")))}")</td>'
        f"<td>{_fmt(baseline.get('macro_f1'))}</td><td>{_fmt(baseline.get('accuracy'))}</td>"
        f"<td>-</td><td>-</td></tr>"
    )

    details = []
    for name, info in models.items():
        m = info.get("metrics", {})
        details.append(
            f"<h3>{html.escape(name)}</h3>"
            + _per_class_table(m.get("per_class", {}))
            + _confusion_table(m.get("confusion", {}))
        )

    errors = ""
    if best and models[best].get("metrics", {}).get("errors_sample"):
        items = "".join(
            f'<div class="err"><b>thật {html.escape(e["true"])} → đoán '
            f'{html.escape(e["pred"])}</b><br>{html.escape(e["text"])}</div>'
            for e in models[best]["metrics"]["errors_sample"]
        )
        errors = f"<h2>Ví dụ {html.escape(best)} đoán sai</h2>{items}"

    labels = dataset.get("label_counts", {})
    cards = "".join(
        f'<div class="card"><b>{v}</b><span>{html.escape(str(k))}</span></div>'
        for k, v in labels.items()
    )

    return f"""<title>So sánh model phân tích cảm xúc</title>
<style>{_CSS}</style>
<main>
<h1>So sánh model phân tích cảm xúc</h1>
<p class="sub">Train lúc {html.escape(str(metadata.get('trained_at')))} ·
seed {html.escape(str(metadata.get('seed')))} ·
preprocessing v{html.escape(str(metadata.get('preprocessing_version')))}</p>

<h2>Tổng hợp</h2>
<div class="scroll"><table><thead><tr><th>Model</th><th>macro-F1</th><th>Accuracy</th>
<th>Train</th><th>Predict</th></tr></thead><tbody>{''.join(summary_rows)}</tbody></table></div>
<p class="sub">macro-F1 là chỉ số chính. Accuracy một mình gây hiểu nhầm khi lớp lệch nhau:
model chỉ đoán lớp đa số vẫn đạt {_fmt(baseline.get('accuracy'))} accuracy.</p>

<h2>macro-F1 so với baseline</h2>
{_bar_chart(models, baseline)}
{_TRY_IT}

<h2>Dữ liệu</h2>
<div class="cards">
<div class="card"><b>{dataset.get('total_rows', 0)}</b><span>dòng thô</span></div>
<div class="card"><b>{dataset.get('final_rows', 0)}</b><span>sau làm sạch</span></div>
<div class="card"><b>{split.get('train', 0)}</b><span>train</span></div>
<div class="card"><b>{split.get('test', 0)}</b><span>test</span></div>
</div>
<div class="cards">{cards}</div>
<p class="sub">Đã bỏ: {dataset.get('dropped_empty', 0)} dòng rỗng ·
{dataset.get('dropped_bad_label', 0)} nhãn không hợp lệ ·
{dataset.get('dropped_conflict', 0)} mâu thuẫn nhãn ·
{dataset.get('dropped_duplicate', 0)} trùng nội dung.
Khử trùng TRƯỚC khi chia train/test để không rò rỉ dữ liệu.</p>

<h2>Chi tiết từng model</h2>
{''.join(details)}
{errors}
<footer>Sinh bởi <code>python -m src.analyze evaluate</code> · trang tự chứa, không tải gì từ mạng.</footer>
</main>"""


def render_csv(metadata: dict) -> str:
    """Bảng metrics dạng CSV để đưa vào báo cáo."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["model", "macro_f1", "accuracy", "train_seconds", "predict_seconds"]
        + [f"f1_{l}" for l in LABELS]
    )
    for name, info in metadata.get("models", {}).items():
        m = info.get("metrics", {})
        per_class = m.get("per_class", {})
        writer.writerow(
            [
                name,
                f"{m.get('macro_f1', 0):.4f}",
                f"{m.get('accuracy', 0):.4f}",
                f"{info.get('train_seconds') or 0:.2f}",
                f"{m.get('predict_seconds') or 0:.2f}",
            ]
            + [f"{per_class.get(l, {}).get('f1', 0):.4f}" for l in LABELS]
        )
    baseline = metadata.get("baseline", {})
    writer.writerow(
        [f"baseline({baseline.get('label')})",
         f"{baseline.get('macro_f1', 0):.4f}", f"{baseline.get('accuracy', 0):.4f}", "", ""]
        + ["" for _ in LABELS]
    )
    return buffer.getvalue()
