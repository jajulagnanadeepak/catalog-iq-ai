import axios from "axios";
import { apiClient } from "@/lib/api/client";

const SESSION_STORAGE_KEY = "catalogiq.session_id";

export type ShoppingEventType = "view" | "click" | "wishlist" | "cart" | "purchase";

export function getShoppingSessionId(): string {
  let sessionId = window.localStorage.getItem(SESSION_STORAGE_KEY);

  if (!sessionId) {
    sessionId = crypto.randomUUID();
    window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }

  return sessionId;
}

export async function trackShoppingEvent(
  eventType: ShoppingEventType,
  product: { id: string; category?: string },
): Promise<void> {
  const payload = {
    session_id: getShoppingSessionId(),
    event_type: eventType,
    category: product.category ?? null,
    product_id: product.id,
  };

  console.log("[Shopping tracking] Event:", payload);
  console.log("[Shopping tracking] API base URL:", apiClient.defaults.baseURL);

  try {
    const response = await apiClient.post("/intent/event", payload);

    console.log("[Shopping tracking] Success:", {
      status: response.status,
      data: response.data,
    });
  } catch (error: unknown) {
    if (axios.isAxiosError(error)) {
      console.error("[Shopping tracking] Request failed:", {
        message: error.message,
        status: error.response?.status,
        response: error.response?.data,
        url: error.config?.url,
        baseURL: error.config?.baseURL,
      });
    } else {
      console.error("[Shopping tracking] Unexpected error:", error);
    }
  }
}
