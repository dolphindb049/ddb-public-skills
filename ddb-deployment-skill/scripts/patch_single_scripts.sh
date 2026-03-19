#!/bin/bash
# scripts/patch_single_scripts.sh
# 单节点补丁脚本（single mode only）
# 仅对已解压目录执行修复：先改 cfg，再改二进制名，再改 startSingle/stopSingle
# 用法：
# ./patch_single_scripts.sh <SERVER_DIR> <BIN_TAG> <LOCAL_IP> <PORT>
# 说明：<SERVER_DIR> 传实际程序目录，支持 /data/node1/server 或 /data/node1/server/server
# 示例：
# ./patch_single_scripts.sh /data/node1/server 3004_FICC 192.168.1.5 8848

set -euo pipefail

if [ "$#" -ne 4 ]; then
  echo "用法: $0 <SERVER_DIR> <BIN_TAG> <LOCAL_IP> <PORT>"
  exit 1
fi

SERVER_DIR="$1"
BIN_TAG="$2"
LOCAL_IP="$3"
PORT="$4"
BIN_NAME="dolphindb_${BIN_TAG}"

cd "$SERVER_DIR"

if [ ! -f "dolphindb.cfg" ]; then
  echo "[错误] 未找到 dolphindb.cfg: $SERVER_DIR"
  exit 1
fi

# 1) 先改配置
cp -n dolphindb.cfg "dolphindb.cfg.bak.$(date +%Y%m%d%H%M%S)" || true
cat > dolphindb.cfg <<EOF
mode=single
localSite=${LOCAL_IP}:${PORT}:local${PORT}
maxMemSize=4
maxConnections=512
workerNum=4
console=0
EOF

# 2) 再改二进制名 + 赋权
if [ -f "dolphindb" ]; then
  cp -n dolphindb dolphindb.origin || true
  mv -f dolphindb "$BIN_NAME"
fi

if [ ! -f "$BIN_NAME" ]; then
  echo "[错误] 未找到可执行文件：$BIN_NAME（也未找到原始 dolphindb）"
  exit 1
fi

chmod +x "$BIN_NAME"

# 3) 改造 startSingle
cat > startSingle <<EOF
#!/bin/sh
nohup ./${BIN_NAME} -console 0 -mode single > single.nohup 2>&1 &
EOF
chmod +x startSingle

# 4) 改造 stopSingle
cat > stopSingle <<EOF
#!/bin/sh
ps -ef|grep -e "${BIN_NAME}" |grep -e "single"|grep -v grep|awk '{print "kill -15 "\$2}'|sh
EOF
chmod +x stopSingle

echo "[完成] 已更新:"
echo "- dolphindb.cfg (localSite=${LOCAL_IP}:${PORT}:local${PORT})"
echo "- 二进制名称: ${BIN_NAME}"
echo "- startSingle / stopSingle"
