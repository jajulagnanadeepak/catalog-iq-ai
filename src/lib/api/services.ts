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
 * Convert a backend or recommendation product into the frontend Product shape.
 * Robustly unwraps nested `{ product: { ... } }` and supports catalog & H&M fields.
 */
export function mapApiProduct(entry: unknown): Product | null {
  if (!isRecord(entry)) return null;

  const raw = isRecord(entry["product"])
    ? { ...(entry["product"] as Record<string, unknown>), ...entry }
    : entry;

  const id = getString(raw, ["product_id", "article_id", "_id", "id"]);
  const name = getString(raw, ["name", "title", "product_name", "prod_name"]);

  if (!id || !name) {
    return null;
  }

  const price = getNumber(raw, ["price", "selling_price", "current_price"]) ?? 0;

  const category =
    getString(raw, ["category", "product_type", "product_group_name", "department"]) ??
    "Uncategorized";

  const image =
    getString(raw, ["image", "image_url", "imageUrl", "thumbnail", "thumbnail_url"]) ??
    getString(isRecord(raw["images"]) ? (raw["images"] as Record<string, unknown>) : {}, [
      "primary",
      "url",
      "src",
    ]) ??
    "";

  const originalPrice = getNumber(raw, ["original_price", "originalPrice", "list_price", "mrp"]);

  const rating = getNumber(raw, ["rating", "average_rating"]) ?? 0;
  const reviews = getNumber(raw, ["reviews", "review_count", "num_reviews"]) ?? 0;

  const currency = getString(raw, ["currency", "price_currency"])?.toUpperCase() ?? "USD";

  const colors = getStringArray(raw, ["colors", "color_options", "colour"]);
  const sizes = getStringArray(raw, ["sizes", "size_options"]);
  const tags = getStringArray(raw, ["tags", "keywords"]);

  return {
    id,
    name,
    brand: getString(raw, ["brand", "brand_name", "manufacturer", "department"]) ?? "CatalogIQ",
    category,
    description: getString(raw, ["description", "details", "summary", "detail_desc"]) ?? "",
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

export const normalizeProduct = mapApiProduct;

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
    async () => {
      const response = await apiClient.get("/products", { params: query });
      const rawData = response.data;
      if (Array.isArray(rawData)) {
        const items = rawData.map(normalizeProduct).filter(Boolean) as Product[];
        return { data: paginate(items, query.page ?? 1, query.pageSize ?? 8) };
      }
      if (isRecord(rawData) && Array.isArray(rawData["items"])) {
        const items = rawData["items"].map(normalizeProduct).filter(Boolean) as Product[];
        return {
          data: {
            items,
            page: getNumber(rawData, ["page"]) ?? 1,
            pageSize: getNumber(rawData, ["pageSize", "page_size"]) ?? query.pageSize ?? 8,
            total: getNumber(rawData, ["total"]) ?? items.length,
          },
        };
      }
      return { data: paginate(PRODUCTS, query.page ?? 1, query.pageSize ?? 8) };
    },
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

  const rawProducts = Array.isArray(data["products"]) ? data["products"] : [];

  const mapped = rawProducts.flatMap((entry: unknown) => {
    if (!isRecord(entry)) return [];

    const nested = entry["product"];
    const raw = isRecord(nested) ? nested : entry;

    const id = getString(raw, ["article_id", "_id", "product_id", "id"]);
    const name = getString(raw, ["name", "title", "product_name"]);

    if (!id || !name) return [];

    const colour = getString(raw, ["colour", "color"]);
    const price = getNumber(raw, ["price", "selling_price", "current_price"]);
    const originalPrice = getNumber(raw, ["original_price", "originalPrice", "list_price", "mrp"]);

    const product: Product = {
      id,
      name,
      brand: getString(raw, ["brand", "brand_name", "department"]) ?? "Unknown brand",
      category: getString(raw, ["category", "product_type"]) ?? "Other",
      description: getString(raw, ["description", "details"]) ?? "",
      image: getString(raw, ["image_url", "image", "imageUrl", "thumbnail_url"]) ?? "",
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
        score: typeof score === "number" && Number.isFinite(score) ? score : 0,
      },
    ];
  });

  // Apply filters to the products returned by semantic search.
  const filtered = mapped.filter(({ product }) => {
    if (payload.category && payload.category !== "All" && product.category !== payload.category) {
      return false;
    }

    // Unknown prices cannot be verified against a price limit.
    if (payload.minPrice != null || payload.maxPrice != null) {
      if (!Number.isFinite(product.price) || product.price <= 0) {
        return false;
      }

      if (payload.minPrice != null && product.price < payload.minPrice) {
        return false;
      }

      if (payload.maxPrice != null && product.price > payload.maxPrice) {
        return false;
      }
    }

    if (payload.minRating != null && product.rating < payload.minRating) {
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
  const pageSize = Math.max(1, Math.min(100, Math.floor(payload.pageSize ?? 8)));
  const start = (page - 1) * pageSize;
  const pageItems = filtered.slice(start, start + pageSize);

  return {
    items: pageItems.map(({ product }) => product),
    page,
    pageSize,
    total,
    interpretation: "Semantic search results ranked by relevance to your query.",
    matches: pageItems.map(({ product, score }) => ({
      productId: product.id,
      score,
    })),
  };
}

/** GET /recommend */
export function getRecommendations(limit = 6) {
  return requestWithFallback<Recommendation[]>(
    async () => {
      const response = await apiClient.get("/recommend", { params: { limit } });
      const rawData = response.data;
      const rawList = Array.isArray(rawData)
        ? rawData
        : isRecord(rawData) && Array.isArray(rawData["recommendations"])
          ? rawData["recommendations"]
          : [];

      const mapped = rawList
        .map((entry: unknown, index: number) => {
          if (!isRecord(entry)) return null;
          const rawProduct = isRecord(entry["product"]) ? entry["product"] : entry;
          const product = normalizeProduct(rawProduct);
          if (!product) return null;

          return {
            id: getString(entry, ["id"]) ?? `r-${index}`,
            title: getString(entry, ["title"]) ?? "Recommended for you",
            reason: getString(entry, ["reason"]) ?? "",
            ranking_score: getNumber(entry, ["ranking_score", "score"]) ?? 0.8,
            product,
          };
        })
        .filter(Boolean) as Recommendation[];

      return { data: mapped };
    },
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

/** POST /stylist */
export function postStylist(payload: StylistPayload) {
  return requestWithFallback<StylistLook[]>(
    () => apiClient.post("/stylist", payload),
    () => {
      const budget =
        typeof payload.budget === "number" && payload.budget > 0 ? payload.budget : Infinity;

      const occasion = (payload.occasion || "").toLowerCase();
      const style = (payload.style || "").toLowerCase();
      const notes = (payload.notes || "").toLowerCase();

      const available = PRODUCTS.filter((product) => product.inStock && product.price <= budget);

      const scoreProduct = (product: Product, lookIndex: number) => {
        const text = [
          product.name,
          product.category,
          product.description,
          ...product.tags,
          ...product.colors,
        ]
          .join(" ")
          .toLowerCase();

        let score = product.rating;

        if (/formal|work|office|business|meeting|interview/.test(occasion)) {
          if (/formal|smart-casual|work|leather|knit|outerwear/.test(text)) {
            score += 5;
          }
          if (/sport|running|swim|fitness/.test(text)) score -= 4;
        }

        if (/casual|everyday|weekend/.test(occasion)) {
          if (/everyday|casual|basics|cotton|sneakers/.test(text)) {
            score += 4;
          }
        }

        if (/evening|party|date|dinner/.test(occasion)) {
          if (/formal|premium|watch|leather|black/.test(text)) {
            score += 4;
          }
        }

        if (/minimal|classic|refined/.test(style)) {
          if (/minimal|classic|neutral|formal|leather|knit/.test(text)) {
            score += 3;
          }
          if (/crimson|bright red|neon/.test(text)) score -= 3;
        }

        if (/sport|athletic|active/.test(style)) {
          if (/sport|running|fitness|performance/.test(text)) score += 4;
        }

        if (/avoid bright|no bright|neutral colours|neutral colors/.test(notes)) {
          if (/crimson|red|neon|bright/.test(text)) score -= 8;
        }

        if (lookIndex === 0 && /formal|work|office|business/.test(occasion)) {
          if (/tops|outerwear|accessories|footwear/.test(product.category.toLowerCase())) {
            score += 2;
          }
        }

        return score;
      };

      const makeLook = (lookIndex: number): StylistLook => {
        const ranked = [...available].sort(
          (a, b) => scoreProduct(b, lookIndex) - scoreProduct(a, lookIndex) || a.price - b.price,
        );

        const items: Product[] = [];
        let total = 0;
        const usedCategories = new Set<string>();

        for (const product of ranked) {
          if (items.length >= 3) break;
          if (usedCategories.has(product.category)) continue;
          if (total + product.price > budget) continue;

          items.push(product);
          total += product.price;
          usedCategories.add(product.category);
        }

        return {
          id: `look-${lookIndex + 1}`,
          title:
            lookIndex === 0
              ? `Refined ${payload.occasion || "everyday"} look`
              : `Alternative ${payload.style || "classic"} look`,
          summary:
            items.length > 0
              ? `Selected from available products to match your preferences and stay within your budget where possible.`
              : "No available products match this budget. Try increasing it to see more outfit options.",
          items,
          total,
        };
      };

      return [makeLook(0), makeLook(1)];
    },
  );
}

/** POST /budget */
export async function postBudget(payload: BudgetPayload): Promise<BudgetResult> {
  try {
    const response = await apiClient.post<BudgetResult>("/budget", payload);
    const data = response.data;
    if (isRecord(data) && Array.isArray(data["allocations"])) {
      const allocations = (data["allocations"] as Record<string, unknown>[])
        .map((a) => {
          if (!isRecord(a)) return null;
          const product = mapApiProduct(a["product"]);
          if (!product) return null;
          return {
            category: getString(a, ["category"]) ?? product.category,
            amount: getNumber(a, ["amount"]) ?? product.price,
            product,
          };
        })
        .filter((a): a is { category: string; amount: number; product: Product } => a !== null);

      return {
        budget: getNumber(data, ["budget"]) ?? payload.budget,
        spent: getNumber(data, ["spent"]) ?? allocations.reduce((sum, a) => sum + a.amount, 0),
        saved:
          getNumber(data, ["saved"]) ??
          Math.max(0, payload.budget - (getNumber(data, ["spent"]) ?? 0)),
        allocations,
      };
    }
    return data;
  } catch {
    const requestedCategories =
      payload.categories.length > 0 ? payload.categories : ["Tops", "Footwear", "Bags"];

    const available = PRODUCTS.filter(
      (p) =>
        requestedCategories.some((c) => c.toLowerCase() === p.category.toLowerCase()) &&
        p.inStock &&
        p.price <= payload.budget,
    );

    const rankKey = (p: Product) => {
      if (payload.priority === "value") return p.price;
      if (payload.priority === "quality") return -p.rating;
      return -(p.rating / Math.max(p.price, 1));
    };

    const sorted = [...available].sort((a, b) => rankKey(a) - rankKey(b));
    const allocations: { category: string; amount: number; product: Product }[] = [];
    let spent = 0;
    const selectedIds = new Set<string>();

    for (const cat of requestedCategories) {
      const match = sorted.find(
        (p) =>
          p.category.toLowerCase() === cat.toLowerCase() &&
          !selectedIds.has(p.id) &&
          spent + p.price <= payload.budget,
      );
      if (match) {
        allocations.push({ category: match.category, amount: match.price, product: match });
        selectedIds.add(match.id);
        spent += match.price;
      }
    }

    return {
      budget: payload.budget,
      spent: Math.round(spent * 100) / 100,
      saved: Math.round(Math.max(0, payload.budget - spent) * 100) / 100,
      allocations,
    };
  }
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
export async function postVisualSearch(file: File): Promise<VisualSearchResult> {
  const form = new FormData();
  form.append("image", file, file.name);

  try {
    const response = await apiClient.post<VisualSearchResult>("/visual-search", form, {
      transformRequest: [(data) => data],
    });

    const data = response.data;
    if (isRecord(data) && Array.isArray(data["items"])) {
      const items = (data["items"] as unknown[]).map(mapApiProduct).filter(Boolean) as (Product & {
        similarity?: number;
      })[];

      return {
        detected: Array.isArray(data["detected"]) ? (data["detected"] as string[]) : [],
        items,
      };
    }
    return response.data;
  } catch (err) {
    console.warn("Visual search backend call failed, using catalog fallback:", err);
    const detected = ["Apparel", "Fashion", "Pattern match"];
    const items = PRODUCTS.slice(0, 6).map((p, idx) => ({
      ...p,
      similarity: Number((0.92 - idx * 0.04).toFixed(2)),
    }));
    return { detected, items };
  }
}

/** GET /seasonal */
export function getSeasonal(season: string) {
  return requestWithFallback<SeasonalResult>(
    async () => {
      const response = await apiClient.get<SeasonalResult>("/seasonal", { params: { season } });
      const rawData = response.data;
      if (isRecord(rawData) && Array.isArray(rawData["items"])) {
        const items = rawData["items"].map(mapApiProduct).filter(Boolean) as Product[];
        return {
          data: {
            season: getString(rawData, ["season"]) ?? season,
            headline: getString(rawData, ["headline"]) ?? `Seasonal recommendations for ${season}.`,
            items,
          },
        };
      }
      return { data: rawData };
    },
    () => {
      const norm = season.toLowerCase();
      const filtered = PRODUCTS.filter((p) => {
        const tags = (p.tags || []).join(" ").toLowerCase();
        const desc = (p.description || "").toLowerCase();
        const name = p.name.toLowerCase();
        const text = `${tags} ${desc} ${name}`;
        if (norm === "summer")
          return /summer|swim|tee|shirt|linen/.test(text) || p.category === "Tops";
        if (norm === "winter")
          return /winter|wool|overcoat|jacket|puffer/.test(text) || p.category === "Outerwear";
        if (norm === "autumn")
          return (
            /autumn|layering|knit|boot|jacket/.test(text) ||
            p.category === "Outerwear" ||
            p.category === "Tops"
          );
        return (
          /spring|casual|cotton|sneaker/.test(text) ||
          p.category === "Tops" ||
          p.category === "Footwear"
        );
      });
      return {
        season,
        headline: `Curated ${season.toLowerCase()} recommendations from our catalog.`,
        items: filtered.length > 0 ? filtered : PRODUCTS.slice(0, 4),
      };
    },
  );
}
