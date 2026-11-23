#!/usr/bin/env python3
"""本地 mock exporter：模拟 postgres_exporter 与 redis_exporter 的指标。

用途：ClawHunt #3182 验收环境。**不连接任何真实 PostgreSQL / Redis**，
不读取客户数据，仅按时间生成可绘制、可聚合的合成序列。
只绑回环。默认起两条独立 target，贴合原文「postgres_exporter + redis_exporter」两个组件：

  python3 mock_exporter.py --family pg    --listen 127.0.0.1:28392
  python3 mock_exporter.py --family redis --listen 127.0.0.1:28394
"""
import argparse
import math
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

START = time.time()

TABLES = [
    "public.orders", "public.members", "public.payments", "public.events",
    "public.audit_log", "public.sessions", "public.resources", "public.leads",
    "public.sites", "public.orgs", "public.tickets", "public.attachments",
]


def counter(rate: float, base: float = 0.0) -> float:
    """单调递增计数器，避免 counter 回退导致 rate() 断点。"""
    return base + rate * (time.time() - START)


def gauge(base: float, amp: float, period: float, phase: float = 0.0) -> float:
    return base + amp * math.sin((time.time() - START) / period + phase)


def render_pg() -> str:
    t = time.time() - START
    L = [
        "# HELP pg_up 模拟实例存活",
        "# TYPE pg_up gauge",
        "pg_up 1",
        "# HELP pg_settings_max_connections 模拟 max_connections",
        "# TYPE pg_settings_max_connections gauge",
        "pg_settings_max_connections 200",
        "# HELP pg_stat_database_numbackends 后端连接数",
        "# TYPE pg_stat_database_numbackends gauge",
        f'pg_stat_database_numbackends{{datname="appdb"}} {max(1, gauge(28, 10, 90)):.0f}',
        f'pg_stat_database_numbackends{{datname="reportdb"}} {max(1, gauge(9, 4, 130, 1.1)):.0f}',
        "# HELP pg_stat_activity_count 按状态统计的活动连接",
        "# TYPE pg_stat_activity_count gauge",
        f'pg_stat_activity_count{{state="active"}} {max(0, gauge(12, 5, 70)):.0f}',
        f'pg_stat_activity_count{{state="idle"}} {max(0, gauge(20, 7, 110, 0.5)):.0f}',
        "# HELP pg_stat_database_xact_commit 已提交事务总数",
        "# TYPE pg_stat_database_xact_commit counter",
        f'pg_stat_database_xact_commit{{datname="appdb"}} {counter(42):.0f}',
        "# HELP pg_stat_database_xact_rollback 回滚事务总数",
        "# TYPE pg_stat_database_xact_rollback counter",
        f'pg_stat_database_xact_rollback{{datname="appdb"}} {counter(1.6):.0f}',
        "# HELP pg_stat_database_deadlocks 死锁总数",
        "# TYPE pg_stat_database_deadlocks counter",
        f'pg_stat_database_deadlocks{{datname="appdb"}} {counter(0.004):.0f}',
        "# HELP pg_slow_queries_total 慢查询总数",
        "# TYPE pg_slow_queries_total counter",
        f"pg_slow_queries_total {counter(0.09, 120):.0f}",
        "# HELP pg_replication_lag_seconds 复制延迟(秒)",
        "# TYPE pg_replication_lag_seconds gauge",
        f"pg_replication_lag_seconds {max(0.0, gauge(0.8, 0.6, 45)):.3f}",
        "# HELP pg_database_size_bytes 数据库磁盘占用",
        "# TYPE pg_database_size_bytes gauge",
        f"pg_database_size_bytes {12.4 * 1024 ** 3 + t * 2048:.0f}",
        "# HELP pg_table_bloat_bytes 表膨胀估算",
        "# TYPE pg_table_bloat_bytes gauge",
    ]
    for i, tb in enumerate(TABLES):
        val = (14 - i) * 1024 ** 2 * (1 + 0.06 * math.sin(t / 60 + i))
        L.append(f'pg_table_bloat_bytes{{relname="{tb}"}} {max(0, val):.0f}')
    L += [
        "# HELP pg_stat_database_tup_fetched 读取元组总数",
        "# TYPE pg_stat_database_tup_fetched counter",
        f"pg_stat_database_tup_fetched {counter(3800):.0f}",
    ]
    return "\n".join(L) + "\n"


def render_redis() -> str:
    t = time.time() - START
    used = 320 * 1024 ** 2 + 40 * 1024 ** 2 * math.sin(t / 80)
    L = [
        "# HELP redis_up 模拟实例存活",
        "# TYPE redis_up gauge",
        "redis_up 1",
        "# HELP redis_memory_used_bytes 已用内存",
        "# TYPE redis_memory_used_bytes gauge",
        f"redis_memory_used_bytes {max(0, used):.0f}",
        "# HELP redis_memory_max_bytes maxmemory 上限",
        "# TYPE redis_memory_max_bytes gauge",
        f"redis_memory_max_bytes {1024 ** 3}",
        "# HELP redis_keyspace_hits_total 命中总数",
        "# TYPE redis_keyspace_hits_total counter",
        f"redis_keyspace_hits_total {counter(900, 50000):.0f}",
        "# HELP redis_keyspace_misses_total 未命中总数",
        "# TYPE redis_keyspace_misses_total counter",
        f"redis_keyspace_misses_total {counter(62, 4000):.0f}",
        "# HELP redis_connected_clients 客户端连接数",
        "# TYPE redis_connected_clients gauge",
        f"redis_connected_clients {max(1, gauge(46, 12, 100)):.0f}",
        "# HELP redis_evicted_keys_total 驱逐总数",
        "# TYPE redis_evicted_keys_total counter",
        f"redis_evicted_keys_total {counter(0.02):.0f}",
        "# HELP redis_commands_processed_total 命令处理总数",
        "# TYPE redis_commands_processed_total counter",
        f"redis_commands_processed_total {counter(1500):.0f}",
    ]
    return "\n".join(L) + "\n"


class Handler(BaseHTTPRequestHandler):
    family = "both"

    def do_GET(self):
        if self.path not in ("/metrics", "/"):
            self.send_response(404)
            self.end_headers()
            return
        if self.family == "pg":
            body = render_pg().encode()
        elif self.family == "redis":
            body = render_redis().encode()
        else:
            body = (render_pg() + render_redis()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", default="127.0.0.1:28392")
    ap.add_argument("--family", choices=["pg", "redis", "both"], default="both")
    a = ap.parse_args()
    host, port = a.listen.rsplit(":", 1)
    Handler.family = a.family
    srv = ThreadingHTTPServer((host, int(port)), Handler)
    print(f"mock exporter family={a.family} listening on http://{host}:{port}/metrics", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
