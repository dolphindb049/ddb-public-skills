#!/bin/bash
# scripts/deploy.sh
# 单节点部署（共享服务器安全版，single mode only）
# 规则：先改 cfg(localSite) -> 再改二进制名 -> 再改 startSingle/stopSingle
#
# 用法：
# ./deploy.sh <VERSION> <BIN_TAG> <LOCAL_IP> <PORT> <INSTALL_DIR>
# 示例：
# ./deploy.sh 3.00.4 3004_FICC 192.168.1.5 8848 /data/ddb/3004_FICC

set -euo pipefail

VERSION=${1:-"3.00.4"}
BIN_TAG=${2:-"3004_FICC"}
LOCAL_IP=${3:-"127.0.0.1"}
PORT=${4:-"8848"}
INSTALL_DIR=${5:-"$HOME/dolphindb_single/${BIN_TAG}"}

ZIP_NAME="${BIN_TAG}.zip"
BIN_NAME="dolphindb_${BIN_TAG}"
URL="https://www.dolphindb.cn/downloads/DolphinDB_Linux64_V${VERSION}.zip"
SERVER_DIR=""

printf "\n=== DolphinDB 单节点部署 ===\n"
echo "版本号      : ${VERSION}"
echo "用途标签    : ${BIN_TAG}"
echo "压缩包名    : ${ZIP_NAME}"
echo "可执行文件  : ${BIN_NAME}"
echo "localSite   : ${LOCAL_IP}:${PORT}:local${PORT}"
echo "部署目录    : ${INSTALL_DIR}"
printf "===========================\n\n"

mkdir -p "${INSTALL_DIR}"
cd "${INSTALL_DIR}"

if [ -f "${ZIP_NAME}" ]; then
  echo "[信息] 发现本地压缩包: ${ZIP_NAME}，跳过下载"
else
  echo "[动作] 下载 ${URL}"
  wget -q "${URL}" -O "${ZIP_NAME}"
fi

echo "[动作] 解压到 server 目录"
unzip -q -o "${ZIP_NAME}" -d server

if [ -f "${INSTALL_DIR}/server/server/dolphindb.cfg" ]; then
  SERVER_DIR="${INSTALL_DIR}/server/server"
elif [ -f "${INSTALL_DIR}/server/dolphindb.cfg" ]; then
  SERVER_DIR="${INSTALL_DIR}/server"
else
  echo "[错误] 未找到 dolphindb.cfg，请检查解压目录（server 或 server/server）"
  exit 1
fi

cd "${SERVER_DIR}"

if [ ! -f "dolphindb.cfg" ]; then
  echo "[错误] 未找到配置文件: ${SERVER_DIR}/dolphindb.cfg"
  exit 1
fi

if [ ! -f "dolphindb" ] && [ ! -f "${BIN_NAME}" ]; then
  echo "[错误] 未找到二进制文件: dolphindb 或 ${BIN_NAME}"
  exit 1
fi

# 1) 先改 cfg
cp -n dolphindb.cfg "dolphindb.cfg.bak.$(date +%Y%m%d%H%M%S)" || true
cat > dolphindb.cfg <<EOF
mode=single
localSite=${LOCAL_IP}:${PORT}:local${PORT}
maxMemSize=4
maxConnections=512
workerNum=4
console=0
EOF

echo "[校验] localSite"
grep -n '^localSite=' dolphindb.cfg

# 2) 再改二进制名 + chmod
if [ -f "dolphindb" ]; then
  cp -n dolphindb dolphindb.origin || true
  mv -f dolphindb "${BIN_NAME}"
fi
chmod +x "${BIN_NAME}"

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

# 启停验证
./stopSingle || true
sleep 1
./startSingle
sleep 2

echo "[校验] 端口监听"
if ss -tulnp | grep -q ":${PORT}"; then
  ss -tulnp | grep ":${PORT}"
else
  echo "[警告] 未检测到端口 ${PORT} 监听，请检查日志"
fi

echo "[校验] 启动日志"
head -n 30 dolphindb.log || true

echo "\n[完成] 部署完成。"
echo "目录: ${SERVER_DIR}"
echo "二进制: ${BIN_NAME}"
echo "后续升级只需更新该二进制并保持 startSingle/stopSingle 一致。"
