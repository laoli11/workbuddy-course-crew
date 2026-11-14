# -*- coding: utf-8 -*-
"""
课程制片团 · 术语批量修复

按 terminology.json 的 canonical 词表，把文稿里漂移的大小写/错写批量修正：
  - deepseek → DeepSeek、kimi → Kimi、claude → Claude、markdown → Markdown
  - space bunning → Space Bunning、open cloud → Open Cloud、IMA → ima
  - Skill Hub → skill hub、workbody → WorkBuddy
  - workbuddy → WorkBuddy（保留 .workbuddy 目录名不动）

覆盖 7 门课的 口播稿.md / TTS朗读稿.txt / 分镜脚本.md。
幂等：正确写法不会命中规则，可重复运行。
先 --dry 看报告，确认无误再正式写。

用法： python tools/fix_terminology.py [--dry]
"""
import glob
import os
import re
import sys

ROOT = r"E:/WorkBuddy课程/01_基础课"

FIXES = [
    (re.compile(r"(?<!\.)(?<![A-Za-z])workbuddy(?![A-Za-z])(?!\.cn|\.com)"), "WorkBuddy"),
    (re.compile(r"(?<![A-Za-z.])workbody(?![A-Za-z])"), "WorkBuddy"),
    (re.compile(r"(?<![A-Za-z])deepseek(?![A-Za-z])"), "DeepSeek"),
    (re.compile(r"(?<![A-Za-z])kimi(?![A-Za-z])"), "Kimi"),
    (re.compile(r"(?<![A-Za-z])claude(?![A-Za-z])"), "Claude"),
    (re.compile(r"(?<![A-Za-z])markdown(?![A-Za-z])"), "Markdown"),
    (re.compile(r"(?<![A-Za-z])space bunning(?![A-Za-z])"), "Space Bunning"),
    (re.compile(r"(?<![A-Za-z])open cloud(?![A-Za-z])"), "Open Cloud"),
    (re.compile(r"(?<![A-Za-z])Skill Hub(?![A-Za-z])"), "skill hub"),
    (re.compile(r"(?<![A-Za-z])IMA(?![A-Za-z])"), "ima"),
]


def files():
    out = []
    for d in sorted(glob.glob(os.path.join(ROOT, "第*课_*", "01_逐字稿与脚本"))):
        n = os.path.basename(os.path.dirname(d))
        for f in sorted(glob.glob(os.path.join(d, "*"))):
            if f.endswith(("口播稿.md", "TTS朗读稿.txt", "分镜脚本.md")):
                out.append((n, f))
    return out


def main():
    dry = "--dry" in sys.argv
    total, changed_files = 0, 0
    for lesson, path in files():
        text = open(path, encoding="utf-8").read()
        new, detail = text, []
        for rx, rep in FIXES:
            for m in rx.finditer(new):
                seg = new[max(0, m.start() - 8):m.end() + 8].replace("\n", " ")
                detail.append(f"{m.group(0)} → {rep}  〔…{seg}…〕")
            new = rx.sub(rep, new)
        if detail:
            total += len(detail)
            changed_files += 1
            print(f"  {lesson} {os.path.basename(path)}：{len(detail)} 处")
            if dry:
                for d in detail:
                    print("      ", d)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new)
    print(f"\n共修 {total} 处 / {changed_files} 个文件" +
          ("（仅试运行）" if dry else "，已写入"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
