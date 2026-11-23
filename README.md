# ClawHunt #3182 · 监控栈部署（Prometheus + Grafana + 主机/PG/Redis 三面板）

- 层级：L2 组件「监控栈」→ L3 模块「compose 编排 / Prometheus 配置 / 三张面板 / 部署脚本」
- 目标：在运维节点用 docker compose 部署 Prometheus、Grafana、Alertmanager、node_exporter、postgres_exporter、redis_exporter；三个面板以 Grafana provisioning JSON 入库；全部只监听私网/回环。

## 1. 目录

```
ACCEPTANCE.md                  验收结论：四条 AC 与证据索引
ACCEPTANCE-EVIDENCE.md         逐条 AC 的命令、真实输出、截图 sha256
MANIFEST.sha256                全仓文件 SHA256 清单（sha256sum -c 可校验）
docker-compose.monitoring.yml  compose 编排（全部 network_mode: host，只绑 127.0.0.1）
deploy.sh / stop.sh            起栈与清栈入口
prometheus/prometheus.yml      抓取配置（file_sd：targets/*.json）
prometheus/rules/*.yml         基础告警规则
alertmanager/alertmanager.yml  告警路由（本次不外发）
grafana/grafana.ini            关闭匿名访问与自助注册（AC2）
grafana/provisioning/          数据源 + 面板自动入库
dashboards/                    三个面板 JSON（可单独导入）
backup/                        三个面板 JSON 的副本，供 AC4 回退使用
scripts/gen_targets.sh         按 nodes.list / exporters.list 生成 file_sd
scripts/gen_container_metrics.sh  生成容器重启次数 textfile 指标
scripts/mock_exporter.py       本地 mock PG/Redis exporter（不连生产库）
nodes.list / exporters.list    节点与 exporter 清单
tools/scan-secrets.py          密钥/PII 扫描（0 命中为通过）
tools/gen-manifest.py          生成 MANIFEST.sha256
evidence/                      截图与运行日志
```

校验交付完整性：

```bash
sha256sum -c MANIFEST.sha256        # 期望：39 行全部 OK
python3 tools/scan-secrets.py       # 期望：FINDINGS=0
```

## 2. 怎么起

前置：Linux 主机、docker 26 + compose v2、`sudo docker` 可用；管理员口令由凭据服务写入本机文件（默认 `~/.config/dnmon/grafana_admin`，单行、权限 600）。

```bash
# 1) 由凭据服务写入口令（示例：从 KMS/secret 管理器取）
mkdir -p ~/.config/dnmon && chmod 700 ~/.config/dnmon
printf '%s\n' "$(your-credential-cli get grafana_admin)" > ~/.config/dnmon/grafana_admin
chmod 600 ~/.config/dnmon/grafana_admin

# 2) 起栈（会生成 targets、启动 mock exporter、docker compose up -d，并探活）
bash deploy.sh
```

预期末尾输出：

```
COMPOSE_UP_EXIT=0
PROMETHEUS_READY_HTTP=200
GRAFANA_HEALTH_HTTP=200
```

## 3. 怎么看板

服务只绑回环，需先建 SSH 隧道（不要对公网开放）：

```bash
ssh -N -L 28300:127.0.0.1:28300 -L 28390:127.0.0.1:28390 <user>@<host>
```

- Grafana：`http://127.0.0.1:28300`（用 `GRAFANA_ADMIN_USER` + 凭据服务口令登录）
- 面板：左侧 Dashboards → 文件夹 `Monitoring` → 主机总览 / PostgreSQL 总览 / Redis 总览
- Prometheus：`http://127.0.0.1:28390`（Targets 页三个 job 应全部 UP）

面板 JSON 也可单独导入：Grafana → Dashboards → New → Import → 上传 `dashboards/*.json`（导入时选择 `Prometheus` 数据源）。

## 4. 变量

| 变量 | 位置 | 默认 | 说明 |
|---|---|---|---|
| `MONITORING_RETENTION_DAYS` | 环境变量 / compose | 30 | Prometheus 数据保留天数 |
| `SCRAPE_INTERVAL` | 环境变量 / compose | 15s | 全局抓取间隔 |
| `GRAFANA_ADMIN_PASSWORD` | 凭据服务文件 | 无（缺则拒绝启动） | 管理员口令，fail-closed |
| `GRAFANA_ADMIN_USER` | 环境变量 | admin | 管理员用户名 |
| `CREDENTIAL_FILE` | 环境变量 | `~/.config/dnmon/grafana_admin` | 凭据服务落点 |

| `GRAFANA_ANON_ENABLED` | 环境变量 | false | 匿名访问开关；默认关闭（AC2），仅截图取证时临时置 true |

每个面板顶部有「环境」与「节点」两个下拉变量。

## 5. 怎么停

```bash
bash stop.sh      # docker compose down + 停 mock exporter，保留数据卷
# 彻底清理（含数据卷，不可恢复）：
sudo docker compose -f docker-compose.monitoring.yml down -v
```

## 6. AC 自证命令

