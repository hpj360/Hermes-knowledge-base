import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { CitationList } from "./CitationList";
import { HistoryPanel } from "./HistoryPanel";
import { showToast } from "./Toast";
import {
  BodyText,
  MetaText,
  MonoText,
  BauhausSectionLabel,
  BauhausDisplay,
  BauhausChip,
  BauhausButton,
} from "./ui";
import type { Citation, ExternalRef, SSEEvent } from "../types";

interface ChatPanelProps {
  refreshDocs: () => void;
  onJumpToDoc?: (docId: string, chunkRowid?: number) => void;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  rejected?: boolean;
  lowConfidence?: boolean;
  modelUsed?: string;
  latencyMs?: number;
  streaming?: boolean;
  externalRefs?: ExternalRef[];  // B6+: IMA「酒博士」外部参考
}

/** 问答面板（M1-03：SSE 流式生成）。 */
export function ChatPanel({ refreshDocs, onJumpToDoc }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  // 视图切换：chat（默认问答）/ history（问答历史）
  const [view, setView] = useState<"chat" | "history">("chat");
  const abortRef = useRef<AbortController | null>(null);

  // 7.3 冷启动溯源引导：首次收到带引用答案时在 CitationList 上方展示提示条，
  // 通过 localStorage hermes_kb_citation_hint_seen 跨会话只展示一次
  const [hintVisible, setHintVisible] = useState(() =>
    localStorage.getItem("hermes_kb_citation_hint_seen") !== "true"
  );
  // 本会话第一条带引用的 assistant 消息索引（仅在该条上展示提示，避免后续重复）
  const firstCitedIdx = messages.findIndex(
    (m) => m.role === "assistant" && m.citations && m.citations.length > 0
  );
  // 首次出现带引用答案后写入 localStorage，标记已展示过
  useEffect(() => {
    if (firstCitedIdx !== -1 && hintVisible) {
      localStorage.setItem("hermes_kb_citation_hint_seen", "true");
    }
  }, [firstCitedIdx, hintVisible]);

  // P2-4: 组件卸载时中止进行中的 SSE 流，避免 LLM token 泄漏与卸载后 setState
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const send = async () => {
    const query = input.trim();
    if (!query || loading) return;

    setInput("");
    setLoading(true);
    const userMsg: Message = { role: "user", content: query };
    const asstMsg: Message = {
      role: "assistant",
      content: "",
      streaming: true,
      citations: [],
    };
    setMessages((m) => [...m, userMsg, asstMsg]);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      await api.askStream(
        query,
        undefined,
        (evt: SSEEvent) => {
          if (evt.type === "meta") {
            setMessages((m) => {
              const copy = [...m];
              const last = copy[copy.length - 1];
              copy[copy.length - 1] = {
                ...last,
                citations: evt.citations,
                rejected: evt.rejected,
                lowConfidence: evt.low_confidence,
                modelUsed: evt.model_used,
                externalRefs: evt.external_refs ?? [],
              };
              return copy;
            });
          } else if (evt.type === "delta") {
            setMessages((m) => {
              const copy = [...m];
              const last = copy[copy.length - 1];
              copy[copy.length - 1] = {
                ...last,
                content: last.content + evt.content,
              };
              return copy;
            });
          } else if (evt.type === "done") {
            setMessages((m) => {
              const copy = [...m];
              const last = copy[copy.length - 1];
              copy[copy.length - 1] = {
                ...last,
                streaming: false,
                latencyMs: evt.latency_ms,
              };
              return copy;
            });
          } else if (evt.type === "error") {
            setMessages((m) => {
              const copy = [...m];
              const last = copy[copy.length - 1];
              copy[copy.length - 1] = {
                ...last,
                content: `生成失败：${evt.message}`,
                streaming: false,
              };
              return copy;
            });
          }
        },
        ctrl.signal
      );
    } catch (err) {
      setMessages((m) => {
        const copy = [...m];
        const last = copy[copy.length - 1];
        copy[copy.length - 1] = {
          ...last,
          content:
            err instanceof Error && err.name === "AbortError"
              ? "（已取消）"
              : `请求失败：${err instanceof Error ? err.message : String(err)}`,
          streaming: false,
        };
        return copy;
      });
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  };

  const cancel = () => {
    abortRef.current?.abort();
  };

  const seed = async () => {
    setLoading(true);
    try {
      const r = await api.seed();
      showToast(`种子导入完成：成功 ${r.seeded} 篇，失败 ${r.failed} 篇`, "success");
      refreshDocs();
    } catch (err) {
      showToast(`种子导入失败：${err instanceof Error ? err.message : err}`, "danger");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* 工具栏 */}
      <div className="flex items-center justify-between px-6 py-3 border-b bg-[color:var(--ink-50)] border-[color:var(--ink-200)]">
        <div className="flex items-baseline gap-3">
          <BauhausSectionLabel>Q&amp;A</BauhausSectionLabel>
          <h2 className="section-title text-base">问答</h2>
        </div>
        <div className="flex items-center gap-2">
          {view === "history" ? (
            <BauhausButton
              variant="outline"
              onClick={() => setView("chat")}
              className="text-xs"
            >
              返回问答
            </BauhausButton>
          ) : (
            <BauhausButton
              variant="outline"
              onClick={() => setView("history")}
              className="text-xs"
            >
              历史
            </BauhausButton>
          )}
          <BauhausButton
            variant="outline"
            onClick={seed}
            disabled={loading}
            className="text-xs"
          >
            导入种子知识
          </BauhausButton>
        </div>
      </div>

      {view === "history" ? (
        <HistoryPanel onBack={() => setView("chat")} />
      ) : (
        <>
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
            <div className="text-center max-w-lg">
              <div className="mb-4 flex justify-center">
                <BauhausSectionLabel>HERMES · 知识库</BauhausSectionLabel>
              </div>
              <BauhausDisplay as="h2" className="mb-4">
                向 Hermes 知识库提问吧
              </BauhausDisplay>
              <div
                className="mx-auto mb-8"
                style={{ width: 44, height: 4, background: "var(--ink-900)" }}
                aria-hidden="true"
              />
              <MetaText className="text-sm mb-8">
                选择下方问题，或直接输入你想了解的酒类知识
              </MetaText>
              <div className="space-y-3">
                {[
                  "金酒的核心风味是什么？",
                  "波本威士忌和苏格兰威士忌有何区别？",
                  "如何调制一杯经典马天尼？",
                ].map((q, i) => (
                  <button
                    key={q}
                    onClick={() => setInput(q)}
                    className="block w-full text-left bauhaus-card px-5 py-3 transition-colors"
                    style={{ color: "var(--ink-900)" }}
                  >
                    <span className="numeral mr-3">{String(i + 1).padStart(2, "0")}</span>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {/*
              消息气泡：包豪斯几何风格
              用户气泡：brand-100 浅底 + wine 深字
              AI 气泡：白底 + amber 左边框 + shadow-sm
            */}
            <div
              className="max-w-3xl rounded-lg px-4 py-3"
              style={
                m.role === "user"
                  ? {
                      background: "var(--brand-100)",
                      color: "var(--wine)",
                      borderRadius: "var(--r-md)",
                    }
                  : {
                      background: "#fff",
                      border: "1px solid var(--ink-200)",
                      borderLeft: "3px solid var(--amber)",
                      borderRadius: "var(--r-md)",
                      boxShadow: "var(--shadow-sm)",
                    }
              }
            >
              {m.role === "user" ? (
                <p className="whitespace-pre-wrap">{m.content}</p>
              ) : (
                <>
                  {m.rejected && (
                    <div
                      className="text-xs px-2 py-1 rounded mb-2 font-[family-name:var(--font-ui)] text-[color:var(--danger)]"
                      style={{ background: "rgba(179, 38, 30, 0.08)" }}
                      role="alert"
                    >
                      已拒绝：检测到越狱尝试
                    </div>
                  )}
                  {m.lowConfidence && (
                    <div className="text-xs px-2 py-1 rounded mb-2 bg-[color:var(--gold-100)] text-[color:var(--warning)] font-[family-name:var(--font-ui)]">
                      低置信度：知识库中暂无足够相关信息
                    </div>
                  )}
                  <BodyText as="p" className="whitespace-pre-wrap">
                    {m.content || (m.streaming ? "生成中..." : "")}
                    {m.streaming && (
                      <span
                        className="inline-block w-2 h-4 ml-1 align-middle animate-pulse"
                        style={{ background: "var(--wine)" }}
                      />
                    )}
                  </BodyText>
                  {m.citations && m.citations.length > 0 && (
                    <>
                      {/* 7.3: 首条带引用答案上方的溯源引导提示条（包豪斯浅底 + ink-600） */}
                      {i === firstCitedIdx && hintVisible && (
                        <MetaText
                          as="div"
                          className="text-xs flex items-center justify-between gap-2 px-3 py-2 rounded mb-2 mt-3"
                          style={{
                            background: "var(--ink-50)",
                            color: "var(--ink-600)",
                          }}
                        >
                          <span>💡 点击下方引用可跳转查看原文出处</span>
                          <button
                            type="button"
                            aria-label="关闭溯源提示"
                            onClick={() => setHintVisible(false)}
                            className="text-sm leading-none hover:opacity-70 transition-opacity"
                            style={{ color: "var(--ink-600)" }}
                          >
                            ×
                          </button>
                        </MetaText>
                      )}
                      <CitationList citations={m.citations} onJumpToDoc={onJumpToDoc} />
                    </>
                  )}
                  {m.externalRefs && m.externalRefs.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-[color:var(--ink-100)]">
                      <div className="text-xs mb-2 flex items-center gap-2 text-[color:var(--ink-600)] font-[family-name:var(--font-ui)]">
                        <BauhausChip variant="amber">外部参考</BauhausChip>
                        <span>来自「酒博士」订阅知识库 · 仅供参考</span>
                      </div>
                      <ul className="space-y-1.5">
                        {m.externalRefs.map((ref, idx) => (
                          <li
                            key={`${ref.title}-${idx}`}
                            className="text-sm flex items-start gap-2 font-[family-name:var(--font-ui)]"
                          >
                            <span
                              className="numeral flex-shrink-0 text-[0.75rem]"
                              style={{ color: "var(--amber)" }}
                            >
                              {String(idx + 1).padStart(2, "0")}
                            </span>
                            <div className="flex-1 min-w-0">
                              {ref.url ? (
                                <a
                                  href={ref.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="hover:underline"
                                  style={{ color: "var(--wine)" }}
                                >
                                  {ref.title}
                                </a>
                              ) : (
                                <span className="text-[color:var(--ink-900)]">
                                  {ref.title}
                                </span>
                              )}
                              {ref.snippet && (
                                <MetaText as="p" className="text-xs mt-0.5 line-clamp-2">
                                  {ref.snippet}
                                </MetaText>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {m.latencyMs !== undefined && !m.streaming && (
                    <MonoText
                      as="div"
                      className="text-xs mt-2 pt-2 border-t border-[color:var(--ink-100)]"
                    >
                      {m.modelUsed} · {m.latencyMs}ms
                    </MonoText>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* 输入区 */}
      <div className="border-t p-4 bg-white">
        <div className="flex gap-2">
          <textarea
            className="input flex-1 resize-none"
            rows={2}
            placeholder="输入问题，回车发送，Shift+回车换行"
            aria-label="问题输入框"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            disabled={loading}
          />
          {loading ? (
            <button onClick={cancel} className="btn-danger">
              取消
            </button>
          ) : (
            <BauhausButton variant="solid" onClick={send} disabled={!input.trim()}>
              发送
            </BauhausButton>
          )}
        </div>
      </div>
        </>
      )}
    </div>
  );
}
