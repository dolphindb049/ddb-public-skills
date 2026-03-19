---
name: execute-dlang
description: 专注于 DolphinDB 脚本执行的技能。当用户提到“执行 DolphinDB 脚本”、“运行 .dos 文件”或“在 Python 中执行 DDB 代码”时，触发此技能。提供一个基于 Python 的执行环境，支持持久化会话（Persistent Session），让用户能够分步骤执行代码并保留变量定义。
license: MIT
metadata:
  author: ddb-user
  version: "3.0.0"
---

# DolphinDB 执行器 (Script Analysis & Persistence)

本技能包提供了一套基于 Python 的 DolphinDB 执行环境，你可以直接执行dolphindb脚本文件（.dos）或代码片段，或者持久化会话，让你在多次执行中保留变量和函数定义。

## 🚀 极简执行指南 (AI Agent 必读)

作为 AI Agent，当你需要执行 DolphinDB 代码时，**首选使用命令行传参的直连模式**，这样最稳定且不需要依赖任何配置文件。

### 1. 准备工作
确保系统已安装 `uv` (如果没有，请先执行 `pip install uv`)。
本技能包的脚本自带依赖声明，`uv run` 会自动处理包下载。

### 2. 快速执行代码 (推荐)
使用 `execute.py` 并通过参数传入连接信息。

`-c/--code` 现在会先把代码片段写入临时 `.dos` 文件，再按文件模式执行。这样可以减少 DolphinDB 侧因为内联片段过长、含特殊字符而出现的执行问题。

**执行代码片段:**
```powershell
# 先设置环境变量，或把下面占位符替换成你的实际连接信息
uv run ./skills/execute-dlang/scripts/ddb_runner/execute.py -c "1+1" --host <DDB_HOST> --port <DDB_PORT> --user <DDB_USER> --password <DDB_PASSWORD>
```

**从 stdin 执行代码片段（PowerShell 更稳妥）:**
```powershell
@"
pattern = "%check%"
select name from objs(true) where shared = true and lower(name) like pattern
"@ | uv run ./skills/execute-dlang/scripts/ddb_runner/execute.py --stdin --host <DDB_HOST> --port <DDB_PORT> --user <DDB_USER> --password <DDB_PASSWORD>
```

**执行 .dos 文件:**
```powershell
uv run ./skills/execute-dlang/scripts/ddb_runner/execute.py path/to/your_script.dos --host <DDB_HOST> --port <DDB_PORT> --user <DDB_USER> --password <DDB_PASSWORD>
```

---

## 🔄 高级用法：持久化会话 (Server 模式)

如果你需要分步执行代码，并且**保留上下文变量**（例如第一步定义了函数，第二步要调用），你需要使用 Server 模式。

### 步骤 1: 启动后台 Server
在终端中启动 Server（它会保持运行）：
```powershell
uv run ./skills/execute-dlang/scripts/ddb_runner/server.py --host <DDB_HOST> --port <DDB_PORT> --user <DDB_USER> --password <DDB_PASSWORD>
```
*(看到 `[Info] Server listening on 127.0.0.1:65432` 表示成功)*

### 步骤 2: 使用 `--use-server` 发送代码
```powershell
# 定义变量
uv run ./skills/execute-dlang/scripts/ddb_runner/execute.py -c "x = 1..100; y = x * 2;" --use-server

# 调用变量
uv run .github/skills/execute-dlang/scripts/ddb_runner/execute.py -c "avg(y)" --use-server
```

---

## ⚠️ 常见问题与 AI 经验总结 (Pitfalls)

在使用 AI 辅助编程或通过脚本自动化执行时，我们总结了以下**高频错误模式**，请务必注意：

### 1. 脚本执行结果为空 (Empty Return)
*   **现象**: 运行 `execute.py` 后显示 `Success` 但没有内容输出，或者返回 `None`。
*   **原因**: 
    1.  DolphinDB 脚本的最后一行是赋值语句（如 `x = 1`），或 `void` 函数调用，默认不返回结果。
    2.  `print()` 函数在 server 端执行，输出可能流向了 server 的 log (dolphindb.log)，而不是通过 API 返回给 Python client。
*   **解决方案**: 
    *   **显式返回**: 在脚本最后一行单独写上通过想要查看的变量名（例如最后一行写 `resultTable`）。
    *   **尽量少用 print**: 除非你在调试服务端日志，否则尽量让脚本**返回**对象，由 Python 端打印。

### 2. 找不到脚本路径
*   **现象**: 提示 `File not found`。
*   **解决方案**: 脚本现在会自动尝试相对于当前工作目录解析路径。如果仍然找不到，请使用**绝对路径**或**相对于工作区根目录的完整路径**。

### 2.1 PowerShell 引号陷阱（新增）
*   **现象**: `-c` 执行复杂代码时，字符串中的引号被 PowerShell 吞掉，DolphinDB 报 `Cannot recognize token`。
*   **解决方案**:
*   优先使用 `.dos` 文件执行：`execute.py your_script.dos`。
*   若必须动态拼代码，优先使用 `--stdin`，它会把原始输入写入临时 `.dos` 后执行。
*   `-c` 现在内部也会落临时 `.dos`，但它仍然无法修复 **Python 进程启动前** 已被 PowerShell 改写的参数。
*   对包含 URL、DFS 路径、数组字面量、`%...%` 模式串的代码，不要直接依赖 `-c` 的 shell 引号。

### 3. 长连接断开与变量丢失
*   **现象**: 之前定义的 `function` 或 `table` 找不到了。
*   **原因**: `server.py` 可能因为网络波动或报错重启了。
*   **解决方案**: 如果发现变量丢失，请检查 `server.py`终端是否有错误堆栈。重新运行初始化脚本。

### 3. Socket 通信限制 (Buffer Size)
*   **现象**: 执行非常长（几千行）的脚本时，报错或被截断。
*   **原因**: 目前 `server.py` 的接收缓冲区逻辑较为简单 (4096 bytes chunk)，对于极其巨大的脚本可能存在粘包或截断风险。
*   **解决方案**: 
    *   尽量不要一次性发送 MB 级别的 SQL 脚本。
    *   将大任务拆分为多个 `.dos` 文件，使用 `include` 或分次执行。

### 4. 数据类型陷阱与格式化
*   **现象**: 也就是 Python 接收到的数据格式看起来很奇怪（如 Dictionary 变成了 String）。
*   **优化**: 现在的脚本已经内置了 `pandas` 依赖，当 DolphinDB 返回 Table 时，会自动使用 `pandas.DataFrame.to_string(index=False)` 进行格式化输出，使其在终端中更易读。对于 List 和 Dict，也会使用 `pprint` 进行美化。
*   **建议**: 本工具定位为**执行与验证**。如需进行大规模数据拉取与分析（如 Pandas 处理），请直接使用 Python SDK (`import dolphindb`) 编写专门的数据处理脚本，而不是依赖本工具的 shell 输出。

## 📂 文件清单

*   `scripts/ddb_runner/server.py`: 持久化会话服务器（核心）。
*   `scripts/ddb_runner/execute.py`: 客户端命令行入口。
*   `scripts/ddb_runner/.env`: 配置文件（需自行创建/修改）。
