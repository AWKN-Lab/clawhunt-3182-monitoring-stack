#!/usr/bin/env bash
# 从 docker inspect 生成「容器重启次数」textfile 指标，供 node_exporter textfile collector 读取。
# 只读 docker 元数据，不启动/停止任何容器。
# 注意：Prometheus 文本格式要求所有 # HELP / # TYPE 必须出现在样本之前。
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p textfile
out=textfile/container_restarts.prom
tmp="${out}.tmp"
{
  echo "# HELP container_restart_count 容器累计重启次数"
  echo "# TYPE container_restart_count gauge"
  echo "# HELP container_running 容器是否运行中"
  echo "# TYPE container_running gauge"
  sudo -n docker ps -a --format '{{.Names}}' | while read -r name; do
    [ -z "$name" ] && continue
    rc=$(sudo -n docker inspect -f '{{.RestartCount}}' "$name" 2>/dev/null || echo 0)
    state=$(sudo -n docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null || echo unknown)
    running=0; [ "$state" = "running" ] && running=1
    echo "container_restart_count{name=\"$name\"} $rc"
    echo "container_running{name=\"$name\"} $running"
  done
} > "$tmp"
mv "$tmp" "$out"
# node-exporter 镜像默认以 nobody 运行，目录/文件需可读
chmod 755 textfile 2>/dev/null || true
chmod 644 "$out" 2>/dev/null || true
echo "wrote $out ($(wc -l < "$out") lines)"
