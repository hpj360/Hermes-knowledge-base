/** api.ts 单元测试：SSE 解析 + 请求封装 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock localStorage
const ls: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((k: string) => ls[k] ?? null),
  setItem: vi.fn((k: string, v: string) => { ls[k] = v; }),
  removeItem: vi.fn((k: string) => { delete ls[k]; }),
  clear: vi.fn(() => { for (const k of Object.keys(ls)) delete ls[k]; }),
};
vi.stubGlobal("localStorage", localStorageMock);

// Mock fetch
const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

// Mock import.meta.env
vi.stubEnv("VITE_API_BASE", "");

// Import after mocks are set up
const { api } = await import("../api");

describe("api client", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("authHeaders + request", () => {
    it("attaches Bearer token when present in localStorage", async () => {
      ls["hermes_kb_token"] = "test-token-123";
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: "ok" }),
      });
      await api.health();
      const [, init] = fetchMock.mock.calls[0];
      expect(init.headers.Authorization).toBe("Bearer test-token-123");
    });

    it("omits Authorization header when no token", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: "ok" }),
      });
      await api.health();
      const [, init] = fetchMock.mock.calls[0];
      expect(init.headers.Authorization).toBeUndefined();
    });

    it("throws Error with detail from response body on non-ok", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({ detail: "validation failed" }),
      });
      await expect(api.health()).rejects.toThrow("validation failed");
    });

    it("falls back to HTTP status when body has no detail", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({}),
      });
      await expect(api.health()).rejects.toThrow("HTTP 500");
    });

    it("returns undefined for 204 No Content", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });
      const result = await api.deleteDocument("doc-1");
      expect(result).toBeUndefined();
    });
  });

  describe("askStream SSE parsing", () => {
    /** Build a ReadableStream from an array of string chunks. */
    function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
      const encoder = new TextEncoder();
      return new ReadableStream({
        start(controller) {
          for (const c of chunks) controller.enqueue(encoder.encode(c));
          controller.close();
        },
      });
    }

    it("parses meta + delta + done events in sequence", async () => {
      const ssePayload = [
        'data: {"type":"meta","citations":[],"rejected":false,"low_confidence":false,"model_used":"mock","latency_ms":0}\n',
        'data: {"type":"delta","content":"Hello"}\n',
        'data: {"type":"delta","content":" world"}\n',
        'data: {"type":"done","latency_ms":42}\n',
      ].join("");
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: makeStream([ssePayload]),
      });

      const events: string[] = [];
      await api.askStream("hi", undefined, (evt) => {
        events.push(evt.type);
      });

      expect(events).toEqual(["meta", "delta", "delta", "done"]);
    });

    it("handles error event type", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: makeStream(['data: {"type":"error","message":"LLM timeout"}\n']),
      });

      const events: string[] = [];
      await api.askStream("hi", undefined, (evt) => {
        events.push(evt.type);
      });

      expect(events).toEqual(["error"]);
    });

    it("skips malformed SSE lines without throwing", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: makeStream([
          'data: {"type":"delta","content":"ok"}\n',
          "data: {broken json}\n",
          'data: {"type":"done","latency_ms":10}\n',
        ]),
      });

      const events: string[] = [];
      await api.askStream("hi", undefined, (evt) => {
        events.push(evt.type);
      });

      // malformed line silently skipped, valid events still processed
      expect(events).toEqual(["delta", "done"]);
    });

    it("handles split chunks across line boundaries", async () => {
      // A single SSE event split across two chunks
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: makeStream([
          'data: {"type":"delta","conte',
          'nt":"split"}\n',
        ]),
      });

      const events: string[] = [];
      await api.askStream("hi", undefined, (evt) => {
        events.push(evt.type);
      });

      expect(events).toEqual(["delta"]);
    });

    it("throws when response is not ok", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 500,
        body: null,
      });
      await expect(
        api.askStream("hi", undefined, () => {})
      ).rejects.toThrow("流式问答失败: HTTP 500");
    });

    it("throws when response body is null", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: null,
      });
      await expect(
        api.askStream("hi", undefined, () => {})
      ).rejects.toThrow();
    });
  });

  describe("token management", () => {
    it("setToken/getToken/logout round-trip", () => {
      api.setToken("abc-123");
      expect(api.getToken()).toBe("abc-123");
      api.logout();
      expect(api.getToken()).toBeNull();
    });
  });

  describe("request 401 处理", () => {
    it("401 响应触发 onUnauthorized 并清 token", async () => {
      const { setUnauthorizedHandler } = await import("../api");
      const handler = vi.fn();
      setUnauthorizedHandler(handler);

      api.setToken("expired-token");
      fetchMock.mockResolvedValueOnce({
        status: 401,
        json: async () => ({ detail: "token expired" }),
      });

      await expect(api.health()).rejects.toThrow("登录已过期");
      expect(handler).toHaveBeenCalled();
      expect(api.getToken()).toBeNull();
      setUnauthorizedHandler(null);
    });
  });

  describe("health", () => {
    it("成功返回健康状态", async () => {
      fetchMock.mockResolvedValueOnce({
        status: 200,
        ok: true,
        json: async () => ({
          status: "ok",
          service: "hermes-kb",
          version: "0.2.0",
          time: "2026-07-21T00:00:00",
          doc_count: 5,
          llm_provider: "mock",
          llm_available: false,
          embedding_provider: "hash",
          embedding_available: false,
          auth_enabled: false,
          age_gate_enabled: true,
        }),
      });

      const h = await api.health();
      expect(h.status).toBe("ok");
      expect(h.doc_count).toBe(5);
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/health",
        expect.objectContaining({
          headers: expect.objectContaining({ "Content-Type": "application/json" }),
        })
      );
    });

    it("非 200 响应抛错", async () => {
      fetchMock.mockResolvedValueOnce({
        status: 500,
        json: async () => ({ detail: "服务器错误" }),
      });

      await expect(api.health()).rejects.toThrow("服务器错误");
    });
  });

  describe("askStream 401", () => {
    it("401 触发 onUnauthorized", async () => {
      const { setUnauthorizedHandler } = await import("../api");
      const handler = vi.fn();
      setUnauthorizedHandler(handler);

      api.setToken("expired");
      fetchMock.mockResolvedValueOnce({ status: 401 });

      await expect(
        api.askStream("测试", undefined, () => {})
      ).rejects.toThrow("登录已过期");
      expect(handler).toHaveBeenCalled();
      setUnauthorizedHandler(null);
    });
  });
});
