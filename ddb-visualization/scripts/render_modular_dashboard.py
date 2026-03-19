from __future__ import annotations

import argparse
import html
import json
import time
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render modular single-page dashboard from JSON spec")
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--strict", action="store_true", help="Enable strict validation for chart inputs")
    parser.add_argument("--metrics-out", help="Optional path to write render metrics JSON")
    return parser.parse_args()


def validate_lengths(section: dict, x: list, y: list) -> None:
    if y and len(x) != len(y):
        title = section.get("title", "")
        raise ValueError(f"Length mismatch in section '{title}': len(x)={len(x)} != len(y)={len(y)}")


def validate_section(section: dict) -> None:
    stype = section.get("type")
    x = section.get("x", [])
    y = section.get("y", [])

    if stype in {"line", "bar", "bar_error"}:
        validate_lengths(section, x, y)

    if stype == "line_multi":
        for series in section.get("series", []):
            validate_lengths(section, x, series.get("y", []))

    if stype == "bar_error":
        err = section.get("error_y", [])
        if err and len(err) != len(y):
            title = section.get("title", "")
            raise ValueError(f"Length mismatch in section '{title}': len(error_y)={len(err)} != len(y)={len(y)}")

    if stype in {"heatmap", "surface3d"}:
        z = section.get("z", [])
        if z and (not isinstance(z, list) or not isinstance(z[0], list)):
            title = section.get("title", "")
            raise ValueError(f"Invalid z matrix in section '{title}'")


def escape_text(value: object) -> str:
    return html.escape(str(value))


def render_table(section: dict) -> str:
    columns = section.get("columns", [])
    rows = section.get("rows", [])
    th = "".join(f"<th>{escape_text(c)}</th>" for c in columns)
    tr = ""
    for row in rows:
        tr += "<tr>" + "".join(f"<td>{escape_text(cell)}</td>" for cell in row) + "</tr>"
    return f"<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>"


def render_code(section: dict) -> str:
    lang = section.get("lang", "text")
    code = section.get("code", "")
    return f"<pre><code class='lang-{escape_text(lang)}'>{escape_text(code)}</code></pre>"


def render_markdown(section: dict) -> str:
    text = section.get("text", "")
    escaped = escape_text(text).replace("\n", "<br/>")
    return f"<div class='md'>{escaped}</div>"


def render_plot_container(section: dict, idx: int) -> str:
    return f"<div id='plot_{idx}' class='plot'></div>"


def get_layout(section: dict) -> str:
    layout = {
        "title": section.get("title", "chart"),
        "xaxis": {"title": section.get("xaxis_title", "")},
        "yaxis": {"title": section.get("yaxis_title", "")},
        "legend": {"orientation": "h", "y": -0.2},
        "margin": {"l": 50, "r": 30, "t": 50, "b": 60},
    }
    if "height" in section:
        layout["height"] = section["height"]
    if "zaxis_title" in section:
        layout["scene"] = {
            "xaxis": {"title": section.get("xaxis_title", "")},
            "yaxis": {"title": section.get("yaxis_title", "")},
            "zaxis": {"title": section.get("zaxis_title", "")},
        }
    return json.dumps(layout, ensure_ascii=False)


def plot_js(section: dict, idx: int) -> str:
    stype = section.get("type")
    x = section.get("x", [])
    y = section.get("y", [])
    name = section.get("name", "series")
    layout = get_layout(section)

    if stype == "line":
        trace = {
            "x": x,
            "y": y,
            "type": "scatter",
            "mode": "lines+markers",
            "name": name,
        }
        traces = [trace]
    elif stype == "line_multi":
        traces = []
        for series in section.get("series", []):
            traces.append(
                {
                    "x": x,
                    "y": series.get("y", []),
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": series.get("name", "series"),
                }
            )
    elif stype == "bar":
        trace = {"x": x, "y": y, "type": "bar", "name": name}
        traces = [trace]
    elif stype == "bar_error":
        trace = {
            "x": x,
            "y": y,
            "type": "bar",
            "name": name,
            "error_y": {
                "type": "data",
                "array": section.get("error_y", []),
                "visible": True,
            },
            "marker": {"opacity": 0.85},
        }
        traces = [trace]
    elif stype == "hist":
        trace = {"x": x, "type": "histogram", "name": name}
        traces = [trace]
    elif stype == "heatmap":
        trace = {
            "x": x,
            "y": section.get("y", []),
            "z": section.get("z", []),
            "type": "heatmap",
            "colorscale": section.get("colorscale", "RdBu"),
        }
        traces = [trace]
    elif stype == "surface3d":
        trace = {
            "x": x,
            "y": section.get("y", []),
            "z": section.get("z", []),
            "type": "surface",
            "colorscale": section.get("colorscale", "Viridis"),
            "showscale": True,
        }
        traces = [trace]
    else:
        return ""
    traces_js = json.dumps(traces, ensure_ascii=False)
    return f"Plotly.newPlot('plot_{idx}', {traces_js}, {layout}, {{responsive: true}});"


