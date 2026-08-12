#!/usr/bin/env python3
"""
MHXX AI Research Studio — 无依赖 Web 应用
==========================================
一个用于"AI 驱动的二进制存档逆向分析"的本地实验平台。

设计原则:
  - 零第三方依赖:仅用 Python 标准库 (http.server / json / base64 / struct)
  - 任何 AI 都可进驻:所有能力以简单 REST API 暴露,配合 SKILL.md 与
    docs/REVERSE_ENGINEERING.md 使用
  - 假设-实验-证据-验证-固化闭环:
      1. AI 读取偏移表/常量表 (GET /api/offsets, /api/constants)
      2. 读取存档字节     (GET /api/save/bytes)
      3. 提出假设并打补丁 (POST /api/save/patch)
      4. 对比/验证        (GET /api/save/diff, hexdump)
      5. 记录实验         (POST /api/experiment)
      6. 固化知识         (POST /api/knowledge)

用法:
  python webapp/server.py [--port 8765] [--data-dir data]

API 速览:
  GET  /api/health                    健康检查
  GET  /api/offsets                   偏移表 (data/offsets.json)
  GET  /api/constants                 常量表列表
  GET  /api/constants/<table>         单张 ID->名称 映射表
  POST /api/save/load  {path}         从磁盘加载存档 (绝对路径)
  POST /api/save/upload {name, data_b64}  上传存档 (base64)
  GET  /api/save/status               当前存档状态
  GET  /api/save/bytes?offset=&length=   读取原始字节 (JSON 数组)
  GET  /api/save/hex?offset=&length=     读取 hex 行 (前端渲染用)
  POST /api/save/patch {offset, bytes|hex}  打补丁 (内存)
  POST /api/save/write {path?}        写回磁盘
  GET  /api/save/download             下载当前内存存档
  GET  /api/save/diff?offset=&length= 磁盘 vs 内存 差异
  GET  /api/experiments               实验记录列表
  POST /api/experiment {title,hypothesis,method,evidence,conclusion}
  GET  /api/knowledge/<name>          读取知识库 markdown
  POST /api/knowledge/<name> {append} 追加知识
"""
import argparse
import base64
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

SAVE_FILE_SIZE = 4726152  # MHXX 存档固定大小
VERSION = "0.1.0"


# ---------------------------------------------------------------- 状态

