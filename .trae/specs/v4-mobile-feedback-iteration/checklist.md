# Checklist

## Task 0: 路线图状态更新
- [ ] product-iteration-roadmap/tasks.md 中 Task 9/10/11 标记为 `[x]` 并补充完成日期
- [ ] product-iteration-roadmap/tasks.md 中插入 V3.5 Obsidian vault 集成记录

## Task 16: 反馈机制完善
- [x] QueryLog 模型新增 feedback_comment(Text) + feedback_tag(str) 字段
- [x] 迁移 0011_add_feedback_fields.py 可正常执行
- [x] POST /api/feedback/{log_id} 支持 comment + tag 可选参数
- [x] GET /api/feedback/list 返回带评论的反馈列表，支持 tag 筛选
- [x] 非 admin 用户访问 /api/feedback/list 返回 403
- [x] ChatPanel 点击 👍/👎 后展开评论框+标签选择器
- [x] 标签枚举：inaccurate / not_found / wrong_citation / other
- [x] 评论限 500 字，支持空串
- [x] SettingsPanel 新增「意见反馈」tab，展示反馈列表
- [x] 后端测试覆盖：评论提交/标签筛选/权限控制/空评论
- [x] 前端测试覆盖：评论框展开/标签选择/提交回调/反馈列表渲染

## Task 12: 移动端响应式 ✅
- [x] 视口 < 768px 时顶部导航隐藏，底部 tab bar 显示
- [x] 视口 ≥ 768px 时顶部导航保持，底部 tab bar 隐藏
- [x] 底部 tab bar 包含 5 个 tab（首页/问答/配方/实验室/设置），图标+文字
- [x] ChatPanel 移动端输入框固定底部，历史消息区可滚动
- [x] LabPanel 材料选择器移动端横向滚动
- [x] RecipePanel 配方卡片移动端单列展示
- [x] 前端测试：mock matchMedia 验证 < 768px 底部 tab 渲染（4 个测试用例）

## Task 13: PWA 离线缓存 ✅
- [x] web/public/manifest.json 包含 name/icons/theme_color/display:standalone
- [x] Service Worker 注册成功（main.tsx 中 import.meta.env.PROD 时注册 /sw.js）
- [x] 配方详情页 stale-while-revalidate 缓存策略生效（sw.js CACHE_RECIPES）
- [x] 问答 API network-first 缓存策略生效（sw.js /api/ask 离线降级 503）
- [x] 离线时顶部显示 OfflineBanner「离线模式」提示
- [x] 离线时问答功能禁用并提示（SW 返回 503 JSON）
- [x] 前端测试：manifest.json 字段验证 + OfflineBanner 显示/隐藏（6 个测试）

## Task 14: 分享卡片 ✅
- [x] RecipePanel 配方详情页显示「分享」按钮
- [x] 点击分享后 Canvas 生成 PNG 图片（含配方名+材料+领域色背景+水印）
- [x] 移动端调用 Web Share API 原生分享面板
- [x] 桌面端提供「下载图片」降级按钮
- [x] 生成耗时 ≤2s（原生 Canvas，无外部库）
- [x] 前端测试：ShareCardButton 渲染 + Canvas 生成 + 分享调用 mock（5 个测试）

## 全局质量 ✅
- [x] 后端全量测试通过（pytest tests/test_kb）：1139 passed, 1 skipped
- [x] 前端全量测试通过（vitest run）：339 passed (22 files)
- [x] TypeScript 0 错误（tsc --noEmit）
- [x] Ruff 无新增警告（B008/noqa 历史遗留 132 个，本次未改 Python 代码无新增）
- [x] 质量分 > 95
