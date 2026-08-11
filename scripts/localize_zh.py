#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
localize_zh.py — StrykerOSS 汉化资源生成器

从英文默认资源 (res/values) 读取 strings*.xml，依据 scripts/zh_dict.py 中的
翻译词典生成简体中文资源目录 res/values-zh-rCN/。

特性:
  * 只翻译 <string> 条目，保留 formatted / translatable 属性
  * translatable="false" 的条目原样保留（品牌名、URL 等）
  * 词典未覆盖的 key 回退为英文原文并打印警告（--strict 时直接失败）
  * 原文中的占位符 (%1$s, %d, %s, \n 等) 由词典负责保留；本脚本不擅自改动值

用法:
  python3 scripts/localize_zh.py \
      --src app/src/main/res/values \
      --out app/src/main/res/values-zh-rCN \
      [--dict scripts/zh_dict.py] [--strict]
"""
import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

DICT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zh_dict.py")


def load_dict(path):
    """加载翻译词典模块并返回 (TRANSLATIONS dict, SKIP set)。"""
    ns = {}
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    exec(compile(code, path, "exec"), ns)
    translations = ns.get("TRANSLATIONS", {})
    if not isinstance(translations, dict):
        raise SystemExit(f"[!] {path} 中未找到 TRANSLATIONS 字典")
    skip = ns.get("SKIP", set())
    return translations, skip


def translate_file(src_path, out_path, translations, skip, strict):
    """翻译单个 strings XML 文件。返回 (translated, fallback) 计数。"""
    tree = ET.parse(src_path)
    root = tree.getroot()
    if root.tag != "resources":
        raise SystemExit(f"[!] 不是 resources 根节点: {src_path}")

    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<resources>"]
    translated = fallback = 0

    for child in root:
        if child.tag != "string":
            # 非 <string> 元素（如注释、plurals、string-array）原样序列化
            lines.append(ET.tostring(child, encoding="unicode"))
            continue

        name = child.get("name", "")
        text = child.text or ""
        attrs = dict(child.attrib)

        if attrs.get("translatable", "").lower() == "false" or name in skip:
            # 品牌名 / URL / 法律文本等条目，原样保留
            lines.append(serialize_string(name, text, attrs))
            continue

        if name in translations:
            new_text = translations[name]
            translated += 1
        else:
            new_text = text
            fallback += 1
            print(f"[warn] 未翻译: {name} -> 保留原文: {text[:60]!r}")
            if strict:
                raise SystemExit(f"[!] strict 模式: 缺少翻译 {name}")

        lines.append(serialize_string(name, new_text, attrs))

    lines.append("</resources>")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return translated, fallback


def serialize_string(name, text, attrs):
    """序列化单个 <string> 元素，保留原属性，并做 Android 资源转义。"""
    attr_str = "".join(f' {k}="{escape(v)}"' for k, v in attrs.items())
    body = escape(text)                      # & < >
    body = body.replace("'", "\\'")          # 单引号必须转义 (aapt 规则)
    body = body.replace('"', '\\"')          # 双引号一并转义，避免歧义
    # 修正非法的反斜杠转义（如 \a \b \f \v）：后跟非合法转义符时加倍
    # 合法: \n \t \' \" \\ \uXXXX
    body = re.sub(r'\\(?![nt\'"u\\])', r'\\\\', body)
    return f"    <string{attr_str}>{body}</string>"


def main():
    ap = argparse.ArgumentParser(description="StrykerOSS 汉化资源生成器")
    ap.add_argument("--src", action="append", required=True,
                    help="英文默认资源目录（可多次传入，处理多模块）")
    ap.add_argument("--out", action="append", required=True,
                    help="输出简体中文资源目录（与 --src 一一对应）")
    ap.add_argument("--dict", action="append", default=None,
                    help="翻译词典 .py 路径（与 --src 一一对应，缺省用默认词典）")
    ap.add_argument("--strict", action="store_true", help="词典缺失条目时报错退出")
    args = ap.parse_args()

    if args.dict is None:
        args.dict = [DICT_PATH]
    if len(args.src) != len(args.out):
        raise SystemExit("[!] --src 与 --out 数量必须一致")
    if len(args.dict) == 1 and len(args.src) > 1:
        args.dict = args.dict * len(args.src)
    if len(args.dict) != len(args.src):
        raise SystemExit("[!] --dict 数量必须与 --src 一致（或只传一个用于所有模块）")

    total_t = total_f = 0
    for src_dir, out_dir, dict_path in zip(args.src, args.out, args.dict):
        translations, skip = load_dict(dict_path)
        print(f"[*] 词典加载完成: {len(translations)} 条, 跳过 {len(skip)} 条  -> {src_dir}")
        for fname in sorted(os.listdir(src_dir)):
            if not (fname.startswith("strings") and fname.endswith(".xml")):
                continue
            src_path = os.path.join(src_dir, fname)
            out_path = os.path.join(out_dir, fname)
            t, f = translate_file(src_path, out_path, translations, skip, args.strict)
            total_t += t
            total_f += f
            print(f"[*] {src_dir}/{fname}: 翻译 {t} 条, 回退 {f} 条")

    print(f"[*] 完成: 共翻译 {total_t} 条, 回退 {total_f} 条")
    if total_f:
        print(f"[!] 有 {total_f} 条未翻译（保留英文）。可补充 {args.dict} 后重跑。")


if __name__ == "__main__":
    main()
