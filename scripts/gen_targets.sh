#!/usr/bin/env bash
# 按节点清单生成 Prometheus file_sd 目标文件（targets/*.json）。
# 幂等：每次覆盖生成；生成的 JSON 与清单一一对应。
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p targets

gen_nodes() {
  local out=targets/nodes.json first=1
  echo -n '[' > "$out"
  while IFS='|' read -r role host port env; do
    [[ -z "${role// }" || "$role" == \#* ]] && continue
    [ "$first" = 1 ] || echo -n ',' >> "$out"
    first=0
    printf '{"targets":["%s:%s"],"labels":{"env":"%s","role":"%s"}}' \
      "$host" "$port" "${env:-dev}" "$role" >> "$out"
  done < nodes.list
  echo -n ']' >> "$out"
}

gen_exporters() {
  local out=targets/exporters.json first=1
  echo -n '[' > "$out"
  while IFS='|' read -r kind host port env; do
    [[ -z "${kind// }" || "$kind" == \#* ]] && continue
    [ "$first" = 1 ] || echo -n ',' >> "$out"
    first=0
    printf '{"targets":["%s:%s"],"labels":{"env":"%s","exporter":"%s"}}' \
      "$host" "$port" "${env:-dev}" "$kind" >> "$out"
  done < exporters.list
  echo -n ']' >> "$out"
}

gen_nodes
gen_exporters
echo "generated: $(ls -1 targets/*.json | tr '\n' ' ')"
python3 -c "import json,sys;[json.load(open(p)) for p in sys.argv[1:]];print('json-valid: ok')" targets/*.json
