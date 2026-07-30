/**
 * Task 14: 配方分享卡片
 *
 * 设计约束（包豪斯风格）：
 * - 白底 + 3px 粗边框 + 领域色实色几何 + 微圆角 2px + Space Grotesk 字体
 * - 领域色：wine #6b2c2c / amber #c9a961 / bronze #3a5a6b
 * - 使用原生 Canvas API，不引入 html2canvas 等额外依赖
 *
 * 行为：
 * - 点击「分享」→ Canvas 生成 PNG → Web Share API（移动端）/ 下载 PNG（桌面端降级）
 * - 生成耗时显示「处理中...」状态
 */
import { useState } from "react";
import type { LabRecipe } from "../types";
import { BauhausButton } from "./ui";

interface ShareCardButtonProps {
  recipe: LabRecipe;
  className?: string;
}

export function ShareCardButton({ recipe, className }: ShareCardButtonProps) {
  const [generating, setGenerating] = useState(false);

  const handleShare = async () => {
    setGenerating(true);
    try {
      const blob = await generateShareCard(recipe);
      const file = new File([blob], `hermes-${recipe.doc_id}.png`, { type: "image/png" });

      // 移动端：Web Share API
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          files: [file],
          title: recipe.title || "Hermes 配方",
          text: `用 Hermes 知识库调一杯 ${recipe.title}`,
        });
      } else {
        // 桌面端：下载 PNG
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `hermes-${recipe.doc_id}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      // 用户取消分享不算错误（AbortError）
      if (err instanceof Error && err.name !== "AbortError") {
        console.error("分享失败:", err);
      }
    } finally {
      setGenerating(false);
    }
  };

  return (
    <BauhausButton variant="outline" onClick={handleShare} disabled={generating} className={className}>
      {generating ? "处理中..." : "分享"}
    </BauhausButton>
  );
}

// ---------------------------------------------------------------------------
// 领域色映射（source → 包豪斯领域色实色）
// ---------------------------------------------------------------------------
const DOMAIN_COLOR: Record<string, string> = {
  iba_dataset: "#6b2c2c",    // wine
  thecocktaildb: "#c9a961",  // amber
  seed: "#3a5a6b",           // bronze
  ugc: "#3a5a6b",            // bronze
  local: "#3a5a6b",          // bronze
};

/**
 * 生成分享卡片图片（1080×1350，4:5 比例适合社交分享）。
 * 使用原生 Canvas API，包豪斯几何布局。
 */
export async function generateShareCard(recipe: LabRecipe): Promise<Blob> {
  const W = 1080;
  const H = 1350; // 4:5 比例适合社交分享

  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d")!;

  // 背景：白底（var(--paper-bg)）
  ctx.fillStyle = "#fafaf7";
  ctx.fillRect(0, 0, W, H);

  // 领域色
  const domainColor = DOMAIN_COLOR[recipe.source || "local"] || "#3a5a6b";

  // 顶部领域色色带（包豪斯几何）
  ctx.fillStyle = domainColor;
  ctx.fillRect(0, 0, W, 12);

  // 左上角实色方块（包豪斯几何装饰）
  ctx.fillRect(60, 60, 80, 80);

  // Hermes 水印（左上角方块内）
  ctx.fillStyle = "#fafaf7";
  ctx.font = "bold 28px 'Space Grotesk', sans-serif";
  ctx.textBaseline = "middle";
  ctx.textAlign = "center";
  ctx.fillText("H", 100, 100);

  // 配方标题
  ctx.fillStyle = "#1a1a1a"; // var(--ink-900)
  ctx.font = "bold 56px 'Space Grotesk', sans-serif";
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillText(recipe.title || "未命名配方", 60, 200, W - 120);

  // 分隔线（3px 粗，包豪斯粗边框）
  ctx.fillStyle = "#1a1a1a";
  ctx.fillRect(60, 290, W - 120, 3);

  // 来源标签（mono 字体）
  ctx.fillStyle = "#6b6b6b"; // var(--ink-400)
  ctx.font = "20px 'Space Grotesk', monospace";
  ctx.fillText(`SOURCE / ${recipe.source || "local"}`.toUpperCase(), 60, 320);

  // 材料区标题（领域色）
  ctx.fillStyle = domainColor;
  ctx.font = "bold 28px 'Space Grotesk', sans-serif";
  ctx.fillText("INGREDIENTS", 60, 400);

  // 材料列表（从 recipe.ingredients 或 recipe.content 解析）
  const ingredients = parseIngredients(recipe);
  ctx.fillStyle = "#1a1a1a";
  ctx.font = "24px 'Space Grotesk', sans-serif";
  ingredients.slice(0, 10).forEach((ing, i) => {
    const y = 460 + i * 50;
    ctx.fillText(`• ${ing}`, 60, y, W - 120);
  });

  // 底部水印
  ctx.fillStyle = "#6b6b6b";
  ctx.font = "20px 'Space Grotesk', monospace";
  ctx.textAlign = "center";
  ctx.fillText("HERMES 知识库 · 可信引用 + 实践闭环", W / 2, H - 60);

  // 底部色带
  ctx.fillStyle = domainColor;
  ctx.fillRect(0, H - 12, W, 12);

  // 转 Blob
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error("Canvas toBlob failed"));
    }, "image/png");
  });
}

/**
 * 解析材料列表（从 recipe 对象）。
 * LabRecipe 类型本身不携带 ingredients/content，运行时可能存在扩展字段，
 * 因此使用 any 收窄以保证兼容性。
 */
function parseIngredients(recipe: LabRecipe): string[] {
  // 优先使用 ingredients 字段（如果是数组）
  const r = recipe as any;
  if (Array.isArray(r.ingredients) && r.ingredients.length > 0) {
    return r.ingredients.map((i: any) =>
      typeof i === "string" ? i : `${i.name} ${i.amount || ""}`.trim(),
    );
  }
  // 退回到 content 解析（<!-- ingredients: a | b | c -->）
  if (typeof r.content === "string") {
    const match = r.content.match(/<!-- ingredients: (.*?) -->/);
    if (match) {
      return match[1]
        .split("|")
        .map((s: string) => s.trim())
        .filter(Boolean);
    }
  }
  return ["(材料信息不可用)"];
}
