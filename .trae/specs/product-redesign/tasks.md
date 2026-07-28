# Tasks

## 阶段一：产品定位与信息架构设计

- [x] Task 1: 完成产品定位重定义文档
  - [x] SubTask 1.1: 撰写统一产品定位叙事（"个人酒类知识工作台"三阶价值）
  - [x] SubTask 1.2: 整合目标用户画像（合并囤积者+创作者为主用户）
  - [x] SubTask 1.3: 定义三阶价值主张（知识可信→实践可用→持续成长）
  - [x] SubTask 1.4: 输出竞品分析对比矩阵（vs ChatGPT/Notion AI/Dify/酒类百科）

- [x] Task 2: 设计信息架构与导航重组方案
  - [x] SubTask 2.1: 定义 3 大区域 + 首页的导航分组结构
  - [x] SubTask 2.2: 明确 5 个模块的功能边界矩阵（问答/文档/配方/实验室/设置）
  - [x] SubTask 2.3: 设计用户主流程图（冷启动/知识沉淀/调酒实践/历史回顾）
  - [x] SubTask 2.4: 定义各模块入口与跳转关系图

## 阶段二：前端 IA 重构实施

- [x] Task 3: 重构 App.tsx 导航结构为分组导航
  - [x] SubTask 3.1: 更新 NAV_ITEMS 为分组结构（首页/知识区/调酒区/设置）
  - [x] SubTask 3.2: 实现导航分组视觉分隔（知识区与调酒区之间分隔符）
  - [x] SubTask 3.3: 默认路由从 /chat 改为 /（首页）
  - [x] SubTask 3.4: 移除顶部全局"导入"按钮，改为各 tab 内上下文导入
  - [x] SubTask 3.5: 更新 App.test.tsx 导航断言（分组结构 + 新路由）

- [x] Task 4: 新增首页 DashboardPanel
  - [x] SubTask 4.1: 创建 DashboardPanel.tsx 组件骨架
  - [x] SubTask 4.2: 实现 Hero 区（价值主张 + 三个核心能力卡片）
  - [x] SubTask 4.3: 实现飞轮健康度概览（4 指标卡，复用 /api/stats 数据）
  - [x] SubTask 4.4: 实现快捷操作区（开始提问/导入文档/浏览配方 3 按钮）
  - [x] SubTask 4.5: 实现空库引导卡片（种子导入引导）
  - [x] SubTask 4.6: 新增 DashboardPanel.test.tsx 单测（11 tests）

- [x] Task 5: 新增问答历史 HistoryPanel
  - [x] SubTask 5.1: 创建 HistoryPanel.tsx 组件（列表 + 搜索）
  - [x] SubTask 5.2: 接入 /api/history 端点
  - [x] SubTask 5.3: 在 ChatPanel 添加"历史"入口（tab 切换）
  - [x] SubTask 5.4: 实现关键词高亮（<mark> 标签）
  - [x] SubTask 5.5: 新增 HistoryPanel.test.tsx 单测（9 tests）

- [x] Task 6: 新增设置中心 SettingsPanel
  - [x] SubTask 6.1: 创建 SettingsPanel.tsx 容器组件（子模块 tab 切换）
  - [x] SubTask 6.2: 迁移 TagPanel 为设置子模块
  - [x] SubTask 6.3: 新增数据导出子模块（ComingSoon 占位，后端 API 已存在待接入）
  - [x] SubTask 6.4: 新增审计日志子模块（ComingSoon 占位，后端 migration 已存在待接入）
  - [x] SubTask 6.5: 更新路由 /admin → /settings
  - [x] SubTask 6.6: 新增 SettingsPanel.test.tsx 单测（3 tests）

## 阶段三：体验流程优化与验证

- [x] Task 7: 优化冷启动引导链
  - [x] SubTask 7.1: 登录后默认跳转首页（非问答页）
  - [x] SubTask 7.2: 首页空库状态展示种子导入引导（L1→L4 链）
  - [x] SubTask 7.3: 首次问答完成后引导溯源（L3 引导提示 + localStorage 记忆）
  - [x] SubTask 7.4: 补全冷启动引导链测试（3 tests）

- [x] Task 8: 实现上下文感知导入
  - [x] SubTask 8.1: 文档 tab 内添加"导入文档"操作按钮
  - [x] SubTask 8.2: 配方 tab 内"创作配方"按钮已存在（验证）
  - [x] SubTask 8.3: 实验室 tab 内添加"创作配方"出口
  - [x] SubTask 8.4: 更新相关测试断言（2 tests）

- [x] Task 9: 全量测试与构建验证
  - [x] SubTask 9.1: 运行全量 vitest，确保零回归（243 tests passed）
  - [x] SubTask 9.2: 运行 TypeScript 构建（tsc --noEmit 零错误）
  - [x] SubTask 9.3: 验证 App.tsx 覆盖率 ≥ 95%（98.09%）
  - [ ] SubTask 9.4: 手动验证 5 大主流程（冷启动/问答/导入/配方/设置）— 需用户手动验证

- [ ] Task 10: 提交代码与文档
  - [ ] SubTask 10.1: 提交阶段二前端 IA 重构
  - [ ] SubTask 10.2: 提交阶段三体验优化
  - [ ] SubTask 10.3: 更新产品文档（docs/product/05-产品定位 v2.0）

# Task Dependencies
- [Task 3] 依赖 [Task 2]（导航结构方案先行）
- [Task 4/5/6] 依赖 [Task 3]（路由结构就绪后新增面板）
- [Task 7/8] 依赖 [Task 4/5/6]（面板就绪后优化流程）
- [Task 9] 依赖 [Task 3-8]（全量验证）
- [Task 10] 依赖 [Task 9]（验证通过后提交）
- [Task 4/5/6] 可并行（独立面板）

# 已知待办（后续迭代）
- HistoryPanel 时间范围筛选（当前仅关键词搜索）
- SettingsPanel 数据导出子模块接入 /api/export（后端 API 已存在）
- SettingsPanel 审计日志子模块接入 /api/audit（后端 migration 已存在）
