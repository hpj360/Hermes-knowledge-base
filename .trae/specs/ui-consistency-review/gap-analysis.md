# UI 设计源对齐差距清单

## 评审摘要
- 评审组件数：17（重点 8 + 通用 9）
- 实测 inline style 总数：**217**（grep `style={{` 统计；任务描述 223 含多行 style 对象）
  - LabPanel 58 / RecipePanel 18 / ImportDialog 18 / DocumentDetailPanel 16 / ChatPanel 17 / CitationList 14 / TagPanel 11 / DocumentList 11 / PendingReviewPanel 11 / ui.tsx 8 / ErrorBoundary 8 / RecipeEditorPanel 7 / AgeGate 7 / Login 7 / Modal 2 / Toast 2 / Skeleton 2
- 重点组件 critical 偏离：**6**；major 偏离：**14**
- 修复目标：inline style ≤ 60（削减 ~72%）

### 全局性发现（影响所有组件）
1. **字体命名欺诈未清扫**：`_tokens.css` 已明确 `--font-sans` 是 `--font-body`（衬线）的别名，注释要求 UI 场景用 `--font-ui`（Noto Sans SC）。但 17 个组件中 30+ 处 inline style 仍写 `fontFamily: "var(--font-sans)"` 用于 hint/meta/button，导致本应无衬线的 UI 文字错用衬线。**修复：全局替换 `var(--font-sans)` → `var(--font-ui)`（ui.tsx 已正确，其余组件未跟进）。**
   位置示例：`web/src/components/LabPanel.tsx#L539` `web/src/components/ChatPanel.tsx#L248` `web/src/components/DocumentDetailPanel.tsx#L209`
2. **mockup 语义类大面积未使用**：`_components.css` 定义的 26 个语义类中，仅 `.btn-*` `.card` `.input` `.skeleton` `.modal-overlay/.modal` `.sub-chip` 被复用；其余 `.material-selector` `.chip-chip.cat-*` `.selected-bar` `.recipe-card.full-match` `.match-badge` `.ing.have/.missing` `.citation-list` `.editor-*` `.lab-*` `.variant-card` `.tag-row` `.swatch` `.daily-recipe` `.gold-foil-card` 均被 inline style 替代。
3. **分类色系丢失**：mockup `.chip-chip.selected.cat-base_spirit/modifier/juice/garnish` 四色分类（brand-700/gold-500/ink-600/ink-400）是实验室核心视觉语言，LabPanel 全部用 brand-700 单色实现。

---

## 重点组件逐区块分析

### 1. LabPanel（58 处 inline style，重灾区）
对应 mockup：`design/mockup/lab.html`

| 区块 | mockup 语义类 | React 现状 | 偏离等级 | 修复建议 |
|---|---|---|---|---|
| 顶部金箔引导卡 | `.gold-foil-card` + `.foil-title/.foil-quote` | **完全缺失** | critical | 补回金箔卡英雄区，lab.html#L84-L88 |
| 今日推荐 | `.daily-recipe` + `.daily-badge/.daily-name/.daily-reason`（金箔渐变底） | `.card-elevated` + inline style，丢失金箔渐变 | major | 改用 `.daily-recipe` 类，LabPanel.tsx#L159-L193 |
| 材料选择器容器 | `.material-selector` | `.card p-6` 替代 | major | 改用 `.material-selector`，LabPanel.tsx#L197 |
| 材料 chip 分类色 | `.chip-chip.cat-base_spirit/modifier/juice/garnish`（4 色） | inline style 全用 brand-700 | critical | 改用 `.chip-chip` + `cat-*` 类，LabPanel.tsx#L220-L243 |
| 已选材料条 | `.selected-bar` + `.selected-chip` | inline style 重写 | major | 改用语义类，LabPanel.tsx#L250-L281 |
| 匹配按钮 pulse | `.match-btn.pulse`（金色脉冲动画） | 无 pulse 动画 | minor | 补 `.match-btn` 类与 pulse 动画，LabPanel.tsx#L283-L294 |
| 配方卡 | `.recipe-card.full-match/.partial-match` | `.card p-5` + inline borderLeft | major | 改用 `.recipe-card` + match 类，LabPanel.tsx#L462-L467 |
| 匹配徽章 | `.match-badge.match-full/.match-partial` | inline style | major | 改用语义类，LabPanel.tsx#L479-L490 |
| 材料清单 | `.ing.have/.missing` | inline style | major | 改用 `.ing` 类，LabPanel.tsx#L494-L512 |
| 替代原料区 | `.substitute-suggest` | inline style（`.sub-chip` 已用 ✓） | major | 包裹层改用 `.substitute-suggest`，LabPanel.tsx#L516-L557 |
| 配方底部 | `.recipe-footer` + `.citation-link` | inline style | minor | 改用语义类，LabPanel.tsx#L642-L669 |
| IMA 同步 Modal 内统计 | `.lab-sync-panel` + `.sync-result-row` | inline style 三宫格 | major | 抽 LabSyncStats 子组件用语义类，LabPanel.tsx#L883-L951 |
| 翻译 Modal 同上 | `.lab-sync-panel` | inline style 三宫格 | major | 同上，LabPanel.tsx#L1093-L1153 |