def render_sections(sections: list[dict], start_idx: int = 0, strict: bool = False) -> tuple[str, str, int, int]:
    html_parts = []
    js_parts = []
    idx = start_idx
    charts = 0
    for sec in sections:
        if strict:
            validate_section(sec)
        title = sec.get("title", "")
        html_parts.append(f"<section class='card'><h3>{escape_text(title)}</h3>")
        stype = sec.get("type")
        if stype == "table":
            html_parts.append(render_table(sec))
        elif stype in {"line", "line_multi", "bar", "bar_error", "hist", "heatmap", "surface3d"}:
            html_parts.append(render_plot_container(sec, idx))
            js_parts.append(plot_js(sec, idx))
            idx += 1
            charts += 1
        elif stype == "code":
            html_parts.append(render_code(sec))
        elif stype == "markdown":
            html_parts.append(render_markdown(sec))
        else:
            html_parts.append("<p>Unsupported section type</p>")
        html_parts.append("</section>")
    return "\n".join(html_parts), "\n".join(js_parts), idx, charts


def build_html(payload: dict, strict: bool = False) -> tuple[str, dict]:
    meta = payload.get("meta", {})
    title = meta.get("title", "Modular Dashboard")
    subtitle = meta.get("subtitle", "")
    tabs = payload.get("tabs", [])

    body_parts = []
    js_parts = []
    plot_idx = 0
    chart_count = 0
    section_count = 0

    if tabs:
        tab_buttons = []
        tab_pages = []
        for i, tab in enumerate(tabs):
            tid = f"tab_{i}"
            tab_name = escape_text(tab.get("name", tid))
            tab_buttons.append(f"<button onclick=\"openTab('{tid}')\">{tab_name}</button>")
            sections = tab.get("sections", [])
            section_html, section_js, plot_idx, tab_charts = render_sections(sections, plot_idx, strict)
            section_count += len(sections)
            chart_count += tab_charts
            tab_pages.append(f"<div id='{tid}' class='tabpage'>{section_html}</div>")
            js_parts.append(section_js)
        body_parts.append(f"<div class='tabs'>{''.join(tab_buttons)}</div>")
        body_parts.extend(tab_pages)
    else:
        sections = payload.get("sections", [])
        section_html, section_js, plot_idx, tab_charts = render_sections(sections, plot_idx, strict)
        section_count += len(sections)
        chart_count += tab_charts
        body_parts.append(section_html)
        js_parts.append(section_js)

    html_content = f"""
<!doctype html>
<html>
<head>
  <meta charset='utf-8'/>
    <title>{escape_text(title)}</title>
  <script src='https://cdn.plot.ly/plotly-2.35.2.min.js'></script>
  <style>
        body {{font-family: Arial, sans-serif; margin: 20px; background:#f7f9fc; color:#212529;}}
        h1 {{margin-bottom: 6px;}}
        .subtitle {{color:#5f6b7a; margin-bottom: 16px;}}
        .tabs button {{margin-right: 8px; padding: 8px 12px; border:1px solid #d7deea; border-radius: 6px; background:white; cursor:pointer;}}
    .tabpage {{display: none; margin-top: 12px;}}
        .card {{border:1px solid #dde3ef; border-radius: 10px; padding: 14px; margin-bottom: 12px; background:white;}}
    table {{border-collapse: collapse; width: 100%;}}
        th, td {{border:1px solid #dde3ef; padding: 8px; font-size: 13px;}}
        th {{background: #f2f5fb;}}
    .plot {{height: 360px;}}
        pre {{background:#f8f9fb; border:1px solid #e6ebf4; padding: 10px; overflow:auto;}}
  </style>
</head>
<body>
    <h1>{escape_text(title)}</h1>
    <div class='subtitle'>{escape_text(subtitle)}</div>
  {''.join(body_parts)}
  <script>
    function openTab(id) {{
      document.querySelectorAll('.tabpage').forEach(el => el.style.display='none');
      const el = document.getElementById(id);
      if (el) el.style.display = 'block';
    }}
    {''.join(js_parts)}
    const firstTab = document.querySelector('.tabpage');
    if (firstTab) firstTab.style.display = 'block';
  </script>
</body>
</html>
"""
    metrics = {
        "title": title,
        "tabs": len(tabs),
        "sections": section_count,
        "charts": chart_count,
    }
    return html_content, metrics


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    html, metrics = build_html(payload, strict=args.strict)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    metrics["render_ms"] = elapsed_ms
    metrics["input"] = args.input
    metrics["output"] = args.out

    if args.metrics_out:
        metrics_out = Path(args.metrics_out)
        metrics_out.parent.mkdir(parents=True, exist_ok=True)
        metrics_out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"dashboard generated: {out}")
    print(f"metrics: sections={metrics['sections']}, charts={metrics['charts']}, render_ms={elapsed_ms}")


if __name__ == "__main__":
    main()
