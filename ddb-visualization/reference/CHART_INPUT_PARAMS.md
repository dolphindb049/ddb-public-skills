# Chart Input Parameters (Atomic)

本文件定义“单个图表”的标准入参，不绑定任何业务名称。

## 通用字段

- `type`: 图表类型
- `title`: 模块标题
- `xaxis_title` / `yaxis_title` / `zaxis_title`: 坐标轴标题
- `height`: 可选图高

## 图表类型参数

### 1) `table`
- `columns: string[]`
- `rows: any[][]`

### 2) `line`
- `x: any[]`
- `y: number[]`
- `name: string`

### 3) `line_multi`
- `x: any[]`
- `series: [{name: string, y: number[]}]`

### 4) `bar`
- `x: any[]`
- `y: number[]`
- `name: string`

### 5) `bar_error`
- `x: any[]`
- `y: number[]`
- `error_y: number[]`
- `name: string`

### 6) `hist`
- `x: number[]`
- `name: string`

### 7) `heatmap`
- `x: any[]`
- `y: any[]`
- `z: number[][]`
- `colorscale: string`

### 8) `surface3d`
- `x: any[]`
- `y: any[]`
- `z: number[][]`
- `colorscale: string`

### 9) `code`
- `lang: string`
- `code: string`

### 10) `markdown`
- `text: string`

## 严格模式约束（`--strict`）

- `line/bar/bar_error`: `len(x)==len(y)`
- `bar_error`: `len(error_y)==len(y)`
- `line_multi`: 每个 `series.y` 与 `x` 等长
- `heatmap/surface3d`: `z` 必须是二维矩阵
