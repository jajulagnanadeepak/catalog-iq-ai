import { useState, useEffect } from "react";
import type { Product } from "@/lib/api/types";

export interface CartItem {
  product: Product;
  quantity: number;
  addedAt: number;
}

export interface WishlistItem {
  product: Product;
  addedAt: number;
}

const CART_STORAGE_KEY = "catalogiq_cart_v1";
const WISHLIST_STORAGE_KEY = "catalogiq_wishlist_v1";
const SYNC_EVENT = "catalogiq_store_sync";

function safeGetStorage<T>(key: string, defaultValue: T): T {
  if (typeof window === "undefined") return defaultValue;
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : defaultValue;
  } catch (err) {
    console.error(`Error reading ${key} from localStorage:`, err);
    return defaultValue;
  }
}

function safeSetStorage<T>(key: string, value: T): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, JSON.stringify(value));
    window.dispatchEvent(new Event(SYNC_EVENT));
  } catch (err) {
    console.error(`Error writing ${key} to localStorage:`, err);
  }
}

// Direct store helpers
export const cartStore = {
  getItems(): CartItem[] {
    return safeGetStorage<CartItem[]>(CART_STORAGE_KEY, []);
  },

  addItem(product: Product, quantity = 1): CartItem[] {
    const current = this.getItems();
    const existingIndex = current.findIndex((item) => item.product.id === product.id);

    let updated: CartItem[];
    if (existingIndex >= 0) {
      updated = [...current];
      const existing = updated[existingIndex];
      if (existing) {
        existing.quantity += quantity;
      }
    } else {
      updated = [{ product, quantity, addedAt: Date.now() }, ...current];
    }

    safeSetStorage(CART_STORAGE_KEY, updated);
    return updated;
  },

  updateQuantity(productId: string, quantity: number): CartItem[] {
    const current = this.getItems();
    let updated: CartItem[];
    if (quantity <= 0) {
      updated = current.filter((item) => item.product.id !== productId);
    } else {
      updated = current.map((item) =>
        item.product.id === productId ? { ...item, quantity } : item,
      );
    }
    safeSetStorage(CART_STORAGE_KEY, updated);
    return updated;
  },

  removeItem(productId: string): CartItem[] {
    const current = this.getItems();
    const updated = current.filter((item) => item.product.id !== productId);
    safeSetStorage(CART_STORAGE_KEY, updated);
    return updated;
  },

  clear(): void {
    safeSetStorage(CART_STORAGE_KEY, []);
  },

  getTotal(): number {
    return this.getItems().reduce((sum, item) => {
      const price = Number.isFinite(item.product.price) ? item.product.price : 0;
      return sum + price * item.quantity;
    }, 0);
  },

  getCount(): number {
    return this.getItems().reduce((sum, item) => sum + item.quantity, 0);
  },
};

export const wishlistStore = {
  getItems(): WishlistItem[] {
    return safeGetStorage<WishlistItem[]>(WISHLIST_STORAGE_KEY, []);
  },

  isWishlisted(productId: string): boolean {
    return this.getItems().some((item) => item.product.id === productId);
  },

  toggle(product: Product): { isWishlisted: boolean; items: WishlistItem[] } {
    const current = this.getItems();
    const exists = current.some((item) => item.product.id === product.id);

    let updated: WishlistItem[];
    if (exists) {
      updated = current.filter((item) => item.product.id !== product.id);
    } else {
      updated = [{ product, addedAt: Date.now() }, ...current];
    }

    safeSetStorage(WISHLIST_STORAGE_KEY, updated);
    return { isWishlisted: !exists, items: updated };
  },

  removeItem(productId: string): WishlistItem[] {
    const current = this.getItems();
    const updated = current.filter((item) => item.product.id !== productId);
    safeSetStorage(WISHLIST_STORAGE_KEY, updated);
    return updated;
  },
};

// React Hooks for reactivity across components
export function useCart() {
  const [items, setItems] = useState<CartItem[]>(() => cartStore.getItems());

  useEffect(() => {
    const handleSync = () => setItems(cartStore.getItems());
    window.addEventListener(SYNC_EVENT, handleSync);
    window.addEventListener("storage", handleSync);
    return () => {
      window.removeEventListener(SYNC_EVENT, handleSync);
      window.removeEventListener("storage", handleSync);
    };
  }, []);

  const total = items.reduce((sum, item) => {
    const price = Number.isFinite(item.product.price) ? item.product.price : 0;
    return sum + price * item.quantity;
  }, 0);

  const count = items.reduce((sum, item) => sum + item.quantity, 0);

  return {
    items,
    total,
    count,
    addItem: (product: Product, quantity = 1) => cartStore.addItem(product, quantity),
    updateQuantity: (productId: string, quantity: number) =>
      cartStore.updateQuantity(productId, quantity),
    removeItem: (productId: string) => cartStore.removeItem(productId),
    clear: () => cartStore.clear(),
  };
}

export function useWishlist() {
  const [items, setItems] = useState<WishlistItem[]>(() => wishlistStore.getItems());

  useEffect(() => {
    const handleSync = () => setItems(wishlistStore.getItems());
    window.addEventListener(SYNC_EVENT, handleSync);
    window.addEventListener("storage", handleSync);
    return () => {
      window.removeEventListener(SYNC_EVENT, handleSync);
      window.removeEventListener("storage", handleSync);
    };
  }, []);

  const isWishlisted = (productId: string) => items.some((item) => item.product.id === productId);

  return {
    items,
    count: items.length,
    isWishlisted,
    toggle: (product: Product) => wishlistStore.toggle(product),
    removeItem: (productId: string) => wishlistStore.removeItem(productId),
  };
}
