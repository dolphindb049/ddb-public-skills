---
name: ddb-cross-node-sync
description: 使用 xdb + remoteRun 在 DolphinDB 节点间拉取数据并落地到目标节点，适用于跨节点数据同步和建模前置数据准备。
license: MIT
metadata:
  author: ddb-user
  version: "1.0.0"
---

## 技能概述 / Overview

这个技能专门处理“跨节点搬数据”，不负责字段语义建模。

- 负责：把源节点库表安全拉到目标节点（可小样本、可增量）。
- 不负责：`parseInstrument` / `parseMktData` 的 mapping 规则。

## 典型场景

- 源数据在 `port1`，标准化和定价要在 `port2` 运行。
- 你希望用纯 DOS（无 Python 中转）完成拉数。
- 你要先把原始表复制到目标节点，再交给建模技能处理。

## 推荐工作流

1. 使用模板脚本从源节点拉取原始表到目标节点。
   - 脚本：[`reference/ficc_cross_node_pull_template.dos`](reference/ficc_cross_node_pull_template.dos)
2. 在目标节点核对行数和日期范围。
3. 再调用建模技能执行 mapping 与 parse。
   - 关联技能：[`../ficc_instru_maket_modeling/SKILL.md`](../ficc_instru_maket_modeling/SKILL.md)

## 参考文档

- 使用说明：[`reference/README.md`](reference/README.md)
- 模板脚本详解：[`reference/ficc_cross_node_pull_template.dos`](reference/ficc_cross_node_pull_template.dos)