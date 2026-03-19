#!/bin/bash
# scripts/prepare_ha_server.sh
# 高可用集群单机准备脚本。
# 作用：
# 1) 同步或跳过同步 server 运行时文件
# 2) 复制有效 license
# 3) 生成 controller/agent/cluster 配置
# 4) 生成 clusterDemo 启停脚本并统一使用 orcaddb
#
# 用法：
# ./prepare_ha_server.sh <HOST_IP> <NODE_INDEX:1|2|3> <TARGET_SERVER_DIR> <OLD_SERVER_DIR> [SOURCE_SERVER_DIR|SKIP]
#
# 第 5 个参数说明：
# - 省略：从 FTP 下载运行时文件
# - /path/to/server：从该目录复制运行时文件
# - SKIP：跳过运行时文件同步，只重写 license、配置和脚本

set -euo pipefail

if [ "$#" -ne 4 ] && [ "$#" -ne 5 ]; then
  echo "用法: $0 <HOST_IP> <NODE_INDEX:1|2|3> <TARGET_SERVER_DIR> <OLD_SERVER_DIR> [SOURCE_SERVER_DIR]"
  exit 1
fi

HOST_IP="$1"
NODE_INDEX="$2"
TARGET="${3%/}"
OLD_SERVER="${4%/}"
SOURCE_SERVER="${5:-}"
if [ -n "$SOURCE_SERVER" ]; then
  SOURCE_SERVER="${SOURCE_SERVER%/}"
fi

FTP_BASE="ftp://192.168.1.204/origin/release300.codeRefactor/Release/ALL/release2/cmake_release_all"
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

case "$NODE_INDEX" in
  1)
    CONTROLLER_ALIAS="controller43"
    AGENT_ALIAS="P1-agent"
    DATANODE_ALIAS="dnode1"
    COMPUTENODE_ALIAS="P1-cnode1"
    ;;
  2)
    CONTROLLER_ALIAS="controller44"
    AGENT_ALIAS="P2-agent"
    DATANODE_ALIAS="dnode2"
    COMPUTENODE_ALIAS="P2-cnode1"
    ;;
  3)
    CONTROLLER_ALIAS="controller45"
    AGENT_ALIAS="P3-agent"
    DATANODE_ALIAS="dnode3"
    COMPUTENODE_ALIAS="P3-cnode1"
    ;;
  *)
    echo "NODE_INDEX 只能是 1、2、3"
    exit 1
    ;;
esac

fetch_file() {
  local src="$1"
  local dst="$2"
  if command -v wget >/dev/null 2>&1; then
    wget -q --user=ftpuser --password=DolphinDB123 "$src" -O "$dst"
  elif command -v curl >/dev/null 2>&1; then
    curl -fsS --disable-epsv -u ftpuser:DolphinDB123 "$src" -o "$dst"
  else
    echo "未找到 wget/curl，无法下载补丁"
    exit 1
  fi
}

copy_or_fetch_runtime_file() {
  local relative_path="$1"
  local dst="$2"
  if [ "$SOURCE_SERVER" = "SKIP" ]; then
    return 0
  fi
  if [ -n "$SOURCE_SERVER" ]; then
    cp -f "$SOURCE_SERVER/$relative_path" "$dst"
  else
    fetch_file "$FTP_BASE/$relative_path" "$dst"
  fi
}

timestamp="$(date +%Y%m%d%H%M%S)"
backup_dir="$TARGET/patch_backup_$timestamp"

mkdir -p "$TARGET" "$TARGET/dict" "$TARGET/clusterDemo/config" "$TARGET/clusterDemo/log" "$TARGET/clusterDemo/data"
mkdir -p "$backup_dir/dict"

for file in "${ROOT_FILES[@]}"; do
  [ -e "$TARGET/$file" ] && cp -a "$TARGET/$file" "$backup_dir/"
done

for file in "${DICT_FILES[@]}"; do
  [ -e "$TARGET/dict/$file" ] && cp -a "$TARGET/dict/$file" "$backup_dir/dict/"
done

for file in controller.cfg agent.cfg cluster.cfg cluster.nodes startController.sh startAgent.sh stopController.sh stopAgent.sh stopAllNode.sh; do
  [ -e "$TARGET/clusterDemo/config/$file" ] && cp -a "$TARGET/clusterDemo/config/$file" "$backup_dir/"
  [ -e "$TARGET/clusterDemo/$file" ] && cp -a "$TARGET/clusterDemo/$file" "$backup_dir/"
done

for file in "${ROOT_FILES[@]}"; do
  copy_or_fetch_runtime_file "$file" "$TARGET/$file"
done

for file in "${DICT_FILES[@]}"; do
  copy_or_fetch_runtime_file "dict/$file" "$TARGET/dict/$file"
done

cp -f "$OLD_SERVER/dolphindb.lic" "$TARGET/dolphindb.lic"
chmod +x "$TARGET/dolphindb"
cp -f "$TARGET/dolphindb" "$TARGET/orcaddb"
chmod +x "$TARGET/orcaddb"

cat > "$TARGET/clusterDemo/config/controller.cfg" <<EOF
mode=controller
localSite=${HOST_IP}:7733:${CONTROLLER_ALIAS}
dfsReplicationFactor=2
dfsReplicaReliabilityLevel=2
dataSync=1
workerNum=4
localExecutors=3
maxConnections=512
maxMemSize=8
lanCluster=0
maxFileHandles=102400
datanodeRestartInterval=30
dfsHAMode=Raft
thirdPartyCreateUserCallback=dashboard_grant_functionviews
thirdPartyDeleteUserCallback=dashboard_delete_user
enableORCA=true
EOF