### 2. RecipePanel（18 处）
对应 mockup：`design/mockup/recipes.html`

| 区块 | mockup 语义类 | React 现状 | 偏离等级 | 修复建议 |
|---|---|---|---|---|
| 页头分隔 | `.page-head`（borderBottom + 衬线标题） | inline flex + borderBottom | minor | 抽 PageHead 组件，RecipePanel.tsx#L110-L121 |
| 筛选 select | `.select`（mockup 用语义类） | inline `text-sm border rounded` | major | 改用 `.select` 类，RecipePanel.tsx#L136-L168 |
| 筛选计数 | `.filter-count` + `.num`（金色衬线大数字） | inline `.numeral` 替代 | minor | 改用 `.filter-count`，RecipePanel.tsx#L186-L197 |
| 配方卡 | `.recipe-card` + `.hidden-recipe` | `.card` + inline opacity | major | 改用 `.recipe-card`，RecipePanel.tsx#L291-L296 |
| 缩略图占位 | `.recipe-thumb-placeholder`（brand-gradient + ◆） | inline linear-gradient | major | 改用 `.recipe-thumb-placeholder`，RecipePanel.tsx#L307-L322 |
| 来源/审核徽章 | `.source-tag.*` + `.verified-badge.yes/.no` | `<StatusBadge>` 组件替代 | minor | StatusBadge 已 token 化，可保留；但丢失了 source-tag 的来源色编码 |
| 变体列表 | `.variant-card` + `.variant-title/.variant-note` | inline style | major | 改用 `.variant-card`，RecipePanel.tsx#L428-L444 |

### 3. DocumentDetailPanel（16 处）
对应 mockup：`design/mockup/doc-detail.html`

| 区块 | mockup 语义类 | React 现状 | 偏离等级 | 修复建议 |
|---|---|---|---|---|
| 双栏布局 | `.doc-layout`（flex + sticky aside） | inline flex 自实现 | major | 改用 `.doc-layout`，DocumentDetailPanel.tsx#L204 |
| 左侧目录 | `.doc-toc` + `.toc-list` + active 金线 | inline `<aside>` + inline `<a>` | major | 改用 `.toc-list` 类，DocumentDetailPanel.tsx#L206-L251 |
| chunk 编号 | `.chunk-num`（gold-100 圆角 pill） | `.numeral`（灰色无背景） | major | 改用 `.chunk-num`，DocumentDetailPanel.tsx#L269 |
| 章节标题 | `.doc-content h2`（gold-300 下边框） | `.card` 包裹每个 chunk | major | 去卡片化，改用 section + h2，DocumentDetailPanel.tsx#L261-L276 |
| 操作按钮区 | `.doc-actions`（flex + actions-hint） | inline flex 工具栏 | minor | 改用 `.doc-actions`，DocumentDetailPanel.tsx#L120-L132 |
| 配方变体区 | `.doc-variants` + `.variant-list` + `.variant-card` | **完全缺失** | critical | 补变体加载区，doc-detail.html#L111-L117 |

### 4. ChatPanel（17 处）
对应 mockup：`design/mockup/ask.html`

