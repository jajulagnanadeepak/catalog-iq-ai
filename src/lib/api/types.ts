export interface Product {
  id: string;
  name: string;
  brand: string;
  category: string;
  price: number;
  originalPrice?: number;
  rating: number;
  reviews: number;
  image: string;
  colors: string[];
  sizes: string[];
  tags: string[];
  description: string;
  inStock: boolean;
}

export interface Paginated<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
}

export interface ProductQuery {
  page?: number;
  pageSize?: number;
  category?: string;
  minPrice?: number;
  maxPrice?: number;
  minRating?: number;
  sort?: "relevance" | "price-asc" | "price-desc" | "rating";
}

export interface SearchPayload extends ProductQuery {
  query: string;
}

export interface SearchResult extends Paginated<Product> {
  interpretation: string;
  matches: { productId: string; score: number }[];
}

export interface Recommendation {
  id: string;
  title: string;
  reason: string;
  confidence: number;
  product: Product;
}

export interface IntentPayload {
  query: string;
}

export interface IntentResult {
  intent: string;
  confidence: number;
  entities: { label: string; value: string }[];
}

export interface StylistPayload {
  occasion: string;
  style: string;
  bodyType?: string;
  budget?: number;
  notes?: string;
}

export interface StylistLook {
  id: string;
  title: string;
  summary: string;
  items: Product[];
  total: number;
}

export interface BudgetPayload {
  budget: number;
  categories: string[];
  priority: "value" | "quality" | "balanced";
}

export interface BudgetResult {
  budget: number;
  spent: number;
  saved: number;
  allocations: { category: string; amount: number; product: Product }[];
}

export interface CopilotMessage {
  role: "user" | "assistant";
  content: string;
}

export interface CopilotPayload {
  messages: CopilotMessage[];
}

export interface CopilotReply {
  message: CopilotMessage;
  suggestions: Product[];
}

export interface VisualSearchResult {
  detected: string[];
  items: Product[];
}

export interface SeasonalResult {
  season: string;
  headline: string;
  items: Product[];
}
