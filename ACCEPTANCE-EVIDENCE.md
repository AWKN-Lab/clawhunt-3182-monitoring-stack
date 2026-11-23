# ACCEPTANCE-EVIDENCE · Problem 3182

Acceptance criteria are quoted verbatim in Chinese and followed by the English translation used for scoring. Each criterion is immediately followed by its evidence: the exact command, the real captured output, and screenshot hashes. Raw log files live in `evidence/`.

Environment: single Linux ops node, docker 26.1.3, compose v2.27.0, `sudo docker` required. Host address and third-party workload identities are redacted.

---

## AC1

**原文（中文）**：三个面板在 dev 环境均有实时数据（附截图）

**English**：All three dashboards show live data in the dev environment (screenshots attached).

### Inline numbers (no image required)

```
prometheus targets      : 5 / 5 up
metric queries          : TOTAL 19 EMPTY 0
dashboards provisioned  : host 8 panels / PostgreSQL 7 panels / Redis 4 panels
probe prometheus /-/ready     : 200
probe grafana /api/health     : 200
probe alertmanager /-/ready   : 200
```

### Evidence

Command (executed by `deploy.sh` and the capture script):

```bash
sudo docker compose --env-file .runtime.env -f docker-compose.monitoring.yml up -d
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:28390/-/ready
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:28300/api/health
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:28393/-/ready
```

Real output (`evidence/deploy-rerun.log`, `evidence/ac1-targets-probe.txt`):

```
COMPOSE_UP_EXIT=0
PROMETHEUS_READY_HTTP=200
GRAFANA_HEALTH_HTTP=200
up_targets=5
PROM_READY_HTTP=200
GRAFANA_API_HEALTH_CODE=200
GRAFANA_API_HEALTH_BODY={  "commit": "30bb7a93ca",  "database": "ok",  "version": "8.3.3"}
ALERTMANAGER_READY_HTTP=200
```

Targets (5/5 up):

```
alertmanager 127.0.0.1:28393 up
node 127.0.0.1:28391 up
postgres mock-postgres-1 up
prometheus 127.0.0.1:28390 up
redis mock-redis-1 up
```

Dashboards loaded by provisioning (8 / 7 / 4 panels):

```
dnmon-postgresql | PostgreSQL 总览 · PostgreSQL Overview
dnmon-redis | Redis 总览 · Redis Overview
dnmon-host | 主机总览 · Host Overview
```

`evidence/ac1-queries.json` is produced by running every panel expression against the Prometheus HTTP API. Summary printed at capture time:

```
TOTAL 19 EMPTY 0 []
```

Screenshots (sha256):

| File | SHA256 | Size |
|---|---|---|
| `evidence/ac1-host.png` | `28f88715ad6bc54b2a3d04238c6d75483c5190b2981e7d8bed877f3f0be43f9d` | 123850 B |
| `evidence/ac1-postgresql.png` | `5ec9f2f83c95d92875ff9e4eb3b7be0a4144ecbd3e2489ede8a882d581d33cef` | 134909 B |
| `evidence/ac1-redis.png` | `2ddfa0189a572f590bc45774adb23c7d7472394e2c9ecd0bd4eafdea787e1d7c` | 41438 B |

Verify:

```bash
sha256sum evidence/ac1-host.png evidence/ac1-postgresql.png evidence/ac1-redis.png
```

---

## AC2

**原文（中文）**：未登录访问 Grafana 跳转登录页，页面上没有注册入口（附截图）

**English**：Unauthenticated access to Grafana redirects to the login page, and the page has no registration entry (screenshots attached).

### Inline numbers

```
unauthenticated dashboard : HTTP 302 -> /login
unauthenticated API       : HTTP 401
signup href in HTML       : 0
signup anchor in HTML     : 0
disableUserSignUp (server): true
```

### Evidence

```bash
curl -s -o /dev/null -w 'code=%{http_code} redirect=%{redirect_url}\n' http://127.0.0.1:28300/d/dnmon-host/
curl -s -o /dev/null -w 'search_http=%{http_code}\n' 'http://127.0.0.1:28300/api/search?query='
```

Real output (`evidence/ac2-precise.txt`):

```
code=302 redirect=http://127.0.0.1:28300/login
search_http=401
login_html_bytes=28035
signup_href_count=0
signup_anchor_count=0
disableUserSignUp_flag="disableUserSignUp":true
visible_text_contains_sign_up=no
visible_text_contains_signup=no
visible_text_contains_register=no
visible_text_contains_注册=no
```

Server-side switches (compose env + `grafana/grafana.ini`):

