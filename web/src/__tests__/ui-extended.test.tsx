// 杂志式语义卡片组件测试（MagazineCard / GoldFoilCard / LabMetric / DailyRecipeCard）
// vitest 配置 css: false，故不验证 _components.css 计算样式，
// 而是验证语义类应用 + inline var(--*) token 透传 + 结构/分支正确性。
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  MagazineCard,
  GoldFoilCard,
  LabMetric,
  DailyRecipeCard,
} from "../components/ui";

/** 取容器内首个匹配元素的 inline style 原始字符串 */
function inlineStyle(container: HTMLElement, selector: string): string {
  const el = container.querySelector(selector);
  return el?.getAttribute("style") || "";
}

// ════════════════════════════════════════════════════════════════════
// MagazineCard
// ════════════════════════════════════════════════════════════════════
describe("MagazineCard", () => {
  it("基本渲染：kicker + title + deck", () => {
    const { container } = render(
      <MagazineCard
        title="Negroni"
        kicker="COCKTAIL CLASSICS"
        deck="金巴利与金酒的永恒对话"
      />
    );
    expect(screen.getByText("Negroni")).toBeInTheDocument();
    expect(screen.getByText("COCKTAIL CLASSICS")).toBeInTheDocument();
    expect(screen.getByText(/金巴利与金酒的永恒对话/)).toBeInTheDocument();
    // 应用语义类
    expect(container.querySelector(".recipe-card-magazine")).not.toBeNull();
  });

  it("thumb 分支：传入 thumb 渲染 <img.mag-thumb>", () => {
    const { container } = render(
      <MagazineCard title="T" thumb="/img/negroni.jpg" />
    );
    const img = container.querySelector("img.mag-thumb");
    expect(img).not.toBeNull();
    expect(img?.getAttribute("src")).toBe("/img/negroni.jpg");
    // 无 placeholder
    expect(container.querySelector(".mag-thumb-placeholder")).toBeNull();
  });

  it("placeholder 分支：不传 thumb 渲染占位符", () => {
    const { container } = render(<MagazineCard title="T" />);
    expect(container.querySelector(".mag-thumb-placeholder")).not.toBeNull();
    expect(container.querySelector("img.mag-thumb")).toBeNull();
  });

  it("className 透传：外部 className 与语义类共存", () => {
    const { container } = render(
      <MagazineCard title="T" className="my-extra featured" />
    );
    const root = container.querySelector(".recipe-card-magazine");
    expect(root).not.toBeNull();
    expect(root?.className).toContain("recipe-card-magazine");
    expect(root?.className).toContain("my-extra");
    expect(root?.className).toContain("featured");
  });

  it("MagazineCard.Meta 子组件渲染 spirit + abv", () => {
    const { container } = render(
      <MagazineCard
        title="Negroni"
        meta={<MagazineCard.Meta spirit="金酒" abv="24%" />}
      />
    );
    expect(screen.getByText("金酒")).toBeInTheDocument();
    expect(screen.getByText("24%")).toBeInTheDocument();
    expect(container.querySelector(".mag-meta")).not.toBeNull();
    expect(container.querySelector(".mag-spirit")).not.toBeNull();
    expect(container.querySelector(".mag-abv")).not.toBeNull();
  });

  it("MagazineCard.Meta 支持 children 兜底", () => {
    render(
      <MagazineCard
        title="T"
        meta={
          <MagazineCard.Meta>
            <span data-testid="custom-meta">自定义</span>
          </MagazineCard.Meta>
        }
      />
    );
    expect(screen.getByTestId("custom-meta")).toBeInTheDocument();
  });

  it("design tokens：inline style 含 var(--*)", () => {
    const { container } = render(
      <MagazineCard title="Negroni" kicker="CLASSIC" deck="desc" />
    );
    expect(inlineStyle(container, ".mag-kicker")).toContain("var(--gold-700)");
    expect(inlineStyle(container, ".mag-title")).toContain("var(--ink-900)");
    expect(inlineStyle(container, ".mag-title")).toContain("var(--font-serif)");
    expect(inlineStyle(container, ".mag-deck")).toContain("var(--ink-600)");
  });

  it("children slot 兜底渲染", () => {
    render(
      <MagazineCard title="T">
        <div data-testid="slot">额外内容</div>
      </MagazineCard>
    );
    expect(screen.getByTestId("slot")).toBeInTheDocument();
  });

  it("onClick 触发回调并标记 role=button", () => {
    const onClick = vi.fn();
    const { container } = render(
      <MagazineCard title="T" onClick={onClick} />
    );
    const root = container.querySelector(".recipe-card-magazine");
    expect(root?.getAttribute("role")).toBe("button");
    fireEvent.click(root as Element);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

// ════════════════════════════════════════════════════════════════════
// GoldFoilCard
// ════════════════════════════════════════════════════════════════════
describe("GoldFoilCard", () => {
  it("基本渲染：title + quote + attribution", () => {
    const { container } = render(
      <GoldFoilCard
        title="调酒哲学"
        quote="一杯好酒是时间与耐心的结晶"
        attribution="— Hermes Master"
      />
    );
    expect(screen.getByText("调酒哲学")).toBeInTheDocument();
    expect(screen.getByText(/一杯好酒是时间与耐心的结晶/)).toBeInTheDocument();
    expect(screen.getByText("— Hermes Master")).toBeInTheDocument();
    expect(container.querySelector(".gold-foil-card")).not.toBeNull();
  });

  it("className 透传：外部 className 与语义类共存", () => {
    const { container } = render(
      <GoldFoilCard title="T" className="hero-card highlight" />
    );
    const root = container.querySelector(".gold-foil-card");
    expect(root).not.toBeNull();
    expect(root?.className).toContain("gold-foil-card");
    expect(root?.className).toContain("hero-card");
  });

  it("design tokens：inline style 含 var(--*)", () => {
    const { container } = render(
      <GoldFoilCard title="T" quote="Q" attribution="A" />
    );
    expect(inlineStyle(container, ".foil-title")).toContain("var(--font-serif)");
    expect(inlineStyle(container, ".foil-quote")).toContain("var(--ink-900)");
    expect(inlineStyle(container, ".foil-quote")).toContain("var(--font-serif)");
    expect(inlineStyle(container, ".foil-attribution")).toContain("var(--ink-400)");
  });

  it("children slot 完全自定义内容", () => {
    render(
      <GoldFoilCard>
        <div data-testid="custom-content">自定义内容</div>
      </GoldFoilCard>
    );
    expect(screen.getByTestId("custom-content")).toBeInTheDocument();
  });

  it("省略可选字段不渲染对应节点", () => {
    const { container } = render(<GoldFoilCard title="仅标题" />);
    expect(container.querySelector(".foil-title")).not.toBeNull();
    expect(container.querySelector(".foil-quote")).toBeNull();
    expect(container.querySelector(".foil-attribution")).toBeNull();
  });
});

// ════════════════════════════════════════════════════════════════════
// LabMetric
// ════════════════════════════════════════════════════════════════════
describe("LabMetric", () => {
  it("基本渲染：label + num + sub", () => {
    const { container } = render(
      <LabMetric label="配方总数" num={128} sub="本周 +3" />
    );
    expect(screen.getByText("配方总数")).toBeInTheDocument();
    expect(screen.getByText("128")).toBeInTheDocument();
    expect(screen.getByText("本周 +3")).toBeInTheDocument();
    expect(container.querySelector(".lab-metric")).not.toBeNull();
  });

  it("alert 变体：应用 alert 类 + num 用 gold-700", () => {
    const { container } = render(
      <LabMetric label="告警阈值" num={5} alert />
    );
    const root = container.querySelector(".lab-metric");
    expect(root?.className).toContain("alert");
    const numStyle = inlineStyle(container, ".lab-num");
    expect(numStyle).toContain("var(--gold-700)");
    expect(numStyle).not.toContain("var(--ink-900)");
  });

  it("非 alert：num 用 ink-900", () => {
    const { container } = render(<LabMetric label="L" num={1} />);
    const numStyle = inlineStyle(container, ".lab-num");
    expect(numStyle).toContain("var(--ink-900)");
    expect(numStyle).not.toContain("var(--gold-700)");
  });

  it("className 透传：外部 className 与语义类共存", () => {
    const { container } = render(
      <LabMetric label="L" num={1} className="extra-metric" />
    );
    const root = container.querySelector(".lab-metric");
    expect(root?.className).toContain("lab-metric");
    expect(root?.className).toContain("extra-metric");
  });

  it("design tokens：inline style 含 var(--*)", () => {
    const { container } = render(<LabMetric label="L" num={1} sub="s" />);
    expect(inlineStyle(container, ".lab-label")).toContain("var(--ink-400)");
    expect(inlineStyle(container, ".lab-label")).toContain("var(--font-ui)");
    expect(inlineStyle(container, ".lab-num")).toContain("var(--font-serif)");
    expect(inlineStyle(container, ".lab-sub")).toContain("var(--brand-700)");
  });

  it("省略 sub 时不渲染 .lab-sub 节点", () => {
    const { container } = render(<LabMetric label="L" num={1} />);
    expect(container.querySelector(".lab-sub")).toBeNull();
  });
});

// ════════════════════════════════════════════════════════════════════
// DailyRecipeCard
// ════════════════════════════════════════════════════════════════════
describe("DailyRecipeCard", () => {
  it("基本渲染：badge + name + reason", () => {
    const { container } = render(
      <DailyRecipeCard badge="今日推荐" name="Mojito" reason="清凉夏日" />
    );
    expect(screen.getByText("今日推荐")).toBeInTheDocument();
    expect(screen.getByText("Mojito")).toBeInTheDocument();
    expect(screen.getByText("清凉夏日")).toBeInTheDocument();
    expect(container.querySelector(".daily-recipe")).not.toBeNull();
  });

  it("href 渲染为 <a> 并携带 href 属性", () => {
    const { container } = render(
      <DailyRecipeCard name="Mojito" href="/recipes/mojito" />
    );
    const link = container.querySelector("a.daily-recipe");
    expect(link).not.toBeNull();
    expect(link?.getAttribute("href")).toBe("/recipes/mojito");
    // 非 a 时不渲染 div
    expect(container.querySelector("div.daily-recipe")).toBeNull();
  });

  it("无 href 渲染为 <div>", () => {
    const { container } = render(<DailyRecipeCard name="Mojito" />);
    const div = container.querySelector("div.daily-recipe");
    expect(div).not.toBeNull();
    expect(container.querySelector("a.daily-recipe")).toBeNull();
  });

  it("className 透传：外部 className 与语义类共存", () => {
    const { container } = render(
      <DailyRecipeCard name="M" className="featured" />
    );
    const root = container.querySelector(".daily-recipe");
    expect(root?.className).toContain("daily-recipe");
    expect(root?.className).toContain("featured");
  });

  it("design tokens：inline style 含 var(--*)", () => {
    const { container } = render(
      <DailyRecipeCard badge="B" name="N" reason="R" />
    );
    expect(inlineStyle(container, ".daily-badge")).toContain("var(--gold-500)");
    expect(inlineStyle(container, ".daily-badge")).toContain("var(--ink-900)");
    expect(inlineStyle(container, ".daily-name")).toContain("var(--font-serif)");
    expect(inlineStyle(container, ".daily-reason")).toContain("var(--ink-400)");
  });

  it("children slot 透传：onClick 触发回调", () => {
    const onClick = vi.fn();
    const { container } = render(
      <DailyRecipeCard name="M" onClick={onClick} />
    );
    const root = container.querySelector(".daily-recipe");
    expect(root?.getAttribute("role")).toBe("button");
    fireEvent.click(root as Element);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
