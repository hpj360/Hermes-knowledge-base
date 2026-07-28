import { useState } from "react";
import { TagPanel } from "./TagPanel";
import { BauhausSectionLabel, BauhausDisplay, BauhausCard, BodyText } from "./ui";

interface SettingsPanelProps {
  onChange: () => void;
}

type SettingsTab = "tags" | "export" | "audit";

// 设置中心三个子模块 tab。数据导出 / 审计日志后端暂无对应 API（api.ts 未实现），
// 故展示“即将上线”占位；后端补齐后只需在下方分支接入 api 调用即可。
const TABS: ReadonlyArray<{ key: SettingsTab; label: string }> = [
  { key: "tags", label: "标签管理" },
  { key: "export", label: "数据导出" },
  { key: "audit", label: "审计日志" },
];

/** 设置中心：聚合标签管理、数据导出、审计日志三个子模块的容器。 */
export function SettingsPanel({ onChange }: SettingsPanelProps) {
  const [active, setActive] = useState<SettingsTab>("tags");

  return (
    <div>
      {/* 顶部标题 + 子模块 tab（pb-0 使 tab 的下边框紧贴内容区） */}
      <div className="p-8 max-w-3xl mx-auto pb-0">
        <div className="mb-8">
          <BauhausSectionLabel className="mb-2">SETTINGS</BauhausSectionLabel>
          <BauhausDisplay as="h2">设置中心</BauhausDisplay>
          <hr className="divider-gold w-24 mt-4" />
        </div>
        <nav
          className="flex items-center gap-1 border-b border-ink-200"
          aria-label="设置子模块"
        >
          {TABS.map((tab) => {
            const isActive = active === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActive(tab.key)}
                className={`nav-tab ${isActive ? "nav-tab-active" : ""}`}
                aria-current={isActive ? "page" : undefined}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* 子模块内容：标签管理直接复用 TagPanel（自带容器与标题，避免双重包裹） */}
      {active === "tags" && <TagPanel onChange={onChange} />}

      {active === "export" && (
        <div className="p-8 max-w-3xl mx-auto">
          <ComingSoonCard message="数据导出功能即将上线" />
        </div>
      )}

      {active === "audit" && (
        <div className="p-8 max-w-3xl mx-auto">
          <ComingSoonCard message="审计日志功能即将上线" />
        </div>
      )}
    </div>
  );
}

/** “即将上线”占位卡片：保持包豪斯视觉风格（金菱形 + mono 标签 + 正文）。 */
function ComingSoonCard({ message }: { message: string }) {
  return (
    <BauhausCard className="p-12 text-center">
      <div className="text-2xl mb-2 text-gold-500">◆</div>
      <BauhausSectionLabel className="mb-2">COMING SOON</BauhausSectionLabel>
      <BodyText className="text-sm">{message}</BodyText>
    </BauhausCard>
  );
}
