# 前端 UI 规范统一与交互评审 Spec

## Why

项目存在两套并行的前端实现：
- **设计源（权威）**：`design/mockup/` 高保真设计稿，含 `_tokens.css`（设计令牌）+ `_components.css`（语义组件样式）+ 13 个 HTML 页面，定义"高级酒类杂志感"视觉语言
- **React 实现（偏离）**：`web/src/components/` 17 个组件，223 处 inline style 残留分布 18 个文件，部分组件绕过 `_components.css` 语义类直接 inline 写样式

R1-R3 阶段已建立 `ui.tsx` 基础组件库并清理 30+ 处 inline style，但与 mockup 设计稿的对齐仍未完成：LabPanel 58 处 inline style 为重灾区，部分组件未使用 mockup 中定义的语义类（如 `.recipe-card-magazine` / `.gold-foil-card` / `.lab-dashboard` / `.daily-recipe` 等），导致视觉与交互体验偏离设计意图。

## What Changes

- 对 5 个主 tab（问答/实验室/配方/文档/管理）+ 通用组件（Modal/Toast/Skeleton/AgeGate/Login）逐个评审，输出差距清单
- 将 React 组件与 `design/mockup/_components.css` 语义类对齐，消除冗余 inline style
- 补齐 `ui.tsx` 组件库缺失组件（如 `MagazineCard` / `GoldFoilCard` / `LabMetric` / `DailyRecipeCard`），承载 mockup 语义类
- 统一交互模式：loading 用 Skeleton、empty 用 EmptyState、error 用 ErrorBanner、success 用 Toast，禁止散落的 inline 实现
- 字体应用统一：标题 `--font-serif`、正文 `--font-body`、UI/数据 `--font-ui`、等宽 `--font-mono`，禁止 `--font-sans` 别名新用法
- 颜色统一：所有颜色经 design tokens，禁止硬编码 hex（除 tokens 自身）
- 不变更：路由结构（R3 已稳定）、业务逻辑、API 契约

## Impact

- **Affected specs**: R1 CSS 止血、R2 组件库、R3 路由 IA（本阶段为 R1-R3 的视觉对齐收口）
- **Affected code**:
  - `web/src/components/` 全部 17 个组件（重点：LabPanel / RecipePanel / DocumentDetailPanel / ChatPanel / ImportDialog）
  - `web/src/components/ui.tsx`（扩展组件库）
  - `web/src/index.css`（可能的语义类补齐）
  - `web/src/App.tsx`（导航栏氛围化）
- **Affected tests**: 现有 136 个前端测试需保持通过，新增组件库单测 + 视觉快照断言
- **不影响后端**：本阶段为纯前端工作

## ADDED Requirements

### Requirement: 设计源对齐评审

系统 SHALL 输出一份覆盖全部 5 个主 tab + 通用组件的差距清单，逐项标注：
1. mockup 设计稿定义的语义类与视觉效果
2. React 实际实现现状（使用语义类 / inline style / 偏离）
3. 偏离等级（critical / major / minor）
4. 修复建议（替换为语义类 / 抽取新组件 / 调整 tokens）

#### Scenario: 评审覆盖完整
- **WHEN** 评审完成后查看差距清单
- **THEN** 每个组件（17 个）都有对应条目
- **AND** LabPanel / RecipePanel / DocumentDetailPanel / ChatPanel / ImportDialog 5 个重点组件有逐区块分析

### Requirement: ui.tsx 组件库扩展

系统 SHALL 在 `web/src/components/ui.tsx` 中新增以下语义组件，承载 mockup `_components.css` 中的复杂卡片样式：
- `MagazineCard`：杂志式配方卡（含 thumb/kicker/title/deck/meta 五区）
- `GoldFoilCard`：金箔英雄卡（含 foil-title/foil-quote/foil-attribution）
- `LabMetric`：实验室指标格（含 label/num/sub + alert 变体）
- `DailyRecipeCard`：今日推荐卡（含 badge/name/reason + hover 抬升）
- `Navbar`（可选）：氛围导航条（噪点底 + 深酒红渐变 + 金箔底边）

