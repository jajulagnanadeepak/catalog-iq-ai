import { apiClient, requestWithFallback } from "./client";
import { PRODUCTS, pick } from "./mock";
import type {
  BudgetPayload,
  BudgetResult,
  CopilotPayload,
  CopilotReply,
  IntentPayload,
  IntentResult,
  Paginated,
  Product,
  ProductQuery,
  Recommendation,
  SearchPayload,
  SearchResult,
  SeasonalResult,
  StylistLook,
  StylistPayload,
  VisualSearchResult,
} from "./types";

function filterSort(query: ProductQuery, source: Product[] = PRODUCTS) {
  let items = [...source];
  if (query.category && query.category !== "All")
    items = items.filter((p) => p.category === query.category);
  if (query.minPrice != null) items = items.filter((p) => p.price >= query.minPrice!);
  if (query.maxPrice != null) items = items.filter((p) => p.price <= query.maxPrice!);
  if (query.minRating != null) items = items.filter((p) => p.rating >= query.minRating!);
  if (query.sort === "price-asc") items.sort((a, b) => a.price - b.price);
  if (query.sort === "price-desc") items.sort((a, b) => b.price - a.price);
  if (query.sort === "rating") items.sort((a, b) => b.rating - a.rating);
  return items;
}

function paginate<T>(items: T[], page = 1, pageSize = 8): Paginated<T> {
  const start = (page - 1) * pageSize;
  return { items: items.slice(start, start + pageSize), page, pageSize, total: items.length };
}

/** GET /products */
export function getProducts(query: ProductQuery = {}) {
  return requestWithFallback<Paginated<Product>>(
    () => apiClient.get("/products", { params: query }),
    () => paginate(filterSort(query), query.page ?? 1, query.pageSize ?? 8),
  );
}

/** GET /products/:id */
export function getProduct(id: string) {
  return requestWithFallback<Product>(
    () => apiClient.get(`/products/${id}`),
    () => PRODUCTS.find((p) => p.id === id) ?? PRODUCTS[0]!,
  );
}

/** POST /search — semantic search */
export function postSearch(payload: SearchPayload) {
  return requestWithFallback<SearchResult>(
    () => apiClient.post("/search", payload),
    () => {
      const q = payload.query.toLowerCase().trim();
      const scored = filterSort(payload)
        .map((p) => {
          const haystack = `${p.name} ${p.brand} ${p.category} ${p.tags.join(" ")} ${p.description}`;
          const hits = q ? q.split(/\s+/).filter((t) => haystack.toLowerCase().includes(t)).length : 1;
          return { p, score: hits ? 0.6 + hits * 0.1 : 0.35 + p.rating / 20 };
        })
        .sort((a, b) => b.score - a.score);
      const page = paginate(
        scored.map((s) => s.p),
        payload.page ?? 1,
        payload.pageSize ?? 8,
      );
      return {
        ...page,
        interpretation: q
          ? `Interpreted as: intent to browse "${q}" ranked by semantic similarity across catalog embeddings.`
          : "Showing the highest-affinity catalog items for your profile.",
        matches: scored.map((s) => ({ productId: s.p.id, score: Math.min(0.99, s.score) })),
      };
    },
  );
}

/** GET /recommend */
export function getRecommendations(limit = 6) {
  return requestWithFallback<Recommendation[]>(
    () => apiClient.get("/recommend", { params: { limit } }),
    () =>
      PRODUCTS.slice(0, limit).map((product, i) => ({
        id: `r-${i}`,
        title: ["Because you viewed outerwear", "Trending in your size", "Frequently bought together", "Matches your saved palette", "Restocked near you", "High value pick"][i % 6]!,
        reason: [
          "Similar silhouette and fabric weight to items in your history.",
          "Popular with shoppers who share your style graph.",
          "Completes 3 of your saved looks.",
          "Colour-matched to your last two purchases.",
          "Back in stock in the size you follow.",
          "Best price-to-rating ratio in this category.",
        ][i % 6]!,
        confidence: 0.72 + ((i * 4) % 25) / 100,
        product,
      })),
  );
}

