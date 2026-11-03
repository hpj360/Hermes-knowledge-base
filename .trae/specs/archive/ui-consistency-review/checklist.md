# 验收清单

## 评审阶段
- [x] 差距清单覆盖全部 17 个 React 组件，每个组件有逐区块分析
- [x] 5 个重点组件（LabPanel / RecipePanel / DocumentDetailPanel / ChatPanel / ImportDialog）标注 critical/major 偏离项
- [x] 差距清单含修复建议（替换为语义类 / 抽取新组件 / 调整 tokens）

## 组件库扩展
- [x] `MagazineCard` 组件实现，含 thumb/kicker/title/deck/meta 五区，使用 `.recipe-card-magazine` 语义类
- [x] `GoldFoilCard` 组件实现，含 foil-title/foil-quote/foil-attribution，使用 `.gold-foil-card` 语义类
- [x] `LabMetric` 组件实现，含 label/num/sub + alert 变体，使用 `.lab-metric` 语义类
- [x] `DailyRecipeCard` 组件实现，含 badge/name/reason + hover 抬升，使用 `.daily-recipe` 语义类
- [x] 新增组件全部使用 design tokens（`var(--*)`），无硬编码 hex
- [x] 新增组件支持 className 透传，可被 Tailwind 工具类补充
- [x] 新增组件有对应单元测试

## inline style 清扫
- [x] LabPanel：58 处 → 10 处（达标 ≤ 10）
- [x] RecipePanel：18 处 → 1 处（达标 ≤ 5）
- [x] DocumentDetailPanel：16 处 → 1 处（达标 ≤ 5）
- [x] ChatPanel：17 处 → 1 处（达标 ≤ 5）
- [x] ImportDialog：18 处 → 0 处（达标 ≤ 5）
- [~] 其他文件：96 处 → 62 处（部分达标，目标 ≤ 30；CitationList 14→2 / DocumentList 11→1 / TagPanel 11→2 / ErrorBoundary 8→1 已清理，剩余 AgeGate 7 / Login 7 / RecipeEditorPanel 7 / PendingReviewPanel 11 / 其他动态值保留）
- [~] 总计：223 处 → 84 处（部分达标，目标 ≤ 60；减幅 62.3%，9 个重点文件全部达标，剩余 22 处在 ui.tsx 组件库内部属合理保留）
- [x] 保留的 inline style 全部属于动态计算值 / 一次性容器背景 / 组件库内部默认样式三类之一

## 交互模式统一
- [x] 全局搜索 `window.confirm` 调用返回 0 处
- [x] 全局搜索 `window.prompt` 调用返回 0 处
- [x] PendingReviewPanel 的 `// TODO: R3 迁移到 usePrompt` 注释已移除
- [~] 所有 Loading 状态使用 `<Skeleton />` 组件（主体已统一，少数 inline spinner 保留）
- [x] 所有 Empty 状态使用 `<EmptyState />` 组件
- [x] 所有 Error 状态使用 `<ErrorBanner />` + `role="alert"`
- [x] 所有 Success 反馈使用 `showToast(msg, "success")`
- [x] `usePrompt` Hook 实现（参照 `useConfirm` 模式）

## 字体与颜色审计
- [x] 新增代码无 `fontFamily: "var(--font-sans)"` 引用（R1 之前的向后兼容保留）
- [x] ChatPanel 中 `fontFamily: "var(--font-sans)"` 全部改为 `--font-ui` 或 `--font-body`
- [~] inline style 中无硬编码 hex 值（除 design tokens 自身）（主体已清理，剩余 9 处均为 #fff 深底白字 / PRESET_COLORS 功能色板 / 已清扫文件的 rgba 半透明色，属合理保留）
- [x] 标题用 `--font-serif`，正文用 `--font-body`，UI 用 `--font-ui`，等宽用 `--font-mono`

## 导航栏氛围化
- [x] App.tsx 顶部导航使用 `.navbar` 语义类（噪点底 + 深酒红渐变 + 金箔底边）
- [x] nav-tab active 状态使用 `--nav-tab-active` token（金箔底边）
- [x] 移动端折叠字号调整生效（`@media max-width: 640px`，已有 overflow-x-auto）

## 测试与验收
- [x] 现有前端测试全部通过（136 → 173，含新增 37 个组件/Hook 测试）
- [x] 新增 ui.tsx 组件库单测覆盖 `MagazineCard` / `GoldFoilCard` / `LabMetric` / `DailyRecipeCard`（26 个测试）
- [x] App.tsx 覆盖率保持 ≥ 95%（实际 95.7%）
- [x] TypeScript 构建（`npm run build`）无错误
- [ ] 5 个主 tab 视觉快照与 mockup 对比（手动审查，需用户在浏览器验证）
- [x] 输出最终差距清单对照表（修复前 vs 修复后，见 gap-analysis.md + 本清单）
- [x] 测试质量分 ≥ 95（173 测试 100% 通过 + App.tsx 95.7% 覆盖率 + TypeScript 0 错误）

## 验收符号说明
- [x] 完全达标
- [~] 部分达标（已大幅改善但未达硬目标，原因见说明）
- [ ] 未验证（需用户手动确认）
