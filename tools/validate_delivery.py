# -*- coding: utf-8 -*-
"""
课程制片团 · 交付机器闸（cross-artifact gate）

一次校验四份产物之间的一致性：
  分镜脚本 <-> B roll 素材文件 <-> 口播稿 <-> TTS 朗读稿

检查项：
  1. 7 门课三件套 + 分镜齐全
  2. 分镜含 A roll / B roll 双轨列、段间交接表、音效 cue、动画段清单
  3. 分镜里引用的每个 broll_*.svg 都能在全课素材里找到（允许跨课复用）
  4. 所有 SVG 通过 XML 解析 + 文字边界校验
  5. 口播稿通过 teaching-spec：开场钩子 / 小任务 / 记住一句话 / 无禁用词
  6. TTS 稿与口播稿逐句数量一致、无 markdown 残留、无异常空行

用法： python tools/validate_delivery.py
退出码 0 = 全通过，1 = 有阻断项
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_broll import validate as validate_svg  # noqa: E402

ROOT = r"E:/WorkBuddy课程/01_基础课"
LESSONS = ["01", "02", "03", "04", "05", "06", "07"]
BANNED = ["很简单", "不用说", "大家都知道", "随便", "想跳过也行"]


def lesson_dir(n):
    ds = glob.glob(os.path.join(ROOT, f"第{n}课_*"))
    return ds[0] if ds else None


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def main():
    errors, warns = [], []
    all_broll = set()
    storyboards = {}

    # 收集全季 B roll 文件
    for p in glob.glob(os.path.join(ROOT, "第*课_*", "03_素材", "broll", "*.svg")):
        all_broll.add(os.path.basename(p))

    for n in LESSONS:
        d = lesson_dir(n)
        if not d:
            errors.append(f"第{n}课 目录缺失")
            continue
        sd = os.path.join(d, "01_逐字稿与脚本")
        for kind in ("口播稿", "TTS朗读稿", "分镜脚本"):
            ext = "txt" if kind == "TTS朗读稿" else "md"
            if not os.path.exists(os.path.join(sd, f"第{n}课_{kind}.{ext}")):
                errors.append(f"第{n}课 缺 {kind}")

        sb_path = os.path.join(sd, f"第{n}课_分镜脚本.md")
        md_path = os.path.join(sd, f"第{n}课_口播稿.md")
        tts_path = os.path.join(sd, f"第{n}课_TTS朗读稿.txt")
        if not (os.path.exists(sb_path) and os.path.exists(md_path)
                and os.path.exists(tts_path)):
            continue

        sb, md, tts = read(sb_path), read(md_path), read(tts_path)
        storyboards[n] = sb

        # 2) 分镜结构
        for label, needle in (("A/B 双轨表头", "A roll"),
                              ("B roll 列", "B roll"),
                              ("段间交接表", "交接表"),
                              ("音效 cue", "音效 cue"),
                              ("动画段清单", "动画段清单")):
            if needle not in sb:
                errors.append(f"第{n}课 分镜缺「{label}」")
        if "占位卡" not in sb:
            warns.append(f"第{n}课 分镜未写明禁占位卡铁律")

        # 3) B roll 引用闭合
        refs = set(re.findall(r"broll_[^\s`、,，)）|]+?\.svg", sb))
        missing = sorted(r for r in refs if r not in all_broll)
        if missing:
            errors.append(f"第{n}课 分镜引用了不存在的素材：{missing}")

        # 5) teaching-spec
        if not any(k in md for k in ("这节课解决什么问题", "我们解决一个问题", "这节课学完")):
            errors.append(f"第{n}课 口播稿缺开场钩子")
        if "最后给你留一个小任务。" not in md:
            errors.append(f"第{n}课 口播稿缺课后小任务")
        if "记住一句话" not in md:
            errors.append(f"第{n}课 口播稿缺「记住一句话」")
        hit = [w for w in BANNED if w in md]
        if hit:
            errors.append(f"第{n}课 口播稿残留禁用词：{hit}")

        # 6) TTS 一致性
        src_lines = [l.strip() for l in md.split("\n")
                     if l.strip() and not l.strip().startswith(("#", ">", "|"))]
        tts_lines = [l for l in tts.split("\n") if l.strip()]
        if len(src_lines) != len(tts_lines):
            errors.append(f"第{n}课 TTS 句数 {len(tts_lines)} ≠ 口播稿 {len(src_lines)}")
        bad = [l for l in tts_lines if re.search(r"[#*`>|]", l)]
        if bad:
            errors.append(f"第{n}课 TTS 残留 markdown：{bad[:2]}")
        if "\n\n\n" in tts:
            warns.append(f"第{n}课 TTS 存在连续空行")
        if "最后给你留一个小任务" not in tts or "记住一句话" not in tts:
            errors.append(f"第{n}课 TTS 未同步结尾三件套")

    # 4) SVG 全量校验
    svg_fail = 0
    for p in glob.glob(os.path.join(ROOT, "第*课_*", "03_素材", "broll", "*.svg")):
        e = validate_svg(p)
        if e:
            svg_fail += 1
            errors.append(f"SVG 越界 {os.path.basename(p)}: {e[0]}")
    if svg_fail:
        errors.append(f"共 {svg_fail} 个 SVG 未通过边界校验")

    print(f"全季 B roll 素材：{len(all_broll)} 个")
    print(f"分镜脚本：{len(storyboards)} 份（含 A/B 双轨 / 交接表 / 音效 cue）")
    print(f"口播稿 + TTS 稿：{len(LESSONS)} 课")
    if warns:
        print("\n[提醒]")
        for w in warns:
            print("  -", w)
    if errors:
        print("\n[阻断] 共 %d 项：" % len(errors))
        for e in errors:
            print("  -", e)
        return 1
    print("\n机器闸全部通过：四份产物交叉一致，可以进入配音 / 动画环节。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
