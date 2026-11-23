#!/usr/bin/env bash
# 清栈：停止 compose 栈与本地 mock exporter，保留数据卷（便于二次启动）。
set -uo pipefail
cd "$(dirname "$0")"

# down 仍需满足 compose 的 ${VAR} 插值，用占位值即可，不读取真实口令
umask 077
cat > .runtime.env <<'EOF'
GRAFANA_ADMIN_PASSWORD=unused-on-down
GRAFANA_ADMIN_USER=admin
MONITORING_RETENTION_DAYS=30
SCRAPE_INTERVAL=15s
EOF
chmod 600 .runtime.env
trap 'rm -f .runtime.env' EXIT

echo "[stop] docker compose down"
sudo -n docker compose --env-file .runtime.env -f docker-compose.monitoring.yml down
echo "COMPOSE_DOWN_EXIT=$?"

for f in run/mock_pg.pid run/mock_redis.pid; do
  if [ -f "$f" ]; then
    pid=$(cat "$f")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" && echo "[stop] killed mock pid=$pid"
    fi
    rm -f "$f"
  fi
done
echo "[stop] 剩余 dnmon 容器："
sudo -n docker ps -a --filter 'name=dnmon-' --format '{{.Names}} {{.Status}}' || true
