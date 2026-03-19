# DolphinDB 数据分析 (Data Analysis)

本技能提供了一套量化金融研究与通用数据统计流程的脚本模板，涵盖聚合、收益率计算、回归分析及假设检验。

## 🎯 核心价值
- **向量化加速**: 利用 DolphinDB 核心引擎的向量计算能力，性能远超 Pandas 等单机库。
- **无需 Python**: 纯 DolphinsDB 脚本(DolLang) 实现全流程分析，直接贴近存储。
- **公式即代码**: 金融指标（如 VWAP, Return, Volatility）的简洁写法。

## 📂 脚本清单

| 脚本文件 | 功能描述 | 关键技术点 |
| :--- | :--- | :--- |
| `scripts/01_aggregation.dos` | **数据压缩**: 高频数据转日线与透视表 | `wavg`, `pivot` |
| `scripts/02_financial_metrics.dos` | **因子计算**: 收益率、波动率、滚动计算 | `ratios`, `mstd` |
| `scripts/03_regression.dos` | **线性建模**: OLS 回归与 Beta 计算 (AR1) | `ols`, `vectors` |
| `scripts/04_hypothesis_testing.dos` | **统计推断**: 相关性矩阵与 T 检验 | `cross`, `corr`, `T-Stat` |

## 🛠️ 使用指南

### 1. 数据准备
在使用任何分析脚本前，请确保你已经完成了数据发现与清洗（Data Discovery Skill）。

### 2. 分析路径
1.  **降维与聚合** (`01_aggregation.dos`):
    - 如果你拿到的每秒/每分钟数据太大，先生成日线/小时线数据。
    - 使用 `pivot by` 快速查看不同时间段（Seasonality）的数据模式。

2.  **指标计算** (`02_financial_metrics.dos`):
    - 针对个股或组合计算基础因子（Return, Volatility）。
    - 结果可直接用于后续因子选股模型。

3.  **统计建模** (`03_regression.dos` & `04_hypothesis_testing.dos`):
    - 验证因子有效性（Beta 是否显著）。
    - 检查多因子共线性（相关性矩阵）。

## 📚 参考文档
- [DolphinDB 函数参考](https://docs.dolphindb.cn/zh/funcs/index.html)
- [量化金融教程](https://docs.dolphindb.cn/zh/tutorials/quant_finance.html)
