# CatalogIQ AI

## Intelligent Multi-Intent Product Discovery & Recommendation Engine

CatalogIQ AI is an AI-powered e-commerce platform that delivers personalized product discovery by understanding **user intent**, **semantic meaning**, and **shopping behavior** instead of relying only on keyword matching or purchase history.

The platform combines **semantic search**, **recommendation intelligence**, and **AI-assisted shopping** to provide relevant, explainable, and personalized recommendations in real time.

---

# Features

* 🔍 Semantic Search using Sentence Transformers
* 🧠 Multi-Intent Detection Engine
* 🎯 Personalized Recommendation Engine
* 🤖 AI Shopping Copilot
* 👔 AI Stylist
* 💰 Budget Optimizer
* 🌦️ Seasonal Intelligence
* 🖼️ Visual Search
* 🛒 Complete the Look Recommendations
* 📈 Explainable AI Recommendations

---

# Technology Stack

## Frontend

* React
* Vite
* TypeScript
* Tailwind CSS
* shadcn/ui
* React Router
* TanStack Query
* Axios

## Backend

* FastAPI
* Python
* Pydantic

## Database

* MongoDB Atlas

## AI & Search

* Sentence Transformers (all-MiniLM-L6-v2)
* FAISS Vector Search
* Cosine Similarity
* Google Gemini (Reasoning & AI Assistant)

---

# System Architecture

```text
                        User
                          │
                    React Frontend
                          │
                   FastAPI Backend
                          │
      ┌───────────────────┼────────────────────┐
      │                   │                    │
Intent Engine      Semantic Search      AI Copilot
      │          (Sentence Transformers)       │
      │                   │                    │
      └─────────────── FAISS Vector Search ────┘
                          │
               Recommendation Engine
                          │
     ┌────────────┬──────────────┬──────────────┐
     │            │              │              │
AI Stylist  Budget Optimizer  Seasonal AI  Explainability
                          │
                    MongoDB Atlas
```

---

# Recommendation Workflow

```text
User Action
      │
      ▼
Intent Detection
      │
      ▼
Session Memory Update
      │
      ▼
Sentence Transformer Embedding
      │
      ▼
FAISS Semantic Search
      │
      ▼
Candidate Product Retrieval
      │
      ▼
Recommendation Ranking
(Intent + Similarity + Popularity + Budget + Season)
      │
      ▼
Explainability Engine
      │
      ▼
Personalized Recommendations
```

---

# Project Structure

```text
CatalogIQ/
│
├── frontend/
│   ├── components/
│   ├── pages/
│   ├── services/
│   ├── hooks/
│   ├── layouts/
│   ├── assets/
│   └── utils/
│
├── backend/
│   ├── api/
│   ├── agents/
│   ├── services/
│   ├── models/
│   ├── database/
│   ├── embeddings/
│   └── utils/
│
├── dataset/
├── docs/
└── README.md
```


# Current Progress

* ✅ Frontend UI Completed
* ✅ Backend Foundation Created
* ✅ MongoDB Integration
* ✅ Product Catalog Prepared
* ✅ Semantic Search using Sentence Transformers
* ✅ FAISS Vector Search

---
TEAM NAME:CatalogIcons
Project: CatalogIQ AI
Category: Customer Experience & Personalization
Hackathon: AI Build Hackathon 2026

1. **Jajula Gnana Deepak** — **2300030263**
2. **Kailash** — **2300031593**
