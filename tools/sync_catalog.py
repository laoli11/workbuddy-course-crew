# -*- coding: utf-8 -*-
"""
组件库沉淀 + 双份同步

课程制片团的 catalog.json 存在两份：
  A. 专家包（本地实际被调用）  ~/.workbuddy/plugins/marketplaces/my-experts/plugins/course-crew/skills/...
  B. 开源仓库（对外发布）      workbuddy-course-crew/skills/...

历史上两份漂移过，且都带过「字符串内嵌未转义直引号」导致 JSON 解析失败
（门禁脚本静默空跑）。本脚本：
  1. 容错修复历史坏字符
  2. 把分镜里新规划的概念组件登记进库（按 id 去重，不覆盖已有）
  3. 写回两份，保证逐字节一致
  4. 输出差异报告

用法： python tools/sync_catalog.py [--dry]
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERT = (r"C:/Users/82668/.workbuddy/plugins/marketplaces/my-experts/"
          r"plugins/course-crew/skills/course-visual-library/catalog.json")
PATHS = [
    os.path.join(REPO, "skills", "course-visual-library", "catalog.json"),
    EXPERT,
]

LEGACY_FIXES = [
    ('重点"别装C盘"停顿强调+局部放大', '重点「别装C盘」停顿强调+局部放大'),
    ('红色警示标签"别装C盘""', '红色警示标签「别装C盘」"'),
]

NEW_COMPONENTS = [
    {
        "id": "WB-C06", "name": "记忆对比", "category": "concept",
        "tags": ["短期记忆", "长期记忆", "无状态", "新窗口对比"],
        "scene": "第02课段10 长期记忆：AI 无状态 → 聊天记录条 vs 笔记本 → 新窗口切换对比",
        "action": "无状态大脑 → 记录条/笔记本左右对比 → 新窗口开窗，长期记忆仍在",
        "source": "第02课段10", "status": "待沉淀",
    },
    {
        "id": "WB-C07", "name": "文件夹归档", "category": "concept",
        "tags": ["工作空间", "散乱vs归档", "目录树", "粒子吸入"],
        "scene": "第03课段9 空间概念：任务散乱存 vs 空间文件夹归档",
        "action": "文件粒子乱飞 → 中缝长出文件夹 → 粒子吸入按类分层 → D 盘目录树逐层展开",
        "source": "第03课段9", "status": "待沉淀",
    },
    {
        "id": "WB-C08", "name": "角色生长", "category": "concept",
        "tags": ["装修比喻", "技能", "工人", "局部蒙版"],
        "scene": "第04课段4 技能=电工/水暖工/瓷砖工，同一房子连着演三层",
        "action": "管线末端鼓起 → 长出人物 + 技能标签错峰弹出 → 瓷砖工不连水电用局部蒙版压出差异",
        "source": "第04课段4", "status": "待沉淀",
    },
    {
        "id": "WB-C09", "name": "跳焦", "category": "concept",
        "tags": ["注意力", "分步执行", "逐块推近", "拆分复杂任务"],
        "scene": "第07课段9 分步相乘 + 复杂任务拆分，注意力光点逐块聚焦",
        "action": "竖式按位逐位点亮（其余压暗 0.6）→ 拉远 → 光点在标书上逐块跳焦，每块 0.6s 到位停 0.85s",
        "source": "第07课段9", "status": "待沉淀",
    },
    {
        "id": "WB-C10", "name": "信息密度", "category": "concept",
        "tags": ["黑盒子", "上下文", "容器填充", "同帧联动"],
        "scene": "第07课段6 技巧一：AI 不是不聪明，是了解太少",
        "action": "黑盒子内粒子密度随每条上下文上升一档 → 盒体由暗转亮 → 输出质量条同帧增长",
        "source": "第07课段6", "status": "待沉淀",
    },
]


def load(path):
    s = open(path, encoding="utf-8").read()
    fixed = False
    try:
        return json.loads(s), fixed
    except json.JSONDecodeError:
        for old, new in LEGACY_FIXES:
            if old in s:
                s = s.replace(old, new)
                fixed = True
        return json.loads(s), fixed


def main():
    dry = "--dry" in sys.argv
    docs = []
    for p in PATHS:
        if not os.path.exists(p):
            print(f"[跳过] 不存在：{p}")
            docs.append(None)
            continue
        d, fixed = load(p)
        print(f"读取 {os.path.basename(os.path.dirname(os.path.dirname(p)))}/… "
              f"组件 {len(d['components'])} 个" + ("（已修复坏字符）" if fixed else ""))
        docs.append(d)

    base = next((d for d in docs if d), None)
    if not base:
        print("[错误] 两份 catalog 都读不到")
        return 1

    ids = {c["id"] for c in base["components"]}
    added = []
    for c in NEW_COMPONENTS:
        if c["id"] not in ids:
            base["components"].append(c)
            added.append(c["id"])
    base["version"] = "1.1.0"
    base["updated"] = "2026-11-14"
    text = json.dumps(base, ensure_ascii=False, indent=2) + "\n"
    print(f"新登记组件：{added or '无'}；总计 {len(base['components'])} 个")

    if dry:
        print("仅试运行，未写文件")
        return 0

    for p, d in zip(PATHS, docs):
        if d is None:
            continue
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        print("已写入", p)

    same = all(open(p, encoding="utf-8").read() == text
               for p, d in zip(PATHS, docs) if d is not None)
    print("两份 catalog 逐字节一致：", "是" if same else "否")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
