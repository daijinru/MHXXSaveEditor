#!/usr/bin/env python3
"""
extract.py — 从 C# 源码提取数据表为 JSON（无第三方依赖）。

功能:
  1. data/offsets.json        <- MHXXSaveEditor/Data/Offsets.cs 的偏移量常量
  2. data/game_constants.json <- MHXXSaveEditor/Data/GameConstants.cs 的 ID->名称映射数组

用法:
  python tools/extract.py [--src-dir MHXXSaveEditor/MHXXSaveEditor/Data] [--out-dir data]

说明:
  提取脚本是"源码唯一权威源"机制的一部分:修改 C# 常量后重新运行本脚本,
  即可重新生成 Web 应用 / AI 使用的 JSON 数据,无需手改 JSON。
"""
import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------- C# 解析工具

def unescape_csharp_string(raw: str) -> str:
    """把 C# 字符串字面量内容(不含引号)转成真实文本。"""
    out = []
    i = 0
    n = len(raw)
    escapes = {
        '"': '"', '\\': '\\', 'n': '\n', 't': '\t', 'r': '\r',
        '0': '\0', 'a': '\a', 'b': '\b', 'f': '\f', 'v': '\v',
    }
    while i < n:
        ch = raw[i]
        if ch == '\\' and i + 1 < n:
            nxt = raw[i + 1]
            if nxt in escapes:
                out.append(escapes[nxt])
                i += 2
                continue
            if nxt == 'u' and i + 5 < n:  # \uXXXX
                try:
                    out.append(chr(int(raw[i + 2:i + 6], 16)))
                    i += 6
                    continue
                except ValueError:
                    pass
            # 未知转义:保留原样(尽量不破坏数据)
            out.append(nxt)
            i += 2
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


ARRAY_RE = re.compile(
    r'public\s+static\s+readonly\s+(string|int)\[\]\s+(\w+)\s*=\s*\{(.*?)\};',
    re.DOTALL,
)


def strip_comments(text: str) -> str:
    """去除 C# 行注释(// ...) 与块注释(/* ... */)。"""
    # 先保护字符串字面量,再删注释
    protected = []
    string_re = re.compile(r'"(?:\\.|[^"\\])*"')

    def _mark(m):
        protected.append(m.group(0))
        return f"\x00{len(protected) - 1}\x00"

    text = string_re.sub(_mark, text)
    text = re.sub(r'//[^\n]*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

    def _restore(m):
        return protected[int(m.group(1))]

    return re.sub(r'\x00(\d+)\x00', _restore, text)


def parse_arrays(cs_text: str) -> dict:
    """解析 C# 源码中的 string[]/int[] 静态数组,返回 {name: [values]}。"""
    clean = strip_comments(cs_text)
    tables = {}
    for typ, name, body in ARRAY_RE.findall(clean):
        if typ == 'string':
            items = re.findall(r'"(?:\\.|[^"\\])*"', body)
            values = [unescape_csharp_string(it[1:-1]) for it in items]
        else:
            values = [int(tok) for tok in re.findall(r'-?\d+', body)]
        tables[name] = values
    return tables


# ---------------------------------------------------------------- 偏移表解析

OFFSET_RE = re.compile(
    r'public\s+const\s+int\s+(\w+)\s*=\s*(0x[0-9A-Fa-f]+|\d+)\s*;'
)


def parse_offsets(cs_text: str) -> list:
    """解析 Offsets.cs,返回 [{name, offset, comment}] 列表(保留行尾注释)。"""
    out = []
    pending_comment = None
    for raw_line in cs_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # 独立注释行(行首为 //):作为下一项的注释
        if line.startswith('//'):
            pending_comment = line.lstrip('/').strip()
            continue
        m = OFFSET_RE.search(line)
        if m:
            name, val = m.group(1), m.group(2)
            offset = int(val, 0)
            comment = pending_comment or ''
            # 行尾注释
            tc = re.search(r'//\s*(.*)$', line)
            if tc:
                comment = (comment + ' ' if comment else '') + tc.group(1).strip()
            out.append({'name': name, 'offset': offset, 'comment': comment})
            pending_comment = None
    return out


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description='从 C# 源码提取数据表为 JSON')
    ap.add_argument('--src-dir', default=os.path.join('MHXXSaveEditor', 'Data'),
                    help='C# Data 源码目录')
    ap.add_argument('--out-dir', default='data', help='JSON 输出目录')
    args = ap.parse_args()

    src = os.path.abspath(args.src_dir)
    out = os.path.abspath(args.out_dir)
    os.makedirs(out, exist_ok=True)

    offsets_path = os.path.join(src, 'Offsets.cs')
    if os.path.exists(offsets_path):
        with open(offsets_path, 'r', encoding='utf-8-sig') as f:
            offsets = parse_offsets(f.read())
        out_path = os.path.join(out, 'offsets.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(offsets, f, ensure_ascii=False, indent=1)
        print(f"[OK] offsets.json: {len(offsets)} 项 -> {out_path}")
    else:
        print(f"[SKIP] 未找到 {offsets_path}", file=sys.stderr)

    const_path = os.path.join(src, 'GameConstants.cs')
    if os.path.exists(const_path):
        with open(const_path, 'r', encoding='utf-8-sig') as f:
            tables = parse_arrays(f.read())
        out_path = os.path.join(out, 'game_constants.json')
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(tables, f, ensure_ascii=False, indent=1)
        total = sum(len(v) for v in tables.values())
        print(f"[OK] game_constants.json: {len(tables)} 张表, {total} 个条目 -> {out_path}")
    else:
        print(f"[SKIP] 未找到 {const_path}", file=sys.stderr)


if __name__ == '__main__':
    main()
