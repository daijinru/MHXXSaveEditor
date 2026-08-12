#!/usr/bin/env python3
"""
diff.py — 对比两个存档(或同一存档的磁盘/工作副本)的差异(无依赖)。

用法:
  python tools/diff.py <文件A> <文件B> [--limit 50]

输出: 每个差异字节的偏移、旧值、新值。
适用于验证: 在游戏中做某个动作 -> 导出存档 -> 与修改前对比,
这是逆向分析"哪个偏移对应什么"的标准证据链。
"""
import argparse


def main():
    ap = argparse.ArgumentParser(description="对比两个存档文件")
    ap.add_argument("file_a", help="存档 A (基线,如游戏内操作前)")
    ap.add_argument("file_b", help="存档 B (操作后)")
    ap.add_argument("--limit", type=int, default=50, help="最多显示差异数 (默认 50, 0=全部)")
    args = ap.parse_args()

    with open(args.file_a, "rb") as f:
        a = f.read()
    with open(args.file_b, "rb") as f:
        b = f.read()

    if len(a) != len(b):
        print(f"警告: 文件大小不同 {len(a)} vs {len(b)}, 只对比公共部分")

    n = min(len(a), len(b))
    changes = []
    for i in range(n):
        if a[i] != b[i]:
            changes.append((i, a[i], b[i]))

    print(f"A: {args.file_a}  B: {args.file_b}")
    print(f"总差异字节数: {len(changes)}")
    print("-" * 50)
    limit = args.limit if args.limit > 0 else len(changes)
    for off, old, new in changes[:limit]:
        print(f"0x{off:08X}  {old:02X} -> {new:02X}")
    if len(changes) > limit:
        print(f"... 还有 {len(changes) - limit} 处差异")


if __name__ == "__main__":
    main()
