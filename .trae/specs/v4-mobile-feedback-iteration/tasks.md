# Tasks

## 前置：更新路线图状态

- [x] Task 0: 更新 product-iteration-roadmap/tasks.md，标记 Task 9-11 为完成，补充 V4 Obsidian 集成记录
  - [x] SubTask 0.1: 将 Task 9/10/11 的 `[ ]` 改为 `[x]` 并补充完成日期
  - [x] SubTask 0.2: 在 V4.0 章节前插入「V3.5 Obsidian vault 集成」记录

## Task 16: 反馈机制完善

**目标**：从 👍/👎 升级为结构化反馈，支持评论+标签+汇总

- [x] Task 16: 反馈机制完善
  - [x] SubTask 16.1: 后端 — QueryLog 新增 `feedback_comment`(Text) + `feedback_tag`(str) 字段 + 迁移 0011
  - [x] SubTask 16.2: 后端 — `/api/feedback/{log_id}` 端点升级，FeedbackReq 增加 comment/tag 可选字段
  - [x] SubTask 16.3: 后端 — 新增 `GET /api/feedback/list` 汇总端点（admin 可查，支持 tag 筛选+分页）
  - [x] SubTask 16.4: 后端测试 — test_feedback.py 覆盖评论/标签/汇总/权限
  - [x] SubTask 16.5: 前端 — ChatPanel 反馈区增加评论框+标签选择器（点击 👍/👎 后展开）
  - [x] SubTask 16.6: 前端 — SettingsPanel 新增「意见反馈」tab（反馈列表+标签筛选）
  - [x] SubTask 16.7: 前端测试 — ChatPanel 反馈组件 + SettingsPanel 反馈列表测试

## Task 12: 移动端响应式 ✅ 2026-07-31

**目标**：移动端（< 768px）核心流程可用，导航折叠为底部 tab bar

**实际成果**：BottomTabBar.tsx + App.tsx 响应式导航 + ChatPanel/LabPanel/RecipePanel 移动端适配 + 4 个响应式测试

- [x] Task 12: 移动端响应式
  - [x] SubTask 12.1: 前端 — App.tsx 导航响应式（≥768px 顶部水平 tab / <768px 底部 tab bar 图标+文字）
  - [x] SubTask 12.2: 前端 — 底部 tab bar 组件（BottomTabBar.tsx，5 个 tab：首页/问答/配方/实验室/设置）
  - [x] SubTask 12.3: 前端 — ChatPanel 移动端优化（已应用响应式类 md:/sm:）
  - [x] SubTask 12.4: 前端 — LabPanel 材料选择器移动端横向滚动（已应用响应式类）
  - [x] SubTask 12.5: 前端 — RecipePanel/DocumentDetail 移动端单列阅读模式（已应用响应式网格类）
  - [x] SubTask 12.6: 前端测试 — App.test.tsx 新增 4 个响应式测试（mock matchMedia 验证 < 768px 底部 tab 渲染/5 个 tab/桌面顶部 nav/点击导航）

## Task 13: PWA 离线缓存 ✅ 2026-07-31

**目标**：可安装到桌面，离线可查已缓存配方

**实际成果**：手写原生 SW（无新依赖）+ manifest.json + OfflineBanner + 6 个测试（manifest 3 + OfflineBanner 3），完整套件 339 测试通过

- [x] Task 13: PWA 离线缓存
  - [x] SubTask 13.1: 前端 — `web/public/manifest.json` 配置（name/icons/theme_color/display:standalone）
  - [x] SubTask 13.2: 前端 — Service Worker 注册（手写 sw.js，无 vite-plugin-pwa 依赖）
  - [x] SubTask 13.3: 前端 — 缓存策略：配方详情 stale-while-revalidate / 问答 API network-first / 静态资源 cache-first
  - [x] SubTask 13.4: 前端 — 离线提示 banner（OfflineBanner.tsx，监听 online/offline 事件）
  - [x] SubTask 13.5: 前端测试 — manifest.json 字段验证 + 离线 banner 显示/隐藏测试（6 个新测试）

## Task 14: 分享卡片 ✅ 2026-07-31

**目标**：配方一键生成分享图片，≤2s

**实际成果**：ShareCardButton + 原生 Canvas 生成 PNG + Web Share API + 5 个测试，RecipePanel 8 个回归测试通过

- [x] Task 14: 分享卡片
  - [x] SubTask 14.1: 前端 — ShareCardButton.tsx 组件（配方详情页「分享」按钮）
  - [x] SubTask 14.2: 前端 — Canvas 生成分享图片（配方名+材料+领域色背景+Hermes 水印）
  - [x] SubTask 14.3: 前端 — Web Share API 调用（移动端）+ 下载 PNG 降级（桌面端）
  - [x] SubTask 14.4: 前端测试 — ShareCardButton 渲染 + Canvas 生成 + 分享调用测试（5 个新测试）

## Task Dependencies

- [Task 16] 无前置依赖，可独立启动
- [Task 12] 无前置依赖，可独立启动
- [Task 13] 依赖 [Task 12]（PWA 需要移动端布局就绪）
- [Task 14] 无前置依赖，可独立启动
- [Task 16] 与 [Task 12/14] 可并行
- [Task 13] 与 [Task 14] 可并行（13 依赖 12 完成后启动）

## 并行执行策略

```
Phase 1（并行）:
  ├─ Task 16: 反馈机制完善（后端→前端→测试）
  ├─ Task 12: 移动端响应式（导航→面板→测试）
  └─ Task 14: 分享卡片（组件→Canvas→测试）

Phase 2（Task 12 完成后）:
  └─ Task 13: PWA 离线缓存（manifest→SW→离线UI→测试）
```

## 发布策略

- V4.0「随身」内测版：Task 12+14 完成后，邀请 3 名画像 A 用户移动端体验
- V4.0「随身」公测版：Task 13+16 完成后，公开发布
- 验收标准：移动端 Lighthouse ≥80，分享卡片 ≤2s，反馈提交成功率 ≥99%
