# ACCEPTANCE · ClawHunt Problem 3182

Prometheus / Grafana monitoring stack with three dashboards (host, PostgreSQL, Redis), deployed with docker compose on a single ops node, all ports loopback-only.

- Problem: **3182**
- Deliverable root: this repository
- Evidence index: [ACCEPTANCE-EVIDENCE.md](ACCEPTANCE-EVIDENCE.md)
- Reproduce: [README.md](README.md)
- Manifest: [MANIFEST.sha256](MANIFEST.sha256)

## 1. Acceptance criteria (verbatim) and verdict

| # | 原文（中文） | English | Verdict |
|---|---|---|---|
| AC1 | 三个面板在 dev 环境均有实时数据（附截图） | All three dashboards show live data in the dev environment (screenshots attached). | PASS |
| AC2 | 未登录访问 Grafana 跳转登录页，页面上没有注册入口（附截图） | Unauthenticated access to Grafana redirects to the login page, and the page has no registration entry (screenshots attached). | PASS |
| AC3 | 从公网访问 9090、3000、9093 端口均不可达（附命令输出） | Accessing ports 9090, 3000, and 9093 from the public network is unreachable (command output attached). | PASS |
| AC4 | 删除一个面板后按 README 回退步骤可恢复 | After deleting a dashboard, it can be restored following the README rollback steps. | PASS |

## 2. Key numbers (inline, no image required)

| Metric | Value |
|---|---|
| Prometheus targets | 5 / 5 up |
| Panel metric queries | TOTAL 19, EMPTY 0 |
| Dashboards provisioned | host 8 panels / PostgreSQL 7 panels / Redis 4 panels |
| Probe Prometheus `/-/ready` | 200 |
| Probe Grafana `/api/health` | 200 |
| Probe Alertmanager `/-/ready` | 200 |
| Unauthenticated dashboard access | 302 -> `/login` |
| Unauthenticated API access | 401 |
| Public probes 9090 / 3000 / 9093 | `http=000` (connect timeout) |
| Non-loopback listeners on 283xx | 0 |
| Delete -> restore (AC4) | 200 -> 404 -> 200 |

Full commands and raw output: [ACCEPTANCE-EVIDENCE.md](ACCEPTANCE-EVIDENCE.md).

## 3. Dashboard coverage against the problem statement

| Dashboard | Required metrics | Delivered |
|---|---|---|
| Host | CPU, memory, disk usage and inodes, network traffic, system load, container restart count | 8 panels, all present |
| PostgreSQL | connections vs max_connections, TPS, slow queries, replication lag, deadlocks, top-10 bloated tables, disk usage | 7 panels, all present |
| Redis | memory usage, hit ratio, connected clients, evicted_keys | 4 panels, all present |

Every dashboard has an `env` and a `node` template variable at the top.

## 4. Run evidence summary

| Item | Value |
|---|---|
| `docker compose up -d` exit code | 0 |
| `docker compose down` exit code | 0 |
| Containers remaining after shutdown | 0 |
| Listeners remaining on 283xx after shutdown | 0 |

## 5. Honest disclosure

1. **Data sources for PostgreSQL and Redis are local mock exporters.** No production database is contacted and no customer data is read. `scripts/mock_exporter.py` emits synthetic, time-based series that are shape-compatible with `postgres_exporter` and `redis_exporter`. Real integration only requires replacing `exporters.list` and supplying read-only credentials.
2. **Host metrics are real** (`node_exporter` on the actual node); container restart counts come from a textfile collector fed by `docker inspect`.
3. **Grafana resolved to 8.3.3** from `grafana/grafana:latest` on the test host. All three dashboards load and render on that version. To upgrade, change the image tag in the compose file and re-run `up -d`; dashboard JSON is forward compatible.
4. **Single node.** Multi-node deployment and full cAdvisor coverage need the customer environment; extend `nodes.list` and re-run `scripts/gen_targets.sh`.
5. Ports differ from the upstream defaults (28300/28390/28391/28392/28393/28394 instead of 3000/9090/9100/9187/9121/9093) to avoid collisions on the shared ops host. Both the offset ports and the upstream defaults are verified unreachable from the public side.
6. Pre-existing workloads on the ops host are referenced with neutral identifiers (`prod-api`, `mail-service`, `ci-server`, `db-lts`). Line structure and status in the snapshots are unchanged from the original capture.

## 6. Scope compliance

No bidding, no price change, no platform submission API calls, no force push. Pre-existing containers on the ops host were not modified.
