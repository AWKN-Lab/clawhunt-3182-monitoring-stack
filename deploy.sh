#!/usr/bin/env bash
# 部署入口：生成 file_sd、生成容器指标、启动 mock exporter 与 compose 栈，并做一次探活。
# 口令 fail-closed：从凭据服务读取，缺则拒绝启动（不写默认值、不落盘明文到仓库）。
set -euo pipefail
cd "$(dirname "$0")"

COMPOSE_FILE=docker-compose.monitoring.yml
CREDENTIAL_FILE="${CREDENTIAL_FILE:-$HOME/.config/dnmon/grafana_admin}"
export MONITORING_RETENTION_DAYS="${MONITORING_RETENTION_DAYS:-30}"
export SCRAPE_INTERVAL="${SCRAPE_INTERVAL:-15s}"
export GRAFANA_ADMIN_USER="${GRAFANA_ADMIN_USER:-admin}"

log() { printf '[deploy] %s\n' "$*"; }

if [ ! -r "$CREDENTIAL_FILE" ]; then
  echo "[deploy] FATAL: 凭据服务文件不可读: $CREDENTIAL_FILE" >&2
  echo "[deploy] 请先由凭据服务写入管理员口令（单行），再重跑。" >&2
  exit 10
fi
GRAFANA_ADMIN_PASSWORD="$(head -n1 "$CREDENTIAL_FILE")"
if [ -z "$GRAFANA_ADMIN_PASSWORD" ]; then
  echo "[deploy] FATAL: 凭据文件为空" >&2
  exit 11
fi
export GRAFANA_ADMIN_PASSWORD

# sudo 默认清空环境，compose 的 ${VAR} 插值必须经 --env-file 传入
RUNTIME_ENV=".runtime.env"
umask 077
cat > "$RUNTIME_ENV" <<EOF
GRAFANA_ADMIN_PASSWORD=$GRAFANA_ADMIN_PASSWORD
GRAFANA_ADMIN_USER=$GRAFANA_ADMIN_USER
MONITORING_RETENTION_DAYS=$MONITORING_RETENTION_DAYS
SCRAPE_INTERVAL=$SCRAPE_INTERVAL
EOF
chmod 600 "$RUNTIME_ENV"
cleanup() { rm -f "$RUNTIME_ENV"; }
trap cleanup EXIT
COMPOSE=(sudo -n docker compose --env-file "$RUNTIME_ENV" -f "$COMPOSE_FILE")

log "生成 file_sd 目标文件"
bash scripts/gen_targets.sh

log "渲染 Prometheus 配置（SCRAPE_INTERVAL=$SCRAPE_INTERVAL）"
mkdir -p run
sed "s|\${SCRAPE_INTERVAL}|$SCRAPE_INTERVAL|g" prometheus/prometheus.yml > run/prometheus.rendered.yml
if grep -q '\${' run/prometheus.rendered.yml; then
  echo "[deploy] FATAL: 渲染后仍存在未替换变量" >&2
  exit 12
fi

log "生成容器重启次数 textfile 指标"
bash scripts/gen_container_metrics.sh || log "WARN: 容器指标生成失败（面板该项可能为空）"

log "启动本地 mock exporter（pg:28392 / redis:28394，只绑回环）"
mkdir -p run
if [ -f run/mock_pg.pid ] && kill -0 "$(cat run/mock_pg.pid)" 2>/dev/null; then
  log "mock pg 已在运行"
else
  nohup python3 scripts/mock_exporter.py --family pg --listen 127.0.0.1:28392 \
    > run/mock_pg.log 2>&1 & echo $! > run/mock_pg.pid
fi
if [ -f run/mock_redis.pid ] && kill -0 "$(cat run/mock_redis.pid)" 2>/dev/null; then
  log "mock redis 已在运行"
else
  nohup python3 scripts/mock_exporter.py --family redis --listen 127.0.0.1:28394 \
    > run/mock_redis.log 2>&1 & echo $! > run/mock_redis.pid
fi
sleep 1

log "docker compose up -d"
"${COMPOSE[@]}" up -d
echo "COMPOSE_UP_EXIT=$?"

log "探活"
for i in $(seq 1 30); do
  p=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:28390/-/ready || true)
  g=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:28300/api/health || true)
  [ "$p" = "200" ] && [ "$g" = "200" ] && break
  sleep 2
done
echo "PROMETHEUS_READY_HTTP=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:28390/-/ready)"
echo "GRAFANA_HEALTH_HTTP=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:28300/api/health)"
log "完成。面板: http://127.0.0.1:28300 （需 SSH 隧道；不对公网开放）"