class AppState:
    def __init__(self, data_dir):
        self.data_dir = os.path.abspath(data_dir)
        self.knowledge_dir = os.path.join(self.data_dir, "knowledge")
        self.experiment_dir = os.path.abspath(os.path.join(self.data_dir, "..", "experiments"))
        self.lock = threading.Lock()
        self.save_path = None      # 磁盘上的原始存档路径
        self.save_bytes = None     # 当前工作副本 (bytearray)
        self.disk_bytes = None     # 上次加载时的磁盘快照 (用于 diff)
        self.loaded = False

        os.makedirs(self.knowledge_dir, exist_ok=True)
        os.makedirs(self.experiment_dir, exist_ok=True)
        # 若尚未生成知识库种子文件,则从 offsets.json 生成
        self._seed_knowledge()

    def _seed_knowledge(self):
        seed = os.path.join(self.knowledge_dir, "known-offsets.md")
        if os.path.exists(seed):
            return
        off_path = os.path.join(self.data_dir, "offsets.json")
        if os.path.exists(off_path):
            with open(off_path, encoding="utf-8") as f:
                offsets = json.load(f)
            lines = [
                "# 已知偏移表 (known-offsets)",
                "",
                "> 来源:原 C# 编辑器 `Offsets.cs`,已由 `tools/extract.py` 提取。",
                "> 格式: `名称 | 偏移(hex) | 大小/说明`。此文件是 AI 逆向研究的知识固话区,",
                "> 新验证的偏移请追加到对应小节,并标记验证人/日期。",
                "",
                "## 已知偏移",
                "",
                "| 名称 | 偏移 | 说明 |",
                "| --- | --- | --- |",
            ]
            for o in offsets:
                lines.append(f"| {o['name']} | 0x{o['offset']:X} | {o['comment']} |")
            with open(seed, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")


STATE = None


# ---------------------------------------------------------------- 工具

def load_json_file(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_experiments():
    """扫描 experiments/ 目录下的 md 文件,提取标题。"""
    out = []
    d = STATE.experiment_dir
    if not os.path.isdir(d):
        return out
    for name in sorted(os.listdir(d)):
        if name.endswith(".md"):
            p = os.path.join(d, name)
            title = name[:-3]
            try:
                with open(p, encoding="utf-8") as f:
                    first = f.readline().strip()
                if first.startswith("#"):
                    title = first.lstrip("# ").strip()
            except OSError:
                pass
            mtime = os.path.getmtime(p)
            out.append({
                "file": name,
                "title": title,
                "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime)),
            })
    return out


def append_knowledge(name, text):
    """向 data/knowledge/<name>.md 追加内容(带时间戳)。"""
    safe = re.sub(r"[^\w\-.]", "_", name)
    path = os.path.join(STATE.knowledge_dir, safe + ".md")
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    block = f"\n\n<!-- appended {stamp} -->\n{text.rstrip()}\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(block)
    return path


# ---------------------------------------------------------------- HTTP 处理

class Handler(BaseHTTPRequestHandler):
    server_version = f"MHXXAIStudio/{VERSION}"

    # -- 基础工具 --
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text(self, text, code=200, ctype="text/plain; charset=utf-8"):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, ctype):
        if not os.path.exists(path):
            self._json({"error": f"not found: {path}"}, 404)
            return
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self, max_bytes=8 * 1024 * 1024):
        length = int(self.headers.get("Content-Length", 0))
        if length > max_bytes:
            raise ValueError("body too large")
        return self.rfile.read(length)

    def _read_json(self):
        raw = self._read_body()
        return json.loads(raw.decode("utf-8")) if raw else {}

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    # -- 静态文件 --
    def _serve_static(self, path):
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        rel = path.lstrip("/")
        if not rel:
            rel = "index.html"
        full = os.path.normpath(os.path.join(root, rel))
        if not full.startswith(root):
            self._json({"error": "forbidden"}, 403)
            return
        if os.path.isdir(full):
            full = os.path.join(full, "index.html")
        ext_map = {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        ctype = ext_map.get(os.path.splitext(full)[1], "application/octet-stream")
        self._file(full, ctype)

    # -- 路由 --
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        q = parse_qs(parsed.query)

        try:
            if path == "/api/health":
                self._json({
                    "ok": True,
                    "version": VERSION,
                    "save_loaded": STATE.loaded,
                })
            elif path == "/api/offsets":
                self._json(load_json_file(os.path.join(STATE.data_dir, "offsets.json"), []))
            elif path == "/api/constants":
                gc = load_json_file(os.path.join(STATE.data_dir, "game_constants.json"), {})
                self._json([{"name": k, "count": len(v)} for k, v in gc.items()])
            elif path.startswith("/api/constants/"):
                table = path[len("/api/constants/"):]
                gc = load_json_file(os.path.join(STATE.data_dir, "game_constants.json"), {})
                if table not in gc:
                    self._json({"error": f"unknown table: {table}"}, 404)
                else:
                    self._json({"name": table, "values": gc[table]})
            elif path == "/api/save/status":
                self._json({
                    "loaded": STATE.loaded,
                    "path": STATE.save_path,
                    "size": len(STATE.save_bytes) if STATE.save_bytes else 0,
                })
            elif path == "/api/save/bytes":
                self._handle_bytes(q)
            elif path == "/api/save/hex":
                self._handle_hex(q)
            elif path == "/api/save/diff":
                self._handle_diff(q)
            elif path == "/api/save/download":
                if not STATE.loaded:
                    self._json({"error": "no save loaded"}, 400)
                    return
                body = bytes(STATE.save_bytes)
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition",
                                 f'attachment; filename="{os.path.basename(STATE.save_path or "save.bin")}"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif path == "/api/experiments":
                self._json({"experiments": list_experiments()})
            elif path.startswith("/api/experiments/"):
                name = path[len("/api/experiments/"):]
                safe = re.sub(r"[^\w\-.]", "_", name)
                full = os.path.join(STATE.experiment_dir, safe)
                self._text(open(full, encoding="utf-8").read() if os.path.exists(full) else "# 不存在\n")
            elif path.startswith("/api/knowledge/"):
                name = path[len("/api/knowledge/"):]
                safe = re.sub(r"[^\w\-.]", "_", name)
                full = os.path.join(STATE.knowledge_dir, safe + ".md")
                if not os.path.exists(full):
                    self._json({"error": f"knowledge file not found: {safe}"}, 404)
                    return
                self._file(full, "text/markdown; charset=utf-8")
            else:
                self._serve_static(path)
        except ValueError as e:
            self._json({"error": str(e)}, 400)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            self._json({"error": f"internal error: {e}"}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/save/load":
                data = self._read_json()
                p = data.get("path")
                if not p:
                    self._json({"error": "missing 'path'"}, 400)
                    return
                self._load_save(p)
            elif path == "/api/save/upload":
                data = self._read_json()
                b64 = data.get("data_b64", "")
                raw = base64.b64decode(b64)
                self._set_save(raw, data.get("name", "upload.bin"))
            elif path == "/api/save/patch":
                data = self._read_json()
                self._apply_patch(data)
            elif path == "/api/save/write":
                data = self._read_json()
                self._write_save(data.get("path"))
            elif path == "/api/experiment":
                data = self._read_json()
                self._create_experiment(data)
            elif path.startswith("/api/knowledge/"):
                name = path[len("/api/knowledge/"):]
                data = self._read_json()
                append = data.get("append", "")
                if not append:
                    self._json({"error": "missing 'append'"}, 400)
                    return
                p = append_knowledge(name, append)
                self._json({"ok": True, "file": os.path.basename(p)})
            else:
                self._json({"error": "not found"}, 404)
        except ValueError as e:
            self._json({"error": str(e)}, 400)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            self._json({"error": f"internal error: {e}"}, 500)

    # -- 业务处理 --
    def _load_save(self, path):
        path = os.path.abspath(path)
        if not os.path.exists(path):
            self._json({"error": f"file not found: {path}"}, 404)
            return
        with open(path, "rb") as f:
            raw = f.read()
        self._set_save(raw, path)

    def _set_save(self, raw, path):
        if len(raw) != SAVE_FILE_SIZE:
            self._json({
                "error": f"不是 MHXX 存档:期望 {SAVE_FILE_SIZE} 字节,实际 {len(raw)} 字节",
            }, 400)
            return
        with STATE.lock:
            STATE.save_bytes = bytearray(raw)
            STATE.disk_bytes = bytearray(raw)
            STATE.save_path = path
            STATE.loaded = True
        self._json({
            "ok": True,
            "path": path,
            "size": len(raw),
            "slots": [i + 1 for i in range(3) if raw[4 + i] == 1],
        })

    def _require_save(self):
        if not STATE.loaded or STATE.save_bytes is None:
            raise ValueError("尚未加载存档 (POST /api/save/load 或 /api/save/upload)")

    @staticmethod
    def _to_int(v):
        """接受 int 或 str(支持 0x 前缀) 的值。"""
        if isinstance(v, bool):
            return int(v)
        if isinstance(v, int):
            return v
        return int(str(v), 0)

    def _parse_range(self, q, default_length=16, max_length=1 << 20):
        offset = self._to_int(q.get("offset", ["0"])[0])
        length = self._to_int(q.get("length", [str(default_length)])[0])
        if offset < 0 or length < 0:
            raise ValueError("offset/length 不能为负")
        if length > max_length:
            raise ValueError(f"length 过大 (max {max_length})")
        return offset, length

    def _handle_bytes(self, q):
        self._require_save()
        offset, length = self._parse_range(q)
        data = STATE.save_bytes
        end = min(offset + length, len(data))
        self._json({
            "offset": offset,
            "length": max(0, end - offset),
            "bytes": list(data[offset:end]),
        })

    def _handle_hex(self, q):
        self._require_save()
        offset, length = self._parse_range(q)
        data = STATE.save_bytes
        end = min(offset + length, len(data))
        rows = []
        for addr in range(offset, end, 16):
            chunk = data[addr:addr + 16]
            hex_str = " ".join(f"{b:02X}" for b in chunk)
            ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            rows.append({"addr": addr, "hex": hex_str, "ascii": ascii_str})
        self._json({"offset": offset, "length": end - offset, "rows": rows})

    def _apply_patch(self, data):
        self._require_save()
        offset = self._to_int(data.get("offset", 0))
        if "hex" in data:
            hex_str = re.sub(r"[^0-9a-fA-F]", "", data["hex"])
            if len(hex_str) % 2:
                raise ValueError("hex 串长度必须为偶数")
            patch = bytes.fromhex(hex_str)
        elif "bytes" in data:
            patch = bytes(int(b) & 0xFF for b in data["bytes"])
        else:
            raise ValueError("需要 'bytes' 数组或 'hex' 字符串")
        if offset < 0 or offset + len(patch) > len(STATE.save_bytes):
            raise ValueError(f"补丁越界: offset={offset} len={len(patch)} file={len(STATE.save_bytes)}")
        old = bytes(STATE.save_bytes[offset:offset + len(patch)])
        with STATE.lock:
            STATE.save_bytes[offset:offset + len(patch)] = patch
        self._json({
            "ok": True,
            "offset": offset,
            "length": len(patch),
            "old_hex": old.hex(),
            "new_hex": patch.hex(),
        })

    def _write_save(self, target=None):
        self._require_save()
        path = os.path.abspath(target) if target else STATE.save_path
        if not path:
            raise ValueError("未指定保存路径")
        with STATE.lock:
            with open(path, "wb") as f:
                f.write(bytes(STATE.save_bytes))
            STATE.disk_bytes = bytearray(STATE.save_bytes)
            STATE.save_path = path
        self._json({"ok": True, "path": path, "size": len(STATE.save_bytes)})

    def _handle_diff(self, q):
        self._require_save()
        offset, length = self._parse_range(q)
        mem = STATE.save_bytes
        disk = STATE.disk_bytes or mem
        end = min(offset + length, len(mem))
        changes = []
        for i in range(offset, end):
            if mem[i] != disk[i]:
                changes.append({
                    "offset": i,
                    "old": disk[i],
                    "new": mem[i],
                })
        self._json({"offset": offset, "length": end - offset, "changes": changes, "count": len(changes)})

    def _create_experiment(self, data):
        title = data.get("title", "untitled").strip()
        hypothesis = data.get("hypothesis", "")
        method = data.get("method", "")
        evidence = data.get("evidence", "")
        conclusion = data.get("conclusion", "")
        if not title:
            raise ValueError("missing 'title'")
        safe = re.sub(r"[^\w\u4e00-\u9fff\-]", "_", title)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        fname = f"{stamp}_{safe[:40]}.md"
        path = os.path.join(STATE.experiment_dir, fname)
        with STATE.lock:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
                f.write(f"- 创建时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"- 存档: {STATE.save_path or '(未加载)'}\n\n")
                f.write("## 假设 (Hypothesis)\n\n" + (hypothesis or "_待填写_") + "\n\n")
                f.write("## 实验方法 (Method)\n\n" + (method or "_待填写_") + "\n\n")
                f.write("## 证据 (Evidence)\n\n" + (evidence or "_待填写_") + "\n\n")
                f.write("## 结论 (Conclusion)\n\n" + (conclusion or "_待填写_") + "\n\n")
        self._json({"ok": True, "file": fname, "path": path})


def main():
    ap = argparse.ArgumentParser(description="MHXX AI 逆向研究平台")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--data-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    global STATE
    STATE = AppState(args.data_dir)

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("=" * 60)
    print("  MHXX AI Research Studio  (无依赖 Web 应用)")
    print(f"  地址: http://{args.host}:{args.port}")
    print("  数据目录:", STATE.data_dir)
    print("  实验目录:", STATE.experiment_dir)
    print("=" * 60)
    print("  加载存档: POST /api/save/load {\"path\": \"C:/.../system\"}")
    print("  接口文档: 见 docs/API.md 与 SKILL.md")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[退出]")
        server.server_close()


if __name__ == "__main__":
    main()
