# Dashboard Orchestration Guide

本文件定义“图表编排”的标准流程，与单图参数解耦。

## 编排原则

1. 先结论后细节：`markdown/table` 放前，图放后。
2. 主图优先：每个 Tab 先放最关键趋势图。
3. 误差显式化：涉及模型估计时加入 `bar_error` 或 `hist`。
4. 二维关系先 `heatmap`，结构演化再 `surface3d`。
5. 代码与参数收尾：`table + code` 放在最后一页签。

## 推荐版式（模板）

- Tab A: 总览（结论 + 关键统计表）
- Tab B: 主图（趋势/曲线/曲面）
- Tab C: 风险与误差（误差图、分布图）
- Tab D: 参数与实现（参数表、代码块）

## 入参驱动渲染

- 不在脚本中写死业务名称。
- 业务名称、图表标题、图表类型、输出文件名全部来自 JSON 配置。

## 执行命令

```powershell
python .github/skills/ddb-visualization/scripts/dashboard_templates.py --config .github/skills/ddb-visualization/reference/examples/jobs.financial_workflows.json --strict
```