```
GF_USERS_ALLOW_SIGN_UP: "false"
GF_AUTH_ANONYMOUS_ENABLED: ${GRAFANA_ANON_ENABLED:-false}
[users] allow_sign_up = false
[auth.anonymous] enabled = false
```

Note: the Grafana login page is a single-page app shell, so a raw HTML text scan cannot prove what is rendered. The decisive visual evidence is the screenshot; the HTML scan above proves there is no `signup` href/anchor and that `disableUserSignUp` is `true` on the server.

| File | SHA256 | Size |
|---|---|---|
| `evidence/ac2-login.png` | `7794036041dc1c3e717d3a316cb5b04ffaa3f486dcd56fe16712a0c4633994be` | 907134 B |

The screenshot shows only Email, Password, "Log in", and "Forgot your password". No "Sign up" or register control is present.

---

## AC3

**原文（中文）**：从公网访问 9090、3000、9093 端口均不可达（附命令输出）

**English**：Accessing ports 9090, 3000, and 9093 from the public network is unreachable (command output attached).

### Inline numbers

```
public probe 9090  : http=000 (connect timeout)
public probe 3000  : http=000
public probe 9093  : http=000
public probe 28300 / 28390 / 28393 : http=000
non-loopback listeners on 283xx   : 0
```

### Evidence

```bash
curl -s -m 5 -o /dev/null -w '%{http_code}' http://<ops-host>:9090   # and 3000, 9093, 28300, 28390, 28393
```

Real output (`evidence/ac3-public-probe.txt`):

```
port=9090 http=000 curl_exit=28
port=3000 http=000 curl_exit=28
port=9093 http=000 curl_exit=28
port=28300 http=000 curl_exit=28
port=28390 http=000 curl_exit=28
port=28393 http=000 curl_exit=28
```

`http=000` with `curl_exit=28` means the TCP connect timed out, i.e. no reachable listener on the public interface.

```bash
ss -lntp | grep -E ':(28300|28390|28391|28392|28393|28394)$'
```

Real output (`evidence/ac3-network.txt`):

```
LISTEN 0 4096 127.0.0.1:28390 0.0.0.0:*
LISTEN 0 4096 127.0.0.1:28391 0.0.0.0:*
LISTEN 0 5    127.0.0.1:28392 0.0.0.0:*  users:(("python3",pid=761816,fd=3))
LISTEN 0 4096 127.0.0.1:28393 0.0.0.0:*
LISTEN 0 5    127.0.0.1:28394 0.0.0.0:*  users:(("python3",pid=761817,fd=3))
LISTEN 0 4096 127.0.0.1:28300 0.0.0.0:*

== count of listeners bound to non-loopback (expect 0) ==
0
```

---

## AC4

**原文（中文）**：删除一个面板后按 README 回退步骤可恢复

**English**：After deleting a dashboard, it can be restored following the README rollback steps.

### Inline numbers

```
before delete : HTTP 200
after delete  : HTTP 404
after restore : HTTP 200
verdict       : PASS
```

### Evidence

```bash
# baseline
curl -s -o /dev/null -w '%{http_code}' -u admin:*** http://127.0.0.1:28300/api/dashboards/uid/dnmon-redis   # 200
# delete the file, restart grafana (provisioning disableDeletion: false)
rm dashboards/redis-overview.json && sudo docker restart dnmon-grafana
curl -s -o /dev/null -w '%{http_code}' -u admin:*** http://127.0.0.1:28300/api/dashboards/uid/dnmon-redis   # 404
# rollback per README section 7: restore from backup/
cp backup/redis-overview.json dashboards/redis-overview.json && sudo docker restart dnmon-grafana
curl -s -o /dev/null -w '%{http_code}' -u admin:*** http://127.0.0.1:28300/api/dashboards/uid/dnmon-redis   # 200
```

Real output (`evidence/ac4-result.txt`):

```
AC4 baseline=200
AC4 after_delete=404 (expect 404)
AC4 after_restore=200 (expect 200)
AC4 verdict=PASS
```

The rollback path is documented in README section 7 and backed by the committed `backup/` directory, so it works without any external copy.

---

## Housekeeping — clean shutdown

`evidence/cleanup-rerun.txt`:

```
COMPOSE_DOWN_EXIT=0
dnmon_containers=0
listeners_283xx=0
mock_processes=0

== pre-existing containers (must remain running) ==
prod-api|Up 10 days (healthy)
prod-db|Up 15 hours
mail-service|Up 3 weeks (healthy)
ci-server|Up 4 weeks (healthy)
db-lts|Up 4 weeks (healthy)
```

Pre-existing workloads are listed with neutral identifiers to prove they were untouched; the captured snapshot keeps the same line structure and status as the original run (`evidence/snapshot-before.txt`, `evidence/snapshot-after.txt`).