| AC | 命令 | 预期 |
|---|---|---|
| AC1 三面板有实时数据 | `curl -s 'http://127.0.0.1:28390/api/v1/query?query=up' \| jq '.data.result[].metric.job'` | 输出 `node`/`postgres`/`redis`/`prometheus`/`alertmanager`，`value[1]` 均为 `1` |
| AC2 未登录跳登录页、无注册入口 | `curl -s -o /dev/null -w '%{http_code} %{redirect_url}' http://127.0.0.1:28300/d/`；`curl -s http://127.0.0.1:28300/login \| grep -ci 'sign up\|signup\|注册'` | `302 .../login`；`0` |
| AC3 公网 9090/3000/9093 不可达 | 在外部主机 `curl -m 5 -o /dev/null -w '%{http_code}' http://<host>:9090`（3000/9093 同） | 三次均 `000`（连接失败）；本机 `ss -lntp \| grep -E ':(28300\|28390\|28393)'` 仅见 `127.0.0.1` |
| AC4 删面板可回退 | 见第 7 节 | 面板消失后按步骤恢复 |

## 7. 回退步骤（AC4）

面板由 Grafana provisioning 从 `dashboards/` 读取，文件即真相。

```bash
# 1) 模拟误删：删除一个面板文件并让 Grafana 重新加载
rm dashboards/redis-overview.json
sudo docker compose -f docker-compose.monitoring.yml restart grafana
# 验证面板已消失
curl -s -u admin:"$PW" 'http://127.0.0.1:28300/api/search?query=Redis'   # 期望空数组

# 2) 回退：从版本库恢复上一提交（或从 backup/ 复制）
git checkout -- dashboards/redis-overview.json        # 版本化回退
# 或者：cp backup/redis-overview.json dashboards/

# 3) 重新加载
sudo docker compose -f docker-compose.monitoring.yml up -d
# 验证面板恢复
curl -s -u admin:"$PW" 'http://127.0.0.1:28300/api/search?query=Redis'   # 期望返回 dnmon-redis
```

compose 文件与面板 JSON 均版本化；整体回退到上一提交后 `docker compose up -d` 即恢复。

## 8. 数据源口径与差异披露（诚实声明）

| 原文要求 | 本次交付 | 说明 |
|---|---|---|
| postgres_exporter（只读 monitor 账号，凭据从 KMS 读取） | 本地 mock exporter（`scripts/mock_exporter.py`，family=pg，127.0.0.1:28392） | **不连接任何真实数据库**；接入真实库需客户环境，替换 targets + 加只读账号凭据后即生效 |
| redis_exporter | 本地 mock exporter（family=redis，127.0.0.1:28394） | 同上 |
| 每个应用节点 node_exporter + cAdvisor | 单节点真实 node_exporter；容器重启次数由 textfile collector 从 docker inspect 生成 | 多节点/全套 cAdvisor 指标需客户环境扩展 `nodes.list` 后补验 |
| 抓取目标 file_sd `targets/*.json`，部署脚本按节点清单生成 | `scripts/gen_targets.sh` + `nodes.list` / `exporters.list` | 一致 |
| 变量 monitoring_retention_days / grafana_admin_secret_name / scrape_interval | `MONITORING_RETENTION_DAYS` / `CREDENTIAL_FILE`（等价于 grafana_admin_secret_name 的落点）/ `SCRAPE_INTERVAL` | 语义一致，命名适配环境变量 |
| 端口 9090 / 3000 / 9093 | 实际监听 28390 / 28300 / 28393（回环） | 与宿主既有服务隔离，端口段 28300-28399 已登记 PORTS.md；默认端口同样探测为不可达 |

## 9. 端口（只绑回环）

| 端口 | 组件 |
|---|---|
| 28300 | Grafana |
| 28390 | Prometheus |
| 28391 | node_exporter |
| 28392 | mock postgres_exporter |
| 28393 | Alertmanager |
| 28394 | mock redis_exporter |

## 10. 实测环境（2026-11-23，161 单节点）

| 项 | 值 |
|---|---|
| 主机 | Linux，2 vCPU / 1.87 GB RAM / 40 GB 磁盘 |
| docker | 26.1.3（overlay2），compose v2.27.0，均需 `sudo` |
| Prometheus | prom/prometheus:latest（201MB） |
| Grafana | grafana/grafana:latest，实测解析为 **8.3.3**（镜像构建于 2021-12-10） |
| Alertmanager | prom/alertmanager:latest（57.5MB） |
| node_exporter | prom/node-exporter:latest（20.9MB） |

> 说明：`grafana/grafana:latest` 在本机拉到的是 8.3.3。三个面板在该版本下已全部加载并渲染（见 evidence/ac1-*.png）。如需更新版本，改 compose 中 `image` 为固定 tag（如 `grafana/grafana:11.3.0`）后重新 `up -d` 即可，面板 JSON 向上兼容。

## 11. 安全

- 全部组件 `127.0.0.1` 监听，公网不可达；
- Grafana 关闭匿名访问（`auth.anonymous.enabled=false`）与自助注册（`allow_sign_up=false`）；
- 管理员口令不写入仓库，仅经环境变量注入进程；
- mock exporter 不读取任何真实数据。
