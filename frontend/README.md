# WMS Dispatch Frontend

WMS Dispatch Frontend is a modern Vue 3 application built with Vite for managing and dispatching warehouse operations, including orders, inventory, and cross-warehouse coordination.

## 🚀 Tech Stack

- **Framework**: Vue 3 (Composition API, <script setup>)
- **Build Tool**: Vite
- **Routing**: Vue Router 4
- **State Management**: Pinia
- **UI Library**: Element Plus
- **HTTP Client**: Axios (with centralized uthApi abstraction and interceptors)

## 📁 Project Structure

`	ext
src/
  ├── api/              # API request abstractions (e.g., authApi) and Axios instance
  ├── assets/           # Static assets (images, logos, etc.)
  ├── layouts/          # Page layouts (e.g., BaseLayout with Sidebar and Header)
  ├── router/           # Application routing and navigation guards (auth requirements, token checking)
  ├── stores/           # Pinia stores (auth store, JWT handling)
  ├── views/            # Main page views
  │   ├── LoginView.vue        # Login page with glassmorphism UI
  │   ├── DashboardView.vue    # Dashboard summary
  │   ├── OrdersView.vue       # Order management
  │   ├── WorkOrdersView.vue   # Dispatching work orders
  │   └── UsersView.vue        # User & permissions management
  ├── App.vue           # Root component
  ├── main.js           # App entry point (mounting Vue, Pinia, Router, Element Plus)
  └── style.css         # Global CSS variables and base styles
`

## ⚙️ Prerequisites

- Node.js 18+
- npm 9+

## 🛠️ Quick Start

`ash
# Install dependencies
npm install

# Start development server
npm run dev
`

Default development address: http://localhost:5173

## 🔗 Backend Integration

The backend service runs on http://localhost:8000.

In the development environment, Vite automatically proxies /api requests to the local backend.

- Frontend makes a request to: /api/...
- Real request targeted to: http://localhost:8000/api/...

If you need to connect to a different backend server URL, you can configure the environment variable:
VITE_API_BASE_URL in .env.

## 📦 Building for Production

`ash
# Build production bundle
npm run build

# Preview production build locally
npm run preview
`

## 📝 Coding Standards

### Axios & APIs
- Service requests should be maintained within the src/api folder rather than firing them straight from components.
- The http.js global interceptor handles attaching the JWT session token (Authorization: Bearer <token>).
- Expired or invalid tokens are handled gracefully by outer/index.js interceptors redirecting safely back to /login.

### Pinia State
- src/stores/auth.js maintains the authentication context.
- Provides getters to evaluate required permissions using hasRole().
