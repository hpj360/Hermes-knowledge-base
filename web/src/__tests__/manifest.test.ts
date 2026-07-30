/**
 * SubTask 13.6: PWA manifest.json 字段校验
 *
 * 说明：tsconfig 已启用 resolveJsonModule，且项目未安装 @types/node
 * （约束禁止新增依赖），因此直接 import JSON 读取 manifest，
 * 而非 fs.readFileSync —— 同样达到「读取并断言字段」的目的且类型安全。
 */
import { describe, it, expect } from "vitest";
import manifest from "../../public/manifest.json";

describe("manifest.json (PWA)", () => {
  it("包含必要字段：name / short_name / display / theme_color / icons", () => {
    expect(manifest.name).toBe("Hermes 知识库");
    expect(manifest.short_name).toBe("Hermes");
    expect(manifest.theme_color).toBe("#6b2c2c");
    expect(Array.isArray(manifest.icons)).toBe(true);
    expect(manifest.icons.length).toBeGreaterThan(0);
    // 任务 13.1：start_url / background_color / lang / orientation 齐全
    expect(manifest.start_url).toBe("/");
    expect(manifest.background_color).toBe("#fafaf7");
    expect(manifest.lang).toBe("zh-CN");
    expect(manifest.orientation).toBe("portrait-primary");
  });

  it("display 为 standalone（独立窗口模式）", () => {
    expect(manifest.display).toBe("standalone");
  });

  it("icons 引用 /icon-192.png 与 /icon-512.png 占位图标", () => {
    const srcs = manifest.icons.map((i: { src: string }) => i.src);
    expect(srcs).toEqual(expect.arrayContaining(["/icon-192.png", "/icon-512.png"]));
  });
});
