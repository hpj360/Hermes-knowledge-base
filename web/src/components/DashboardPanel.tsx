/**
 * 首页 DashboardPanel
 *
 * 产品定位：个人酒类知识工作台首页
 * 三阶价值：知识可信 → 实践可用 → 持续可成长
 *
 * 结构（紧凑化版）：
 * 1. Hero banner：价值主张 + 3 张实时数据卡 + 快捷操作（单行紧凑布局）
 * 2. 空库引导：种子导入卡片
 * 3. 飞轮健康度概览：4 指标卡（文档数/问答数/引用密度/配方数）
 * 4. 今日推荐 / 最近问答
 */
import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { api } from "../api";
import type { HealthStatus, LabDashboard, LabDailyRecipe, HistoryItem } from "../types";
import { Skeleton } from "./Skeleton";
import {
  BauhausButton,
  BauhausCard,
  BauhausDisplay,
  BauhausMetric,
  BauhausSectionLabel,
  BodyText,
  MetaText,
} from "./ui";

interface DashboardPanelProps {
  health: HealthStatus | null;
  onSeed: () => void;
  seeding: boolean;
  onShowImport: () => void;
}

export function DashboardPanel({ health, onSeed, seeding, onShowImport }: DashboardPanelProps) {
  const [, navigate] = useLocation();
  const [dashboard, setDashboard] = useState<LabDashboard | null>(null);
  const [daily, setDaily] = useState<LabDailyRecipe | null>(null);
  const [recentHistory, setRecentHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [dash, dailyRecipe, hist] = await Promise.all([
          api.labDashboard().catch(() => null),
          api.labDaily().catch(() => null),
          api.history(3).catch(() => ({ total: 0, items: [] })),
        ]);
        if (!cancelled) {
          setDashboard(dash);
          setDaily(dailyRecipe);
          setRecentHistory(hist.items || []);
          setLoading(false);
        }
      } catch {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const isEmpty = health?.doc_count === 0;

  /** 季节性推荐 reason 文案 */
  const dailyReasonText = (reason?: string): string => {
    if (reason === "season") return "应季推荐";
    if (reason === "hot") return "本周热门";
    if (reason === "random") return "随机发现";
    return "今日推荐";
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Hero 区：单行 banner + 实时数据卡 + 快捷操作（紧凑化） */}
        <div className="mb-6 pb-4" style={{ borderBottom: "var(--border-bold)" }}>
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex-1 min-w-0">
              <BauhausSectionLabel className="mb-1">HERMES KNOWLEDGE WORKSPACE</BauhausSectionLabel>
              <BauhausDisplay as="h1" className="mb-1">从知识到实践</BauhausDisplay>
              <BodyText className="text-sm" style={{ color: "var(--ink-400)" }}>
                沉淀酒类知识，智能检索引用，实践调酒配方
              </BodyText>
            </div>
            {/* 3 张实时数据卡，水平排列 */}
            <div className="flex gap-3 flex-shrink-0">
              <BauhausMetric num={health?.doc_count ?? 0} label="文档" variant="wine" />
              <BauhausMetric num={dashboard?.total_queries ?? recentHistory.length} label="问答" variant="amber" />
              <BauhausMetric num={dashboard?.total_recipes ?? 0} label="配方" variant="bronze" />
            </div>
          </div>
          {/* 快捷操作合并到 Hero banner 底部 */}
          <div className="flex flex-wrap gap-2 mt-4">
            <BauhausButton variant="solid" onClick={() => navigate("/chat")}>
              开始提问
            </BauhausButton>
            <BauhausButton variant="outline" onClick={onShowImport}>
              导入文档
            </BauhausButton>
            <BauhausButton variant="outline" onClick={() => navigate("/recipes")}>
              浏览配方
            </BauhausButton>
            <BauhausButton variant="outline" onClick={() => navigate("/lab")}>
              进入实验室
            </BauhausButton>
          </div>
        </div>

        {/* 空库引导 */}
        {isEmpty && (
          <BauhausCard accent="wine" className="mb-8 text-center py-8">
            <BauhausDisplay as="h2" className="mb-3">开始你的知识库</BauhausDisplay>
            <BodyText className="mb-4">导入 5 篇酒类种子知识（金酒/威士忌/葡萄酒/白酒/朗姆+龙舌兰），立即体验引用式问答</BodyText>
            <BauhausButton variant="solid" onClick={onSeed} disabled={seeding}>
              {seeding ? "导入中..." : "导入种子知识"}
            </BauhausButton>
          </BauhausCard>
        )}

        {/* 飞轮健康度概览 */}
        <div className="mb-6">
          <BauhausSectionLabel className="mb-4">飞轮健康度</BauhausSectionLabel>
          {loading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} height="80px" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <BauhausMetric
                num={health?.doc_count ?? 0}
                label="文档总数"
                variant="outline"
              />
              <BauhausMetric
                num={dashboard?.total_queries ?? recentHistory.length}
                label="问答次数"
                variant="wine"
              />
              <BauhausMetric
                num={dashboard?.avg_citations?.toFixed(1) ?? "0.0"}
                label="平均引用数"
                variant="amber"
              />
              <BauhausMetric
                num={dashboard?.total_recipes ?? 0}
                label="配方总数"
                variant="bronze"
              />
            </div>
          )}
        </div>

        {/* 今日推荐 / 应季推荐 */}
        {daily && daily.title && (
          <div className="mb-6">
            <BauhausSectionLabel className="mb-4">今日推荐</BauhausSectionLabel>
            <BauhausCard
              accent={daily.reason === "season" ? "amber" : "wine"}
              className="cursor-pointer hover:opacity-90 transition-opacity"
              onClick={() =>
                daily.doc_id
                  ? navigate(`/recipes?doc_id=${encodeURIComponent(daily.doc_id)}`)
                  : navigate("/lab")
              }
              title={
                <span style={{ fontFamily: "var(--font-serif)" }}>
                  {daily.title}
                </span>
              }
              meta={
                <span>
                  <span
                    className="text-xs px-2 py-0.5 rounded-full"
                    style={{
                      background: daily.reason === "season" ? "var(--amber)" : "var(--ink-900)",
                      color: daily.reason === "season" ? "var(--ink-900)" : "#fff",
                      fontFamily: "var(--font-ui)",
                    }}
                    aria-label={`推荐理由：${dailyReasonText(daily.reason)}`}
                  >
                    {dailyReasonText(daily.reason)}
                  </span>
                  {daily.base_spirit && (
                    <>
                      <span className="mx-2">·</span>
                      <span style={{ fontFamily: "var(--font-mono)" }}>
                        {daily.base_spirit}
                      </span>
                    </>
                  )}
                  {daily.difficulty && (
                    <>
                      <span className="mx-2">·</span>
                      <span style={{ fontFamily: "var(--font-mono)" }}>
                        {daily.difficulty}
                      </span>
                    </>
                  )}
                </span>
              }
            >
              <BodyText className="text-sm">
                {daily.reason === "season"
                  ? "应季配方，跟随节气品味当令风味。"
                  : daily.reason === "hot"
                  ? "本周热门配方，社区高频匹配。"
                  : "从配方库随机发现一杯灵感。"}
              </BodyText>
            </BauhausCard>
          </div>
        )}

        {/* 最近问答 */}
        {recentHistory.length > 0 && (
          <div className="mb-6">
            <BauhausSectionLabel className="mb-4">最近问答</BauhausSectionLabel>
            <div className="space-y-3">
              {recentHistory.map((item) => (
                <BauhausCard
                  key={item.log_id}
                  accent="ink"
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() => navigate("/chat")}
                >
                  <BodyText className="text-sm font-medium mb-1">{item.query}</BodyText>
                  <MetaText className="text-xs">
                    {new Date(item.created_at).toLocaleString("zh-CN")}
                  </MetaText>
                </BauhausCard>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
