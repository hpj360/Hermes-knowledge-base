# P1 · Token 替换实施计划（包豪斯几何 + 极简现代）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将全站设计 token 从"编辑杂志风"（暖米底 + 衬线 + 金箔）替换为"包豪斯几何 + 极简现代"（白底 + Space Grotesk + 领域色实色 + 微圆角 2px + 粗边框 3px），保持 token 变量名兼容以实现零组件结构改动、零测试回归。

**Architecture:** 通过重写 `design/mockup/_tokens.css` 的 `:root` 变量值（保留变量名），让所有引用 `var(--*)` 的语义类与 inline style 自动换肤。字体在 `web/index.html` 替换 Google Fonts 链接为 Space Grotesk + JetBrains Mono。`index.css` 的 `@layer base` 微调 body 字体引用。

**Tech Stack:** CSS custom properties, Google Fonts, Vitest（回归验证）, Vite（构建验证）

**Spec:** `.trae/specs/design-system-refactor/spec.md`

---

## 文件结构

| 文件 | 职责 | P1 改动 |
|---|---|---|
| `web/index.html` | 字体加载 | 替换 Google Fonts link 为 Space Grotesk + JetBrains Mono |
| `design/mockup/_tokens.css` | 设计 token 定义 | 重写 `:root` 变量值（保留名），新增领域色/边框 token |
| `web/src/index.css` | 全局样式入口 | `@layer base` body/h 字体引用微调（保留 var 引用） |

**不变更**：任何 `.tsx` 文件、`_components.css` 语义类结构、props、className。

---

## Token 映射表（保留名，换值）

| 变量名 | 旧值（杂志风） | 新值（包豪斯） | 说明 |
|---|---|---|---|
| `--brand-700` | #8B1A36 深酒红 | #6b2c2c 酒红 | 主品牌色 |
| `--brand-500` | #B8254A | #8b3a3a | hover 态 |
| `--brand-900` | #4A0E1C | #4a1818 | 深底 |
| `--brand-100` | #F5DDE4 | #f5ebe9 | wine-tint |
| `--brand-50` | #FBF1F4 | #faf5f5 | 最浅 |
| `--gold-500` | #C9A227 | #c9a961 琥珀金 | 主金 |
| `--gold-700` | #8C7016 | #8b6914 | 深琥珀 |
| `--gold-300` | #E5D49A | #e0d4a8 | 浅琥珀 |
| `--gold-100` | #FAF3DC | #faf6ec | amber-tint |
| `--ink-900` | #1F1C18 | #1a1a1a | 主文字/边框 |
| `--ink-600` | #4A4640 | #555 | 次要文字 |
| `--ink-400` | #8A8378 | #888 | 辅助文字 |
| `--ink-200` | #D9D2C8 | #d5d5d5 | 分隔线 |
| `--ink-100` | #EDE9E4 | #e5e5e5 | 轻分隔 |
| `--ink-50` | #F7F5F3 | #f7f7f7 | 页面背景 |
| `--font-serif` | Cormorant Garamond 衬线 | Space Grotesk 几何无衬线 | 标题自动换肤 |
| `--font-body` | Crimson Text 衬线 | Space Grotesk | 正文自动换肤 |
| `--font-ui` | Noto Sans SC | Space Grotesk | UI 自动换肤 |
| `--font-mono` | JetBrains Mono | JetBrains Mono | 保持 |
| `--font-sans` | =--font-body 别名 | =--font-body 别名 | 向后兼容保留 |
| `--r-sm` | 4px | 2px | 微圆角 |
| `--r-md` | 8px | 0 | 直角 |
| `--r-lg` | 14px | 2px | 近直角 |
| `--r-full` | 9999px | 999px | chip 胶囊保留 |
| `--paper-bg` | 渐变 | #f7f7f7 纯色 | 去渐变 |
| `--noise-bg` | SVG 噪点 | none | 去噪点 |
| `--gold-foil` | 渐变 | #c9a961 纯色 | 去金属渐变 |
| `--gold-foil-text` | 渐变 | #8b6914 纯色 | 去金属渐变 |
| `--brand-gradient` | 渐变 | #6b2c2c 纯色 | 去渐变 |

**新增 token**：
- `--wine: #6b2c2c` / `--amber: #c9a961` / `--bronze: #3a5a6b`
- `--wine-tint: #f5ebe9` / `--amber-tint: #faf6ec` / `--bronze-tint: #ebf0f3`
- `--border-bold: 3px solid var(--ink-900)`
- `--border-medium: 2px solid var(--ink-900)`