cat > "$TARGET/clusterDemo/config/agent.cfg" <<EOF
mode=agent
localSite=${HOST_IP}:7734:${AGENT_ALIAS}
controllerSite=192.168.100.43:7733:controller43
sites=${HOST_IP}:7734:${AGENT_ALIAS}:agent,192.168.100.43:7733:controller43:controller,192.168.100.44:7733:controller44:controller,192.168.100.45:7733:controller45:controller
workerNum=4
localExecutors=3
maxMemSize=4
lanCluster=0
EOF

cat > "$TARGET/clusterDemo/config/cluster.cfg" <<EOF
maxMemSize=256
maxConnections=512
workerNum=4
localExecutors=3
maxBatchJobWorker=4
OLAPCacheEngineSize=2
TSDBCacheEngineSize=1
newValuePartitionPolicy=add
maxPubConnections=64
subExecutors=4
lanCluster=0
enableChunkGranularityConfig=true
maxFileHandles=102400
subThrottle=1
persistenceWorkerNum=1
enableDFSQueryLog=true
enableAuditLog=true
auditLogRetentionTime=30
webModules=streaming-graph,lineage
enableORCA=true
persistenceDir=/hdd/hdd9/jrzhang/ORCA_3.00.5/server/clusterDemo/data/persistenceDir/<ALIAS>
streamingHADir=/hdd/hdd9/jrzhang/ORCA_3.00.5/server/clusterDemo/data/streamLog/<ALIAS>
streamingRaftGroups=2:dnode1:dnode2:dnode3
streamingHAMode=raft
clusterName=cluster1
EOF

cat > "$TARGET/clusterDemo/config/cluster.nodes" <<EOF
localSite,mode,computeGroup
192.168.100.43:7733:controller43,controller,
192.168.100.44:7733:controller44,controller,
192.168.100.45:7733:controller45,controller,
192.168.100.43:7734:P1-agent,agent,
192.168.100.44:7734:P2-agent,agent,
192.168.100.45:7734:P3-agent,agent,
192.168.100.43:7735:dnode1,datanode,
192.168.100.44:7735:dnode2,datanode,
192.168.100.45:7735:dnode3,datanode,
192.168.100.43:7736:P1-cnode1,computenode,cgroup1
192.168.100.44:7736:P2-cnode1,computenode,cgroup1
192.168.100.45:7736:P3-cnode1,computenode,cgroup1
EOF

cat > "$TARGET/clusterDemo/startController.sh" <<'EOF'
#!/bin/sh
export LD_LIBRARY_PATH=$PWD/../:$LD_LIBRARY_PATH
nohup ./../orcaddb -console 0 -mode controller -home data -script dolphindb.dos -config config/controller.cfg -logFile log/controller.log -nodesFile config/cluster.nodes -clusterConfig config/cluster.cfg > controller.nohup 2>&1 &
EOF

cat > "$TARGET/clusterDemo/startAgent.sh" <<'EOF'
#!/bin/sh
export LD_LIBRARY_PATH=$PWD/../:$LD_LIBRARY_PATH
nohup ./../orcaddb -console 0 -mode agent -home data -script dolphindb.dos -config config/agent.cfg -logFile log/agent.log > agent.nohup 2>&1 &
EOF

cat > "$TARGET/clusterDemo/stopController.sh" <<'EOF'
#!/bin/bash
ps -o ruser=userForLongName -e -o pid,ppid,c,time,cmd | grep "mode controller" | grep -v grep | grep "$USER" | awk '{print $2}' | xargs -r kill -TERM
EOF

cat > "$TARGET/clusterDemo/stopAgent.sh" <<'EOF'
#!/bin/bash
ps -o ruser=userForLongName -e -o pid,ppid,c,time,cmd | grep "mode agent" | grep -v grep | grep "$USER" | awk '{print $2}' | xargs -r kill -TERM
EOF

cat > "$TARGET/clusterDemo/stopAllNode.sh" <<'EOF'
#!/bin/bash
ps -o ruser=userForLongName -e -o pid,ppid,c,time,cmd | grep orcaddb | grep -v grep | grep "$USER" | awk '{print $2}' | xargs -r kill -TERM
EOF

chmod +x \
  "$TARGET/orcaddb" \
  "$TARGET/clusterDemo/startController.sh" \
  "$TARGET/clusterDemo/startAgent.sh" \
  "$TARGET/clusterDemo/stopController.sh" \
  "$TARGET/clusterDemo/stopAgent.sh" \
  "$TARGET/clusterDemo/stopAllNode.sh"

echo "[OK] prepared $(hostname)"
if [ "$SOURCE_SERVER" = "SKIP" ]; then
  echo "[OK] runtime source: skipped"
elif [ -n "$SOURCE_SERVER" ]; then
  echo "[OK] runtime source: $SOURCE_SERVER"
else
  echo "[OK] runtime source: $FTP_BASE"
fi
echo "[OK] binary: $TARGET/orcaddb"
echo "[OK] controller: ${HOST_IP}:7733:${CONTROLLER_ALIAS}"
echo "[OK] agent: ${HOST_IP}:7734:${AGENT_ALIAS}"
echo "[OK] datanode: ${HOST_IP}:7735:${DATANODE_ALIAS}"
echo "[OK] computenode: ${HOST_IP}:7736:${COMPUTENODE_ALIAS}"