| 区块 | mockup 语义类 | React 现状 | 偏离等级 | 修复建议 |
|---|---|---|---|---|
| 用户气泡 | `.msg-user`（brand-100 浅底圆角） | inline `background: var(--brand-700)` 深底白字 | critical | 颜色反了！改用 `.msg-user`，ChatPanel.tsx#L208-L215 |
| AI 气泡 | `.msg-ai`（白底 + ai-label） | inline `borderLeft: 3px solid gold-500` | major | 改用 `.msg-ai` + `.ai-label`，ChatPanel.tsx#L216-L224 |
| 底部输入栏 | `.ask-input-bar`（fixed 底栏 + hint） | inline flex 无 fixed | major | 改用 `.ask-input-bar`，ChatPanel.tsx#L342-L373 |
| 空状态示例 | `.ask-empty` + `.example-list .btn-ghost` | `.card` + `.numeral` 自实现 | minor | 风格已对齐，可保留 |
| 反馈区 | `.feedback`（有用/无用 + low-confidence） | **完全缺失** | major | 补反馈按钮，ask.html#L80-L86 |
| 外部参考 | （mockup 无） | inline style 自实现 | minor | 已有设计无对应，可保留 |

### 5. ImportDialog（18 处）
对应 mockup：`design/mockup/_modal-import.html`

| 区块 | mockup 语义类 | React 现状 | 偏离等级 | 修复建议 |
|---|---|---|---|---|
| Modal 容器 | `.modal-overlay` + `.modal`（Modal.tsx 已封装） | **未复用 Modal 组件**，自写 inline overlay | critical | 改用 `<Modal>` 组件，ImportDialog.tsx#L113-L117 |
| Tab 导航 | `.nav-tab` + `.nav-tab-active` | 已使用 ✓ | — | 保持 |
| 错误提示 | （mockup 无专属类） | inline style | minor | 抽 ErrorInline 子组件 |
| 拖拽区 | （mockup 无） | inline style | minor | 可保留 |

### 6. RecipeEditorPanel（7 处）
对应 mockup：`design/mockup/recipe-editor.html`

| 区块 | mockup 语义类 | React 现状 | 偏离等级 | 修复建议 |
|---|---|---|---|---|
| 编辑器容器 | `.recipe-editor` | inline `.card p-6` | major | 改用 `.recipe-editor`，RecipeEditorPanel.tsx#L200 |
| 字段 | `.editor-field` + label | inline `<label>` + `.input` | major | 改用 `.editor-field`，RecipeEditorPanel.tsx#L210-L337 |
| 材料 chip | `.editor-ingredient-chip` | inline style | major | 改用语义类，RecipeEditorPanel.tsx#L299-L316 |
| 状态横幅 | `.editor-status-banner.draft/pending/published/rejected` | inline bannerStyle 对象 | major | 改用语义类，RecipeEditorPanel.tsx#L202-L207 |
| 顶部金箔卡 | `.gold-foil-card` + `.foil-title/.foil-quote/.foil-attribution` | **完全缺失** | critical | 补金箔英雄区，recipe-editor.html#L42-L46 |

### 7. TagPanel（11 处）
对应 mockup：`design/mockup/tags.html`

| 区块 | mockup 语义类 | React 现状 | 偏离等级 | 修复建议 |
|---|---|---|---|---|
| 8 色预设 | `.swatches` + `.swatch.selected`（酒红/暗金/酒绿/琥珀/靛蓝/莓红/橡木/墨黑） | 原生 `<input type="color">` + 10 色预设 | critical | 改用 8 色 `.swatch`，TagPanel.tsx#L12-L16 L86-L92 |
| 标签行 | `.tag-row` + `.tag-dot` + `.tag-name` + `.tag-count` | inline flex 列表 | major | 改用 `.tag-row` 类，TagPanel.tsx#L114-L125 |
| 关联数 | `.tag-count .num`（金色衬线大数字） | inline `text-xs` 灰色 | major | 改用 `.tag-count`，TagPanel.tsx#L120 |

### 8. PendingReviewPanel（11 处）
对应 mockup：`_components.css` `.lab-pending-queue` + `.pending-*`

| 区块 | mockup 语义类 | React 现状 | 偏离等级 | 修复建议 |
|---|---|---|---|---|
| 队列容器 | `.lab-pending-queue` | `.card p-4` 替代 | major | 改用 `.lab-pending-queue`，PendingReviewPanel.tsx#L175 |
| 待审项 | `.pending-item` + `.pending-title/.pending-meta/.pending-actions` | inline flex `<li>` | major | 改用 `.pending-item`，PendingReviewPanel.tsx#L267-L345 |
| 通过/驳回按钮 | `.btn-approve` + `.btn-reject` | `.btn-primary` + `.btn-danger` + inline padding | major | 改用 `.btn-approve/.btn-reject`，PendingReviewPanel.tsx#L326-L343 |

