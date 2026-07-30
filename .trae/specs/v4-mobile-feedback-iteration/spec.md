# V4.0「随身」+ 反馈机制完善 Spec

## Why

V1-V3 + Obsidian 集成已完成「可信→可用→可协作→可连接」四个维度，但产品仍局限于桌面端。画像 A（进阶爱好者）70% 使用手机，调酒时手边没有电脑是 P3 痛点。同时反馈机制仅有 👍/👎，无法收集结构化用户反馈来指导后续优化。

本迭代解决两个问题：
1. **移动端可用**：让产品从"坐在电脑前用"变成"调酒时用"
2. **反馈闭环**：从 👍/👎 升级为结构化反馈，为 V4.1 年终复盘提供数据基础

## What Changes

### 反馈机制完善（Task 16）
- QueryLog 新增 `feedback_comment` + `feedback_tag` 字段
- `/api/feedback/{log_id}` 端点支持提交评论+标签
- 前端问答反馈区增加评论框+问题标签选择器
- SettingsPanel 新增「意见反馈」入口（查看历史反馈）
- 后端新增 `/api/feedback/list` 汇总端点（admin 可查）

### 移动端响应式（Task 12）
- 导航栏：桌面水平 tab → 移动端底部 tab bar（< 768px）
- 配方卡片：桌面 3 列 → 平板 2 列 → 手机 1 列（已有部分，补全）
- 问答面板：移动端输入框固定底部 + 历史消息全宽
- 实验室材料选择器：移动端横向滚动 chip
- 文档详情页：移动端单列阅读模式

### PWA 离线缓存（Task 13）
- `manifest.json` 配置（name/icons/theme_color/display standalone）
- Service Worker 缓存策略（配方详情 stale-while-revalidate，问答 API network-first）
- 离线提示 UI（顶部 banner「离线模式 — 仅显示已缓存内容」）

### 分享卡片（Task 14）
- 配方详情页新增「分享」按钮
- Canvas 生成分享图片（配方名+材料列表+领域色背景+Hermes 水印）
- 支持 Web Share API（移动端原生分享面板）+ 下载 PNG 降级

## Impact

- Affected specs: `product-iteration-roadmap`（Task 12-16 实施细化）
- Affected code:
  - `src/hermes_kb/models.py`（QueryLog 新增 feedback_comment/feedback_tag 字段）
  - `src/hermes_kb/api/ask.py`（feedback 端点升级 + feedback/list 汇总端点）
  - `migrations/versions/0011_add_feedback_fields.py`（新增字段迁移）
  - `web/src/App.tsx`（导航栏响应式 + 底部 tab bar）
  - `web/src/components/ChatPanel.tsx`（反馈评论框+标签+移动端输入固定）
  - `web/src/components/RecipePanel.tsx`（分享按钮+卡片生成）
  - `web/src/components/SettingsPanel.tsx`（反馈汇总子模块）
  - `web/public/manifest.json`（PWA 配置）
  - `web/src/sw.ts`（Service Worker 注册）
  - `web/vite.config.ts`（PWA 插件配置）

## ADDED Requirements

### Requirement: 结构化问答反馈
系统 SHALL 支持用户提交带评论和问题标签的反馈，替代当前仅 👍/👎 的机制。

#### Scenario: 提交带评论的反馈
- **WHEN** 用户点击 👍 或 👎 后
- **THEN** 展开评论框 + 问题标签选择器（答案不准/找不到文档/引用错误/其他）
- **AND** 用户可输入可选评论（≤500 字）
- **AND** 提交后反馈关联到 QueryLog 记录

#### Scenario: Admin 查看反馈汇总
- **WHEN** admin 访问 SettingsPanel → 意见反馈
- **THEN** 展示所有带评论的反馈列表
- **AND** 支持按标签筛选（答案不准/找不到文档/引用错误/全部）
- **AND** 显示反馈对应的问答摘要

### Requirement: 移动端底部导航
系统 SHALL 在移动端（< 768px）将顶部水平导航折叠为底部 tab bar。

#### Scenario: 移动端导航切换
- **WHEN** 视口宽度 < 768px
- **THEN** 顶部导航隐藏，底部显示 tab bar（首页/问答/配方/实验室/设置）
- **AND** tab bar 使用图标 + 文字，点击切换路由
- **AND** 内容区高度自动调整为 `100vh - header - tabbar`

#### Scenario: 桌面端导航保持
- **WHEN** 视口宽度 ≥ 768px
- **THEN** 保持现有顶部水平导航
- **AND** 不显示底部 tab bar

### Requirement: 问答面板移动端优化
系统 SHALL 在移动端将问答输入框固定在底部，历史消息全宽展示。

#### Scenario: 移动端问答
- **WHEN** 移动端使用问答功能
- **THEN** 输入框固定在底部 tab bar 上方
- **AND** 历史消息区域可滚动，占满剩余空间
- **AND** 引用卡片单列展示

### Requirement: PWA 离线缓存
系统 SHALL 支持 PWA 安装与离线访问已缓存的配方。

#### Scenario: 安装到桌面
- **WHEN** 用户在浏览器选择「添加到主屏幕」
- **THEN** 应用以 standalone 模式启动
- **AND** 显示自定义图标和启动画面

#### Scenario: 离线访问配方
- **WHEN** 用户离线打开已访问过的配方
- **THEN** 展示缓存的配方内容
- **AND** 顶部提示「离线模式 — 仅显示已缓存内容」
- **AND** 问答功能禁用并提示「离线无法问答」

### Requirement: 配方分享卡片
系统 SHALL 支持一键生成配方分享图片。

#### Scenario: 生成分享卡片
- **WHEN** 用户在配方详情页点击「分享」
- **THEN** 生成包含配方名+材料+领域色背景的 PNG 图片
- **AND** 移动端调用 Web Share API 原生分享
- **AND** 桌面端提供「下载图片」按钮
- **AND** 生成耗时 ≤2s

## MODIFIED Requirements

### Requirement: 问答反馈端点
从仅 👍/👎 升级为结构化反馈。

**修改前**：`POST /api/feedback/{log_id}` 仅接受 `{feedback: 1|-1|0}`
**修改后**：`POST /api/feedback/{log_id}` 接受 `{feedback: 1|-1|0, comment?: string, tag?: string}`
- tag 枚举：`inaccurate` | `not_found` | `wrong_citation` | `other`
- comment 限 500 字，支持空串（仅评分无评论）

### Requirement: 导航栏布局
从固定顶部水平导航升级为响应式导航。

**修改前**：顶部水平导航，`overflow-x-auto` 水平滚动
**修改后**：≥768px 顶部水平导航；<768px 底部 tab bar（图标+文字）
