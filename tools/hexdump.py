#!/usr/bin/env python3
"""
hexdump.py — 按偏移查看 MHXX 存档字节(无依赖)。

用法:
  python tools/hexdump.py <存档文件> [--offset 0x24] [--length 64] [--ascii]

示例:
  python tools/hexdump.py save/system --offset 0x280F --length 16
  python tools/hexdump.py save/system --offset 10255 --length 4   (十进制偏移也支持)
"""
import argparse


def main():
    ap = argparse.ArgumentParser(description="查看 MHXX 存档的 hex 字节")
    ap.add_argument("file", help="存档文件路径")
    ap.add_argument("--offset", default="0", help="起始偏移 (支持 0x 前缀或十进制)")
    ap.add_argument("--length", default="64", help="查看长度")
    ap.add_argument("--ascii", action="store_true", help="显示 ASCII 列")
    args = ap.parse_args()

    offset = int(args.offset, 0)
    length = int(args.length, 0)

    with open(args.file, "rb") as f:
        f.seek(offset)
        data = f.read(length)

    print(f"文件: {args.file}")
    print(f"偏移: 0x{offset:X} 长度: {len(data)} 字节")
    print("-" * 60)
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        hex_str = hex_str.ljust(47)
        ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        line = f"0x{offset + i:08X}  {hex_str}"
        if args.ascii:
            line += f"  |{ascii_str}|"
        print(line)


if __name__ == "__main__":
    main()
