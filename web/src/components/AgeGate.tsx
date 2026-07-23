import { useEffect, useState } from "react";
import { api } from "../api";

interface AgeGateProps {
  onConfirm: () => void;
}

/** 年龄门（M1-08）：未满 18 岁请勿访问。 */
export function AgeGate({ onConfirm }: AgeGateProps) {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.ageGateStatus().then((s) => {
      setEnabled(s.age_gate_enabled);
      setMessage(s.message);
      // 未启用年龄门直接放行
      if (!s.age_gate_enabled) onConfirm();
    }).catch(() => {
      // 接口失败也放行，避免阻塞
      onConfirm();
    });
  }, [onConfirm]);

  if (enabled === null || !enabled) {
    return null;
  }

  const handleConfirm = async (confirmed: boolean) => {
    setLoading(true);
    try {
      await api.ageGateConfirm(confirmed);
      if (confirmed) onConfirm();
      else window.location.href = "about:blank";
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-brand-gradient bg-noise">
      <div
        className="max-w-md w-full mx-6 p-10 text-center relative"
        style={{
          background: "rgba(255, 255, 255, 0.06)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(201, 162, 39, 0.3)",
          borderRadius: "var(--r-lg)",
        }}
      >
        {/* 顶部金线 */}
        <hr className="divider-gold mb-8" />

        <div className="text-5xl mb-4">🍷</div>

        <p className="eyebrow mb-3" style={{ color: "var(--gold-300)" }}>AGE VERIFICATION</p>

        <h2
          className="text-gold-foil mb-4"
          style={{ fontFamily: "var(--font-serif)", fontSize: "1.75rem", fontWeight: 600 }}
        >
          年龄确认
        </h2>

        {message && (
          <p className="mb-3" style={{ color: "rgba(250, 243, 220, 0.85)", fontFamily: "var(--font-serif)", fontSize: "0.95rem" }}>
            {message}
          </p>
        )}

        <p className="text-sm mb-8" style={{ color: "rgba(250, 243, 220, 0.6)", fontFamily: "var(--font-sans)" }}>
          本站内容含酒类知识，依据相关法律法规，未满 18 岁请勿访问。
        </p>

        <div className="flex gap-3">
          <button
            className="btn-secondary flex-1"
            onClick={() => handleConfirm(false)}
            disabled={loading}
            style={{ color: "rgba(250, 243, 220, 0.8)", borderColor: "rgba(250, 243, 220, 0.3)" }}
          >
            我未满 18 岁
          </button>
          <button
            className="btn-primary flex-1"
            onClick={() => handleConfirm(true)}
            disabled={loading}
          >
            我已满 18 岁
          </button>
        </div>

        {/* 底部金线 */}
        <hr className="divider-gold mt-8" />
      </div>
    </div>
  );
}