#### Scenario: 组件支持 design tokens 透传
- **WHEN** 使用 `MagazineCard` 渲染配方
- **THEN** 所有颜色/字体/间距经 `var(--*)` tokens
- **AND** 不含任何硬编码 hex 值
- **AND** className 透传可被 Tailwind 工具类补充

### Requirement: inline style 清扫收口

系统 SHALL 将 18 个文件中的 223 处 inline style 清理至以下基线：
- LabPanel：58 处 → ≤ 10 处（保留动态计算值）
- RecipePanel：18 处 → ≤ 5 处
- DocumentDetailPanel：16 处 → ≤ 5 处
- ChatPanel：17 处 → ≤ 5 处
- ImportDialog：18 处 → ≤ 5 处
- 其他 13 个文件：96 处 → ≤ 30 处
- **总目标**：223 处 → ≤ 60 处（减幅 ≥ 73%）

#### Scenario: 清扫后保留的 inline style 性质
- **WHEN** 检查清扫后剩余的 inline style
- **THEN** 每处剩余 inline style 必须属于以下三类之一：
  - 动态计算值（如 `highlightChunk === rowid ? "bg-highlight" : ""`）
  - 一次性容器背景（如 `background: var(--paper-bg)`）
  - 组件库内部默认样式（`ui.tsx` 8 处）

### Requirement: 交互模式统一

系统 SHALL 统一以下交互模式，禁止散落的 inline 实现：
- **Loading**：所有异步加载用 `<Skeleton />` 组件，禁止 `<div>加载中...</div>` 或 inline spinner
- **Empty**：所有空状态用 `<EmptyState />` 组件，禁止 inline `<p>暂无数据</p>`
- **Error**：所有错误展示用 `<ErrorBanner />` 组件 + `role="alert"`，禁止 inline 红字
- **Success**：所有成功反馈用 `showToast(msg, "success")`，禁止 inline 绿色横幅
- **Confirm**：所有确认弹窗用 `useConfirm()` Hook，禁止 `window.confirm()`
- **Prompt**：所有输入弹窗用 `usePrompt()` Hook，禁止 `window.prompt()`（含 PendingReviewPanel R3 遗留 TODO）

#### Scenario: window.confirm/prompt 完全消除
- **WHEN** 全局搜索 `window.confirm` / `window.prompt`
- **THEN** 返回 0 处匹配
- **AND** `PendingReviewPanel.tsx` 的 `// TODO: R3 迁移到 usePrompt` 注释被消除

### Requirement: 字体应用统一

系统 SHALL 按以下规则统一字体应用：
- 标题（h1-h3 / .section-title / .display-title / .card-title）：`--font-serif`
- 正文段落：`--font-body`
- UI 文字（按钮 / 标签 / 表单 / 元信息 / chip / badge）：`--font-ui`
- 等宽数据（doc_id / score / chunk 索引 / 代码）：`--font-mono`
- **禁止**新增对 `--font-sans` 别名的引用（保留仅作为向后兼容）

#### Scenario: 字体引用审计
- **WHEN** 全局搜索 `fontFamily: "var(--font-sans)"`
- **THEN** 返回 0 处新增引用（R1 之前已有的保留为向后兼容）
- **AND** ChatPanel 中 `fontFamily: "var(--font-sans)"` 全部改为 `--font-ui` 或 `--font-body`

## MODIFIED Requirements

### Requirement: 视觉一致性

R1-R3 阶段已建立 design tokens 与基础组件库，本阶段为视觉对齐收口：
- 将 React 实现与 `design/mockup/_components.css` 中的语义类对齐
- 补齐 mockup 中已有但 React 未实现的语义类（如 `.recipe-card-magazine` / `.gold-foil-card` / `.lab-dashboard` / `.daily-recipe`）
- App.tsx 顶部导航栏氛围化（参考 mockup `.navbar` 噪点底 + 深酒红渐变 + 金箔底边）

## REMOVED Requirements

### Requirement: inline style 散落实现
**Reason**: R2 阶段未完全清扫，223 处 inline style 散落 18 文件，导致视觉不一致与维护负担
**Migration**: 通过 ui.tsx 组件库 + _components.css 语义类替换，保留动态计算值的 inline style
