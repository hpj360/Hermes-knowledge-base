# 酒类知识库数据源评估矩阵

> 评估维度：**权威性**（来源信誉与机构背书）、**准确性**（数据严谨度/可核验性）、**时效性**（更新频率与新鲜度）。评分 1-5，5 为最优。
> 准入结论：**采纳**（纳入注册表并接入）/ **观望**（暂不接入，记录备选）/ **不采纳**（不符合内容标准或无法合法获取）。
> 评估日期：2026-08-12

## 一、学术期刊（学术性 / 高准确性）

| 数据源 | 权威性 | 准确性 | 时效性 | 准入结论 | 理由 |
|---|---|---|---|---|---|
| Journal of Agricultural and Food Chemistry (ACS) | 5 | 5 | 3 | 采纳（经 Crossref 摘要） | 蒸馏烈酒酚类/抗氧化成分的权威化学研究，可引用 DOI；付费正文 → 仅取公开摘要+元数据 |
| FEMS Yeast Research | 5 | 5 | 3 | 采纳（经 Crossref 摘要） | 酵母/烈酒发酵研究权威期刊（如加拿大酵母产香研究） |
| Journal of the Institute of Brewing / Sustainable Food Technology (RSC) | 4 | 5 | 3 | 观望 | 威士忌/酿造相关研究，权威但领域偏窄 |
| Food Chemistry (Elsevier) | 5 | 5 | 4 | 观望 | 酒类成分分析权威期刊，但 Elsevier 摘要开放度较低 |
| 中文核心期刊（食品科学/酿酒科技） | 4 | 4 | 3 | 观望 | 中文酒类研究权威，但数字化/DOI 覆盖参差 |

**学术期刊接入策略**：不整篇搬运付费内容，通过 **Crossref 开放 API** 获取文章标题/摘要/DOI/引用，作为"权威知识点+可溯源引用"接入，规避版权风险。

## 二、行业报告（时效性强 / 市场数据）

| 数据源 | 权威性 | 准确性 | 时效性 | 准入结论 | 理由 |
|---|---|---|---|---|---|
| IWSR 全球酒类市场数据 | 5 | 5 | 5 | 采纳（策划快照） | 全球最权威饮料酒市场数据机构，追踪 160 国，年度发布+十年预测；仅接入公开新闻稿/摘要（付费全量报告不接入） |
| WHO 全球酒精与健康报告 | 5 | 5 | 4 | 采纳（策划快照） | 公共卫生领域最高权威，CC BY 许可，公开事实可合法引用 |
| Euromonitor 酒类板块 | 4 | 4 | 5 | 观望 | 权威但付费订阅，开放数据有限 |
| Grand View / Mordor Intelligence | 3 | 3 | 4 | 不采纳 | 权威性一般，数据可核验性弱 |

## 三、权威机构 / 参考书（高权威 / 标准）

| 数据源 | 权威性 | 准确性 | 时效性 | 准入结论 | 理由 |
|---|---|---|---|---|---|
| IBA 国际调酒师协会官方配方 | 5 | 5 | 4 | 采纳（策划快照） | 配方金标准，业界公认 |
| WSET 葡萄酒与烈酒教育信托 | 5 | 5 | 4 | 观望 | 教育标准权威，但教材版权受限 |
| 牛津葡萄酒/烈酒指南（Oxford Companion） | 5 | 5 | 4 | 观望 | 权威参考书，版权受限 |
| LCBO 烈酒质量保证 | 4 | 5 | 4 | 观望 | 政府机构品控数据，权威但覆盖有限 |
| Wikidata 结构化实体 | 4 | 4 | 5 | 采纳（SPARQL API） | CC0，带引用的结构化属性+多语言别名，实时可 API 拉取 |
| TheCocktailDB | 3 | 3 | 4 | 采纳（已有） | 社区开源配方库，覆盖广，权威性低于 IBA |

## 四、首波接入清单（与注册表一致）

| id | 名称 | 接入方式 | 许可 |
|---|---|---|---|
| wikidata | Wikidata 结构化实体 | api | CC0 |
| crossref | Crossref 学术摘要 | api | CC0 |
| iwsr_summary | IWSR 市场摘要 | curated | open-access |
| who_alcohol | WHO 酒精健康 | curated | CC BY |
| iba_official | IBA 官方配方 | curated | open-access |
| thecocktaildb | TheCocktailDB | api | open-access |

## 五、质量门槛

接入数据源需通过以下校验（`scripts/_verify_data_sources.py`）：
1. 来源值 ∈ 注册表 id ∪ 白名单（local/iba/thecocktaildb/user/ugc/seed）
2. curated/api 来源文档 `source_authority`/`source_url` 必填
3. `source_refreshed_at` 距当前不超过该源 `refresh_cadence_days`
4. 同一 `source_url`/标题不产生重复文档
5. 新内容满足既有内容质量标准（非空、长度达标、元数据完整）
