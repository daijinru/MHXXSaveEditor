#!/usr/bin/env python3
"""
patch.py — 对存档应用补丁 / 导出补丁(无依赖)。

用法:
  应用补丁:
    python tools/patch.py apply <存档> <偏移> <hex字节> [--out 输出路径]
      示例: python tools/patch.py apply save/system 0x24 "00 00 00 00"
      示例: python tools/patch.py apply save/system 0x280F "E7 03"  (金钱 999)

  导出补丁(与基线对比,生成可复现的修改清单):
    python tools/patch.py export <基线存档> <修改后存档> [--out patch.json]

设计说明:
  补丁是"假设->实验->验证"闭环的产物,JSON 补丁清单可提交进仓库,
  供其他 AI/人复现同一实验。
"""
import argparse
import json
import re
import sys


def parse_hex(s):
    s = re.sub(r"[^0-9a-fA-F]", "", s)
    if len(s) % 2:
        sys.exit("hex 字节串长度必须为偶数")
    return bytes.fromhex(s)


def cmd_apply(args):
    data = bytearray(open(args.file, "rb").read())
    offset = int(args.offset, 0)
    patch = parse_hex(args.hex)
    if offset < 0 or offset + len(patch) > len(data):
        sys.exit(f"补丁越界: offset={offset} len={len(patch)} file={len(data)}")
    old = bytes(data[offset:offset + len(patch)])
    data[offset:offset + len(patch)] = patch
    out = args.out or args.file
    with open(out, "wb") as f:
        f.write(bytes(data))
    print(f"[应用] 0x{offset:X}: {old.hex().upper()} -> {patch.hex().upper()}")
    print(f"[保存] {out} ({len(data)} 字节)")


def cmd_export(args):
    with open(args.base, "rb") as f:
        base = f.read()
    with open(args.modified, "rb") as f:
        mod = f.read()
    patches = []
    n = min(len(base), len(mod))
    i = 0
    while i < n:
        if base[i] != mod[i]:
            j = i
            while j < n and base[j] != mod[j]:
                j += 1
            patches.append({
                "offset": i,
                "old_hex": base[i:j].hex(),
                "new_hex": mod[i:j].hex(),
            })
            i = j
        else:
            i += 1
    payload = {
        "base_file": args.base,
        "modified_file": args.modified,
        "patch_count": len(patches),
        "patches": patches,
    }
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[导出] {len(patches)} 个补丁 -> {args.out}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description="MHXX 存档补丁工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_apply = sub.add_parser("apply", help="应用补丁")
    p_apply.add_argument("file", help="存档文件")
    p_apply.add_argument("offset", help="偏移 (0x 或十进制)")
    p_apply.add_argument("hex", help="hex 字节, 如 '00 FF 10'")
    p_apply.add_argument("--out", help="输出路径 (默认覆盖原文件)")
    p_apply.set_defaults(fn=cmd_apply)

    p_export = sub.add_parser("export", help="对比两个文件导出补丁清单")
    p_export.add_argument("base", help="基线存档")
    p_export.add_argument("modified", help="修改后存档")
    p_export.add_argument("--out", help="输出 JSON 路径")
    p_export.set_defaults(fn=cmd_export)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
