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

type ApiProduct = Record<string, unknown>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function getString(record: Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return undefined;
}

function getNumber(record: Record<string, unknown>, keys: string[]): number | undefined {
  for (const key of keys) {
    const value = record[key];

    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }

    if (typeof value === "string" && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
    }
  }

  return undefined;
}

function getStringArray(record: Record<string, unknown>, keys: string[]): string[] {
  for (const key of keys) {
    const value = record[key];

    if (Array.isArray(value)) {
      return value.filter(
        (item): item is string => typeof item === "string" && item.trim().length > 0,
      );
    }
  }

  return [];
}

/**
 * Convert a backend product into the frontend Product shape.
 * Missing prices or IDs are not replaced with fabricated values.
 */
function mapApiProduct(raw: unknown): Product | null {
  if (!isRecord(raw)) return null;

  const id = getString(raw, ["product_id", "_id", "id"]);
  const name = getString(raw, ["name", "title", "product_name"]);
  const price = getNumber(raw, ["price", "selling_price", "current_price"]);

  if (!id || !name || price === undefined || price < 0) {
    return null;
  }

  const category =
    getString(raw, ["category", "product_category", "department"]) ?? "Uncategorized";

  const image =
    getString(raw, ["image", "image_url", "thumbnail", "thumbnail_url"]) ??
    getString(isRecord(raw["images"]) ? raw["images"] : {}, ["primary", "url", "src"]) ??
    "";

  const originalPrice = getNumber(raw, ["original_price", "originalPrice", "list_price", "mrp"]);

  const rating = getNumber(raw, ["rating", "average_rating"]) ?? 0;
  const reviews = getNumber(raw, ["reviews", "review_count", "num_reviews"]) ?? 0;

  const currency = getString(raw, ["currency", "price_currency"])?.toUpperCase() ?? "USD";

  const colors = getStringArray(raw, ["colors", "color_options"]);
  const sizes = getStringArray(raw, ["sizes", "size_options"]);
  const tags = getStringArray(raw, ["tags", "keywords"]);

  return {
    id,
    name,
    brand: getString(raw, ["brand", "brand_name", "manufacturer"]) ?? "Unknown brand",
    category,
    description: getString(raw, ["description", "details", "summary"]) ?? "",
    image,
    price,
    currency,
    ...(originalPrice !== undefined ? { originalPrice } : {}),
    rating,
    reviews,
    colors,
    sizes,
    tags,
    inStock:
      typeof raw["in_stock"] === "boolean"
        ? raw["in_stock"]
        : typeof raw["inStock"] === "boolean"
          ? raw["inStock"]
          : true,
  };
}

function filterSort(query: ProductQuery, source: Product[] = PRODUCTS) {
  let items = [...source];

  if (query.category && query.category !== "All") {
    items = items.filter((product) => product.category === query.category);
  }

  if (query.minPrice != null) {
    items = items.filter((product) => product.price >= query.minPrice!);
  }

  if (query.maxPrice != null) {
    items = items.filter((product) => product.price <= query.maxPrice!);
  }

  if (query.minRating != null) {
    items = items.filter((product) => product.rating >= query.minRating!);
  }

  if (query.sort === "price-asc") {
    items.sort((a, b) => a.price - b.price);
  }

  if (query.sort === "price-desc") {
    items.sort((a, b) => b.price - a.price);
  }

  if (query.sort === "rating") {
    items.sort((a, b) => b.rating - a.rating);
  }

  return items;
}

function paginate<T>(items: T[], page = 1, pageSize = 8): Paginated<T> {
  const start = (page - 1) * pageSize;

  return {
    items: items.slice(start, start + pageSize),
    page,
    pageSize,
    total: items.length,
  };
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
    () => PRODUCTS.find((product) => product.id === id) ?? PRODUCTS[0]!,
  );
}

/** POST /semantic-search */

/** POST /semantic-search — semantic product discovery */

/** POST /semantic-search — map the backend semantic-search response. */

