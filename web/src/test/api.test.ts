// api.ts 单元测试
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { api } from "../api";

// mock fetch
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
vi.stubGlobal("localStorage", localStorageMock);

describe("api", () => {
  beforeEach(() => {
    mockFetch.mockReset();
    localStorageMock.clear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("authHeaders / token", () => {
    it("getToken 返回 localStorage 中的 token", () => {
      localStorageMock.setItem("hermes_kb_token", "test-token-123");
      expect(api.getToken()).toBe("test-token-123");
    });

    it("setToken 写入 localStorage", () => {
      api.setToken("new-token");
      expect(localStorageMock.getItem("hermes_kb_token")).toBe("new-token");
    });

    it("清除 token 后 getToken 返回 null", () => {
      api.setToken("token");
      localStorageMock.removeItem("hermes_kb_token");
      expect(api.getToken()).toBeNull();
    });
  });

  describe("request 401 处理", () => {
    it("401 响应触发 onUnauthorized 并清 token", async () => {
      const handler = vi.fn();
      const { setUnauthorizedHandler } = await import("../api");
      setUnauthorizedHandler(handler);

      api.setToken("expired-token");
      mockFetch.mockResolvedValueOnce({
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
      mockFetch.mockResolvedValueOnce({
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
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/health",
        expect.objectContaining({
          headers: expect.objectContaining({ "Content-Type": "application/json" }),
        })
      );
    });

    it("非 200 响应抛错", async () => {
      mockFetch.mockResolvedValueOnce({
        status: 500,
        json: async () => ({ detail: "服务器错误" }),
      });

      await expect(api.health()).rejects.toThrow("服务器错误");
    });
  });

  describe("askStream", () => {
    it("401 触发 onUnauthorized", async () => {
      const handler = vi.fn();
      const { setUnauthorizedHandler } = await import("../api");
      setUnauthorizedHandler(handler);

      api.setToken("expired");
      mockFetch.mockResolvedValueOnce({ status: 401 });

      await expect(
        api.askStream("测试", undefined, () => {})
      ).rejects.toThrow("登录已过期");
      expect(handler).toHaveBeenCalled();
      setUnauthorizedHandler(null);
    });
  });
});
