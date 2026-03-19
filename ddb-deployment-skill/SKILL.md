---
name: ddb-deployment-skill
description: DolphinDB 部署与升级技能，覆盖单节点部署、共享服务器安全改造，以及三机高可用集群部署。
license: MIT
metadata:
  author: ddb-user
  version: "2.0.0"
---

# DolphinDB 部署与升级 Skill（中文）

本 Skill 现在覆盖两类场景：

1. 单节点部署与升级。
2. 三机高可用集群部署与升级。

设计目标：

- 不误杀他人的 DolphinDB 进程。
- 二进制名称、配置和启停脚本保持一致。
- 共享服务器上可安全并存多个实例。
- 高可用场景下三台机器的 cluster 配置可重复生成。
- 当 FTP 传大文件不稳定时，支持“从一台可用机器打 bundle，再统一下发”的做法。

## 模式划分

### 模式 A：单节点

适用场景：

- 只启动一个 `single` 实例。
- 需要安全改造 `dolphindb.cfg`、二进制名称、`startSingle`、`stopSingle`。

核心规范：

1. 先改 `dolphindb.cfg`，再改二进制名。
2. `localSite` 必须精确匹配用户要求。
3. 二进制必须重命名为实例名，例如 `dolphindb_3004_FICC`。
4. `startSingle` 与 `stopSingle` 必须同步改成新名称。

### 模式 B：高可用集群

适用场景：

- 三台机器部署 controller + agent + datanode + computenode。
- 需要 Raft 控制节点和统一的 `cluster.nodes` / `cluster.cfg`。
- 需要以 `orcaddb` 这样的独立名称运行集群二进制，避免影响其他实例。

当前脚本默认支持的拓扑是每台机器各 1 个 controller、1 个 agent、1 个 datanode、1 个 computenode：

- `7733`：controller
- `7734`：agent
- `7735`：datanode
- `7736`：computenode

当前内置三机映射：

- `192.168.100.43` -> `controller43` / `P1-agent` / `dnode1` / `P1-cnode1`
- `192.168.100.44` -> `controller44` / `P2-agent` / `dnode2` / `P2-cnode1`
- `192.168.100.45` -> `controller45` / `P3-agent` / `dnode3` / `P3-cnode1`

高可用模式核心规范：

1. 三台机器的 `cluster.nodes` 必须完全一致。
2. `controller.cfg` 的 `localSite` 必须各自唯一。
3. `agent.cfg` 中 `sites=` 必须写成 `host:port:alias:type` 形式。
4. 三台机器都必须有可运行的 `server` 运行时文件。
5. 如果大文件直传不稳定，优先从一台已验证可用的机器打一个 bundle，再统一上传。
6. 有效 license 必须从可用旧实例复制，不能依赖新包自带的试用 license。

## 单节点工作流

### 一键部署

```bash
./scripts/deploy.sh 3.00.4 3004_FICC 192.168.1.5 8848 /data/ddb/3004_FICC
```

### 对现有目录做安全改造

```bash
./scripts/patch_single_scripts.sh /data/ddb/3004_FICC/server 3004_FICC 192.168.1.5 8848
```

### 单节点验证

```bash
./startSingle
sleep 2
ss -tulnp | grep 8848
head -n 30 dolphindb.log
```

## 高可用集群工作流

### 前置条件

- 三台服务器之间网络互通。
- 管理机可以通过 `ssh` / `scp` 免密访问三台机器。
- 三台机器目标目录中已经解压出对应版本的 `server` 目录，或者可以被 bundle 覆盖。
- 至少有一台机器存在一份“确认可运行”的 `server` 运行时文件，可作为 `SOURCE_HOST`。
- 旧版本有效 license 位于 `OLD_SERVER_DIR/dolphindb.lic`。

### 推荐目录约定

```bash
TARGET_SERVER_DIR=/hdd/hdd9/jrzhang/ORCA_3.00.5/server
OLD_SERVER_DIR=/hdd/hdd9/jrzhang/ORCA_3.00.4.3_7733/server
```

### 单机准备脚本

如果你只想修某一台机器，用：

```bash
./scripts/prepare_ha_server.sh 192.168.100.43 1 \
  /hdd/hdd9/jrzhang/ORCA_3.00.5/server \
  /hdd/hdd9/jrzhang/ORCA_3.00.4.3_7733/server \
  SKIP
```

第 5 个参数支持三种模式：

1. 省略：从 FTP 下载运行时文件。
2. 传目录路径：从某个现成 `server` 目录复制运行时文件。
3. `SKIP`：跳过运行时文件同步，只重写 license、配置和脚本。

### 三机总控脚本

建议优先使用总控脚本：

```bash
./scripts/deploy_ha_cluster.sh jrzhang \
  192.168.100.43 192.168.100.44 192.168.100.45 \
  /hdd/hdd9/jrzhang/ORCA_3.00.5/server \
  /hdd/hdd9/jrzhang/ORCA_3.00.4.3_7733/server \
  192.168.100.43
```

它会自动完成：

1. 从 `SOURCE_HOST` 拉取一份已验证的运行时文件。
2. 在管理机本地打包成单个 `tar.gz`。
3. 上传到三台机器并覆盖解压。
4. 调用 `prepare_ha_server.sh` 为三台机器生成 HA 配置和脚本。
5. 依次启动三台 controller，再启动三台 agent。
6. 校验 `7733`、`7734`、`7735`、`7736` 监听状态。

### 高可用验证要点

controller 启动后，应至少看到：

```bash
ss -ltnp | grep 7733
tail -n 30 clusterDemo/log/controller.log
```

agent 启动后，应看到 agent 收到 `startDataNodeAgent` 指令，并拉起 datanode / computenode：

```bash
ss -ltnp | grep -E '7734|7735|7736'
tail -n 50 clusterDemo/log/agent.log
```

## 升级建议

### 单节点升级

1. `./stopSingle`
2. 用新版本 `dolphindb` 覆盖当前实例名二进制。
3. `chmod +x`
4. `./startSingle`

### 高可用集群升级

1. 先停三台机器上的 controller / agent / datanode / computenode。
2. 备份 controller 元数据和 datanode 元数据。
3. 优先使用一台机器验证新版本运行时文件。
4. 以“bundle 下发”的方式替换三台机器运行时文件。
5. 保留现有 `clusterDemo/config` 语义一致，再统一重启 controller 和 agent。

## 脚本清单

- `scripts/deploy.sh`
  单节点一键部署脚本。
- `scripts/patch_single_scripts.sh`
  单节点目录修复脚本。
- `scripts/prepare_ha_server.sh`
  高可用集群单机准备脚本。
- `scripts/deploy_ha_cluster.sh`
  高可用集群三机总控脚本。

## 适用边界

当前高可用脚本是按“3 台机器、每台 1 controller + 1 agent + 1 datanode + 1 computenode”的模式写死的。

如果你要扩成：

- 每台多个 datanode
- 不同端口规划
- 不同节点别名
- 不同持久化目录或 volumes

则应在 `prepare_ha_server.sh` 里调整别名映射和 `cluster.nodes` / `cluster.cfg` 生成逻辑。

如果你要我直接执行部署，请给我以下信息：

1. 版本号
2. 三台机器 IP
3. controller / agent / datanode / computenode 端口规划
4. 目标安装目录
5. 旧 license 所在目录
6. 运行时文件来源：FTP、某台已可用机器，或本地 bundle