---

## 通用组件快速扫描

| 组件 | 偏离等级 | 说明 |
|---|---|---|
| AgeGate | minor | inline 玻璃态卡片合理（mockup `_modal-age-gate.html` 未读），但 7 处 style 可抽 GlassCard 组件复用 Login/ErrorBoundary |
| Login | minor | 同 AgeGate，7 处 inline 玻璃态可与 AgeGate 共用组件 |
| Modal | — | 正确使用 `.modal-overlay/.modal`，仅 2 处 maxWidth/footer inline ✓ |
| Toast | minor | 用 `.toast show` 类 + 8 处 inline 覆盖颜色，可改用 `.toast-*` 变体类 |
| Skeleton | — | 正确使用 `.skeleton` 类 ✓ |
| DocumentList | major | 11 处 inline；select 未用 `.select` 类；标签 chip 未用 `.tag` 类（用 inline backgroundColor） |
| CitationList | major | 14 处 inline；**未使用 `.citation-list/.citation-item/.cite-num/.cite-snippet`**，完全自定义实现。实现质量高（保留金箔质感）但偏离 mockup 结构，建议评估后二选一：回归语义类 或 把自定义实现沉淀为新类 `.citation-card-*` |
| ErrorBoundary | minor | 8 处 inline 玻璃态，可与 AgeGate/Login 共用 GlassCard |

---

## 修复优先级

### P0 critical（6 项，阻断核心视觉语言）
1. **LabPanel 材料 chip 分类色丢失**：4 色分类是实验室核心交互视觉，LabPanel.tsx#L220-L243
2. **ChatPanel 用户气泡颜色反了**：mockup brand-100 浅底深字，React brand-700 深底白字，ChatPanel.tsx#L208-L215
3. **ImportDialog 未复用 Modal 组件**：自写 overlay 绕过 `.modal-overlay`，ImportDialog.tsx#L113-L117
4. **LabPanel 顶部金箔卡缺失**：`.gold-foil-card` 英雄区是杂志感门面，LabPanel.tsx 顶部
5. **RecipeEditorPanel 金箔卡 + `.editor-*` 语义类全缺**：recipe-editor.html#L42-L46
6. **TagPanel 8 色酒类预设丢失**：原生 color picker + 10 色 generic 替代酒类主题 8 色，TagPanel.tsx#L12-L16

### P1 major（14 项，语义类未使用 + 结构偏离）
1. LabPanel `.material-selector/.selected-bar/.recipe-card/.match-badge/.ing/.substitute-suggest/.daily-recipe/.lab-sync-panel`（8 处）
2. RecipePanel `.select/.recipe-card/.recipe-thumb-placeholder/.variant-card`（4 处）
3. DocumentDetailPanel `.doc-layout/.toc-list/.chunk-num/.doc-content h2`（4 处）
4. ChatPanel `.msg-user/.msg-ai/.ask-input-bar` + 反馈区缺失（4 处）
5. DocumentDetailPanel 变体区 `.doc-variants/.variant-list` 缺失
6. PendingReviewPanel `.lab-pending-queue/.pending-item/.btn-approve/.btn-reject`（3 处）

### P2 minor（全局清扫，~8 项）
1. 全局 `var(--font-sans)` → `var(--font-ui)` 替换（30+ 处）
2. 抽 GlassCard 组件统一 AgeGate/Login/ErrorBoundary 玻璃态
3. Toast 变体类 `.toast-success/.toast-warning/.toast-danger`
4. CitationList 评估回归 `.citation-list` 或沉淀自定义类
5. 补 LabPanel 匹配按钮 `.match-btn.pulse` 动画
6. RecipePanel 补 `.source-tag.*` 来源色编码

### 修复后 inline style 预估
- P0+P1 完成后：~80 处（LabPanel 58→15，RecipePanel 18→8，ImportDialog 18→5，DocumentDetailPanel 16→6，ChatPanel 17→5，其余不变）
- P2 完成后：~50 处（达成 ≤60 目标）

### 建议执行顺序
1. 先做 P2.1 全局字体替换（1 处 sed，影响 30+ 处）
2. 再做 P0.3 ImportDialog 改用 Modal（最小改动，最大收益）
3. 集中攻坚 LabPanel（P0.1 + P0.4 + P1.1，占重灾区 58 处中的 40+ 处）
4. 其余 P1 按组件逐个清扫
