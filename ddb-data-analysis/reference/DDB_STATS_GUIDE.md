# DolphinDB Statistics & Regression (Guide)

本文记录了在 DolphinDB 中进行统计分析和线性回归时的关键点和常见陷阱，特别是针对 `ols` 函数的使用细节。

## 1. 线性回归 (OLS)

DolphinDB 提供了强大的 `ols` 函数，但其返回值结构和参数行为可能因 `mode` 不同而异。

### 1.1 函数签名
```dolphin
ols(y, x, [intercept=true], [mode=0])
```

### 1.2 返回值结构 (Critical)

- **mode=0 (Default)**: 返回系数向量 `Vector`。
- **mode=1**: 返回简单字典 `Dictionary` (Beta, StdError, tValue, pValue)。
- **mode=2 (Comprehensive)**: 返回复杂字典，包含多个表：
  - `Coefficient`: **Table** containing `Factor`, `Estimate` (Beta), `StdError`, `tStat`, `Prob`.
  - `RegressionStat`: Dictionary or Table with `R2`, `AdjR2`, `StdError`, `FStat`, etc.
  - `ANOVA`: Analysis of variance table.
  - `Residual`: Vector of residuals.

### 1.3 系数提取与顺序

当 `intercept=true` 时，DolphinDB 的 OLS 输出中，**Intercept (截距) 通常位于系数列表的第一位**（Index 0），随后是按照 `x` 输入顺序排列的自变量系数。

**提取代码示例 (mode=2)**:
```dolphin
// 如果 x 是 table，y 是 vector
model = ols(y, x, true, 2)

// 提取系数表的第一列（Factor Names）和第二列（Estimates）
// 注意：values(table) 返回列向量的大列表
factor_names = values(model.Coefficient)[0]
estimates = values(model.Coefficient)[1]

// 截距通常是第一项
intercept_val = estimates[0]
weights = estimates[1:] 
```

### 1.4 预测 (Prediction)

DolphinDB 的矩阵乘法 `x ** w` 或 `dot(x, w)` 对类型要求严格。如果遇到类型兼容性问题（如 vector vs scalar vs matrix），推荐显式转换或手动展开计算：

```dolphin
// 安全的预测计算方式 (Manual Dot Product)
// 确保系数转换为 double 标量
w0 = double(weights[0])
w1 = double(weights[1])
inter = double(intercept_val)

// 显式加权求和
y_pred = (x_col1 * w0) + (x_col2 * w1) + inter
```

## 2. 数据处理最佳实践

### 2.1 空值处理 (NaN)
回归函数对 NaN 非常敏感。务必在建模前清洗数据。
```dolphin
// 清洗逻辑：只要任意一个特征是 NaN，就丢弃整行
valid_rows = isValid(Feature1) and isValid(Feature2) and isValid(Target)
clean_data = select * from data where valid_rows
```

### 2.2 样本切分 (Train/Test Split)
金融时间序列必须使用**时间切分 (Time-based Split)**，严禁使用随机切分 (Random Shuffle)，否则会导致未来信息泄露 (Look-ahead Bias)。

```dolphin
// 计算切分点时间
split_ratio = 0.8
split_idx = int(0.8 * count(data))
cutoff_time = data.DateTime[split_idx]

train = select * from data where DateTime <= cutoff_time
test = select * from data where DateTime > cutoff_time
```

## 3. 常见错误排查

- **"Unrecognized column name [R2]"**: `RegressionStat` 可能是一个字典而不是表，访问方式应为 `dict["R2"]` 而不是 `exec R2 from dict`。
- **"Size mismatch"**: 检查 `x` 和 `y` 是否长度一致，通常并在 `ols` 调用前就需要对齐及去空。
- **"Multiply function types"**: 检查是否试图将向量与含有 NULL 的变量相乘，或者将 String 类型系数与数值相乘。
