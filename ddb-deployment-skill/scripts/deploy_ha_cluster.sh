#!/bin/bash
# scripts/deploy_ha_cluster.sh
# 三机高可用集群总控脚本。
# 运行位置：运维机/跳板机，本机需具备 ssh、scp、tar。
#
# 流程：
# 1) 从 SOURCE_HOST 拉取一份可用的 server 运行时文件到本地临时目录
# 2) 打包为单个 tar.gz
# 3) 上传到三台机器并解压覆盖
# 4) 调用 prepare_ha_server.sh 为每台机器写入 license、HA 配置和启停脚本
# 5) 启动 controller、agent，并校验 7733/7734/7735/7736
#
# 用法：
# ./deploy_ha_cluster.sh <SSH_USER> <HOST1> <HOST2> <HOST3> <TARGET_SERVER_DIR> <OLD_SERVER_DIR> [SOURCE_HOST]
#
# 示例：
# ./deploy_ha_cluster.sh jrzhang 192.168.100.43 192.168.100.44 192.168.100.45 \
#   /hdd/hdd9/jrzhang/ORCA_3.00.5/server \
#   /hdd/hdd9/jrzhang/ORCA_3.00.4.3_7733/server

set -euo pipefail

if [ "$#" -lt 6 ] || [ "$#" -gt 7 ]; then
  echo "用法: $0 <SSH_USER> <HOST1> <HOST2> <HOST3> <TARGET_SERVER_DIR> <OLD_SERVER_DIR> [SOURCE_HOST]"
  exit 1
fi

SSH_USER="$1"
HOST1="$2"
HOST2="$3"
HOST3="$4"
TARGET_SERVER_DIR="${5%/}"
OLD_SERVER_DIR="${6%/}"
SOURCE_HOST="${7:-$HOST1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREP_SCRIPT="$SCRIPT_DIR/prepare_ha_server.sh"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ddb-ha-XXXXXX")"
BUNDLE_FILE="$WORK_DIR/ha_runtime_bundle.tar.gz"

ROOT_FILES=(
  dolphindb
  libDolphinDB.so
  libLLVM-7.1.so
  libgcc_s.so.1
  libgfortran.so.3
  libgfortran.so.5
  libquadmath.so.0
  libstdc++.so.6
  libtcmalloc.so.4
  libunwind.so.8
)

DICT_FILES=(
  hmm_model.utf8
  idf.utf8
  jieba.dict.utf8
  stop_words.utf8
  user.dict.utf8
)

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "缺少命令: $cmd"
    exit 1
  fi
}

fetch_runtime_bundle() {
  mkdir -p "$WORK_DIR/server/dict"

  for file in "${ROOT_FILES[@]}"; do
    scp "$SSH_USER@$SOURCE_HOST:$TARGET_SERVER_DIR/$file" "$WORK_DIR/server/$file"
  done

  for file in "${DICT_FILES[@]}"; do
    scp "$SSH_USER@$SOURCE_HOST:$TARGET_SERVER_DIR/dict/$file" "$WORK_DIR/server/dict/$file"
  done

  tar -C "$WORK_DIR/server" -czf "$BUNDLE_FILE" .
}

push_bundle_to_host() {
  local host="$1"
  scp "$BUNDLE_FILE" "$SSH_USER@$host:/tmp/ha_runtime_bundle.tar.gz"
  ssh "$SSH_USER@$host" "mkdir -p '$TARGET_SERVER_DIR' && tar -xzf /tmp/ha_runtime_bundle.tar.gz -C '$TARGET_SERVER_DIR'"
}

prepare_host() {
  local host="$1"
  local index="$2"
  scp "$PREP_SCRIPT" "$SSH_USER@$host:/tmp/prepare_ha_server.sh"
  ssh "$SSH_USER@$host" "chmod +x /tmp/prepare_ha_server.sh && /tmp/prepare_ha_server.sh '$host' '$index' '$TARGET_SERVER_DIR' '$OLD_SERVER_DIR' SKIP"
}

restart_controller() {
  local host="$1"
  ssh "$SSH_USER@$host" "cd '$TARGET_SERVER_DIR/clusterDemo' && ./stopController.sh || true && ./startController.sh"
}

restart_agent() {
  local host="$1"
  ssh "$SSH_USER@$host" "cd '$TARGET_SERVER_DIR/clusterDemo' && ./stopAgent.sh || true && ./startAgent.sh"
}

verify_host() {
  local host="$1"
  ssh "$SSH_USER@$host" "hostname; ss -ltnp | grep -E ':7733|:7734|:7735|:7736' || true"
}

require_cmd ssh
require_cmd scp
require_cmd tar

if [ ! -f "$PREP_SCRIPT" ]; then
  echo "未找到 prepare_ha_server.sh: $PREP_SCRIPT"
  exit 1
fi

echo "[1/5] 从 $SOURCE_HOST 抓取运行时文件并打包"
fetch_runtime_bundle

echo "[2/5] 上传运行时包到三台机器"
push_bundle_to_host "$HOST1"
push_bundle_to_host "$HOST2"
push_bundle_to_host "$HOST3"

echo "[3/5] 为三台机器写入 license、HA 配置和 clusterDemo 脚本"
prepare_host "$HOST1" 1
prepare_host "$HOST2" 2
prepare_host "$HOST3" 3

echo "[4/5] 启动三台 controller"
restart_controller "$HOST1"
restart_controller "$HOST2"
restart_controller "$HOST3"
sleep 5

echo "[5/5] 启动三台 agent"
restart_agent "$HOST1"
restart_agent "$HOST2"
restart_agent "$HOST3"
sleep 8

echo "[校验] 三台节点监听状态"
verify_host "$HOST1"
verify_host "$HOST2"
verify_host "$HOST3"

echo "[完成] 高可用集群部署流程已执行完毕。"