/** POST /intent */
export function postIntent(payload: IntentPayload) {
  return requestWithFallback<IntentResult>(
    () => apiClient.post("/intent", payload),
    () => ({
      intent: "product_discovery",
      confidence: 0.91,
      entities: [
        { label: "query", value: payload.query },
        { label: "category", value: "Outerwear" },
        { label: "budget", value: "under $300" },
      ],
    }),
  );
}

/** POST /stylist */
export function postStylist(payload: StylistPayload) {
  return requestWithFallback<StylistLook[]>(
    () => apiClient.post("/stylist", payload),
    () => {
      const looks = [pick(["p-001", "p-011", "p-008"]), pick(["p-005", "p-002", "p-006"])];
      return looks.map((items, i) => ({
        id: `look-${i}`,
        title: i === 0 ? `Refined ${payload.occasion || "evening"} layering` : `Relaxed ${payload.style || "everyday"} edit`,
        summary:
          i === 0
            ? "Structured outer layer over fine knit, grounded with clean leather. Reads polished without a suit."
            : "Soft cotton base with performance footwear and a utility carry — built for movement.",
        items,
        total: items.reduce((sum, p) => sum + p.price, 0),
      }));
    },
  );
}

/** POST /budget */
export function postBudget(payload: BudgetPayload) {
  return requestWithFallback<BudgetResult>(
    () => apiClient.post("/budget", payload),
    () => {
      const chosen = (payload.categories.length ? payload.categories : ["Tops", "Footwear", "Bags"])
        .map((category) => PRODUCTS.filter((p) => p.category === category).sort((a, b) => a.price - b.price)[0])
        .filter((p): p is (typeof PRODUCTS)[number] => Boolean(p));
      const spent = chosen.reduce((s, p) => s + p.price, 0);
      return {
        budget: payload.budget,
        spent,
        saved: Math.max(0, payload.budget - spent),
        allocations: chosen.map((product) => ({
          category: product.category,
          amount: product.price,
          product,
        })),
      };
    },
  );
}

/** POST /copilot */
export function postCopilot(payload: CopilotPayload) {
  return requestWithFallback<CopilotReply>(
    () => apiClient.post("/copilot", payload),
    () => {
      const last = payload.messages[payload.messages.length - 1]?.content ?? "";
      return {
        message: {
          role: "assistant",
          content: `Here's what I'd suggest for "${last}". I looked across the catalog for fit, price band, and review sentiment, then narrowed to three items that work together. Want me to swap any of them for a cheaper alternative?`,
        },
        suggestions: pick(["p-001", "p-003", "p-008"]),
      };
    },
  );
}

/** POST /visual-search */
export function postVisualSearch(file: File) {
  const form = new FormData();
  form.append("image", file);
  return requestWithFallback<VisualSearchResult>(
    () => apiClient.post("/visual-search", form, { headers: { "Content-Type": "multipart/form-data" } }),
    () => ({
      detected: ["outerwear", "neutral palette", "structured shoulder", "mid-length"],
      items: pick(["p-001", "p-012", "p-011", "p-008"]),
    }),
  );
}

/** GET /seasonal */
export function getSeasonal(season: string) {
  return requestWithFallback<SeasonalResult>(
    () => apiClient.get("/seasonal", { params: { season } }),
    () => ({
      season,
      headline: `${season} picks tuned to your region, climate signals, and past ${season.toLowerCase()} purchases.`,
      items:
        season === "Summer"
          ? pick(["p-005", "p-009", "p-002", "p-006"])
          : season === "Spring"
            ? pick(["p-011", "p-008", "p-005", "p-004"])
            : season === "Autumn"
              ? pick(["p-011", "p-001", "p-006", "p-010"])
              : pick(["p-001", "p-012", "p-011", "p-003"]),
    }),
  );
}
