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
/* POST /semantic-search */

export async function postSearch(payload: SearchPayload) {
  const response = await apiClient.post("/semantic-search", payload);

  const data = response.data;

  const items = data.products.map((p: any) => ({
    id: p.product_id ?? p._id,
    name: p.name,
    brand: p.brand ?? p.department ?? "H&M",
    category: p.category,
    description: p.description,
    image:
      p.image ??
      "https://via.placeholder.com/300x400?text=Product",
    price: p.price ?? 0,
    originalPrice: p.original_price ?? null,
    rating: p.rating ?? 4.5,
    reviews: p.reviews ?? 0,
    inStock: true,
    tags: p.tags ?? [],
  }));

  return {
    items,
    page: 1,
    pageSize: items.length,
    total: items.length,
    interpretation: "Semantic Search Results",
    matches: items.map((item: any) => ({
      productId: item.id,
      score: 1,
    })),
  };
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
export async function postCopilot(payload: CopilotPayload) {
  // Get the latest user message from the chat
  const latestMessage =
    payload.messages[payload.messages.length - 1]?.content ?? "";

  // Call your FastAPI backend
  console.log("Calling backend:", "/copilot/chat");
  const response = await apiClient.post("/copilot/chat", {
    message: latestMessage,
  });

  const data = response.data;

  return {
    message: {
      role: "assistant",
      content: data.response,
    },

    suggestions: data.recommendations.map((p: any) => ({
      id: p.product_id ?? p._id,
      name: p.name,
      brand: p.department ?? "H&M",
      category: p.category,
      description: p.description,
      image:
        p.image ??
        "https://via.placeholder.com/300x400?text=Product",
      price: p.price ?? 0,
      originalPrice: null,
      rating: p.rating ?? 4.5,
      reviews: p.reviews ?? 0,
      inStock: true,
      tags: [],
      recommendationScore: p.recommendation_score,
      reason: p.reason,
    })),
  };
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
