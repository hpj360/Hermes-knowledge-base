# Tasks

## V1.0「可信」— 知识可信度攻坚（2026-08，M1 里程碑）

**目标**：recall_rate 从 5% 提升至 ≥40%，让问答值得信任

**实际成果**：recall_rate 提升至 72.9%（远超目标），keyword_rate 提升至 80.7%

- [x] Task 1: Embedding Provider 升级 ✅ 2026-07-29
  - [x] SubTask 1.1: 验证 BAAI/bge-small-zh-v1.5 本地部署可行性（GPU/CPU 性能基准）
  - [x] SubTask 1.2: 验证 OpenAI text-embedding-3-small API 效果与成本
  - [x] SubTask 1.3: 实现 embedding 迁移脚本（重新生成所有文档 chunk 的向量）— `scripts/reindex_embeddings.py`
  - [x] SubTask 1.4: 配置切换开关（KB_EMBEDDING_PROVIDER=openai/bge/hash）
  - [x] SubTask 1.5: 迁移后运行评估管线，记录 recall_rate 变化（5% → 10.7%）
  - [x] SubTask 1.6: 百科种子数据导入 — 执行 `seed_encyclopedia()` 将 `src/hermes_kb/seed.py` 中的百科文档（金酒/威士忌/伏特加等）导入数据库，补充知识底座（spec 4.1 关键举措）

- [x] Task 2: 查询改写与 HyDE ✅ 2026-07-29
  - [x] SubTask 2.1: 启用 query_rewrite（config 已有 KB_QUERY_REWRITE=true，验证实际效果）
  - [x] SubTask 2.2: 实现 HyDE 假设文档生成（LLM 生成假设答案→检索→真实答案）— `src/hermes_kb/hyde.py`
  - [x] SubTask 2.3: HyDE 效果评估（对比开/关的 recall_rate 差异：10.7% → 15.7%）
  - [x] SubTask 2.4: 配置 HyDE 开关（KB_HYDE=true/false）

- [x] Task 3: 分片策略调优 ✅ 2026-07-29
  - [x] SubTask 3.1: 分析当前 chunk_size=500/overlap=80 的分片质量
  - [x] SubTask 3.2: 针对酒类知识（配方/百科/品鉴笔记）设计差异化分片策略
  - [x] SubTask 3.3: 实现按文档类型动态调整 chunk_size — `src/hermes_kb/rag.py::_get_chunk_strategy`
  - [x] SubTask 3.4: 重新分片后评估 recall_rate（15.7% → 72.9%）
  - [x] SubTask 3.5: 补全单元测试与集成测试 — `tests/test_kb/test_rag.py`（11 个新测试）

- [x] Task 4: RAG 评估自动化管线 ✅ 2026-07-29
  - [x] SubTask 4.1: 创建 `scripts/run_eval.py` 评估脚本（读取 eval_set.jsonl → 批量检索 → 输出指标）
  - [x] SubTask 4.2: 支持对比基线（读取 baseline.json，回归时非零退出）
  - [x] SubTask 4.3: 集成到 CI（可选：PR 时自动运行评估子集）
  - [x] SubTask 4.4: 输出评估报告（JSON + Markdown 可读格式）— `tests/eval/eval_report.{json,md}`

## V2.0「可用」— 实践闭环深化（2026-09，M2 里程碑）

**目标**：配方图片覆盖率 ≥80%，≥30% 活跃配方有评分，WARPM ≥5

- [ ] Task 5: 配方图片接入
  - [ ] SubTask 5.1: 后端 — 配方列表/详情 API 返回 image_url 字段（TheCocktailDB 已有数据）
  - [ ] SubTask 5.2: 前端 — RecipePanel 配方卡片展示缩略图
  - [ ] SubTask 5.3: 前端 — 无图片时展示领域色（wine/amber/bronze）占位符
  - [ ] SubTask 5.4: 前端 — 配方详情页展示大图 + 来源标注
  - [ ] SubTask 5.5: 补充 IBA/seed 配方图片（手动收集或 Unsplash API）

- [ ] Task 6: 配方评分与笔记
  - [ ] SubTask 6.1: 后端 — 新增 ratings 表（user_id, doc_id, score, comment, created_at）
  - [ ] SubTask 6.2: 后端 — POST /api/lab/recipes/{doc_id}/rate 端点
  - [ ] SubTask 6.3: 后端 — GET /api/lab/recipes/{doc_id}/rating 返回平均分+人数+用户笔记列表
  - [ ] SubTask 6.4: 前端 — 星级评分组件（1-5 星可交互）
  - [ ] SubTask 6.5: 前端 — 调酒笔记输入与展示

- [ ] Task 7: SettingsPanel 功能补全
  - [ ] SubTask 7.1: 前端 — 数据导出子模块接入 GET /api/export/all.json（下载 JSON）
  - [ ] SubTask 7.2: 前端 — 数据导入子模块接入 POST /api/export/import（上传 JSON 恢复）
  - [ ] SubTask 7.3: 前端 — 审计日志子模块接入 GET /api/audit（展示操作日志列表）
  - [ ] SubTask 7.4: 补全 SettingsPanel.test.tsx 测试

