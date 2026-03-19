# ddb-cross-node-sync 使用说明

## 目标

把源节点（如 8671）的原始表同步到目标节点（如 7731），供后续建模技能使用。

本技能只做“数据搬运”，不做业务字段语义转换。

## 为什么单独拆 skill

跨节点同步与字段 mapping 的失败原因完全不同：
- 跨节点常见问题：连接、权限、网络、库表存在性。
- mapping 常见问题：枚举、单位、类型、必填字段。

拆分后便于定位问题，也更方便复用。

## 模板脚本

- `ficc_cross_node_pull_template.dos`
  - 从源节点拉取四张 FICC 常见原始表：
    - instrument
    - getBondRating
    - BondYieldCurveSh
    - CFETSValuation
  - 落地到目标节点本地 DFS（默认 `dfs://instrument_dbtest2`）

## 执行前必改参数

- `SRC_HOST` / `SRC_PORT` / `SRC_USER` / `SRC_PWD`
- `SRC_DB`
- `LOCAL_DB`
- `START_DATE`（增量同步起始日期）
- `DROP_LOCAL_DB_IF_EXISTS`（是否重建本地库）

## 执行后检查

至少检查以下 SQL：

```dos
select count(*) from loadTable("dfs://instrument_dbtest2", "instrument")
select count(*) from loadTable("dfs://instrument_dbtest2", "BondYieldCurveSh")
select min(listDate), max(listDate) from loadTable("dfs://instrument_dbtest2", "instrument")
```

## 下一步

同步完成后，进入建模技能：
- `../ficc_instru_maket_modeling`
- 先跑 `instrument_standardize_template.dos` / `marketdata_standardize_template.dos` 的 dry-run。
