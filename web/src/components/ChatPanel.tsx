import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { CitationList } from "./CitationList";
import { showToast } from "./Toast";
import { BodyText, MetaText, MonoText, StatusBadge } from "./ui";
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
  const abortRef = useRef<AbortController | null>(null);

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
          <p className="eyebrow">Q&amp;A</p>
          <h2 className="section-title text-base">问答</h2>
        </div>
        <button
          onClick={seed}
          className="text-xs hover:opacity-75 text-[color:var(--brand-700)]"
          disabled={loading}
        >
          导入种子知识
        </button>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center px-6 py-12">
            <div className="text-center max-w-lg reveal-stagger">
              <p className="eyebrow mb-4">HERMES · 知识库</p>
              <h2 className="display-title mb-4">向 Hermes 知识库提问吧</h2>
              <hr className="divider-gold w-32 mx-auto mb-8" />
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
                    className="block w-full text-left card px-5 py-3 hover:shadow-md transition-shadow font-[family-name:var(--font-serif)] text-[color:var(--ink-900)]"
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
              消息气泡：critical 修复
              原实现 brand-700 深底 + 白字（颜色反了）
              修复为 mockup ask.html .msg-user 规范：brand-100 浅底 + brand-700 深字
              AI 气泡：白底 + gold-500 左边框 + shadow-sm
            */}
            <div
              className="max-w-3xl rounded-lg px-4 py-3"
              style={
                m.role === "user"
                  ? {
                      background: "var(--brand-100)",
                      color: "var(--brand-700)",
                      borderRadius: "var(--r-md)",
                    }
                  : {
                      background: "#fff",
                      border: "1px solid var(--ink-200)",
                      borderLeft: "3px solid var(--gold-500)",
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
                      <span className="inline-block w-2 h-4 ml-1 align-middle animate-pulse bg-[color:var(--brand-500)]" />
                    )}
                  </BodyText>
                  {m.citations && m.citations.length > 0 && (
                    <CitationList citations={m.citations} onJumpToDoc={onJumpToDoc} />
                  )}
                  {m.externalRefs && m.externalRefs.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-[color:var(--ink-100)]">
                      <div className="text-xs mb-2 flex items-center gap-2 text-[color:var(--ink-600)] font-[family-name:var(--font-ui)]">
                        <StatusBadge variant="warning">外部参考</StatusBadge>
                        <span>来自「酒博士」订阅知识库 · 仅供参考</span>
                      </div>
                      <ul className="space-y-1.5">
                        {m.externalRefs.map((ref, idx) => (
                          <li
                            key={`${ref.title}-${idx}`}
                            className="text-sm flex items-start gap-2 font-[family-name:var(--font-ui)]"
                          >
                            <span className="numeral flex-shrink-0 text-[color:var(--gold-500)] text-[0.75rem]">
                              {String(idx + 1).padStart(2, "0")}
                            </span>
                            <div className="flex-1 min-w-0">
                              {ref.url ? (
                                <a
                                  href={ref.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="hover:underline text-[color:var(--brand-700)]"
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
            <button
              onClick={send}
              className="btn-primary"
              disabled={!input.trim()}
            >
              发送
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
