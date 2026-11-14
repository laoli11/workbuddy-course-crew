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
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_broll import validate as validate_svg  # noqa: E402

ROOT = r"E:/WorkBuddy课程/01_基础课"
LESSONS = ["01", "02", "03", "04", "05", "06", "07"]
BANNED = ["很简单", "不用说", "大家都知道", "随便", "想跳过也行"]


def load_terminology():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                     "skills", "terminology-spec", "terminology.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def check_terminology(term, text, where, errors, warns, space_mode="expect"):
    """术语闸：forbidden 硬拦、大小写错误硬拦、中英空格提醒。

    space_mode: expect=口播稿（中英间应加空格）；none=TTS稿（不该有空格）；
                off=分镜（文件名/表格除外，只查术语与大小写）。
    """
    # .workbody 是历史错词，先单独抓；.workbuddy 是合法目录名，占位避免误报
    if ".workbody" in text.lower():
        errors.append(f"{where} 历史错词「.workbody」→ 应为「.workbuddy」")
    text = text.replace(".workbuddy", "\ue000DIR\ue000")
    for e in term.get("exceptions", []):
        text = text.replace(e, "\ue001URL\ue001")
    low = text.lower()
    # forbidden 与大小写检查去重：已在 forbidden 里的小写变体不再重复报
    dup = {f.lower() for t in term["terms"] for f in t.get("forbidden", [])}
    for t in term["terms"]:
        canon = t["canonical"]
        for f in t.get("forbidden", []):
            for m in re.finditer(r"(?<![A-Za-z0-9.])(" + re.escape(f) + r")(?![A-Za-z0-9])", text, re.I):
                if m.group(1) == canon:      # 正确写法本身不算违规
                    continue
                errors.append(f"{where} 禁用写法「{m.group(1)}」→ 应为「{canon}」")
    for w in term["case_sensitive"]["强制"]:
        if w.lower() in dup:
            continue
        for m in re.finditer(r"(?<![A-Za-z])(" + re.escape(w.lower()) + r")(?![A-Za-z])", text):
            errors.append(f"{where} 大小写错误「{m.group(1)}」→ 应为「{w}」")
    for w in term["case_sensitive"]["强制小写"]:
        if w.lower() in dup:
            continue
        for m in re.finditer(r"(?<![A-Za-z])(" + re.escape(w.upper()) + r")(?![A-Za-z])", text):
            errors.append(f"{where} 大小写错误「{m.group(1)}」→ 应为「{w}」")
    if space_mode == "off":
        return
    wl = term["space_rules"]["whitelist"]
    # 只查英文字母与中文之间（数字+中文如「22万次」「11点」是中文表述，不查）
    pat = (r"[\u4e00-\u9fff] [A-Za-z]|[A-Za-z] [\u4e00-\u9fff]"
           if space_mode == "none"
           else r"[\u4e00-\u9fff][A-Za-z]|[A-Za-z][\u4e00-\u9fff]")
    cnt = 0
    for m in re.finditer(pat, text):
        line = text[:m.start()].rsplit("\n", 1)[-1].strip()
        if line.startswith("#"):          # markdown 标题行不查
            continue
        seg = text[max(0, m.start() - 4):m.end() + 4]
        if any(w in seg for w in wl):
            continue
        cnt += 1
        if cnt <= 8:
            tag = "多空格" if space_mode == "none" else "缺空格"
            warns.append(f"{where} 中英{tag}：…{seg}…")
    if cnt > 8:
        tag = "多空格" if space_mode == "none" else "缺空格"
        warns.append(f"{where} 中英{tag}共 {cnt} 处（只列前 8）")


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
    try:
        term = load_terminology()
    except Exception as e:
        errors.append(f"术语表加载失败：{e}")
        term = None

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

        # 7) 术语闸（分镜只查术语与大小写，口播稿要求中英空格，TTS 要求无空格）
        if term:
            check_terminology(term, sb, f"第{n}课·分镜", errors, warns, space_mode="off")
            check_terminology(term, md, f"第{n}课·口播稿", errors, warns, space_mode="expect")
            check_terminology(term, tts, f"第{n}课·TTS", errors, warns, space_mode="none")

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
