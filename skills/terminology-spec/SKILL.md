---
name: terminology-spec
description: "Binding terminology glossary for the Course Production Crew: the single source of truth for product names, concepts, numbers and writing rules. Load before writing any script, storyboard, subtitle or voiceover line, and every delivery must pass the terminology gate in validate_delivery.py. Prevents terminology drift when models change mid-project."
---

# 术语规范（Terminology Spec）

> 本规范解决一个真实风险：**项目中途切换 AI 模型**。
> 不同模型不认识 WorkBuddy 的专有名词，会把「WorkBuddy」写成「workbody」、
> 把「工作空间」说成「工作区」、把「积分倍率」改成「消耗系数」——
> 一旦漂移，分镜、动画字幕、配音三处各说各话，返工成本极高。
> 因此：**一切以 `terminology.json` 为唯一事实源**，机器可读、人机同源，
> 换任何模型接手，第一件事就是对照这份表。

## 一、总则

1. `terminology.json` 是本规范的数据本体，SKILL.md 只讲规则。两者必须双写：
   专家包 `skills/terminology-spec/` 与开源仓库 `skills/terminology-spec/`，改动用 `tools/sync_catalog.py` 思路同步。
2. 任何产出（口播稿 / TTS 稿 / 分镜 / 动画字幕 / 配音 / 截图卡文字）落笔前，
   先查 `terminology.json` 的 `terms`；写数字先查 `facts`。
3. 换模型续写时，**先跑 `python tools/validate_delivery.py`** 让机器闸指出已漂移的术语，再动手。
4. 表里没有的新术语，先登记 `terminology.json` 再用；禁止先用在后补表。

## 二、术语三档用法

| 档位 | 规则 | 例子 |
|---|---|---|
| `canonical`（权威写法） | 任何位置都用它，包括字幕 | WorkBuddy、DeepSeek、尧哥AI |
| `forbidden`（禁用写法） | 任何位置都不许出现，机器闸硬拦 | workbody、workbuddy、姚哥 |
| `aliases`（可用别名） | 口播稿口语化时可用，但**首次出现必须是 canonical** | 空间（canonical：工作空间） |

- 大小写是术语的一部分：`WorkBuddy` 的 W/B 大写、`DeepSeek` 的 S 大写、
  `Kimi`、`Claude`、`Markdown` 首字母大写；`ima`、`prompt` 全小写；`AI` 全大写。
- 中英混排：**口播稿正文**中英文之间加空格（`WorkBuddy 的`）；**TTS 稿**去掉空格
  （`WorkBuddy的`）。白名单例外（品牌连写）：`尧哥AI`、`AI客服`。

## 三、数字事实口径（facts 表）

- 课程里的数字（积分、价格、时长、容量）是**教学内容**，一字不改：
  登录送约 1500 积分、每天领 100、Kimi 3 倍率 1.62、图片重命名消耗 1.98 积分、
  免费 20G、夜间免费 23:00–08:00、上下文默认 6 小时截断、长期记忆 12 点刷新、
  讲师背景 10000+ 学员 / 200+ 公司。
- 各课讲同一个数字时口径必须一致；需要修改时先改 `facts` 再改稿。

## 四、沉淀流程（团队自动升级的一环）

每完成一门新课时，如果出现了新的产品词 / 品牌 / 数字：
1. 登记进 `terminology.json`（terms / facts）
2. 双写专家包 + 仓库
3. 跑 `python tools/validate_delivery.py` 确认机器闸认账

## 五、机器闸（术语闸）

`tools/validate_delivery.py` 对全部 7 门口播稿 / TTS 稿 / 分镜执行：
- `forbidden` 词硬拦（大小写不敏感）
- 大小写敏感词的错误变体硬拦（如 `deepseek`、`kimi`、`markdown` 出现在中文正文中）
- 中英混排空格规则为**提醒级**（warn，不阻断），白名单例外
- 任一 `facts` 数字出现在上下文里时，检查其关键数字是否被改写

> 机器闸 PASS 只是技术上没写错；「这个词该不该这样讲」仍需编导人工判断。
