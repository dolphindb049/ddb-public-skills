---
name: ddb-data-discovery
description: DolphinDB 数据发现与预处理专家技能。提供从全库扫描、表结构透视到数据清洗与内存共享的完整工作流脚本。
license: MIT
metadata:
  author: ddb-user
  version: "3.0.0"
  tags: ["etl", "exploration", "cleaning", "metadata", "dolphindb", "data-quality"]
---

# DolphinDB 数据发现与操作元技能 (Data Discovery Meta-Skill)

本技能是一套**经过实战验证**的 DolphinDB 操作指南。所有脚本和语法都来自在真实集群上的实际执行和纠错，而非凭空编写。

## 🧠 核心理念：效率优先的探索方法论

操作 DolphinDB 时，最高效的方式是遵循这个流程：

```
全库扫描 → 锁定目标表 → 看Schema → 采样 → 数据画像 → 质量检查 → 清洗/分析
```

每一步都**写成 .dos 文件后执行**，不要在 `-c` 参数中直接敲复杂代码（PowerShell 会吃引号）。

## 📂 技能结构

```text
ddb-data-discovery/
├── scripts/
│   ├── 01_exploration.dos  # [全库扫描] getDFSDatabases + getDFSTables
│   ├── 02_structure.dos    # [结构透视] schema().colDefs + partitionSchema
│   ├── 03_queries.dos      # [数据画像] 采样、统计、exec vs select
│   ├── 04_cleaning.dos     # [质量检查] NULL统计、重复检测、基础清洗
│   └── 05_sharing.dos      # [分析示例] context by、pivot by 等高级查询
└── reference/
    └── METHODOLOGY.md      # 📖 详细使用指南：语法速查 + 踩坑记录 + deepwiki查文档技巧
```

## 🔑 关键语法速查 (经过实战验证)

### 库表发现
```dolphindb
getDFSDatabases()                              // 列出所有 DFS 数据库
getDFSTables()                                 // 列出所有 DFS 表 (全路径)
getDFSTablesByDatabase("dfs://minute_factor")  // 列出指定库的表 ✅ 推荐
```

> ⚠️ **踩坑**: `getDFSTables` 不接受参数！要按库筛选必须用 `getDFSTablesByDatabase()`。

### 加载表 & 查看 Schema
```dolphindb
t = loadTable("dfs://minute_factor", "stock_minute_1m")   // 直接传路径+表名, 最简
schema_info = t.schema()        // 返回一个 dict，包含多个 key
schema_info.colDefs             // 列定义: name, typeString, typeInt, comment
schema_info.partitionSchema     // 分区方案
schema_info.partitionColumnName // 分区列名 (数组)
schema_info.partitionTypeName   // 分区类型: RANGE, HASH, VALUE, LIST, COMPO
schema_info.engineType          // 存储引擎: TSDB, OLAP
schema_info.sortColumns         // TSDB 的排序列
```

### select vs exec
```dolphindb
select count(*) from t                        // 返回表 (table)
exec count(*) from t                          // 返回标量 (scalar) 或向量 (vector)
exec distinct ts_code from t                  // 返回去重后的向量
```

### 去重计数 (DDB 不支持 count(distinct ...))
```dolphindb
// ❌ 错误: select count(distinct ts_code) from t  → "Cannot nest aggregate function"
// ✅ 正确: 用子查询或 exec
exec count(*) from (select distinct ts_code from t)
// 或
size(exec distinct ts_code from t)
```

### DolphinDB SQL 扩展子句
```dolphindb
// context by: 分组但不聚合，把窗口函数结果填回每一行
select ts_code, trade_time, close,
       close \ prev(close) - 1 as minute_ret
from t context by ts_code

// group by + having: 标准分组聚合
select count(*) as cnt from t group by ts_code having count(*) > 100

// limit: 放在 group by 或 order by 后面
select * from t order by trade_time limit 10
// 也可以用 top N（放在 select 后面）
select top 10 * from t
```

### NULL 检查模式
```dolphindb
// 单列
select count(*) from t where isNull(pre_close)
// 全列批量统计
select count(*) as total,
    sum(iif(isNull(open), 1, 0)) as null_open,
    sum(iif(isNull(pre_close), 1, 0)) as null_pre_close
from t
```

## 📖 查文档技巧：善用 DeepWiki

当你遇到不确定的函数名或语法时，可以到 DolphinDB 官方文档的 DeepWiki 索引进行搜索：

```
https://deepwiki.com/search/_7a7f1325-7754-4fb1-920b-b482e1a37c5d?mode=fast&q=你的关键词
```

**最佳搜索技巧**:
- 搜函数名精准：`getDFSTables`、`getDFSTablesByDatabase`、`loadTable`
- 如果搜索返回的结果总是同一个页面，**直接浏览 wiki 的目录页面**:
  - 总目录: `https://deepwiki.com/tradercjz/documentation`
  - 数据库特性: `https://deepwiki.com/tradercjz/documentation/2-database-features`
  - 分区: `https://deepwiki.com/tradercjz/documentation/2.1-distributed-computing-and-partitioning`
- DolphinDB 函数参考手册（最权威）: `https://docs.dolphindb.cn/zh/funcs/funcs_intro.html`

## ⚠️ 高频踩坑记录

| 场景 | 错误写法 | 正确写法 | 说明 |
|------|----------|----------|------|
| 列出指定库的表 | `getDFSTables("dfs://db")` | `getDFSTablesByDatabase("dfs://db")` | getDFSTables 不接参数 |
| 去重计数 | `count(distinct col)` | `exec count(*) from (select distinct col from t)` | DDB 不支持嵌套聚合 |
| 全库扫描 | `getChunksMeta()` | `getDFSDatabases()` + `getDFSTables()` | getChunksMeta 太慢 |
| PowerShell 引号 | `execute.py -c "loadTable('dfs://xx', 'yy')"` | 写成 .dos 文件再执行 | PS 会吃掉内层引号 |
| 脚本无返回值 | 最后一行是 `x = 1` | 最后一行写 `x` 或写 `select ...` | 赋值语句不返回结果 |
| 整数除法 | `close / prev(close)` | `close \ prev(close)` | `\` 是浮点除法, `/` 是整数除法 |
| string→symbol | `symbol(varName)` | `symbol([varName])[0]` 或 `` `literal `` | symbol()要求向量输入 |

## 🚀 快速开始

1. **确认执行环境**: 需要 `execute-dlang` 技能已可用或者有内置的 ddb 执行工具
2. **修改脚本配置**: 打开任意 `.dos` 文件，修改 `dbPath` 和 `tableName`
3. **按序号执行**: `01 → 02 → 03 → 04 → 05`，每步都产出结论再进下一步

```powershell
# 示例（替换为你的连接信息）
uv run .github/skills/execute-dlang/scripts/ddb_runner/execute.py ^
    .github/skills/ddb-data-discovery/scripts/01_exploration.dos ^
    --host ip --port port --user admin --password xxxxx
```
