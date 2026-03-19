---
name: ddb-data-analysis
description: DolphinDB 专家数据分析技能。涵盖从数据聚合、收益率建模到假设检验的标准化工作流脚本。
license: MIT
metadata:
  author: ddb-user
  version: "2.0.0"
  tags: ["quant", "statistics", "regression", "metrics"]
---

# DolphinDB 数据分析 (Quant & Statistics)

本技能提供了一套标准化的量化研究工作流，展示了如何使用 DolphinDB 的向量化引擎完成复杂的金融统计分析，替代传统的 Pandas `df.apply` 模式，实现显著的性能提升。

## 📂 技能结构

```text
ddb-data-analysis/
├── scripts/
│   ├── 01_aggregation.dos           # [数据压缩] 日线指标聚合、透视表分析
│   ├── 02_financial_metrics.dos     # [因子计算] 收益率、波动率、滚动窗口
│   ├── 03_regression.dos            # [线性建模] OLS 回归与 Beta 计算 (AR1)
│   ├── 04_hypothesis_testing.dos    # [统计推断] 资产相关性矩阵、T 检验
│   └── 05_comprehensive_analysis.dos # [完整流程] 端到端数据清洗、建模、回测
└── reference/
    ├── METHODOLOGY.md               # 📖 分析思路与方法论
    └── DDB_STATS_GUIDE.md           # 📚 Stats & Regression 使用手册与避坑指南 (Added!)

```

## 🚀 核心能力

### 1. 向量化聚合 (Group By & Pivot)
- **High-Freq to Low-Freq**: 自动将分钟级高频数据压缩为日线 OHLC 或 VWAP。
- **Pivot Table**: 生成透视表，快速洞察数据的季节性或结构性特征。

### 2. 金融指标工厂 (Formula As Code)
- **Log Returns**: `ratios(x) - 1` 或 `log(ratios(x))`，一行代码完成所有时刻计算。
- **Rolling Volatility**: `mstd(x, window)` 极其高效地计算移动方差。

### 3. 深层统计建模 (OLS & Correlation)
- **线性回归 (Linear Regression)**: 内置 `ols` 函数，无需导出数据即可在库内完成因子检验。
- **T 检验 (Hypothesis Testing)**: 展示了手动计算统计量的全过程，透明且可定制。

## 💡 快速开始

1.  **数据清洗**: 推荐先使用 `ddb-data-discovery` 确保数据无空值。
2.  **配置参数**: 打开脚本，修改顶部的 `USER CONFIG` 区域：
    ```dolphin
    // --- 配置参数 (USER CONFIG) ---
    securityIDs = ["000001.SZ", "600000.SH"]  // 设定股票池
    ```
3.  **运行分析**: 使用 `execute-dlang` 技能运行脚本：
    ```bash
    python ../execute-dlang/scripts/ddb_runner/execute.py scripts/05_comprehensive_analysis.dos
    ```

## 🔧 常见问题

- **Q: 为什么回归结果有很多 NaN？**
    - A: 脚本中已包含 `isValid` 过滤逻辑。如果你在第一行就有 NaN (比如 `ratios` 导致)，回归会自动报错或返回无效结果，必须先 `drop` 或 `fill`。
- **Q: 如何扩展到几千只股票？**
    - A: 脚本使用了 `context by SecurityID`，无需修改代码，DolphinDB 会自动并行分组计算。

## 🧪 实战排障补充（2026-03）

- **PowerShell 引号陷阱**：`execute.py -c "..."` 在复杂表达式下容易被转义破坏，建议优先执行 `.dos` 文件。
- **数据库路径漂移**：不同环境常见 `dfs://day_factor` 与 `dfs://stock_daily` 不一致，先用 `getChunksMeta()` 探测再编码。
- **分位分组越界**：`asof(quantileSeries(...))+1` 可能产生超出目标组数的标签，务必用 `iif(q>k,k,q)` 截断。
- **分钟级依赖缺失**：分钟库存在但表名不可解析时，先给出日频代理因子跑通主链路，再补分钟版分支。