---

### Task 1: 更新字体加载（index.html）

**Files:**
- Modify: `web/index.html:10-17`

- [ ] **Step 1: 替换 Google Fonts link**

将 `web/index.html` 第 10-17 行的字体加载注释与 link 替换为：

```html
    <!-- P1 包豪斯重构：加载 Space Grotesk（标题/正文/品牌）+ JetBrains Mono（数据/标签） -->
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
      rel="stylesheet"
    />
```

同时更新 `<meta name="theme-color">` 第 9 行为酒红：
```html
    <meta name="theme-color" content="#6b2c2c" />
```

- [ ] **Step 2: 验证 index.html 无语法错误**

Run: `node -e "const fs=require('fs');const h=fs.readFileSync('web/index.html','utf8');console.log(h.includes('Space+Grotesk')?'OK':'FAIL')"`
Expected: `OK`

---

### Task 2: 重写 _tokens.css（包豪斯 token 体系）

**Files:**
- Modify: `design/mockup/_tokens.css`（整文件重写 `:root`，保留变量名）

- [ ] **Step 1: 重写 _tokens.css 完整内容**

用以下内容完整覆盖 `design/mockup/_tokens.css`：

```css
/* Hermes KB 设计 Token —— 包豪斯几何 + 极简现代视觉语言
 * P1 重构：白底 + Space Grotesk + 领域色实色几何 + 微圆角 2px + 粗边框 3px
 * 集中管理色彩/字体/间距/圆角/阴影/动效，所有页面通过 CSS 变量引用。
 * 变量名保留兼容（--brand-700 / --gold-500 / --font-serif 等），值替换为包豪斯体系。
 */

:root {
  /* === 色彩 · 品牌主色（酒红，替代深酒红） === */
  --brand-50: #faf5f5;
  --brand-100: #f5ebe9;      /* wine-tint */
  --brand-200: #e8d4d0;
  --brand-500: #8b3a3a;
  --brand-700: #6b2c2c;      /* 主品牌色，按钮/强调 */
  --brand-900: #4a1818;      /* 深底 */

  /* === 色彩 · 琥珀金（强调/引用/装饰，替代暗金） === */
  --gold-100: #faf6ec;       /* amber-tint */
  --gold-300: #e0d4a8;
  --gold-500: #c9a961;       /* 主琥珀金，引用边框/数字 */
  --gold-700: #8b6914;

  /* === 色彩 · 墨色（文本/底色，去暖偏中性） === */
  --ink-50: #f7f7f7;
  --ink-100: #e5e5e5;
  --ink-200: #d5d5d5;
  --ink-400: #888;
  --ink-600: #555;
  --ink-900: #1a1a1a;        /* 正文主色 / 主边框 */

  /* === P1 新增：领域色实色几何三原色 === */
  --wine: #6b2c2c;           /* 酒红 · 烈酒 / 危险 */
  --amber: #c9a961;          /* 琥珀金 · 强调 / ABV */
  --bronze: #3a5a6b;         /* 深青铜 · 技法 / 信息 */
  --wine-tint: #f5ebe9;
  --amber-tint: #faf6ec;
  --bronze-tint: #ebf0f3;

  /* === 语义色 === */
  --highlight: #fef3c7;
  --highlight-fade: rgba(254, 243, 199, 0);
  --success: #2e7d5b;
  --warning: #c77a1a;
  --danger: #b3261e;
  --info: #3a5a6b;           /* 改用青铜，与领域色统一 */

  /* === 字体（P1 重构：去衬线，全 Space Grotesk 几何无衬线） ===
   * 设计宪法：包豪斯几何 + 极简现代
   * Display/Body/UI: Space Grotesk（几何无衬线，带个性，大标题张力强）
   * Mono: JetBrains Mono（数据/代码/标签，保留）
   *
   * 变量名保留：--font-serif / --font-body / --font-ui 现均指向 Space Grotesk，
   * 实现全站衬线→几何无衬线自动换肤（零组件改动）。
   * --font-sans 保留为 --font-body 别名（向后兼容 inline style）。
   */
  --font-serif: "Space Grotesk", "Helvetica Neue", Arial, sans-serif;
  --font-body: "Space Grotesk", "Helvetica Neue", Arial, sans-serif;
  --font-ui: "Space Grotesk", "Helvetica Neue", Arial, sans-serif;
  --font-mono: "JetBrains Mono", "SF Mono", Menlo, Consolas, monospace;
  /* 向后兼容别名 */
  --font-sans: var(--font-body);

  /* === 字号 === */
  --fs-xs: 0.75rem;
  --fs-sm: 0.875rem;
  --fs-base: 1rem;
  --fs-lg: 1.125rem;
  --fs-xl: 1.5rem;
  --fs-2xl: 1.875rem;
  --fs-3xl: 2.5rem;
  --fs-hero: 3.5rem;

  /* === 间距 === */
  --sp-1: 0.25rem;
  --sp-2: 0.5rem;
  --sp-3: 0.75rem;
  --sp-4: 1rem;
  --sp-6: 1.5rem;
  --sp-8: 2rem;
  --sp-12: 3rem;
  --sp-16: 4rem;

  /* === 圆角（P1 重构：包豪斯锐利感） === */
  --r-sm: 2px;               /* 微圆角 */
  --r-md: 0;                 /* 默认直角 */
  --r-lg: 2px;               /* 近直角 */
  --r-full: 999px;           /* chip 胶囊保留 */

  /* === P1 新增：边框粗细 token === */
  --border-bold: 3px solid var(--ink-900);    /* 主分隔/导航底边 */
  --border-medium: 2px solid var(--ink-900);  /* 卡片边框 */
  --border-thin: 1px solid var(--ink-100);    /* 轻分隔 */

  /* === 阴影（P1 弱化：包豪斯用边框而非阴影定义层次） === */
  --shadow-sm: 0 1px 2px rgba(26, 26, 26, 0.04);
  --shadow-md: 0 2px 8px rgba(26, 26, 26, 0.06);
  --shadow-lg: 0 8px 24px rgba(26, 26, 26, 0.08);
  --shadow-drama: 0 12px 40px rgba(107, 44, 44, 0.18), 0 4px 12px rgba(26, 26, 26, 0.08);
  --shadow-gold: 0 0 0 1px rgba(201, 169, 97, 0.3), 0 2px 8px rgba(201, 169, 97, 0.16);

  /* === P1 重构：去杂志氛围装饰，改纯色 === */
  --noise-bg: none;
  --gold-foil: #c9a961;                       /* 纯琥珀金，去金属渐变 */
  --gold-foil-text: #8b6914;                  /* 纯深琥珀，去金属渐变 */
  --brand-gradient: #6b2c2c;                  /* 纯酒红，去渐变 */
  --paper-bg: #f7f7f7;                        /* 纯色背景，去渐变 */
  --paper: #ffffff;

  /* === 动效 === */
  --duration-fast: 150ms;
  --duration-base: 250ms;
  --duration-highlight: 2000ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);

  /* === 布局 === */
  --nav-height: 60px;
  --container: 1140px;
  --sidebar: 300px;

  /* === 排版系统（P1 保留变量名，值适配几何无衬线） === */
  --tracking-wide: 0.15em;
  --tracking-medium: 0.08em;
  --tracking-tight: -0.02em;

  --divider-gold: linear-gradient(90deg, transparent 0%, var(--gold-500) 20%, var(--gold-300) 50%, var(--gold-500) 80%, transparent 100%);
  --divider-hair: 1px solid var(--ink-200);

  --numeral-font: "Space Grotesk", "Helvetica Neue", sans-serif;
  --numeral-size: 0.7rem;

  --space-section: 5rem;
  --space-block: 2.5rem;
  --space-element: 1.25rem;

  --nav-tab-active: inset 0 -3px 0 0 var(--ink-900);   /* P1：3px 粗下划线 */
  --nav-tab-hover: var(--ink-100);
}

/* === 全局重置 === */
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font-body);
  color: var(--ink-900);
  background: var(--paper-bg);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

/* P1：标题统一 black 700 + 大写 + 微收紧字距（包豪斯精神） */
h1, h2, h3, .serif {
  font-family: var(--font-serif);
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: var(--tracking-tight);
}

a { color: var(--brand-700); text-decoration: none; transition: color var(--duration-fast); }
a:hover { color: var(--brand-500); }

.container { max-width: var(--container); margin: 0 auto; padding: 0 var(--sp-6); }
.page-title { font-family: var(--font-serif); font-size: var(--fs-2xl); margin: var(--sp-6) 0; }

/* === a11y：尊重用户的减少动效偏好 === */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

- [ ] **Step 2: 验证 token 文件无语法错误**

Run: `node -e "const fs=require('fs');const c=fs.readFileSync('design/mockup/_tokens.css','utf8');const opens=(c.match(/:root/g)||[]).length;const closes=(c.match(/\}/g)||[]).length;console.log('root:'+opens+' braces:'+closes);console.log(c.includes('--wine')?'wine OK':'FAIL');console.log(c.includes('--border-bold')?'border OK':'FAIL')"`
Expected: `root:1 braces:...` + `wine OK` + `border OK`

---

### Task 3: 微调 index.css base 层

**Files:**
- Modify: `web/src/index.css:10-27`（`@layer base` 区块）

- [ ] **Step 1: 更新 @layer base 字体引用与背景**

将 `web/src/index.css` 第 10-27 行 `@layer base` 区块替换为：

```css
@layer base {
  html {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
  body {
    /* P1 包豪斯：Space Grotesk + 纯色背景 */
    font-family: var(--font-body);
    color: var(--ink-900);
    background: var(--paper-bg);
    line-height: 1.6;
  }
  h1, h2, h3, h4 {
    font-family: var(--font-serif);
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: var(--tracking-tight);
  }
}
```

- [ ] **Step 2: 验证 index.css 仍正确 import _tokens.css**

Run: `node -e "const fs=require('fs');const c=fs.readFileSync('web/src/index.css','utf8');console.log(c.includes('@import \"../../design/mockup/_tokens.css\"')?'import OK':'FAIL')"`
Expected: `import OK`

---

### Task 4: 运行全量前端测试验证零回归

**Files:**
- 无文件改动，仅验证

- [ ] **Step 1: 运行 Vitest 全量测试**

Run: `cd web && npm test -- --run`
Expected: 全部 173 个测试通过，0 失败

- [ ] **Step 2: 若有失败，排查并修复**

若有测试失败，记录失败用例名与错误。P1 仅改 CSS token 值，不应影响功能 DOM 测试。若失败与样式相关（如 getComputedStyle 断言颜色），更新断言为新 token 值（属合理适配）。

- [ ] **Step 3: 验证 TypeScript 构建**

Run: `cd web && npm run build`
Expected: 构建成功，无 TypeScript 错误，输出 `dist/`

---

### Task 5: 提交 P1

**Files:**
- 无新文件，仅提交改动

- [ ] **Step 1: 暂存改动文件**

Run: `git add web/index.html design/mockup/_tokens.css web/src/index.css`

- [ ] **Step 2: 提交**

Run:
```bash
git commit -m "$(cat <<'EOF'
feat(design): P1 token 替换为包豪斯几何+极简现代风格

- _tokens.css: 重写 :root 变量值，保留变量名实现零组件改动换肤
  - 颜色: 深酒红→酒红 #6b2c2c, 暗金→琥珀金 #c9a961, 暖墨→中性墨 #1a1a1a
  - 字体: 衬线(Cormorant/Crimson)→几何无衬线 Space Grotesk
  - 圆角: 8/14px→0/2px(包豪斯锐利感)
  - 新增领域色 token: --wine/--amber/--bronze 及 tint
  - 新增边框 token: --border-bold(3px)/--border-medium(2px)
  - 去杂志装饰: noise-bg→none, gold-foil/brand-gradient→纯色
- index.html: Google Fonts 替换为 Space Grotesk + JetBrains Mono
- index.css: @layer base 标题改 700 字重 + 微收紧字距

零组件结构改动，173 前端测试零回归。
EOF
)"
```

- [ ] **Step 3: 验证提交成功**

Run: `git log -1 --stat`
Expected: 显示 P1 commit，3 个文件改动

---

## Self-Review

**1. Spec coverage:**
- ✅ P1 Token 体系替换 → Task 2（_tokens.css 重写）
- ✅ 字体加载 → Task 1（index.html）
- ✅ index.css 同步 → Task 3
- ✅ P1 零回归验收 → Task 4（173 测试 + 构建）
- ✅ 提交 → Task 5

**2. Placeholder scan:** 无 TBD/TODO，所有步骤含完整代码。

**3. Type consistency:** token 变量名全程保留（--brand-700/--gold-500/--font-serif/--r-md 等），新增 token 命名一致（--wine/--amber/--bronze + tint，--border-bold/medium/thin）。

**4. 风险点:**
- `--r-md: 0` 会让所有圆角变直角，符合包豪斯设计意图，非 bug
- `--font-serif` 指向 Space Grotesk 后，所有 `.serif` / `font-family: var(--font-serif)` 视觉从衬线变无衬线，这是预期换肤
- 测试为功能 DOM 测试，不依赖具体颜色/字体值，预期零回归