/** POST /semantic-search — map actual backend results. */
export async function postSearch(payload: SearchPayload): Promise<SearchResult> {
  const response = await apiClient.post("/semantic-search", payload);
  const data: unknown = response.data;

  if (!isRecord(data)) {
    throw new Error("Semantic search returned an invalid response.");
  }

  const rawProducts = Array.isArray(data["products"])
    ? data["products"]
    : [];

  const mapped = rawProducts.flatMap((entry: unknown) => {
    if (!isRecord(entry)) return [];

    const nested = entry["product"];
    const raw = isRecord(nested) ? nested : entry;

    const id = getString(raw, [
      "article_id",
      "_id",
      "product_id",
      "id",
    ]);
    const name = getString(raw, ["name", "title", "product_name"]);

    if (!id || !name) return [];

    const colour = getString(raw, ["colour", "color"]);
    const price = getNumber(raw, [
      "price",
      "selling_price",
      "current_price",
    ]);
    const originalPrice = getNumber(raw, [
      "original_price",
      "originalPrice",
      "list_price",
      "mrp",
    ]);

    const product: Product = {
      id,
      name,
      brand:
        getString(raw, ["brand", "brand_name", "department"]) ??
        "Unknown brand",
      category:
        getString(raw, ["category", "product_type"]) ?? "Other",
      description:
        getString(raw, ["description", "details"]) ?? "",
      image:
        getString(raw, [
          "image_url",
          "image",
          "imageUrl",
          "thumbnail_url",
        ]) ?? "",
      price: price ?? 0,
      currency: getString(raw, ["currency"]) ?? "USD",
      ...(originalPrice !== undefined ? { originalPrice } : {}),
      rating: getNumber(raw, ["rating", "average_rating"]) ?? 0,
      reviews: getNumber(raw, ["reviews", "review_count"]) ?? 0,
      colors: colour ? [colour] : [],
      sizes: getStringArray(raw, ["sizes", "size_options"]),
      tags: [
        getString(raw, ["product_type"]),
        getString(raw, ["category"]),
        getString(raw, ["section"]),
        colour,
      ].filter((tag): tag is string => Boolean(tag)),
      inStock:
        typeof raw["in_stock"] === "boolean"
          ? raw["in_stock"]
          : typeof raw["inStock"] === "boolean"
            ? raw["inStock"]
            : true,
    };

    const score = entry["score"];

    return [
      {
        product,
        score:
          typeof score === "number" && Number.isFinite(score)
            ? score
            : 0,
      },
    ];
  });

  // Apply filters to the products returned by semantic search.
  let filtered = mapped.filter(({ product }) => {
    if (
      payload.category &&
      payload.category !== "All" &&
      product.category !== payload.category
    ) {
      return false;
    }

    // Unknown prices cannot be verified against a price limit.
    if (payload.minPrice != null || payload.maxPrice != null) {
      if (!Number.isFinite(product.price) || product.price <= 0) {
        return false;
      }

      if (
        payload.minPrice != null &&
        product.price < payload.minPrice
      ) {
        return false;
      }

      if (
        payload.maxPrice != null &&
        product.price > payload.maxPrice
      ) {
        return false;
      }
    }

    if (
      payload.minRating != null &&
      product.rating < payload.minRating
    ) {
      return false;
    }

    return true;
  });

  // Preserve semantic relevance order unless another sort is selected.

  switch (payload.sort ?? "relevance") {
    case "price-asc":
      filtered.sort((a, b) => {
        const aPrice = a.product.price;
        const bPrice = b.product.price;
        const aValid = Number.isFinite(aPrice) && aPrice > 0;
        const bValid = Number.isFinite(bPrice) && bPrice > 0;

        if (!aValid && !bValid) return b.score - a.score;
        if (!aValid) return 1;
        if (!bValid) return -1;
        return aPrice - bPrice;
      });
      break;

    case "price-desc":
      filtered.sort((a, b) => {
        const aPrice = a.product.price;
        const bPrice = b.product.price;
        const aValid = Number.isFinite(aPrice) && aPrice > 0;
        const bValid = Number.isFinite(bPrice) && bPrice > 0;

        if (!aValid && !bValid) return b.score - a.score;
        if (!aValid) return 1;
        if (!bValid) return -1;
        return bPrice - aPrice;
      });
      break;

    case "rating":
      filtered.sort((a, b) => {
        const aRating = a.product.rating;
        const bRating = b.product.rating;
        const aValid = Number.isFinite(aRating) && aRating > 0;
        const bValid = Number.isFinite(bRating) && bRating > 0;

        if (!aValid && !bValid) return b.score - a.score;
        if (!aValid) return 1;
        if (!bValid) return -1;
        return bRating - aRating;
      });
      break;

    case "relevance":
    default:
      filtered.sort((a, b) => b.score - a.score);
      break;
  }


  const total = filtered.length;
  const page = Math.max(1, Math.floor(payload.page ?? 1));
  const pageSize = Math.max(
    1,
    Math.min(100, Math.floor(payload.pageSize ?? 8)),
  );
  const start = (page - 1) * pageSize;
  const pageItems = filtered.slice(start, start + pageSize);

  return {
    items: pageItems.map(({ product }) => product),
    page,
    pageSize,
    total,
    interpretation:
      "Semantic search results ranked by relevance to your query.",
    matches: pageItems.map(({ product, score }) => ({
      productId: product.id,
      score,
    })),
  };
}


