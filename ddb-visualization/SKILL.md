---
name: ddb-visualization
description: 金融数据可视化通用技能。按“单图入参 + 图表编排指南”组织，支持参数化生成任意业务报告，不在脚本中写死业务名称。
license: MIT
metadata:
  author: ddb-user
  version: "4.0.0"
  tags: ["visualization", "plotly", "dashboard", "template", "orchestration"]
---

# DDB Visualization (Parameterized)

本技能只负责可视化展示层，不负责因子计算/定价计算本体。

## 📂 技能结构

```text
ddb-visualization/
├── scripts/
│   ├── render_modular_dashboard.py   # [单报告渲染] 输入 spec 输出 html（支持 strict 校验与 metrics）
│   └── dashboard_templates.py        # [批量编排执行] 读取 jobs 配置，批量生成报告
├── reference/
│   ├── CHART_INPUT_PARAMS.md         # [单图参数] 原子图表入参规范
│   ├── ORCHESTRATION_GUIDE.md        # [编排指南] tab/section 的组织方法
│   ├── SPEED_ACCURACY_CHECKLIST.md   # [质控] 速度与准确度验收清单
│   └── examples/
│       ├── jobs.financial_workflows.json
│       ├── spec.factor_eval.json
│       ├── spec.ficc_pricing.json
│       └── spec.bond_trend.json
└── outputs/
```

## 🚀 核心原则

1. **不写死业务名称**：脚本中不得硬编码“因子评价/FICC定价”等场景名。
2. **全入参驱动**：图表类型、标题、布局、输出文件名由 JSON 提供。
3. **单图与编排解耦**：单图参数见 `CHART_INPUT_PARAMS.md`，编排规则见 `ORCHESTRATION_GUIDE.md`。
4. **速度与准确度并重**：支持 `--strict` 与 `--metrics-out` 进行校验与性能记录。

## 💡 快速开始

### 1) 渲染单个报告

```powershell
python .github/skills/ddb-visualization/scripts/render_modular_dashboard.py --input <spec.json> --out <report.html> --strict --metrics-out <metrics.json>
```

### 2) 按 jobs 批量生成多个报告

```powershell
python .github/skills/ddb-visualization/scripts/dashboard_templates.py --config .github/skills/ddb-visualization/reference/examples/jobs.financial_workflows.json --strict
```

### 3) 发布静态报告到端口

```powershell
python -m http.server 8777 --directory .github/skills/ddb-visualization/outputs
```

访问：

- `http://127.0.0.1:8777/`

## 🔧 常见问题

- **Q: 为什么 strict 模式报维度不一致？**
  - A: 说明图表 `x` 与 `y`（或 `error_y`）长度不一致，需要在上游数据对齐。
- **Q: 为什么不把业务流程写在脚本里？**
  - A: 为了复用性与可维护性，业务流程必须放入配置文件，而不是 Python 逻辑。
