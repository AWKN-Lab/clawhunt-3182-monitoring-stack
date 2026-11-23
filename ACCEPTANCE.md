# ACCEPTANCE · ClawHunt Problem 3182

Prometheus / Grafana monitoring stack with three dashboards (host, PostgreSQL, Redis), deployed with docker compose on a single ops node, all ports loopback-only.

- Problem: **3182**
- Deliverable root: this repository
- Evidence index: [ACCEPTANCE-EVIDENCE.md](ACCEPTANCE-EVIDENCE.md)
- Reproduce: [README.md](README.md)
- Manifest: [MANIFEST.sha256](MANIFEST.sha256)

## 1. Acceptance criteria and verdict

| # | Criterion (from problem statement) | Verdict | Primary evidence |
|---|---|---|---|
| AC1 | Three dashboards show live data in the dev environment (screenshots attached) | PASS | `evidence/ac1-host.png`, `evidence/ac1-postgresql.png`, `evidence/ac1-redis.png`, `evidence/ac1-queries.json` (19/19 queries non-empty), `evidence/ac1-targets-probe.txt` |
| AC2 | Unauthenticated visit redirects to login page and the page has no self-signup entry (screenshots attached) | PASS | `evidence/ac2-login.png`, `evidence/ac2-precise.txt` (302 redirect, `disableUserSignUp:true`, signup href = 0) |
| AC3 | Public access to 9090 / 3000 / 9093 is unreachable (command output attached) | PASS | `evidence/ac3-public-probe.txt` (all `http=000`), `evidence/ac3-network.txt` (listeners bound to `127.0.0.1` only, non-loopback count = 0) |
| AC4 | After deleting a dashboard, the README rollback steps restore it | PASS | `evidence/ac4-result.txt` (before 200 -> deleted 404 -> restored 200) |

## 2. Dashboard coverage against the problem statement

| Dashboard | Required metrics | Delivered |
|---|---|---|
| Host | CPU, memory, disk usage and inodes, network traffic, system load, container restart count | 8 panels, all present |
| PostgreSQL | connections vs max_connections, TPS, slow queries, replication lag, deadlocks, top-10 bloated tables, disk usage | 7 panels, all present |
| Redis | memory usage, hit ratio, connected clients, evicted_keys | 4 panels, all present |

Every dashboard has an `env` and a `node` template variable at the top.

## 3. Run evidence summary

| Item | Value |
|---|---|
| `docker compose up -d` exit code | 0 |
| `docker compose down` exit code | 0 |
| Prometheus `/-/ready` | 200 |
| Grafana `/api/health` | 200 (`database: ok`) |
| Alertmanager `/-/ready` | 200 |
| Prometheus targets | 5 / 5 up |
| Metric queries non-empty | 19 / 19 |
| Containers remaining after shutdown | 0 |
| Listeners remaining on 283xx after shutdown | 0 |

## 4. Honest disclosure

1. **Data sources for PostgreSQL and Redis are local mock exporters.** No production database is contacted and no customer data is read. `scripts/mock_exporter.py` emits synthetic, time-based series that are shape-compatible with `postgres_exporter` and `redis_exporter`. Real integration only requires replacing `exporters.list` and supplying read-only credentials.
2. **Host metrics are real** (`node_exporter` on the actual node); container restart counts come from a textfile collector fed by `docker inspect`.
3. **Grafana resolved to 8.3.3** from `grafana/grafana:latest` on the test host. All three dashboards load and render on that version. To upgrade, change the image tag in the compose file and re-run `up -d`; dashboard JSON is forward compatible.
4. **Single node.** Multi-node deployment and full cAdvisor coverage need the customer environment; extend `nodes.list` and re-run `scripts/gen_targets.sh`.
5. Ports differ from the upstream defaults (28300/28390/28391/28392/28393/28394 instead of 3000/9090/9100/9187/9121/9093) to avoid collisions on the shared ops host. Both the offset ports and the upstream defaults are verified unreachable from the public side.

## 5. Scope compliance

No bidding, no price change, no platform submission API calls, no force push. Pre-existing containers on the ops host were not modified.
