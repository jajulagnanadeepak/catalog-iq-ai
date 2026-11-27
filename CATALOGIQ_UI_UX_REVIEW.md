# CatalogIQ AI — UI/UX Review

Commit audited: `5d7ba72`. Companion to [CATALOGIQ_AUDIT.md](CATALOGIQ_AUDIT.md); IDs `C-/H-/M-/L-` refer to its register, `UX-` IDs are specific to this review.

**Method and limit:** source-level review of every route and shared component. The app was **not built or run** (no network, no `node_modules`), so there are no screenshots, Lighthouse scores, contrast measurements or screen-reader tests. Findings that depend on rendering are flagged *"verify visually"*.

---

## 1. Summary

The visual layer is the project's strongest asset: a consistent shadcn/ui design system, thoughtful skeletons, a responsive app shell (mobile sheet navigation, collapsible desktop sidebar), toast feedback and tidy product cards that already handle missing price/image gracefully. The UX problems are about **truthfulness and completeness**, not styling: the interface shows invented data on failure, advertises features that don't exist (checkout), and leads real catalog products to the wrong detail page.

| Rating | Meaning |
|---|---|
| ✅ Ready | Usable for customers as-is |
| 🟡 Needs work | Works, but gaps listed below |
| ❌ Not ready | Missing, misleading or broken for real use |

---

## 2. Page-by-page evaluation

| Page / area | File | Rating | Headline issues |
|---|---|---|---|
| Landing | `routes/index.tsx` | ❌ | Built from `mock.ts`; "Live Catalog Inventory" and "Live mock catalog ready" (`:567, :751`); invented match scores (`0.98`, `0.96`); preset products ("Studio ANC Headphones") don't exist in the real catalog (UX-04) |
| Navigation & discovery | `navbar.tsx`, `sidebar.tsx`, `app-shell.tsx` | 🟡 | Good responsive pattern; no category/browse navigation for a 105k-item catalog; no global search in app shell; no wishlist/cart/orders pages in nav |
| Login / Registration | `login.tsx`, `signup.tsx` | 🟡 | Clean forms with server-error mapping; fabricated "31% lift" copy (`login.tsx:67`); no password-strength hint, show/hide, "forgot password", email verification (H-14) |
| Dashboard | `dashboard.tsx` | ❌ | All KPIs and the 7-day chart are constants (`:37-52`); public route; "Products indexed 128,410" is wrong (UX-04) |
| Product listing | `search.tsx`, `product-card.tsx`, `filters.tsx` | 🟡 | Cards are good; filters/pagination don't match backend behaviour (UX-05); no browse-all-products page |
| Product details | `product.$productId.tsx` | ❌ | Wrong product for search results (UX-03); allows $0 item into cart (UX-06); hard-coded "Free delivery and 30-day returns" (`:248`); "related" = top-4 by rating, not related; colours/sizes are non-interactive badges (no variant selection) |
| Semantic search | `search.tsx` | 🟡 | Max 10 results (`top_k` default), cosmetic pagination, filters applied after retrieval (H-04); "interpretation" text is a constant string (`services.ts:379`) |
| Shopping cart | `cart-sheet.tsx` | 🟡 | Works as a drawer; `$` hard-coded (`:124`); mixes currencies; no variant/size, no stock re-check, no promo/shipping estimate |
| Checkout | — | ❌ | Button only closes the sheet (`cart-sheet.tsx:167-176`) |
| Orders | — | ❌ | No route, no API |
| User profile | `profile.tsx` | ✅/🟡 | Works; defaults shown as if saved ("M", "minimal, modern, neutral" at `:47-48`); no route guard; no address book/orders/security settings |
| AI Shopping Copilot | `copilot.tsx` | 🟡 | Nice layout and starter chips; stateless (only the last message is sent); no streaming; no `aria-live`; starters like "Compare your two best-rated sneakers" can't be answered (H-06); on error says "ensure the backend is connected" — developer language to customers |
| AI Stylist | `stylist.tsx` | 🟡 | Clear form with labels; USD only; results from 12 demo items; empty-state copy OK |
| Budget Optimizer | `budget.tsx` | 🟡 | Validation and toasts present; label "Total budget (USD)"; results are from the demo collection; silent mock on failure |
| Visual Search | `visual-search.tsx` | 🟡 | Good client-side type/size checks (8 MB) and retry; but on API failure the service returns **fake matches** so the error card never shows (C-05); drop zone keyboard handling incomplete (UX-08) |
| Seasonal | `seasonal.tsx` | 🟡 | Mojibake in title/headline (UX-09); loading skeleton present |
| Admin interface | — | ❌ | Does not exist |

