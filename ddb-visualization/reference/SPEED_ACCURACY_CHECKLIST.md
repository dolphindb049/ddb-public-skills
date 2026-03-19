# Speed & Accuracy Checklist

## 速度（Speed）

- 渲染器输出 `render_ms` 指标。
- 优先单页多 tab，而不是多次重复渲染。
- 图表数据先在上游聚合，避免前端承载超大明细。

## 准确度（Accuracy）

- 开启 `--strict` 做维度一致性校验。
- 关键指标图必须附参数/口径表（`table`）。
- 误差场景必须展示误差本体（`bar_error`/`hist`）。

## 运行示例

```powershell
python .github/skills/ddb-visualization/scripts/render_modular_dashboard.py --input <spec.json> --out <report.html> --strict --metrics-out <metrics.json>
```

## 建议验收阈值

- 校验错误数：`0`
- 关键图表缺失：`0`
- `render_ms` 在同规模数据下稳定（波动可控）
