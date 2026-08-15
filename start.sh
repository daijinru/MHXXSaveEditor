#!/usr/bin/env bash
# MHXX Save Editor - AI 逆向研究平台 启动脚本
# 适用于 Git Bash (Windows) / Linux / macOS
set -uo pipefail
cd "$(dirname "$0")"

PORT="${1:-8765}"
URL="http://127.0.0.1:${PORT}"
LOG=/tmp/mhxx_server.log

echo "============================================"
echo "  MHXX Save Editor - AI 逆向研究平台"
echo "  ${URL}"
echo "============================================"
echo

# ---------- 1. 找 Python ----------
PYTHON=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then PYTHON="$cand"; break; fi
done
if [[ -z "$PYTHON" ]] && [[ -x "$HOME/.workbuddy/binaries/python/versions/3.13.12/python.exe" ]]; then
    PYTHON="$HOME/.workbuddy/binaries/python/versions/3.13.12/python.exe"
fi
if [[ -z "$PYTHON" ]]; then
    echo "[错误] 未找到 Python，请安装 Python 3.10+ 或配置 PATH。" >&2
    exit 1
fi
echo "[Python] $PYTHON"

open_browser() {
    if command -v cmd >/dev/null 2>&1; then
        cmd //c start "" "${URL}" >/dev/null 2>&1
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "${URL}" >/dev/null 2>&1
    elif command -v open >/dev/null 2>&1; then
        open "${URL}" >/dev/null 2>&1
    fi
}

# ---------- 2. 平台是否已在运行 ----------
if curl -s --max-time 2 "${URL}/api/health" >/dev/null 2>&1; then
    echo "[提示] 平台已在运行，直接打开浏览器..."
    open_browser
    exit 0
fi

# ---------- 3. 数据文件缺失时自动提取 ----------
if [[ ! -f data/offsets.json ]]; then
    echo "[初始化] 数据文件缺失，正在从 C# 源码提取..."
    "$PYTHON" tools/extract.py || {
        echo "[错误] 数据提取失败，请检查 MHXXSaveEditor/Data/ 源码是否存在。" >&2
        exit 1
    }
fi

# ---------- 4. 启动服务 ----------
echo "[启动] 研究平台服务 (Ctrl+C 停止)..."
"$PYTHON" webapp/server.py --port "${PORT}" >"${LOG}" 2>&1 &
SERVER_PID=$!
trap 'kill "${SERVER_PID}" 2>/dev/null' EXIT INT TERM

sleep 2
if curl -s --max-time 2 "${URL}/api/health" >/dev/null 2>&1; then
    echo "[就绪] 平台已启动: ${URL}"
    open_browser
    echo "[日志] ${LOG}"
    echo "[提示] 按 Ctrl+C 停止服务。"
else
    echo "[警告] 健康检查未通过，查看日志:" >&2
    tail -n 20 "${LOG}" >&2
fi

wait "${SERVER_PID}"