---

## 3. Findings

### Critical

**UX-01 · Failures are hidden behind invented content** — see **C-05**. `requestWithFallback` (`client.ts:30-41`) and the catch blocks in `services.ts` turn every error into plausible-looking mock data. Customers cannot tell an outage from real results; operators never see the failure. *Fix:* delete from production, keep an opt-in `VITE_USE_MOCKS`; build real error/empty/retry states (the components largely exist). **P0**

**UX-02 · The storefront advertises a checkout that does not exist** — see **C-04**. **P0**

### High

**UX-03 · Product page shows the wrong product for semantic-search results** — `product.$productId.tsx:43-46` → `getProduct` (`services.ts:212-217`) → `/products/{id}` only searches the 12-item `products` collection; H&M `article_id`s 404 and the fallback returns `PRODUCTS[0]` ("Aurora Merino Overcoat"). *Fix:* unify catalog (C-02) and show a real "Product not found" state on 404. **P0**

**UX-04 · Invented statistics and policies** — see **H-08**: `dashboard.tsx:37-52`, `login.tsx:67`, `index.tsx:567-573,751`, `product.$productId.tsx:248`. Replace with real data or remove; keep marketing claims you can substantiate. **P1**

**UX-05 · Filters and pagination don't reflect the catalog** — see **H-04**. Additional UI points: category options are the six demo categories (`mock.ts:209`), the price slider is hard-coded 0–700 with no currency (`filters.tsx:25,64`), and the result count says "N matches" where N ≤ 10. *Fix:* facets from the API, currency-aware price range, honest counts ("Showing top 10 of …" or true pagination). **P1**

**UX-06 · A $0.00 item can be added to the cart from the detail page** — `product.$productId.tsx:80-96` only checks `inStock`; for H&M items `price` maps to `0` (`services.ts:258`) and the page renders "$0.00" (`:173-179`). The product *card* correctly shows "Price unavailable" and disables the button (`product-card.tsx:24-35, 208`). *Fix:* same guard on the detail page, shared helper, and — once C-03 is solved — remove the state. **P1**

### Medium

**UX-07 · Currency handling is USD-only in the UI** — cart total and line items hard-code USD (`cart-sheet.tsx:14-17,124`); budget/stylist labels say "USD" while `/recommend` and chat can return INR/EUR/GBP; all `Intl.NumberFormat` calls use locale `en-US` (`product-card.tsx:64`, `product.$productId.tsx:175`) so INR renders in US grouping. *Fix:* one `formatPrice(amount, currency, locale)` helper; per-cart currency. **P2**

**UX-08 · Accessibility gaps (source-level; verify with axe/NVDA)**
- Copilot messages and search status have no live region (no `aria-live`/`role="status"` anywhere in routes/components).
- Visual-search drop zone: `role="button"` reacts to Enter only (`visual-search.tsx:71`); Space doesn't activate; duplicate "Choose image" button; preview `alt="Uploaded reference"` is generic.
- Several `<Label>`s for Radix `<Select>` lack `htmlFor` association (`stylist.tsx:84,100,116`, `filters.tsx:~29`).
- Broken-image handler hides the element (`product.$productId.tsx:144-146`) leaving an empty card with no text alternative; product-card hides with `display:none` (`product-card.tsx:88-90`) and shows nothing.
- No skip-to-content link; no visible focus audit performed; colour contrast for `text-muted-foreground` on tinted cards unverified.
*Fix:* add live regions, keyboard handlers (Enter **and** Space), label associations, image fallback component, run axe + manual keyboard/screen-reader pass; target WCAG 2.2 AA. **P2**

