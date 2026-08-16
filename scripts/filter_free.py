# -*- coding: utf-8 -*-
"""严格过滤脚本：删除 APILayer 商业推广区，仅保留 Auth=No（免费、无需认证）的 API 条目，
重建 Index 目录，空分类整块删除。

用法: python scripts/filter_free.py README.md
"""

import re
import sys

# 分类标题前的内容（商业推广区）截止于此标题行
KEEP_FROM_HEADER = "## Learn more about Public APIs"
INDEX_HEADER = "## Index"

# Auth 列允许保留的值（严格过滤：无需认证 = 免费公开访问）
FREE_AUTH = {"No"}

# 描述中出现这些词视为收费/闭源暗示，一并剔除（严格模式）
PAID_HINTS = re.compile(
    r"\b(paid|premium|pricing|paywall|subscription|commercial\s+license|pro\s+plan|"
    r"freemium|trial|credit[s]?\s+required|billing)\b",
    re.IGNORECASE,
)

COLUMN_AUTH = 2  # API | Description | Auth | HTTPS | CORS


def github_slug(title: str) -> str:
    """GitHub 风格的标题锚点（小写、删除标点、空格转连字符，连续空格不合并）。"""
    cleaned = re.sub(r"[^a-z0-9\- ]", "", title.lower())
    return cleaned.replace(" ", "-")


def is_table_header(line: str) -> bool:
    return line.startswith("|") and line.split("|")[1].strip() == "API"


def is_table_separator(line: str) -> bool:
    return line.startswith("|---") or line.startswith("|:---")


def segments_of(line: str):
    """去掉首尾管道符后按列切分并 trim。"""
    return [s.strip() for s in line.split("|")[1:-1]]


def keep_entry_line(line: str) -> bool:
    segs = segments_of(line)
    if len(segs) < 3:
        return False
    auth = segs[COLUMN_AUTH].strip("`")
    if auth not in FREE_AUTH:
        return False
    desc = segs[1]
    return not PAID_HINTS.search(desc)


def split_blocks(lines):
    """把分类区按 '### 标题' 切块，返回 [(title_line, [body_lines]), ...]"""
    blocks = []
    cur_title, cur_body = None, []
    for ln in lines:
        if ln.startswith("### "):
            if cur_title is not None:
                blocks.append((cur_title, cur_body))
            cur_title, cur_body = ln, []
        else:
            cur_body.append(ln)
    if cur_title is not None:
        blocks.append((cur_title, cur_body))
    return blocks


def main(filename: str) -> None:
    with open(filename, encoding="utf-8") as fh:
        lines = list(fh.read().split("\n"))

    # 1) 找到保留起点（商业推广区结束）与 Index 标题位置
    keep_from = next(i for i, ln in enumerate(lines) if ln.strip() == KEEP_FROM_HEADER)
    idx_header = next(i for i, ln in enumerate(lines) if ln.strip() == INDEX_HEADER)

    # 2) 保留段 = Learn more 块（KEEP_FROM_HEADER 到 Index 之前）
    head_part = lines[keep_from:idx_header]

    # 3) 分类区 = Index 之后全部内容，切块过滤
    category_zone = lines[idx_header + 1:]
    first_block = next(i for i, ln in enumerate(category_zone) if ln.startswith("### "))
    blocks = split_blocks(category_zone[first_block:])

    kept_blocks = []  # (title, body, kept_entry_count)
    for title, body in blocks:
        kept_body = []
        kept_count = 0
        for ln in body:
            if is_table_header(ln) or is_table_separator(ln):
                kept_body.append(ln)
                continue
            if ln.startswith("|") and keep_entry_line(ln):
                kept_body.append(ln)
                kept_count += 1
                continue
            if not ln.startswith("|"):
                kept_body.append(ln)
        if kept_count > 0:
            kept_blocks.append((title, kept_body, kept_count))

    # 4) 重建 Index 目录
    toc_lines = ["## Index", ""]
    for title, _, _ in kept_blocks:
        name = title[len("### "):].strip()
        toc_lines.append(f"* [{name}](#{github_slug(name)})")
    toc_lines.append("")

    # 5) 组装新文件
    out = head_part + toc_lines
    for title, body, _ in kept_blocks:
        out.append(title)
        out.extend(body)
        out.append("")

    with open(filename, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out).rstrip("\n") + "\n")

    total = sum(c for _, _, c in kept_blocks)
    print(f"分类数: {len(kept_blocks)}")
    print(f"保留条目数: {total}")
    print(f"删除分类数: {len(blocks) - len(kept_blocks)}")
    removed = sum(
        1 for _, b in blocks
        for ln in b
        if ln.startswith("|") and not is_table_header(ln) and not is_table_separator(ln)
    ) - total
    print(f"删除条目数: {removed}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/filter_free.py README.md")
        sys.exit(1)
    main(sys.argv[1])
