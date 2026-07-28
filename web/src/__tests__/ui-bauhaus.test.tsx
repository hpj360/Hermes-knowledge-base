// P2 包豪斯几何 + 极简现代组件库测试
// vitest 配置 css: false，故不验证 _components.css 计算样式，
// 而是验证语义类应用 + 变体分支 + className/props 透传 + 结构正确性。
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  BauhausCard,
  BauhausMetric,
  BauhausChip,
  BauhausButton,
  BauhausSectionLabel,
  BauhausDisplay,
  BauhausGeometry,
  BauhausLayout,
  BauhausBrandMark,
} from "../components/ui";

// ════════════════════════════════════════════════════════════════════
// BauhausCard
// ════════════════════════════════════════════════════════════════════
describe("BauhausCard", () => {
  it("基本渲染：title + meta + children", () => {
    const { container } = render(
      <BauhausCard title="Negroni" meta="IBA CLASSIC">
        <p>金巴利 30ml</p>
      </BauhausCard>
    );
    expect(screen.getByText("Negroni")).toBeInTheDocument();
    expect(screen.getByText("IBA CLASSIC")).toBeInTheDocument();
    expect(screen.getByText("金巴利 30ml")).toBeInTheDocument();
    expect(container.querySelector(".bauhaus-card")).not.toBeNull();
    expect(container.querySelector(".bauhaus-card-title")).not.toBeNull();
    expect(container.querySelector(".bauhaus-card-meta")).not.toBeNull();
  });

  it("默认 accent=wine：应用 accent-wine 类", () => {
    const { container } = render(<BauhausCard title="T" />);
    const root = container.querySelector(".bauhaus-card");
    expect(root?.className).toContain("accent-wine");
  });

  it("accent 变体：amber/bronze/ink 透传到类名", () => {
    const { container: amberC } = render(<BauhausCard title="T" accent="amber" />);
    expect(amberC.querySelector(".bauhaus-card")?.className).toContain("accent-amber");

    const { container: bronzeC } = render(<BauhausCard title="T" accent="bronze" />);
    expect(bronzeC.querySelector(".bauhaus-card")?.className).toContain("accent-bronze");

    const { container: inkC } = render(<BauhausCard title="T" accent="ink" />);
    expect(inkC.querySelector(".bauhaus-card")?.className).toContain("accent-ink");
  });

  it("可选 title/meta：缺省时不渲染对应节点", () => {
    const { container } = render(<BauhausCard><p>body</p></BauhausCard>);
    expect(container.querySelector(".bauhaus-card-title")).toBeNull();
    expect(container.querySelector(".bauhaus-card-meta")).toBeNull();
    expect(container.querySelector(".bauhaus-card")).not.toBeNull();
  });

  it("className 与 props 透传（onClick 等）", () => {
    const onClick = vi.fn();
    const { container } = render(
      <BauhausCard title="T" className="my-extra" onClick={onClick} data-testid="card" />
    );
    const root = container.querySelector(".bauhaus-card") as HTMLElement;
    expect(root.className).toContain("my-extra");
    expect(root.getAttribute("data-testid")).toBe("card");
    fireEvent.click(root);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

// ════════════════════════════════════════════════════════════════════
// BauhausMetric
// ════════════════════════════════════════════════════════════════════
describe("BauhausMetric", () => {
  it("基本渲染：num + label", () => {
    const { container } = render(
      <BauhausMetric num={57} label="IBA 配方" />
    );
    expect(screen.getByText("57")).toBeInTheDocument();
    expect(screen.getByText("IBA 配方")).toBeInTheDocument();
    expect(container.querySelector(".bauhaus-metric")).not.toBeNull();
    expect(container.querySelector(".bauhaus-metric-num")).not.toBeNull();
    expect(container.querySelector(".bauhaus-metric-label")).not.toBeNull();
  });

  it("默认 variant=outline：应用 variant-outline 类", () => {
    const { container } = render(<BauhausMetric num={1} label="x" />);
    expect(container.querySelector(".bauhaus-metric")?.className).toContain("variant-outline");
  });

  it("variant 变体：wine/amber/bronze 透传到类名", () => {
    const { container: wineC } = render(<BauhausMetric num={1} label="x" variant="wine" />);
    expect(wineC.querySelector(".bauhaus-metric")?.className).toContain("variant-wine");

    const { container: amberC } = render(<BauhausMetric num={1} label="x" variant="amber" />);
    expect(amberC.querySelector(".bauhaus-metric")?.className).toContain("variant-amber");

    const { container: bronzeC } = render(<BauhausMetric num={1} label="x" variant="bronze" />);
    expect(bronzeC.querySelector(".bauhaus-metric")?.className).toContain("variant-bronze");
  });

  it("num 支持 ReactNode（字符串/元素）", () => {
    render(<BauhausMetric num={<span>99+</span>} label="x" />);
    expect(screen.getByText("99+")).toBeInTheDocument();
  });

  it("className 透传", () => {
    const { container } = render(<BauhausMetric num={1} label="x" className="metric-extra" />);
    expect(container.querySelector(".bauhaus-metric")?.className).toContain("metric-extra");
  });
});

// ════════════════════════════════════════════════════════════════════
// BauhausChip
// ════════════════════════════════════════════════════════════════════
describe("BauhausChip", () => {
  it("基本渲染：children + 默认 variant=wine", () => {
    const { container } = render(<BauhausChip>STIRRED</BauhausChip>);
    expect(screen.getByText("STIRRED")).toBeInTheDocument();
    const root = container.querySelector(".bauhaus-chip");
    expect(root).not.toBeNull();
    expect(root?.className).toContain("variant-wine");
  });

  it("variant 变体：amber/bronze/outline", () => {
    const { container: amberC } = render(<BauhausChip variant="amber">A</BauhausChip>);
    expect(amberC.querySelector(".bauhaus-chip")?.className).toContain("variant-amber");

    const { container: bronzeC } = render(<BauhausChip variant="bronze">B</BauhausChip>);
    expect(bronzeC.querySelector(".bauhaus-chip")?.className).toContain("variant-bronze");

    const { container: outlineC } = render(<BauhausChip variant="outline">O</BauhausChip>);
    expect(outlineC.querySelector(".bauhaus-chip")?.className).toContain("variant-outline");
  });

  it("渲染为 <span> 元素", () => {
    const { container } = render(<BauhausChip>X</BauhausChip>);
    expect(container.querySelector(".bauhaus-chip")?.tagName).toBe("SPAN");
  });

  it("className 与 props 透传", () => {
    const { container } = render(
      <BauhausChip className="chip-extra" data-foo="bar">X</BauhausChip>
    );
    const root = container.querySelector(".bauhaus-chip") as HTMLElement;
    expect(root.className).toContain("chip-extra");
    expect(root.getAttribute("data-foo")).toBe("bar");
  });
});

// ════════════════════════════════════════════════════════════════════
// BauhausButton
// ════════════════════════════════════════════════════════════════════
describe("BauhausButton", () => {
  it("基本渲染：children + 默认 variant=solid + type=button", () => {
    const { container } = render(<BauhausButton>导入</BauhausButton>);
    const btn = screen.getByRole("button", { name: "导入" });
    expect(btn).toBeInTheDocument();
    expect(btn.className).toContain("bauhaus-btn");
    expect(btn.className).toContain("variant-solid");
    expect(btn.getAttribute("type")).toBe("button");
  });

  it("variant 变体：accent/outline", () => {
    const { container: accentC } = render(<BauhausButton variant="accent">A</BauhausButton>);
    expect(accentC.querySelector(".bauhaus-btn")?.className).toContain("variant-accent");

    const { container: outlineC } = render(<BauhausButton variant="outline">O</BauhausButton>);
    expect(outlineC.querySelector(".bauhaus-btn")?.className).toContain("variant-outline");
  });

  it("type 透传：submit/reset", () => {
    render(<BauhausButton type="submit">提交</BauhausButton>);
    expect(screen.getByRole("button", { name: "提交" }).getAttribute("type")).toBe("submit");
  });

  it("onClick 触发", () => {
    const onClick = vi.fn();
    render(<BauhausButton onClick={onClick}>点我</BauhausButton>);
    fireEvent.click(screen.getByRole("button", { name: "点我" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("disabled 透传", () => {
    render(<BauhausButton disabled>禁用</BauhausButton>);
    expect(screen.getByRole("button", { name: "禁用" })).toBeDisabled();
  });

  it("className 透传", () => {
    const { container } = render(<BauhausButton className="my-btn">X</BauhausButton>);
    expect(container.querySelector(".bauhaus-btn")?.className).toContain("my-btn");
  });
});

// ════════════════════════════════════════════════════════════════════
// BauhausSectionLabel
// ════════════════════════════════════════════════════════════════════
describe("BauhausSectionLabel", () => {
  it("基本渲染：children + 语义类", () => {
    const { container } = render(
      <BauhausSectionLabel>SOURCE</BauhausSectionLabel>
    );
    expect(screen.getByText("SOURCE")).toBeInTheDocument();
    expect(container.querySelector(".bauhaus-section-label")).not.toBeNull();
  });

  it("渲染为 <div> 元素", () => {
    const { container } = render(<BauhausSectionLabel>X</BauhausSectionLabel>);
    expect(container.querySelector(".bauhaus-section-label")?.tagName).toBe("DIV");
  });

  it("className 透传", () => {
    const { container } = render(
      <BauhausSectionLabel className="label-extra">X</BauhausSectionLabel>
    );
    expect(container.querySelector(".bauhaus-section-label")?.className).toContain("label-extra");
  });
});

// ════════════════════════════════════════════════════════════════════
// BauhausDisplay
// ════════════════════════════════════════════════════════════════════
describe("BauhausDisplay", () => {
  it("基本渲染：默认 as=h2 + 语义类", () => {
    const { container } = render(<BauhausDisplay>HERMES</BauhausDisplay>);
    expect(screen.getByText("HERMES")).toBeInTheDocument();
    const root = container.querySelector(".bauhaus-display");
    expect(root).not.toBeNull();
    expect(root?.tagName).toBe("H2");
  });

  it("as 透传：支持 h1/h3", () => {
    const { container: h1C } = render(<BauhausDisplay as="h1">A</BauhausDisplay>);
    expect(h1C.querySelector(".bauhaus-display")?.tagName).toBe("H1");

    const { container: h3C } = render(<BauhausDisplay as="h3">B</BauhausDisplay>);
    expect(h3C.querySelector(".bauhaus-display")?.tagName).toBe("H3");
  });

  it("className 透传", () => {
    const { container } = render(<BauhausDisplay className="display-extra">X</BauhausDisplay>);
    expect(container.querySelector(".bauhaus-display")?.className).toContain("display-extra");
  });
});

// ════════════════════════════════════════════════════════════════════
// BauhausGeometry
// ════════════════════════════════════════════════════════════════════
describe("BauhausGeometry", () => {
  it("默认 positions=['tr','br']：渲染 2 个装饰元素", () => {
    const { container } = render(<BauhausGeometry />);
    const items = container.querySelectorAll(".bauhaus-geometry");
    expect(items.length).toBe(2);
    expect(items[0].className).toContain("pos-tr");
    expect(items[1].className).toContain("pos-br");
  });

  it("自定义 positions：['tr','br','ml'] 渲染 3 个", () => {
    const { container } = render(<BauhausGeometry positions={["tr", "br", "ml"]} />);
    const items = container.querySelectorAll(".bauhaus-geometry");
    expect(items.length).toBe(3);
    expect(items[2].className).toContain("pos-ml");
  });

  it("空 positions：渲染 0 个", () => {
    const { container } = render(<BauhausGeometry positions={[]} />);
    expect(container.querySelectorAll(".bauhaus-geometry").length).toBe(0);
  });

  it("aria-hidden=true 保证 a11y", () => {
    const { container } = render(<BauhausGeometry />);
    const items = container.querySelectorAll(".bauhaus-geometry");
    items.forEach((item) => {
      expect(item.getAttribute("aria-hidden")).toBe("true");
    });
  });

  it("className 透传到每个装饰元素", () => {
    const { container } = render(<BauhausGeometry className="geom-extra" />);
    const items = container.querySelectorAll(".bauhaus-geometry");
    items.forEach((item) => {
      expect(item.className).toContain("geom-extra");
    });
  });
});

// ════════════════════════════════════════════════════════════════════
// BauhausLayout
// ════════════════════════════════════════════════════════════════════
describe("BauhausLayout", () => {
  it("无 aside：仅渲染 main，不应用 bauhaus-layout 类", () => {
    const { container } = render(
      <BauhausLayout main={<p>主内容</p>} />
    );
    expect(screen.getByText("主内容")).toBeInTheDocument();
    expect(container.querySelector(".bauhaus-layout")).toBeNull();
    expect(container.querySelector("aside")).toBeNull();
  });

  it("有 aside：应用 bauhaus-layout 类 + aside 元素", () => {
    const { container } = render(
      <BauhausLayout
        main={<p>主内容</p>}
        aside={<p>辅助</p>}
      />
    );
    expect(screen.getByText("主内容")).toBeInTheDocument();
    expect(screen.getByText("辅助")).toBeInTheDocument();
    expect(container.querySelector(".bauhaus-layout")).not.toBeNull();
    expect(container.querySelector("aside")).not.toBeNull();
  });

  it("className 透传（有 aside 时）", () => {
    const { container } = render(
      <BauhausLayout
        main={<p>M</p>}
        aside={<p>A</p>}
        className="layout-extra"
      />
    );
    expect(container.querySelector(".bauhaus-layout")?.className).toContain("layout-extra");
  });

  it("className 透传（无 aside 时应用到外层 div）", () => {
    const { container } = render(
      <BauhausLayout main={<p>M</p>} className="layout-extra" />
    );
    const outer = container.firstChild as HTMLElement;
    expect(outer.className).toContain("layout-extra");
  });
});

// ════════════════════════════════════════════════════════════════════
// BauhausBrandMark
// ════════════════════════════════════════════════════════════════════
describe("BauhausBrandMark", () => {
  it("渲染为 <span.brand-mark> + aria-hidden", () => {
    const { container } = render(<BauhausBrandMark />);
    const mark = container.querySelector(".brand-mark");
    expect(mark).not.toBeNull();
    expect(mark?.tagName).toBe("SPAN");
    expect(mark?.getAttribute("aria-hidden")).toBe("true");
  });

  it("className 透传", () => {
    const { container } = render(<BauhausBrandMark className="mark-extra" />);
    expect(container.querySelector(".brand-mark")?.className).toContain("mark-extra");
  });
});
