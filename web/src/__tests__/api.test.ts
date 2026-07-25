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
          version: "0.5.0",
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

  // ---------------------------------------------------------------
  // 实验室 / 文档 / 认证 / 年龄门 / 标签：补齐 API 客户端契约测试
  // ---------------------------------------------------------------
  describe("lab API 端点契约", () => {
    it("labMatch：用 ingredients 拼接 query string", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ full_match: [], partial_match: [] }),
      });
      await api.labMatch(["金酒", "汤力水"]);
      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toContain("/api/lab/match?ingredients=");
      expect(url).toContain(encodeURIComponent("金酒,汤力水"));
    });

    it("labHot：limit 与 days 进入 query string", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [] }),
      });
      await api.labHot(5, 7);
      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toContain("limit=5");
      expect(url).toContain("days=7");
    });

    it("labView：POST /api/lab/view/{doc_id}", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ doc_id: "d1", status: "ok" }),
      });
      const r = await api.labView("d1");
      expect(r.status).toBe("ok");
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toContain("/api/lab/view/d1");
      expect(init.method).toBe("POST");
    });

    it("labDaily：GET /api/lab/daily", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ title: "Mojito", reason: "season" }),
      });
      const r = await api.labDaily();
      expect(r.title).toBe("Mojito");
      expect(fetchMock.mock.calls[0][0]).toBe("/api/lab/daily");
    });

    it("labSaveSubstitute：POST JSON body", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ canonical: "金酒", substitute: "伏特加", status: "ok" }),
      });
      await api.labSaveSubstitute("金酒", "伏特加");
      const [, init] = fetchMock.mock.calls[0];
      expect(init.method).toBe("POST");
      expect(init.body).toBe(JSON.stringify({ canonical: "金酒", substitute: "伏特加" }));
    });

    it("labSync：POST /api/lab/sync 含 source 与可选 limit", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ source: "iba", imported: 1 }),
      });
      await api.labSync("iba", 10);
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/api/lab/sync");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body)).toEqual({ source: "iba", limit: 10 });
    });

    it("labSync：省略 limit 时不写入 limit 字段", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ source: "iba" }),
      });
      await api.labSync("iba");
      const [, init] = fetchMock.mock.calls[0];
      expect(JSON.parse(init.body)).toEqual({ source: "iba" });
    });

    it("labRecipes：筛选参数拼到 query string", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [] }),
      });
      await api.labRecipes({ source: "iba", verified: true, limit: 20 });
      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toContain("source=iba");
      expect(url).toContain("verified=true");
      expect(url).toContain("limit=20");
    });

    it("labVerifyRecipe：POST verify 端点", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ doc_id: "d1", status: "verified" }),
      });
      await api.labVerifyRecipe("d1");
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toContain("/api/lab/recipes/d1/verify");
      expect(init.method).toBe("POST");
    });

    it("labHideRecipe：hidden flag 通过 query 传递", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ doc_id: "d1", hidden: true }),
      });
      await api.labHideRecipe("d1", true);
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toContain("/api/lab/recipes/d1/hide?hidden=true");
      expect(init.method).toBe("POST");
    });

    it("labCreateRecipe：POST 配方创建", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ doc_id: "d1", status: "ok", title: "T" }),
      });
      const payload = {
        title: "金汤力",
        ingredients: ["金酒", "汤力水"],
        content: "倒一起",
      };
      await api.labCreateRecipe(payload);
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/api/lab/recipes");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body)).toEqual(payload);
    });

    it("labUpdateRecipe：PUT 编辑端点", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ doc_id: "d1", status: "ok" }),
      });
      await api.labUpdateRecipe("d1", { title: "新名" });
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/api/lab/recipes/d1");
      expect(init.method).toBe("PUT");
      expect(JSON.parse(init.body)).toEqual({ title: "新名" });
    });

    it("labSubmitRecipe / labApproveRecipe / labRejectRecipe：状态机端点", async () => {
      const transitions: Array<[string, () => Promise<unknown>]> = [
        ["submit", () => api.labSubmitRecipe("d1")],
        ["approve", () => api.labApproveRecipe("d1")],
        ["reject", () => api.labRejectRecipe("d1", "理由")],
      ];
      for (const [name, fn] of transitions) {
        fetchMock.mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ doc_id: "d1", status: name }),
        });
        await fn();
        const last = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
        const [url, init] = last as [string, RequestInit];
        expect(url).toContain(`/api/lab/recipes/d1/${name}`);
        expect(init.method).toBe("POST");
      }
    });

    it("labListVariants：GET 变体列表", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [], count: 0 }),
      });
      await api.labListVariants("d1");
      expect(fetchMock.mock.calls[0][0]).toContain("/api/lab/recipes/d1/variants");
    });

    it("labCreateVariant：POST 关联变体", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ base_doc_id: "d1", variant_doc_id: "d2", status: "ok" }),
      });
      await api.labCreateVariant("d1", { variant_doc_id: "d2", variant_note: "n" });
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toContain("/api/lab/recipes/d1/variant");
      expect(init.method).toBe("POST");
    });

    it("labSyncAll：POST /api/lab/sync-all", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          status: "ok",
          results: { iba_dataset: { imported: 1, skipped: 0, failed: 0 } },
        }),
      });
      const r = await api.labSyncAll();
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/api/lab/sync-all");
      expect(init.method).toBe("POST");
      expect(r.results.iba_dataset?.imported).toBe(1);
    });

    it("labSyncStatus：GET /api/lab/sync-status", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ total_recipes: 10, by_source: { iba: 5 }, substitutes: 3 }),
      });
      const r = await api.labSyncStatus();
      expect(r.total_recipes).toBe(10);
      expect(fetchMock.mock.calls[0][0]).toBe("/api/lab/sync-status");
    });

    it("labRecipeStats：GET 单配方统计", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          doc_id: "d1",
          title: "Mojito",
          abv: 12.5,
          calories: 180,
          source: "frontmatter",
        }),
      });
      const r = await api.labRecipeStats("d1");
      expect(r.abv).toBe(12.5);
      expect(fetchMock.mock.calls[0][0]).toContain("/api/lab/recipes/d1/stats");
    });

    it("labListSubstitutes：传 canonical 时拼到 query", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ canonical: "金酒", substitutes: ["伏特加"] }),
      });
      await api.labListSubstitutes("金酒");
      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toContain("canonical=");
      expect(url).toContain(encodeURIComponent("金酒"));
    });

    it("labListSubstitutes：不传 canonical 时无 query", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ total: 0, items: [] }),
      });
      await api.labListSubstitutes();
      expect(fetchMock.mock.calls[0][0]).toBe("/api/lab/substitutes");
    });

    it("labImaListKbs：query 与 limit 进入 query string", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0 }),
      });
      await api.labImaListKbs("鸡尾酒", 10);
      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toContain("query=");
      expect(url).toContain("limit=10");
    });

    it("labImaSync：POST 同步含全部字段", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          source: "ima",
          kb_id: "kb1",
          imported: 1,
          skipped: 0,
          failed: 0,
          items: [],
        }),
      });
      await api.labImaSync({ query: "q", kb_id: "kb1", limit: 5, category: "资料" });
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/api/lab/ima/sync");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body)).toEqual({
        query: "q",
        kb_id: "kb1",
        limit: 5,
        category: "资料",
      });
    });

    it("labImaSearch：query 必传，kbId/limit 可选", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ info_list: [], cursor: "", has_more: false }),
      });
      await api.labImaSearch("test", "kb1", 3);
      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toContain("query=test");
      expect(url).toContain("kb_id=kb1");
      expect(url).toContain("limit=3");
    });

    it("labTranslateTitles：默认参数（空 doc_ids/source + limit 50）", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          status: "ok",
          translated: 0,
          skipped: 0,
          failed: 0,
          model_used: "mock-llm",
        }),
      });
      const r = await api.labTranslateTitles({});
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/api/lab/translate-titles");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body)).toEqual({
        doc_ids: [],
        source: "",
        limit: 50,
      });
      expect(r.model_used).toBe("mock-llm");
      expect(r.translated).toBe(0);
    });

    it("labTranslateTitles：传 doc_ids + source + limit", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          status: "ok",
          translated: 3,
          skipped: 1,
          failed: 0,
          model_used: "gpt-4o-mini",
        }),
      });
      await api.labTranslateTitles({
        doc_ids: ["d1", "d2"],
        source: "iba",
        limit: 100,
      });
      expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
        doc_ids: ["d1", "d2"],
        source: "iba",
        limit: 100,
      });
    });

    it("labTranslateTitles：HTTP 400 时抛错并带 detail", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: "limit 超出范围" }),
      });
      await expect(api.labTranslateTitles({ limit: 9999 })).rejects.toThrow("limit 超出范围");
    });
  });

  describe("文档/标签/认证/年龄门 API 契约", () => {
    it("listDocuments：category 与 tag_id 拼接", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ total: 0, items: [] }),
      });
      await api.listDocuments("recipe", 7);
      const url = fetchMock.mock.calls[0][0] as string;
      expect(url).toContain("category=recipe");
      expect(url).toContain("tag_id=7");
    });

    it("importText：POST 含 source_type/file_type", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ doc_id: "d1", status: "ok" }),
      });
      await api.importText("T", "内容", "recipe");
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/api/documents/import-text");
      const body = JSON.parse(init.body);
      expect(body.title).toBe("T");
      expect(body.content).toBe("内容");
      expect(body.source_type).toBe("local");
      expect(body.file_type).toBe("txt");
      expect(body.category).toBe("recipe");
    });

    it("getDocument：GET /api/documents/{docId}", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ doc: { doc_id: "d1" }, tags: [], chunks: [] }),
      });
      await api.getDocument("d1");
      expect(fetchMock.mock.calls[0][0]).toBe("/api/documents/d1");
    });

    it("updateDocMetadata：PUT 含 title/category/tag_ids", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: "ok" }),
      });
      await api.updateDocMetadata("d1", { title: "新标题", tag_ids: [1, 2] });
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/api/documents/d1/metadata");
      expect(init.method).toBe("PUT");
      expect(JSON.parse(init.body)).toEqual({ title: "新标题", tag_ids: [1, 2] });
    });

    it("createTag / deleteTag：POST 与 DELETE", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ id: 5, name: "tag", color: "#fff" }),
      });
      await api.createTag("tag", "#fff");
      expect(fetchMock.mock.calls[0][1].method).toBe("POST");

      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: "ok" }),
      });
      await api.deleteTag(5);
      const [url2, init2] = fetchMock.mock.calls[1];
      expect(url2).toBe("/api/tags/5");
      expect(init2.method).toBe("DELETE");
    });

    it("ask：POST 含 query 与 top_k", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ answer_id: "a1", query: "q", answer: "a", citations: [], model_used: "m", latency_ms: 1, rejected: false, low_confidence: false }),
      });
      await api.ask("金酒怎么调", 5);
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/api/ask");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body)).toEqual({ query: "金酒怎么调", top_k: 5 });
    });

    it("history：limit 进入 query", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ total: 0, items: [] }),
      });
      await api.history(20);
      expect(fetchMock.mock.calls[0][0]).toBe("/api/history?limit=20");
    });

    it("feedback：POST 含 feedback 值", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: "ok" }),
      });
      await api.feedback(7, 1);
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/api/feedback/7");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body)).toEqual({ feedback: 1 });
    });

    it("seed：POST /api/seed", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ seeded: 1, failed: 0, items: [] }),
      });
      await api.seed();
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/api/seed");
      expect(init.method).toBe("POST");
    });

    it("login：POST 含 password", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ token: "tk", auth_enabled: true }),
      });
      const r = await api.login("pwd");
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/api/auth/login");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body)).toEqual({ password: "pwd" });
      expect(r.token).toBe("tk");
    });

    it("me：GET /api/auth/me", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ auth_enabled: true, username: "admin" }),
      });
      const r = await api.me();
      expect(r.username).toBe("admin");
      expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/me");
    });

    it("ageGateStatus / ageGateConfirm：GET 与 POST", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ age_gate_enabled: true, message: "msg" }),
      });
      await api.ageGateStatus();
      expect(fetchMock.mock.calls[0][0]).toBe("/api/age-gate/status");

      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ confirmed: true }),
      });
      await api.ageGateConfirm(true);
      const [url2, init2] = fetchMock.mock.calls[1];
      expect(url2).toBe("/api/age-gate/confirm");
      expect(init2.method).toBe("POST");
      expect(JSON.parse(init2.body)).toEqual({ confirmed: true });
    });

    it("listCategories：GET /api/categories", async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ total: 0, items: [] }),
      });
      await api.listCategories();
      expect(fetchMock.mock.calls[0][0]).toBe("/api/categories");
    });
  });
});
