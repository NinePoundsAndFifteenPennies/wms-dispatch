# WMS Dispatch Guidelines

## Code Style
- **Frontend**: Vue 3 with Composition API (`<script setup>`) and Vite. Use Element Plus for UI components. State management is handled by Pinia (e.g., `src/stores/auth.js`).
- **Backend**: FastAPI with Python. Follow modular structure in `backend/modules/` (organized by domain: admin, agent, auth, dispatcher, worker). 
- **Database**: SQLAlchemy with Alembic for migrations. 

## Architecture
- **Frontend** (`frontend/`): All API requests must be abstracted in `src/api/` rather than fired directly from components. The global Axios interceptor (`src/api/http.js`) handles JWT session tokens (`Authorization: Bearer <token>`).
- **Backend** (`backend/`): Router logic is cleanly separated in `backend/api/router.py` and `backend/modules/{domain}/router.py`. Shared utilities and configurations are in `backend/modules/shared/`.
- **AI Agent**: Natural language dispatch and cross-warehouse allocation. Integrates with the backend.

## Build and Test
- **Frontend**:
  - Install: `cd frontend && npm install`
  - Run dev server: `npm run dev` (Vite proxies `/api` to `localhost:8000`)
  - Build: `npm run build`
- **Backend**:
  - Install dependencies: `cd backend && pip install -r requirements.txt`
  - Run dev server: `uvicorn main:app --reload` (runs on `localhost:8000`)
  - Database migrations: `alembic upgrade head`

## Conventions and Business Rules
- **Strict State Machines**: Adhere to the strict state machine rules for Orders and Work Orders defined in `docs/service_rule.md`.
- **Inventory Protection**: `qty_available` is a dynamically calculated PostgreSQL generated column (`GENERATED ALWAYS AS (qty_on_hand - qty_reserved - qty_locked) STORED`). **Never** write to `qty_available` from backend code.
- **Stage Lockdowns**: A stage (picking -> staging -> shipping) becomes locked once completed (`status='completed'`). Never physically create a new work order for a completed stage.
- **Cross-Warehouse Transfer**: Uses a "two-stage lock" model (soft lock -> admin approval -> physical deduct). Follow the lifecycle strictly as documented in `docs/service_rule.md`.