- [ ] Task 8: HistoryPanel 时间筛选 + 季节性推荐
  - [ ] SubTask 8.1: 前端 — HistoryPanel 添加时间范围筛选器（近 7 天/30 天/全部/自定义）
  - [ ] SubTask 8.2: 后端 — /api/history 支持 start_date/end_date 参数
  - [ ] SubTask 8.3: 前端 — DashboardPanel 季节性推荐区（基于 season 字段）
  - [ ] SubTask 8.4: 补全 HistoryPanel.test.tsx 测试

## V3.0「可协作」— 从个人到社群（2026-10，M3 里程碑）

**目标**：≥3 个团队试用，每个团队 ≥3 人活跃

- [ ] Task 9: 用户数据模型
  - [ ] SubTask 9.1: 后端 — 新增 users 表（id, username, password_hash, role, created_at）
  - [ ] SubTask 9.2: 后端 — Alembic migration 脚本
  - [ ] SubTask 9.3: 后端 — 密码哈希（bcrypt/argon2）
  - [ ] SubTask 9.4: 后端 — 现有 admin 用户迁移为 owner 角色

- [ ] Task 10: 认证流程升级
  - [ ] SubTask 10.1: 后端 — POST /api/auth/register（邀请码注册）
  - [ ] SubTask 10.2: 后端 — POST /api/auth/invite（owner 生成邀请链接）
  - [ ] SubTask 10.3: 后端 — 权限中间件 require_owner/require_member/require_viewer
  - [ ] SubTask 10.4: 前端 — 注册页面
  - [ ] SubTask 10.5: 前端 — 登录页支持用户名+密码（替代单一密码）
  - [ ] SubTask 10.6: Feature flag 控制（KB_MULTIUSER=true/false，默认关闭）

- [ ] Task 11: UGC 审核流完善
  - [ ] SubTask 11.1: 后端 — 配方 draft→pending→published/rejected 状态机完善
  - [ ] SubTask 11.2: 前端 — PendingReviewPanel 接入多审核人
  - [ ] SubTask 11.3: 后端 — 审核通知（站内消息或邮件）
  - [ ] SubTask 11.4: 前端 — 个人配方库 vs 公共配方库分离

## V4.0「随身」— 移动端适配与 PWA（2026-11，M4 里程碑）

**目标**：移动端 Lighthouse ≥80，分享卡片生成 ≤2s

- [ ] Task 12: 响应式布局
  - [ ] SubTask 12.1: 前端 — 导航栏移动端折叠为底部 tab bar
  - [ ] SubTask 12.2: 前端 — 配方卡片网格响应式（桌面 3 列/平板 2 列/手机 1 列）
  - [ ] SubTask 12.3: 前端 — 问答面板移动端优化（输入框固定底部）
  - [ ] SubTask 12.4: 前端 — 实验室材料选择器移动端横向滚动

- [ ] Task 13: PWA 离线缓存
  - [ ] SubTask 13.1: 前端 — manifest.json 配置
  - [ ] SubTask 13.2: 前端 — Service Worker 缓存已访问配方
  - [ ] SubTask 13.3: 前端 — 离线提示与降级 UI

- [ ] Task 14: 分享卡片
  - [ ] SubTask 14.1: 前端 — 配方一键生成分享图片（Canvas/SVG → PNG）
  - [ ] SubTask 14.2: 前端 — 分享卡片包含配方名+材料+领域色背景

## V4.1「复盘」— 年终版（2026-12，M5 里程碑）

- [ ] Task 15: 全年数据回顾
  - [ ] SubTask 15.1: 后端 — 个人调酒统计 API（调酒次数、最爱配方、评分历史）
  - [ ] SubTask 15.2: 前端 — 年度调酒报告页面
  - [ ] SubTask 15.3: 性能优化（问答延迟 ≤2s）

## 通用：用户反馈收集机制（贯穿全周期）

- [ ] Task 16: 反馈机制建设
  - [ ] SubTask 16.1: 前端 — 问答反馈按钮增加可选评论框 + 问题标签
  - [ ] SubTask 16.2: 后端 — feedback 表增加 comment + tag 字段
  - [ ] SubTask 16.3: 前端 — SettingsPanel 新增「意见反馈」入口
  - [ ] SubTask 16.4: 后端 — 反馈汇总 API（admin 可查看反馈列表）
  - [ ] SubTask 16.5: 数据反馈 — 埋点（配方详情停留时长、材料匹配使用率、UGC 完成率）

# Task Dependencies
- [Task 2/3] 依赖 [Task 1]（embedding 升级后再优化改写/分片）
- [Task 4] 依赖 [Task 1/2/3]（评估管线验证所有优化效果）
- [Task 5/6] 可并行（图片与评分独立）
- [Task 7/8] 可并行（Settings 与 History 独立）
- [Task 9/10] 串行（模型→认证流程）
- [Task 11] 依赖 [Task 9/10]（UGC 审核需要多用户）
- [Task 12/13/14] 可并行（移动端各子模块独立）
- [Task 15] 依赖 [Task 6]（评分数据支撑年度报告）
- [Task 16] 贯穿全周期，无前置依赖

# 发布策略
- V1.0「可信」(M1): 内部验证版 — RAG 质量提升，不对外发布
- V2.0「可用」(M2): 公测版 — 内容深度+运营工具，邀请 5 名画像 A 种子用户
- V3.0「可协作」(M3): 正式版 — 多用户支持，公开发布，目标 ≥3 个团队试用
- V4.0「随身」(M4): 增强版 — 移动端+PWA，移动端用户占比 ≥30%
- V4.1「复盘」(M5): 年终版 — 数据回顾 + 体验打磨