**UX-09 · Text-encoding corruption** — `seasonal.tsx:15,20,56` contains mojibake (`â€”`, `â€¦`): the tab title and OG title read "Seasonal Recommendations â€” CatalogIQ AI". *Fix:* re-save as UTF-8 and correct the characters. **P2**

**UX-10 · Copilot UX** — no streaming/typing feedback beyond "Thinking…"; no conversation memory so follow-ups ("make it cheaper") fail; developer-oriented error text (`copilot.tsx:66-67`: "Please ensure the backend is connected"); chat history is lost on navigation; no way to reset or give feedback on an answer. **P2**

**UX-11 · Missing core shopping surfaces** — no browse/category pages, no wishlist page (wishlist exists only as toggle + count), no size/colour selection, no stock/availability per variant, no reviews, no order tracking. **P1 as part of Phase 3/5**

### Low

**UX-12 · Terminology inconsistency** — "Add to bag" (card) vs "Add to cart" (detail) vs "Cart" (drawer).
**UX-13 · Profile defaults look saved** — `preferredSize` "M" and style keywords are pre-filled when empty (`profile.tsx:47-48`), so a user may believe preferences exist that were never set.
**UX-14 · Brand shows department** for H&M items (`services.ts:116,254`).
**UX-15 · Third-party font CDN** (`__root.tsx:99-104`): self-host for speed/privacy.
**UX-16 · `/dashboard` and `/profile` are not guarded**; logged-out users see the full dashboard (with fake data) and a "Not logged in" card in profile.

---

## 4. Cross-cutting evaluation

| Dimension | Assessment |
|---|---|
| **Responsive design** | Good foundations: mobile nav sheet (`app-shell.tsx:52-62`), responsive grids (`sm:/lg:/xl:`), filters in a sheet on small screens (`search.tsx:120-136`). Needs real-device verification, esp. cart drawer width, copilot `h-[70vh]` on mobile keyboards, and checkout (not built). |
| **Accessibility** | Partial (UX-08). Radix primitives give a solid base; app-level gaps above. |
| **Loading states** | Skeletons exist for grids, panels, lists (`skeletons.tsx`). Missing: skeleton on product page "related", per-route Suspense/pending UI for navigation. |
| **Empty states** | Present for search, cart, copilot picks, stylist. Missing: wishlist page, orders. |
| **Error messages** | Mixed: some good (`login.tsx` maps server detail), some developer-facing; many errors are swallowed by fallbacks (C-05). No global offline/API-down banner. |
| **Consistency** | Strong visual consistency; copy/currency/terminology inconsistent (UX-07, UX-12). |
| **Usability** | Discovery flow is clear; the dead-end at checkout and wrong-product navigation will dominate real-user experience. |
| **Performance (perceived)** | `index.tsx` is a ~36 KB route; product imagery comes from third-party Unsplash URLs (12 in `src/lib/api/mock.ts`, plus the demo seed data) at fixed `w=800`/`w=600`; no image dimensions or `srcset` (layout-shift risk — verify with Lighthouse). |
| **Trust & compliance** | No terms, privacy, returns, shipping pages; footer links not verified to resolve; invented claims (UX-04). Needed before taking payments. |

---

## 5. Recommended UI work (maps to Roadmap Phases 0, 3, 5)

1. Remove mocks from production, add real error/empty/offline states.
2. Add product-not-found, price-unavailable and out-of-stock states that are consistent between card and detail.
3. Replace fabricated content with real aggregates or remove.
4. Build: browse/category page with facets and true pagination; wishlist page; variant selection; cart with currency; checkout (address → shipping → payment → confirmation); orders list/detail; account security settings; admin console (products, stock, orders, users).
5. Accessibility pass to WCAG 2.2 AA with automated (axe, Lighthouse CI) and manual checks.
6. Copy and policy pages (shipping, returns, privacy, terms) supplied by you — not generated placeholders.

**Preserve:** component library, skeletons, toasts, theme provider, app-shell responsiveness, `ProductCard` price/image guards, visual-search client-side validation.
