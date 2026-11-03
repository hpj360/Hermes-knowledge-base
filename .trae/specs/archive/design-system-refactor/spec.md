# 设计风格重构 Spec · 包豪斯几何 + 极简现代

## Why

当前 UI 采用"编辑杂志风"（米色纸张底 + 衬线字体 + 金箔点缀），用户审美不符。需重构为**包豪斯几何 + 极简现代**风格：白底为主、粗体大写标题、3px 粗边框、领域色实色几何块装饰、Space Grotesk 字体。

本次重构在 R1-R4 + UI 规范统一基础上进行，保留已稳定的路由 IA（R3）与业务逻辑，仅替换视觉层。采用 3 阶段渐进策略（P1 Token 替换 → P2 核心 Shell + 组件库 → P3 面板逐个迁移），每阶段独立验收，测试质量分 ≥ 95。

## Design Decisions（已确认）

| 维度 | 决策 | 备注 |
|---|---|---|
| 风格方向 | 包豪斯几何 + 极简现代 | 白底 + 粗体大写 + 几何色块 + 大留白 |
| 配色 | 方案 3 · 领域色实色几何 | 酒红 #6b2c2c / 琥珀金 #c9a961 / 深青铜 #3a5a6b |
| 字体 | Space Grotesk | 标题/正文/品牌；数据标签可选 JetBrains Mono |
| 圆角 | 微圆角 2px | 保留锐利感又消除像素冰冷感；chip 仍可用胶囊 |
| 边框 | 粗边框 3px | 包豪斯标志性视觉力度；卡片 2px，主分隔 3px |
| 布局 | 顶栏 + 主内容 + 右辅助面板 | 方案 C；移动端右栏折叠到下方 |
| 几何密度 | 适度（2-3 处色块） | 角落圆形 + 1 处小方块点缀，不喧宾夺主 |
| 执行 | 方案 B · 3 阶段渐进 | P1/P2/P3 每阶段验收 ≥ 95 |

## What Changes

### P1 · Token 替换（CSS 层，零组件结构改动）

- 重写 `design/mockup/_tokens.css`：替换全部颜色/字体/圆角/边框 token 为包豪斯体系
- 替换 `web/src/index.css` 中 `@layer tokens`：同步新 token 值
- 字体加载：在 `web/index.html` 引入 Google Fonts `Space Grotesk` + `JetBrains Mono`
- 语义类适配：`_components.css` / `index.css` 中 `.btn-*` / `.card` / `.input` / `.tag-*` 等语义类颜色/字体/圆角跟随 token 自动换肤
- **不变更**：任何 `.tsx` 组件结构、props、className 引用

### P2 · 核心 Shell + 组件库

- 扩展 `web/src/components/ui.tsx`，新增包豪斯语义组件：
  - `BauhausNavbar`：顶栏（3px 底边粗线 + brand mark + tabs + active 3px 下划线）
  - `BauhausLayout`：主内容 + 右辅助面板两栏布局（移动端折叠）
  - `BauhausCard`：2px 黑边框 + 左上角实色方块 + 大写标题
  - `BauhausMetric`：实色填充指标卡（酒红/琥珀/青铜三变体，反白数字）
  - `BauhausChip`：实色填充 chip（mono 字体 + 大写）
  - `BauhausButton`：solid（黑底白字）/ accent（黑底琥珀字）/ outline（2px 黑边）
  - `SectionLabel`：mono 大写 + 44×4px 黑色前条
  - `GeometryDecorator`：角落圆形色块装饰组件（2-3 处，opacity 0.1）
- 重构 `App.tsx` 导航 shell：采用 `BauhausNavbar` + `BauhausLayout`
- **不变更**：面板内部内容（LabPanel/RecipePanel 等内部结构在 P3 迁移）

### P3 · 面板逐个迁移

按优先级迁移到新组件库（每个面板独立验收）：
1. RecipePanel / DocumentDetailPanel（配方核心）
2. LabPanel（实验室，含右辅助指标）
3. ChatPanel（问答）
4. ImportDialog / PendingReviewPanel / RecipeEditorPanel（管理流）
5. DocumentList / CitationList / TagPanel / Login / AgeGate / ErrorBoundary

## Impact

- **Affected specs**: ui-consistency-review（本 spec 为其视觉风格重构后继）
- **Affected code**:
  - `design/mockup/_tokens.css`（P1 重写）
  - `web/src/index.css`（P1 token 同步 + P2 语义类）
  - `web/index.html`（P1 字体引入）
  - `web/src/components/ui.tsx`（P2 扩展包豪斯组件库）
  - `web/src/App.tsx`（P2 shell 重构）
  - `web/src/components/*.tsx`（P3 逐个面板迁移）