/** GET /recommend */
export function getRecommendations(limit = 6) {
  return requestWithFallback<Recommendation[]>(
    () => apiClient.get("/recommend", { params: { limit } }),
    () =>
      PRODUCTS.slice(0, limit).map((product, index) => ({
        id: `r-${index}`,
        title: [
          "Because you viewed outerwear",
          "Trending in your size",
          "Frequently bought together",
          "Matches your saved palette",
          "Restocked near you",
          "High value pick",
        ][index % 6]!,
        reason: [
          "Similar silhouette and fabric weight to items in your history.",
          "Popular with shoppers who share your style graph.",
          "Completes 3 of your saved looks.",
          "Colour-matched to your last two purchases.",
          "Back in stock in the size you follow.",
          "Best price-to-rating ratio in this category.",
        ][index % 6]!,
        ranking_score: 0.72 + ((index * 4) % 25) / 100,
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

      return looks.map((items, index) => ({
        id: `look-${index}`,
        title:
          index === 0
            ? `Refined ${payload.occasion || "evening"} layering`
            : `Relaxed ${payload.style || "everyday"} edit`,
        summary:
          index === 0
            ? "Structured outer layer over fine knit, grounded with clean leather. Reads polished without a suit."
            : "Soft cotton base with performance footwear and a utility carry — built for movement.",
        items,
        total: items.reduce((sum, product) => sum + product.price, 0),
      }));
    },
  );
}

/** POST /budget */

/** POST /budget */
export async function postBudget(
  payload: BudgetPayload,
): Promise<BudgetResult> {
  const response = await apiClient.post<BudgetResult>(
    "/budget",
    payload,
  );

  return response.data;
}


/** POST /copilot/chat */
export async function postCopilot(payload: CopilotPayload): Promise<CopilotReply> {
  const latestMessage = payload.messages[payload.messages.length - 1]?.content ?? "";

  const response = await apiClient.post("/copilot/chat", {
  message: latestMessage,
  session_id: payload.session_id,
});

  const data: unknown = response.data;

  if (!isRecord(data)) {
    throw new Error("Copilot returned an invalid response.");
  }

  const message =
    getString(data, ["response", "message", "reply"]) ??
    "I couldn't generate a response. Please try again.";

  const rawRecommendations = Array.isArray(data["recommendations"])
    ? data["recommendations"]
    : Array.isArray(data["suggestions"])
      ? data["suggestions"]
      : [];

  const suggestions = rawRecommendations
    .map(mapApiProduct)
    .filter((product): product is Product => product !== null);

  return {
    message: {
      role: "assistant",
      content: message,
    },
    suggestions,
  };
}

/** POST /visual-search */

/** POST /visual-search */

/** POST /visual-search */
export async function postVisualSearch(
  file: File,
): Promise<VisualSearchResult> {
  const form = new FormData();
  form.append("image", file, file.name);

  const response = await apiClient.post<VisualSearchResult>(
    "/visual-search",
    form,
    {
      transformRequest: [(data) => data],
    },
  );

  return response.data;
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
