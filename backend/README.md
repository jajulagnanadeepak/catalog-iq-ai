# CatalogIQ AI — FastAPI Backend

AI-powered commerce intelligence API.

## Quick Start

### 1. Prerequisites
- Python 3.11+
- MongoDB Atlas cluster (or local MongoDB)

### 2. Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# or: source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Create environment file
copy .env.example .env
# Edit .env — add your MONGODB_URL and change JWT_SECRET
```

### 3. Seed the database (first run only)

```bash
python -m database.seed
```

### 4. Start the API server

```bash
uvicorn main:app --reload --port 8000
```

### 5. Swagger UI

Open **http://localhost:8000/docs** in your browser.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/products` | List/filter/paginate products |
| `GET` | `/api/products/{id}` | Single product detail |
| `POST` | `/api/search` | Keyword product search |
| `GET` | `/api/recommend` | Top-rated recommendations |
| `POST` | `/api/intent` | NLU intent classification |
| `POST` | `/api/auth/signup` | Create account → JWT |
| `POST` | `/api/auth/login` | Login → JWT |
| `GET` | `/health` | Health check |

All routes are prefixed with `/api` to match the Vite dev proxy and frontend `requestWithFallback`.

---

## Folder Structure

```
backend/
├── main.py               # FastAPI app factory
├── config.py             # Pydantic-settings (reads .env)
├── dependencies.py       # DI: get_db, JWT auth guards
├── api/v1/               # Route handlers (thin controllers)
│   ├── products.py
│   ├── search.py
│   ├── intent.py
│   ├── recommend.py
│   └── auth.py
├── services/             # Business logic
│   ├── product_service.py
│   ├── search_service.py
│   ├── intent_service.py
│   └── recommendation_service.py
├── models/               # Pydantic schemas & DB models
│   ├── product.py
│   ├── user.py
│   └── schemas.py
├── database/             # MongoDB connection + seed
│   ├── connection.py
│   └── seed.py
├── utils/                # JWT, security, pagination
│   ├── jwt.py
│   ├── security.py
│   └── pagination.py
├── agents/               # Placeholder — future AI agents
└── embeddings/           # Placeholder — future embedding models
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB Atlas connection string |
| `DATABASE_NAME` | `catalogiq` | Database name |
| `JWT_SECRET` | *(required)* | Secret key for JWT signing |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRE_MINUTES` | `1440` | Token lifetime (24h) |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | CORS allowed origins |
