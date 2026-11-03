# 技术债清单(2026-11-03 收编)

> 来源:文档整理时发现 `knowledge-base-quality-sources`(数据源治理规格)的 Task 6 门禁项挂着 3 个
> "**存量无关**"的失败,导致该规格永远无法标"完结"。2026-11-03 经用户拍板将这些债平移到本清单独立管理,
> quality-sources 规格状态改为"已交付(带已归槽债)"。挂在规格里会让收尾判定失真——这就是本文件存在的根因。

## TD-1 测试存量失败(11 个,pytest 1336 passed / 11 failed)

来源:quality-sources SubTask 6.1(2026-08 前后状态)。

| # | 失败测试 | 现象 |
|---|---|---|
| 1-× | test_loop 系列 | 引用 `hermes.main` 已缺失的函数(主仓六仓归一后接口漂移) |
| ? | test_m1 | embedding 断言不符 |
| ? | test_obsidian_sync | 缺 watchdog 依赖(未入 requirements) |

> 修复顺序建议:先补 `watchdog` 依赖(最廉价)→ test_m1 断言核对 → test_loop 按
> `src/hermes/workbench/`(冻结副本,不得直改,按 AGENTS 约定向主仓提需求)核对引用面,必要时
> 把引用面改为 `hermes_kb` 自有入口,而不是复活主仓旧函数。
> 注意:实际清单以再次运行 `pytest tests/ -q` 为准,本表是 08 月快照,可能已漂移。

## TD-2 ruff 存量风格错误(310 个,src/ + scripts/)

来源:quality-sources SubTask 6.2。全部为存量风格问题,非数据源规格引入。
建议按 kb 仓 AGENTS 硬规则(修复后验证 → commit → push)分 3-4 个独立小批量清理,
每批配 `ruff check` 计数下降趋势,不做大爆炸一次性重排。

## TD-3 评估集权威内容查询缺口

来源:quality-sources SubTask 5.3:`tests/eval/eval_set.jsonl` 尚未新增"权威内容查询"
用例(用于校验 IBA/WHO/IWSR 等权威源的检索质量)。原规格标注"归入 P5 检索优化/评估集校准"。
归属:与 cocktail-data-agent Phase 5(评估与上线)合并执行,避免两处各写一套评估集口径。

## 与两份数据源 spec 的关系

- `knowledge-base-quality-sources`:本清单收编 TD-1/TD-2 后,其 Task 6 门禁语义改为
  "本 spec 引入的改动无回归"(1336/11 的 11 中与本 spec 相关 = 0),即可标完绌;
- `cocktail-data-agent`:Phase 5(评估与上线)执行时一并消化 TD-3。
