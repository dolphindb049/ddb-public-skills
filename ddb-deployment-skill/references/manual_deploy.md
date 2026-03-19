# DolphinDB 单节点手工部署（中文详细版）

本文是 `ddb-deployment-skill` 的参考细化版，适用于 Linux 服务器。

## 1. 前置条件

- Linux（CentOS/Ubuntu 均可）。
- 已安装 `unzip`、`wget`、`ss`（或 `netstat`）。
- 具备下载 DolphinDB 安装包的网络。

---

## 2. 命名约定（建议）

为了多实例共存和后续升级，建议统一命名：

- 压缩包：`版本号+用途.zip`，例如 `3004_FICC.zip`
- 可执行文件：`dolphindb_版本号+用途`，例如 `dolphindb_3004_FICC`

这样可以避免多个目录里都叫 `dolphindb`，排查和升级更清晰。

---

## 3. 下载与解压

```bash
export DDB_VERSION="3.00.4"
export DDB_TAG="3004_FICC"
export ZIP_NAME="${DDB_TAG}.zip"
export INSTALL_DIR="/path/to/your/node/${DDB_TAG}"

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

wget "https://www.dolphindb.cn/downloads/DolphinDB_Linux64_V${DDB_VERSION}.zip" -O "$ZIP_NAME"
unzip -q -o "$ZIP_NAME" -d server
cd server/server
```

---

## 4. 必须先改 `dolphindb.cfg`

先改配置，再改二进制名。

```bash
export LOCAL_IP="<SERVER_IP>"
export DDB_PORT=8848

cp -n dolphindb.cfg "dolphindb.cfg.bak.$(date +%Y%m%d%H%M%S)"

cat > dolphindb.cfg <<EOF
mode=single
localSite=${LOCAL_IP}:${DDB_PORT}:local${DDB_PORT}
maxMemSize=4
maxConnections=512
workerNum=4
console=0
EOF

grep -n '^localSite=' dolphindb.cfg
```

检查点：
- `localSite` 必须与用户要求完全一致。
- 文件中仅保留 1 条 `localSite=`。

---

## 5. 重命名并赋权

```bash
export BIN_NAME="dolphindb_${DDB_TAG}"
cp -n dolphindb dolphindb.origin
mv -f dolphindb "$BIN_NAME"
chmod +x "$BIN_NAME"
```

---

## 6. 改造 `startSingle`

默认脚本常见内容：

```bash
#!/bin/sh
nohup ./dolphindb -console 0 -mode single > single.nohup 2>&1 &
```

改为新二进制名：

```bash
cat > startSingle <<EOF
#!/bin/sh
nohup ./${BIN_NAME} -console 0 -mode single > single.nohup 2>&1 &
EOF
chmod +x startSingle
```

---

## 7. 改造 `stopSingle`（避免影响别人）

默认脚本常见内容：

```bash
#!/bin/sh
ps -ef|grep -e "dolphindb" |grep -e "single"|grep -v grep|awk '{print "kill -15 "$2}'|sh
```

改为匹配新二进制名：

```bash
cat > stopSingle <<EOF
#!/bin/sh
ps -ef|grep -e "${BIN_NAME}" |grep -e "single"|grep -v grep|awk '{print "kill -15 "\$2}'|sh
EOF
chmod +x stopSingle
```

这样不会误停其他目录里的 `dolphindb`。

---

## 8. 启动与验证

```bash
./startSingle
sleep 2
ss -tulnp | grep 8848
head -n 30 dolphindb.log
```

浏览器访问：`http://<SERVER_IP>:8848`

---

## 9. 升级流程（关键）

升级时的重点是更新“实例名二进制”：

1. 下载并解压新版本。
2. `./stopSingle`。
3. 用新版本 `dolphindb` 覆盖当前 `dolphindb_3004_FICC`（你的实例名）。
4. `chmod +x`。
5. `./startSingle`。
6. 看 `dolphindb.log` 和监听端口。

若实例名变化，必须同步更新 `startSingle/stopSingle`。
