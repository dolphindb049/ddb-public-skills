# DolphinDB 数据发现方法论与语法速查

本文档是在**真实集群**上反复试错后总结的实战经验。每一条都经过验证。

## 一、高效探索工作流

```
Step 1: getDFSDatabases() + getDFSTables()    → 知道有哪些库表
Step 2: schema().colDefs                       → 知道有哪些列和类型
Step 3: select count(*) + select top 5 *       → 知道数据量级和样貌
Step 4: NULL 统计 + 重复检测                    → 知道数据质量
Step 5: context by / pivot by / wavg 等        → 做初步分析
```

**关键原则**：每一步都先**写成 .dos 文件**再执行，不要在命令行 `-c` 参数里写复杂代码。

## 二、DolphinDB SQL 与标准 SQL 的关键差异

### 2.1 独有子句
| DolphinDB | 标准 SQL 等价 | 说明 |
|-----------|-------------|------|
| `context by` | `PARTITION BY` (窗口函数) | 分组但不聚合，结果填回每行 |
| `pivot by row, col` | `PIVOT` + 手动构造 | 行转列，直接生成矩阵 |
| `exec` | 无 | 返回向量/标量而非表 |
| `top N` (在 select 后) | `LIMIT N` (在末尾) | 位置不同！ |
| `limit N` (在 order 后) | `LIMIT N` | 与标准 SQL 相同 |

### 2.2 运算符差异
| 操作 | DolphinDB | 标准 SQL/Python |
|------|-----------|----------------|
| 浮点除法 | `a \ b` | `a / b` |
| 整数除法 | `a / b` | `a // b` |
| 字符串连接 | `+` | `\|\|` 或 `CONCAT` |
| Backtick 字面量 | `` `name `` | 无（DDB特有的SYMBOL字面量） |

### 2.3 不支持的标准 SQL 语法
- `count(distinct col)` → 用子查询: `exec count(*) from (select distinct col from t)`
- `CASE WHEN` → 用 `iif(cond, trueVal, falseVal)`
- 多层嵌套聚合 → 拆成多个查询

## 三、核心函数速查

### 3.1 库表元数据
```dolphindb
getDFSDatabases()                             // 所有数据库
getDFSTables()                                // 所有表 (全路径, 无参数!)
getDFSTablesByDatabase("dfs://db")            // 指定库的表
getClusterDFSTables()                         // 集群级别
```

### 3.2 表操作
```dolphindb
t = loadTable("dfs://db", "tableName")       // 加载表句柄(惰性,不读数据)
t.schema()                                    // 返回 schema 字典
t.schema().colDefs                            // 列定义表
t.schema().partitionSchema                    // 分区方案
t.schema().engineType                         // 存储引擎: TSDB / OLAP
t.schema().sortColumns                        // TSDB 排序列
t.size()                                      // 行数 (等价 exec count(*))
```

### 3.3 NULL 处理
```dolphindb
isNull(x)                                     // 判空
nullFill(x, 0)                                // 指定值填充
ffill(x)                                      // 前向填充
bfill(x)                                      // 后向填充
iif(isNull(x), defaultVal, x)                 // 条件替换
```

### 3.4 时间序列 (配合 context by)
```dolphindb
prev(x)                                       // 前一行
next(x)                                       // 后一行
deltas(x)                                     // 一阶差分 (x - prev(x))
ratios(x)                                     // 比率 (x / prev(x))
move(x, n)                                    // 位移 n 行
mavg(x, n)                                    // 移动平均
msum(x, n)                                    // 移动求和
cumsum(x)                                     // 累计求和
```

### 3.5 聚合函数
```dolphindb
avg(x), sum(x), std(x), var(x)               // 基础统计
first(x), last(x)                             // 首尾值
wavg(x, w)                                    // 加权平均 (VWAP 常用)
percentile(x, 50)                             // 百分位
nunique(x)                                    // 去重计数 (直接用, 非嵌套)
```

### 3.6 物理存储
```dolphindb
getTabletsMeta("/db_name/%", `table, true)    // 查 tablet 信息
// 返回包含 diskUsage, rowNum 等列的表
```

## 四、查阅文档的技巧

### 4.1 DeepWiki (DolphinDB 文档 AI 索引)

搜索入口:
```
https://deepwiki.com/search/_7a7f1325-7754-4fb1-920b-b482e1a37c5d?mode=fast&q=关键词
```

直接浏览 wiki 目录（比搜索更可靠）:
```
https://deepwiki.com/tradercjz/documentation          # 总目录
https://deepwiki.com/tradercjz/documentation/2-database-features
https://deepwiki.com/tradercjz/documentation/2.1-distributed-computing-and-partitioning
```

### 4.2 DolphinDB 官方文档
- 函数手册: `https://docs.dolphindb.cn/zh/funcs/funcs_intro.html`
- SQL 参考: `https://docs.dolphindb.cn/zh/sql/index.html`
- 教程集: `https://docs.dolphindb.cn/zh/tutorials/index.html`

### 4.3 搜索策略
1. **函数名精确搜索**: 直接搜 `getDFSTablesByDatabase`
2. **概念搜索**: 搜 `partition` / `context by` / `streaming`
3. **遇到报错**: 复制报错信息搜索（如 `Cannot nest aggregate function`）
4. **如果 deepwiki 总是返回同一页**: 直接浏览目录页，手动进入对应章节

## 五、经典踩坑记录

### 5.1 getDFSTables 不接受参数
```
❌ getDFSTables("dfs://db")    → 报错: expects 0 argument(s)
✅ getDFSTablesByDatabase("dfs://db")
```

### 5.2 count(distinct) 不可嵌套
```
❌ select count(distinct ts_code) from t    → Cannot nest aggregate function
✅ exec count(*) from (select distinct ts_code from t)
```

### 5.3 整数除法 vs 浮点除法
```
❌ close / prev(close)    → 整数除法, 结果截断!
✅ close \ prev(close)    → 浮点除法
```

### 5.4 PowerShell 引号被吃掉
```
❌ execute.py -c "loadTable('dfs://xx', 'yy')"    → 引号丢失
✅ 写成 .dos 文件, 然后 execute.py script.dos
```

### 5.5 脚本最后一行是赋值 → 无输出
```
❌ x = select count(*) from t    → Success 但无结果显示
✅ select count(*) from t         → 直接输出结果
```

### 5.6 时间字面量格式
```dolphindb
2026.03.10            // DATE 类型
2026.03.10T09:30:00   // DATETIME 类型
09:30:00.000          // TIME 类型
2026.03.10 09:30:00   // ⚠️ 空格分隔 → 这是两个值, 不是一个DATETIME!
```

### 5.7 symbol() 函数要求向量输入
```dolphindb
// ❌ symbol(tableName)         → 报错: must be a string/symbol vector
// ✅ symbol([tableName])[0]    → 先包成向量再取第一个
// ✅ `stock_minute_1m          → 直接用 backtick 字面量 (但不能用变量)
```

## 六、典型数据检查报告模板

对于一张新表，按以下顺序出具检查结论:

```
1. 数据规模: X 行, Y 列, Z 只证券, 日期范围 A~B
2. 分区方案: VALUE(trade_date) + HASH(ts_code, 20), TSDB 引擎
3. 数据完整性: 每日每股 241 bar (正常), 无重复
4. 数据质量: pre_close/change/pct_chg 列 99.98% 为 NULL, 其余列无缺失
5. 异常值: close <= 0 的记录 X 条, vol < 0 的记录 Y 条
6. 磁盘占用: ~33 MB
```