- **Affected tests**: 现有 173 个前端测试需 P1 零回归；P2 新增组件库单测；P3 每面板迁移后测试通过
- **不影响后端**：纯前端视觉重构

## ADDED Requirements

### Requirement: P1 Token 体系替换

系统 SHALL 在 `design/mockup/_tokens.css` 与 `web/src/index.css` 中定义包豪斯设计 token：

```css
/* Color */
--ink-900: #1a1a1a; --ink-600: #555; --ink-400: #888;
--ink-100: #e5e5e5; --ink-50: #f7f7f7; --paper: #ffffff;
--wine: #6b2c2c; --amber: #c9a961; --bronze: #3a5a6b;
--wine-tint: #f5ebe9; --amber-tint: #faf6ec; --bronze-tint: #ebf0f3;

/* Typography */
--font-display: "Space Grotesk", "Helvetica Neue", sans-serif;
--font-body: "Space Grotesk", "Helvetica Neue", sans-serif;
--font-mono: "JetBrains Mono", "SF Mono", Consolas, monospace;
/* 字号: xs10 / sm12 / base14 / lg18 / xl24 / 2xl30 / 3xl40 */
/* 标题: black 900 + 大写 + letter-spacing -0.8px */

/* Radius & Border */
--r-sm: 2px; --r-md: 0; --r-pill: 999px;
--border-bold: 3px solid var(--ink-900);
--border-medium: 2px solid var(--ink-900);
--border-thin: 1px solid var(--ink-100);
```

#### Scenario: P1 零回归
- **WHEN** P1 token 替换完成
- **THEN** 现有 173 个前端测试全部通过
- **AND** 全站颜色/字体/圆角自动换肤为包豪斯体系
- **AND** 无任何 `.tsx` 文件结构改动

### Requirement: P2 包豪斯组件库

系统 SHALL 在 `ui.tsx` 新增 8 个包豪斯语义组件，全部使用 design tokens，无硬编码 hex，支持 className 透传。

#### Scenario: 组件 token 透传
- **WHEN** 使用 `BauhausCard` 渲染配方
- **THEN** 边框为 `var(--border-medium)`（2px 黑）
- **AND** 左上角方块用领域色（`var(--wine)` / `var(--amber)` / `var(--bronze)`）
- **AND** 标题为 `var(--font-display)` + black 900 + 大写

#### Scenario: 布局响应式
- **WHEN** 在 < 768px 视口查看 `BauhausLayout`
- **THEN** 右辅助面板折叠到主内容下方
- **AND** 顶栏 tabs 可横向滚动

### Requirement: P3 面板迁移

每个面板迁移后 SHALL 满足：
- inline style ≤ 5 处（动态值除外）
- 使用 `Bauhaus*` 组件库替代手写 div + inline style
- 现有测试通过，新增视觉断言

#### Scenario: RecipePanel 迁移验收
- **WHEN** RecipePanel 迁移完成
- **THEN** 配方卡使用 `BauhausCard`
- **AND** 元数据使用 `BauhausChip`
- **AND** inline style ≤ 5 处
- **AND** RecipePanel 相关测试全部通过

### Requirement: 几何装饰

系统 SHALL 通过 `GeometryDecorator` 组件提供适度几何装饰：
- 每屏 2-3 处圆形色块（直径 60-110px，opacity 0.1-0.15）
- 角落定位（top-right / bottom-right / mid-left）
- 颜色循环领域色（wine / amber / bronze）
- **禁止**：装饰元素遮挡内容、影响可读性、增加 DOM 嵌套层级

### Requirement: 阶段验收门槛

每阶段完成 SHALL 满足测试质量分 ≥ 95：
- P1：173 现有测试 100% 通过 + App.tsx 覆盖率 ≥ 95%
- P2：P1 基础 + 新增组件库单测覆盖 8 个组件 + App.tsx 覆盖率 ≥ 95%
- P3：每面板迁移后该面板相关测试通过 + 全量测试通过 + TypeScript 构建零错误

## Non-Goals

- 不变更路由结构（R3 已稳定）
- 不变更业务逻辑、API 契约、数据模型
- 不重写后端
- 不引入新依赖（wouter 等已有依赖除外）
- 不做暗色模式（如需后续另立 spec）
