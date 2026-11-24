# 交付物路径对照表（DELIVERABLE PATH MAP）

> **为什么有这张表**：投标时提交的第一版提案里写的是"计划中的文件路径"；本仓落地时
> 部分文件做了更准确的命名或换了位置（**同一实现**）。买家若按提案里的路径找会找不到，
> 本表给出**一一对应**。
>
> - 提案原文（第一版）：`proposals/3182-proposal.md`
> - 平台现行提案：2026-11-24 修订版，`sha256=ed8d1ea7a025c455e9a00c23624d8cdcf0ba3da8b28eebd23e6b1c0b8dcebc78`
>   （修订后即按本表"本仓实际路径"书写）
> - 逐条验收对照见 `ACCEPTANCE.md`；证据见 `ACCEPTANCE-EVIDENCE.md`

## 一、路径对照

| 提案里写的路径 | 本仓实际路径 | 说明 |
|---|---|---|
| `docker-compose.monitoring.yml` | `docker-compose.monitoring.yml` | 同名：Prometheus / Grafana / Alertmanager / postgres_exporter / redis_exporter，端口全部 `127.0.0.1:<宿主>:<容器>` |
| `deploy/prometheus/prometheus.yml` | `prometheus/prometheus.yml` | 抓取配置（配置在 `prometheus/` 根，不在 `deploy/` 下） |
| `deploy/prometheus/targets/*.json` | `scripts/gen_targets.sh` 生成 → `evidence/ac1-targets-probe.txt` | 目标清单由**脚本按节点清单生成**（`nodes.list` / `exporters.list`），不作为静态文件入库 |
| `deploy/grafana/provisioning/dashboards/*.json` | `dashboards/host-overview.json`<br>`dashboards/postgresql-overview.json`<br>`dashboards/redis-overview.json`<br>`grafana/provisioning/dashboards/default.yml` | 三个面板 JSON + provisioning 入口 |
| `deploy/generate_targets.sh` | `scripts/gen_targets.sh` | 同功能，目录改为 `scripts/` |
| `deploy/verify_private_bind.sh` | **该脚本未入库** ⇒ 等价核验见下表"实测证据" | 本单不交付脚本，改为**交付实测证据**（见下） |
| `docs/panel-screenshots.md` | `evidence/ac1-host.png`<br>`evidence/ac1-postgresql.png`<br>`evidence/ac1-redis.png`<br>`evidence/ac2-login.png` | 面板截图改为**直接放在 `evidence/`**（PNG，不写进 Markdown） |
| `docs/rollback.md` | `README.md`（版本化回退步骤）+ `stop.sh` + `evidence/cleanup-rerun.txt` | 回退步骤并入 README，停止脚本在仓根 |
| `README.md` | `README.md` | 部署 / 变量 / 访问方式 / 回滚 |

## 二、"私网/回环可达"这条 AC 的实测证据（替代未入库的脚本）

| 证据文件 | 内容（实测输出，非说明） |
|---|---|
| `evidence/ac3-public-probe.txt` | 从外部主机探测 9090 / 3000 / 9093 / 28300 / 28390 / 28393 —— 全部 `http=000`、`curl_exit=28`（连接超时/不可达） |
| `evidence/ac3-network.txt` | `ss -ltn` 输出：28300/28390/28391/28392/28393/28394 **全部 LISTEN 在 127.0.0.1**；**非回环监听数 = 0** |
| `evidence/ac4-result.txt` / `evidence/cleanup-rerun.txt` | 面板可用性与收尾（`stop.sh` 后容器 0、283xx 监听 0） |

复跑（在本仓自带等价环境）：

```bash
bash deploy.sh                     # 起监控栈
bash scripts/gen_targets.sh        # 生成抓取目标
bash stop.sh                       # docker compose down + 停 mock exporter
```

## 三、提案未列、但本仓实际提供

| 路径 | 用途 |
|---|---|
| `ACCEPTANCE.md` / `ACCEPTANCE-EVIDENCE.md` | 逐条 AC ↔ 实现 ↔ 复跑命令 ↔ 实测输出 |
| `alertmanager/alertmanager.yml`、`prometheus/rules/dnmon-rules.yml` | 告警规则与 Prometheus 规则 |
| `grafana/grafana.ini`、`grafana/provisioning/datasources/prometheus.yml` | Grafana 配置与数据源 |
| `scripts/mock_exporter.py`、`scripts/gen_container_metrics.sh` | 等价环境用的 mock exporter 与容器指标采集 |
| `backup/{host,postgresql,redis}-overview.json` | 备份/导出用的概览 JSON |
| `nodes.list`、`exporters.list` | 节点清单与 exporter 清单 |
| `tools/gen-manifest.py`、`tools/scan-secrets.py` | 清单生成 / 秘密扫描 |

## 四、复跑命令（与提案一致）

```bash
sha256sum -c MANIFEST.sha256        # 期望：全部 OK（FAILED=0）
python3 tools/scan-secrets.py       # 期望：FINDINGS=0
bash deploy.sh
bash stop.sh
```

## 五、变更说明

本表为**新增说明文件**，不改动任何实现、配置或证据；
`MANIFEST.sha256` 已按本仓规则重算（`python3 tools/gen-manifest.py --root .`）。
