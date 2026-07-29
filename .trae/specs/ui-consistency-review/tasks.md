# Tasks

- [x] Task 1: 设计源对齐评审报告
  - [x] SubTask 1.1: 逐个读取 `design/mockup/` 13 个 HTML 页面，提取每个页面的语义类与视觉关键点
  - [x] SubTask 1.2: 逐个读取 `web/src/components/` 17 个 React 组件，标注每个区块的样式实现方式（语义类 / inline style / 偏离）
  - [x] SubTask 1.3: 输出差距清单（Markdown 表格），含组件名 / 区块 / mockup 定义 / React 现状 / 偏离等级 / 修复建议
  - [x] SubTask 1.4: 在 5 个重点组件（LabPanel / RecipePanel / DocumentDetailPanel / ChatPanel / ImportDialog）中标注 critical/major 偏离项

- [x] Task 2: ui.tsx 组件库扩展（承载 mockup 语义类）
  - [x] SubTask 2.1: 实现 `MagazineCard`（杂志式配方卡，含 thumb/kicker/title/deck/meta 五区，对应 `.recipe-card-magazine`）
  - [x] SubTask 2.2: 实现 `GoldFoilCard`（金箔英雄卡，含 foil-title/foil-quote/foil-attribution，对应 `.gold-foil-card`）
  - [x] SubTask 2.3: 实现 `LabMetric`（实验室指标格，含 label/num/sub + alert 变体，对应 `.lab-metric`）
  - [x] SubTask 2.4: 实现 `DailyRecipeCard`（今日推荐卡，含 badge/name/reason + hover 抬升，对应 `.daily-recipe`）
  - [x] SubTask 2.5: 为新增组件编写单元测试（渲染 / className 透传 / design tokens 应用 / children slot）

- [x] Task 3: App.tsx 顶部导航栏氛围化
  - [x] SubTask 3.1: 替换 `bg-brand-gradient` inline 实现为 `.navbar` 语义类（噪点底 + 深酒红渐变 + 金箔底边）
  - [x] SubTask 3.2: 验证 nav-tab active 状态使用 `--nav-tab-active` token（金箔底边）
  - [x] SubTask 3.3: 移动端折叠验证（`@media max-width: 640px` 字号调整）

- [x] Task 4: LabPanel inline style 清扫（重灾区，58 → ≤ 10）
  - [x] SubTask 4.1: 抽取材料选择器区块为 `MaterialSelector` 子组件，使用 `.material-selector` / `.material-category` / `.chip-list` / `.chip-chip` 语义类
  - [x] SubTask 4.2: 抽取配方卡片为 `MagazineCard` 组件实例（替换 inline 实现的 `.recipe-card`）
  - [x] SubTask 4.3: 抽取运营看板为 `LabDashboard` 子组件，使用 `.lab-dashboard` / `.lab-metrics` / `.lab-metric` 语义类
  - [x] SubTask 4.4: 抽取今日推荐为 `DailyRecipeCard` 组件实例
  - [x] SubTask 4.5: 抽取同步面板为 `LabSyncPanel` 子组件，使用 `.lab-sync-panel` / `.lab-sync-btn` / `.sync-result-row` 语义类
  - [x] SubTask 4.6: 保留的 inline style 必须是动态计算值，编写注释说明

- [x] Task 5: RecipePanel / DocumentDetailPanel / ChatPanel / ImportDialog inline style 清扫
  - [x] SubTask 5.1: RecipePanel（18 → 1）：配方列表用 `MagazineCard`，状态徽章用 `StatusBadge`
  - [x] SubTask 5.2: DocumentDetailPanel（16 → 1）：chunk 列表用 `BodyText` + `MonoText`，元信息用 `MetaText`
  - [x] SubTask 5.3: ChatPanel（17 → 1）：消息气泡抽 `MessageBubble` 组件，外部参考抽 `ExternalRefList` 组件
  - [x] SubTask 5.4: ImportDialog（18 → 0）：表单用 `FormField`，状态用 `StatusBadge`

- [x] Task 6: 交互模式统一
  - [x] SubTask 6.1: 全局搜索 `<div>加载中` / `<p>暂无` / inline 红字错误 / inline 绿色成功横幅，替换为 Skeleton / EmptyState / ErrorBanner / Toast
  - [x] SubTask 6.2: 实现 `usePrompt` Hook（参照 `useConfirm` 模式）
  - [x] SubTask 6.3: 迁移 PendingReviewPanel 的 `window.prompt` 到 `usePrompt`，移除 `// TODO: R3 迁移到 usePrompt` 注释
  - [x] SubTask 6.4: 全局搜索 `window.confirm` / `window.prompt`，断言返回 0 处

- [x] Task 7: 字体与颜色审计
  - [x] SubTask 7.1: 全局搜索 `fontFamily: "var(--font-sans)"`，逐处替换为 `--font-ui` 或 `--font-body`（R1 之前的向后兼容除外）
  - [x] SubTask 7.2: 全局搜索 inline style 中的硬编码 hex（非 `var(--*)`），逐处替换为 design tokens
  - [x] SubTask 7.3: 验证 ChatPanel 中 `fontFamily: "var(--font-sans)"` 全部清理

- [x] Task 8: 测试与验收
  - [x] SubTask 8.1: 现有 136 个前端测试全部保持通过（实际 173 个含新增）
  - [x] SubTask 8.2: 新增 ui.tsx 组件库单测覆盖 `MagazineCard` / `GoldFoilCard` / `LabMetric` / `DailyRecipeCard`（26 测试）
  - [x] SubTask 8.3: App.tsx 覆盖率保持 ≥ 95%（实际 95.7%）
  - [x] SubTask 8.4: TypeScript 构建（`npm run build`）无错误
  - [ ] SubTask 8.5: 视觉快照断言：5 个主 tab 截图与 mockup 对比（手动审查，待用户验证）
  - [x] SubTask 8.6: 输出最终差距清单对照表（修复前 vs 修复后）

# Task Dependencies

- Task 1（评审报告）独立，应最先完成，输出指导 Task 2-7
- Task 2（ui.tsx 扩展）依赖 Task 1 评审结论，与 Task 3-7 可部分并行
- Task 3（导航栏）依赖 Task 2 的 `Navbar` 组件（若实现）
- Task 4（LabPanel）依赖 Task 2 的 `MagazineCard` / `LabMetric` / `DailyRecipeCard`
- Task 5（其他面板）依赖 Task 2 的 `MagazineCard`
- Task 6（交互模式）独立，可与 Task 3-5 并行
- Task 7（字体颜色审计）独立，最后执行收口
- Task 8（测试验收）依赖 Task 2-7 全部完成
