from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from render_modular_dashboard import build_html


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render one or many dashboards from parameterized job config")
    parser.add_argument("--config", required=True, help="Path to dashboard jobs JSON")
    parser.add_argument("--strict", action="store_true", help="Enable strict validation for all jobs")
    parser.add_argument(
        "--default-out-dir",
        default=".github/skills/ddb-visualization/outputs",
        help="Fallback output directory if a job omits outHtml/outSpec",
    )
    parser.add_argument("--results-out", help="Optional path to write batch render metrics JSON")
    return parser.parse_args()


def load_spec(job: dict, config_path: Path) -> dict:
    if "spec" in job:
        return job["spec"]

    spec_file = job.get("specFile")
    if not spec_file:
        raise ValueError("Each job must provide either 'spec' or 'specFile'")

    spec_path = Path(spec_file)
    if not spec_path.is_absolute():
        spec_path = (config_path.parent / spec_file).resolve()
    return json.loads(spec_path.read_text(encoding="utf-8"))


def render_job(job: dict, config_path: Path, default_out_dir: Path, strict: bool) -> dict:
    started = time.perf_counter()
    job_id = job.get("id", "dashboard")
    spec = load_spec(job, config_path)

    out_html = Path(job.get("outHtml", default_out_dir / f"{job_id}.html"))
    out_spec = job.get("outSpec")

    html, metrics = build_html(spec, strict=strict)

    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")

    if out_spec:
        out_spec_path = Path(out_spec)
        out_spec_path.parent.mkdir(parents=True, exist_ok=True)
        out_spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    metrics["render_ms"] = round((time.perf_counter() - started) * 1000, 2)

    return {
        "id": job_id,
        "outHtml": str(out_html),
        "outSpec": str(out_spec) if out_spec else "",
        "metrics": metrics,
    }


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    jobs = config.get("jobs", [])
    if not jobs:
        raise ValueError("No jobs found in config. Expected key: jobs")

    default_out_dir = Path(args.default_out_dir)
    results = [render_job(job, config_path, default_out_dir, args.strict) for job in jobs]

    print(f"Rendered jobs: {len(results)}")
    for item in results:
        metrics = item["metrics"]
        print(
            f"- {item['id']}: {item['outHtml']} | tabs={metrics.get('tabs', 0)} "
            f"sections={metrics.get('sections', 0)} charts={metrics.get('charts', 0)} "
            f"render_ms={metrics.get('render_ms', 0)}"
        )

    if args.results_out:
        results_path = Path(args.results_out)
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
