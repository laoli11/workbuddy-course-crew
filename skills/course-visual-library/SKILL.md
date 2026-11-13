---
name: course-visual-library
description: "WorkBuddy course visual component library: maps each spoken line to a reusable screen component. Video director must search this catalog first and reuse approved components by default, then pass the delivery gate before output. Includes per-sentence action table, good/bad paired examples and a shared component-kit for style consistency."
---

# WorkBuddy 课程视觉组件库（Course Visual Library）

> 本规范是「课程制片团」做动画时的**强制约束**，与 animation-spec 并列。
> - animation-spec 管「丝滑与美感」的方法论
> - **本库管「画面从哪来」**——默认复用已认可组件，禁止脱离库原创
> 方法论吸收自 FredTalk（组件库 + 门禁 + 质量审计）。

## 一、核心原则（最高优先级）

1. **画面只能复用已认可组件，或基于已认可组件二创**。默认禁止脱离组件库原创，除非用户当次明确授权。
2. **组件库是弹药库，不是装饰**：每段画面先查 `catalog.json`，选中真实组件再实现；不先写通用模板、后补编号。
3. **禁止退成大字页 / 纯文本页**：候选都不合适就报告「待选组件及缺口」，不得擅自原创或退化成大字页。

## 二、组件库（catalog.json）

- 组件库是 `catalog.json`，当前含 **19 个组件**，分 5 类：
  - `concept` 概念动画（WB-C01 进化蜕变 / C02 定位对比 / C03 生态连接 / C04 流程步骤 / C05 层级架构）
  - `screen` 实操录屏包装（WB-S01 下载 / S02 安装避坑 / S03 登录扫码 / S04 积分 / S05 配置）
  - `text` 文字强调（WB-T01 要点列表 / T02 关键词结论 / T03 数字滚动 / T04 终端命令 / T05 提示词输入 / T06 长回复拎要点）
  - `data` 数据图表（WB-D01 趋势折线 / D02 对比柱状）
  - `transition` 章节转场（WB-TR01 章节转场）
- 每个组件带 `tags`（检索词）与 `searchHint`（口播在讲什么 → 先试哪个组件），按内容选画面，不按个人喜好硬套。

## 三、选型工作流（每段必做，不跳步）

1. 读分镜脚本，为每段在 `componentPlan` 写 `query`：本段画面里**看得见的对象和动作**（如「两个 AI 并排对比、箭头指向会干活」），不是照抄旁白。
2. 查 `catalog.json`，按 `tags` / `searchHint` 匹配出候选组件，逐个看 `scene` 与 `action`。
3. 前 3 个候选必须记录 `selected` / `rejected` 及**具体理由**（为什么选这个、为什么不用那两个）。
4. 选定后「场景级定制」：为本期内容重写场景，可拆组件动作、改时序、删自带开场收尾、多组件动作组合，但底层 kit（字体/颜色/阴影/缓动/字幕/角标）**照用，不手写近似值**。每个场景文件第一行注释写明「动作来自哪个组件」。
5. 候选都不合适：换说法再查（拆成「对象+动作」），仍没有就报告缺口，不退成大字页。

## 四、门禁（交付前必过，程序化强制）

交付「逐段建议」或「真实关键帧」前，必须逐项确认，任一不满足即返工，不得交付：

- [ ] 每段画面都能指认来源组件 id（`source` 或 `action from WB-xxx`）
- [ ] 前 3 候选的 selected/rejected 理由已记录，无「漏比较」
- [ ] 没有退成大字页 / 纯文本页 / 无来源的通用模板
- [ ] 底层 kit 被照用（无手写近似字体/颜色/缓动）
- [ ] 场景文件第一行注释写了动作来源

> 门禁只证明「来源合规」，不证明「画面好」——质量靠第六节的审计。

## 五、逐句动作表（写代码前先填）

每段写代码前，先按此表逐句拆清动作，作为实现依据：

| 字段 | 含义 |
|---|---|
| 对象 | 这句口播画面上「谁」在动（卡片/气泡/数字/曲线/光标）|
| 变化 | 对象发生什么变化（飞入/点亮/滚动/长出/连线）|
| 证据在哪 | 变化对应的屏幕区域 / 关键帧 |
| 观众看哪 | 这一秒观众的视线焦点 |
| 交给谁 | 由哪个组件/动作实现 |

## 六、好坏成对样例 + 质量审计

1. **好坏成对样例**：沉淀「同一句口播，做对 vs 做错」各一例（见 `references/paired-examples.md`），做新段前先看对错长什么样。
2. **动态自检**：渲染后抽帧，检查——是否慢推（镜头长时间缓慢移动）、纯滚动（超过 2 秒无变化）、定格凑时长。有即返工。
3. **可读性自检**：标题/字幕是否过长（中文超约 1400px 断句）、是否遮挡画面主体、字号层级是否拉开（标题大字 / 正文中字 / 说明小字）。

## 七、底层 kit（风格统一，全片共用）

整期动画共享一套 kit，禁止各场景手写近似值：

- **字体**：标题 微软雅黑 Bold / 得意黑，正文 微软雅黑，说明小字同族 Regular
- **颜色**：深色底 `#0a0e1a` 起多层径向渐变；主色青 `#22d3ee`、强调金 `#fbbf24`、危险红 `#ef4444`
- **光晕**：发光元素先压暗实色再叠辉光，防过曝
- **胶片颗粒**：opacity 0.04–0.08 细噪点
- **缓动**：进场 `easeOutCubic`、弹出 `easeOutBack`、位移 `easeInOutCubic`
- **字幕区**：纵向 80%–95%，画面主体最低点 ≤ y840

## 八、入库流程（新组件沉淀）

同类表达第二次出现时，才把本期场景提炼成公共组件，写入 `catalog.json`：
1. 场景代码 + 真实素材跑通、认可
2. 提炼 `id / name / tags / scene / action / source`
3. 加入 `catalog.json` 的 `components`，补 `searchHint`
4. 重新校验注册专家团
