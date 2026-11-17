# Streamlit → React Migration Guide

**Scope:** How to migrate an existing Streamlit application to the UI stack and design system used in EIBO (React 18 + TypeScript 5.5 + Vite 5 + Zustand + inline `React.CSSProperties` + hand-coded SVG + OPB design tokens).

**Audience:** A developer who has a working Streamlit app and wants to port it to this stack. The guide covers the mental model shift, scaffolding, component-by-component mapping, API extraction, state migration, and routing.

---

## Table of Contents

1. [Why migrate from Streamlit?](#1-why-migrate-from-streamlit)
2. [The mental model shift](#2-the-mental-model-shift)
3. [Project scaffolding](#3-project-scaffolding)
4. [Design system foundation — tokens and fonts](#4-design-system-foundation--tokens-and-fonts)
5. [Routing migration — multipage app → App.tsx state switch](#5-routing-migration--multipage-app--apptsx-state-switch)
6. [State migration — st.session_state → Zustand / useState](#6-state-migration--stsession_state--zustand--usestate)
7. [API layer extraction — Python functions → FastAPI endpoints](#7-api-layer-extraction--python-functions--fastapi-endpoints)
8. [Component mapping — every Streamlit widget and its React equivalent](#8-component-mapping--every-streamlit-widget-and-its-react-equivalent)
9. [OPB design system applied to migrated components](#9-opb-design-system-applied-to-migrated-components)
10. [Page structure migration — from st.write to the hero + body pattern](#10-page-structure-migration--from-stwrite-to-the-hero--body-pattern)
11. [Worked example — migrating a Streamlit dashboard page end to end](#11-worked-example--migrating-a-streamlit-dashboard-page-end-to-end)
12. [Charts — from st.plotly_chart to hand-coded SVG](#12-charts--from-stplotly_chart-to-hand-coded-svg)
13. [Data tables — from st.dataframe to a styled HTML table](#13-data-tables--from-stdataframe-to-a-styled-html-table)
14. [Dark mode](#14-dark-mode)
15. [Migration checklist](#15-migration-checklist)
16. [Common mistakes](#16-common-mistakes)

---

## 1. Why migrate from Streamlit?

Streamlit is excellent for rapid prototyping and internal data tools. It has real limitations when the application needs to grow into a production-quality product:

**What Streamlit cannot do easily:**
- Custom navigation that does not look like a Streamlit app (the sidebar, the menu, the hamburger)
- Design systems (every Streamlit app looks similar by default)
- Stateful interactions without re-running the entire script from top to bottom on every widget change
- Components that require fine-grained layout control (pixel-precise positioning, custom animation, SVG charts with hover tooltips)
- Role-based UI (showing different views to different users without full page re-renders)
- Offline-first or fast sub-100ms interactions (Streamlit has a round-trip to the Python server on every interaction)

**What this React stack gives you:**
- Full control over every pixel — your design system, not Streamlit's defaults
- Sub-100ms interactions — state updates re-render only the affected component in the browser; no server round-trip for UI changes
- A real component model — reusable typed components with props, not Python functions that call `st.write`
- TypeScript safety — shapes of API responses are checked at compile time
- A professional design system that can be applied consistently across pages and future applications

The migration has a real cost: you lose Streamlit's extreme speed of development (one file, no build step) and you gain a production-ready, design-consistent, high-performance frontend. Make the trade consciously.

---

## 2. The mental model shift

Before writing a single line of code, understand how these two models differ. Getting this wrong makes the migration harder.

### Streamlit's model: script re-execution

In Streamlit, the entire Python script re-executes top to bottom on every user interaction. A slider change triggers a full re-run. `st.session_state` persists values between runs. The rendering order is the code order — what comes first in the file renders first on the page.

```python
# Streamlit mental model
import streamlit as st

dept = st.selectbox("Department", ["Engineering", "Finance"])   # renders, re-runs on change
data = load_data(dept)                                          # runs AFTER dept is chosen
st.dataframe(data)                                             # renders the result
```

### React's model: component trees with local state

React renders a tree of components. When state changes, only the components that depend on that state re-render — not the whole page. State is declared with hooks (`useState`, `useEffect`) inside components. Data fetching is triggered by effects, not script execution order.

```tsx
// React equivalent
function DashboardPage() {
  const [dept, setDept] = useState('Engineering')
  const [data, setData] = useState<Row[]>([])

  useEffect(() => {
    api.dashboard.get(dept).then(setData)
  }, [dept])   // re-fetches when dept changes, nothing else re-renders

  return (
    <>
      <Select value={dept} onChange={setDept} options={['Engineering', 'Finance']} />
      <DataTable rows={data} />
    </>
  )
}
```

### Key translation table

| Streamlit concept | React equivalent |
|---|---|
| Script re-runs on widget change | Component re-renders on `setState` call |
| `st.session_state` | `useState` (local) or Zustand store (global) |
| `@st.cache_data` | `useEffect` with a dependency array + state variable |
| `st.sidebar` | No sidebar — everything is in the top nav or on-page controls |
| `st.columns(3)` | CSS Grid: `display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)'` |
| `st.tabs(["A", "B"])` | `useState` tab index + conditional render |
| `st.spinner` | Boolean loading state + conditional spinner element |
| `st.success / st.error` | Toast component with ok/error boolean |
| `st.form` | Controlled form with `useState` per field |
| `st.expander` | `useState(false)` open/close toggle |
| `st.plotly_chart` | Hand-coded SVG (see section 12) |
| `st.dataframe` | HTML `<table>` with OPB table styling (see section 13) |
| Page routing (`pages/` folder) | `Page` union type + switch in `App.tsx` |
| `st.set_page_config(title=...)` | `document.title = ...` or `<title>` in `index.html` |

---

## 3. Project scaffolding

Start with a fresh Vite project and layer the stack on top.

### Step 1 — create the Vite project

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

### Step 2 — install the only non-standard dependency

```bash
npm install zustand
```

That is the only npm package beyond React/Vite/TypeScript. No UI library, no CSS framework, no charting library, no router.

### Step 3 — configure Vite to proxy API calls

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
```

The proxy means the frontend fetches `/api/dashboard` and Vite forwards it to `http://localhost:8000/api/dashboard` during development. No CORS issues. In production, nginx handles the same proxying.

### Step 4 — enable TypeScript strict mode

```json
// tsconfig.json — relevant section
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

### Step 5 — directory structure

```
frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.tsx           ← entry point, imports tokens.css
│   ├── App.tsx            ← Page union type + routing switch
│   ├── styles/
│   │   └── tokens.css     ← ALL design tokens — copy from BRAND.md
│   ├── hooks/
│   │   └── useTheme.ts    ← dark mode toggle
│   ├── stores/
│   │   └── demoStore.ts   ← Zustand global state (scenario, size, demoEnabled)
│   ├── services/
│   │   └── api.ts         ← all HTTP calls — no component imports fetch directly
│   ├── components/
│   │   ├── Nav.tsx
│   │   ├── Footer.tsx
│   │   └── Eyebrow.tsx
│   └── pages/
│       ├── DashboardPage.tsx
│       ├── InfoPage.tsx
│       └── ...            ← one file per Streamlit page
```

---

## 4. Design system foundation — tokens and fonts

Before writing any component, install the two files that define the entire visual system.

### tokens.css — copy this verbatim

```css
/* src/styles/tokens.css */
:root {
  /* Brand colours */
  --primary:    #003366;
  --primary-80: #1a4d80;
  --primary-60: #336699;
  --primary-30: #99bbdd;
  --primary-10: #e0eaf4;
  --gold:       #c8982a;
  --gold-light: #e8c46a;
  --dark:       #1c1c2e;
  --mid:        #6b7280;
  --light:      #f4f6f9;
  --white:      #ffffff;

  /* Semantic status colours — use ONLY for data signals, never for structure */
  --status-green:    #27b97c;
  --status-red:      #e03448;
  --status-orange:   #f07020;
  --status-purple:   #7c4dbd;
  --status-blue:     #003366;

  /* Typography */
  --fd: 'Fraunces', Georgia, serif;      /* display only */
  --fb: 'Plus Jakarta Sans', sans-serif; /* interface and body */

  /* Spacing (8-point grid) */
  --space-4:  4px;  --space-8:  8px;  --space-12: 12px;
  --space-16: 16px; --space-24: 24px; --space-32: 32px;
  --space-40: 40px; --space-48: 48px; --space-64: 64px;

  /* Border radius */
  --radius-sm:   6px;
  --radius-md:  12px;
  --radius-lg:  14px;
  --radius-pill: 20px;

  /* Shadows */
  --shadow-card: 0 1px 4px rgba(0,51,102,0.08);
  --shadow-soft: 0 1px 6px rgba(0,51,102,0.09);

  /* Layout */
  --max-width-content:   1200px;
  --max-width-dashboard: 1300px;
  --nav-height: 52px;
}

/* Dark mode overrides — only affects light/white surfaces */
html[data-theme="dark"] {
  --light:      #0f1117;
  --white:      #1a1d27;
  --dark:       #e2e8f0;
  --mid:        #8b9099;
  --primary-10: rgba(255,255,255,0.07);
  --shadow-card: 0 1px 4px rgba(0,0,0,0.35);
  --shadow-soft: 0 1px 6px rgba(0,0,0,0.30);
}

/* Base reset */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background-color: var(--light);
  font-family: var(--fb);
  font-size: 15px;
  line-height: 1.7;
  color: var(--dark);
}
```

### index.html — add Google Fonts

```html
<!-- public/index.html <head> -->
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,600;1,9..144,300;1,9..144,400&display=swap" rel="stylesheet">
```

### main.tsx — import tokens once

```tsx
// src/main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import './styles/tokens.css'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>
)
```

---

## 5. Routing migration — multipage app → App.tsx state switch

Streamlit's multi-page routing uses files in a `pages/` folder. React has no filesystem routing here — all routing is a `useState` in `App.tsx`.

### Streamlit (before)

```
ui/
├── main.py
└── pages/
    ├── 1_Dashboard.py
    ├── 2_Simulation.py
    └── 3_Analytics.py
```

### React (after)

```tsx
// src/App.tsx
import { useState } from 'react'
import Nav from './components/Nav'
import Footer from './components/Footer'
import DashboardPage from './pages/DashboardPage'
import SimulationPage from './pages/SimulationPage'
import AnalyticsPage from './pages/AnalyticsPage'

export type Page = 'dashboard' | 'simulation' | 'analytics'

function renderPage(page: Page) {
  switch (page) {
    case 'dashboard':  return <DashboardPage />
    case 'simulation': return <SimulationPage />
    case 'analytics':  return <AnalyticsPage />
  }
}

export default function App() {
  const [page, setPage] = useState<Page>('dashboard')
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav currentPage={page} onNavigate={setPage} />
      <main style={{ flex: 1 }}>{renderPage(page)}</main>
      <Footer />
    </div>
  )
}
```

Adding a new page requires three changes: add the string literal to the `Page` type, add a `case` to `renderPage`, and add the entry to the `GROUPS` array in `Nav.tsx`. Nothing else.

---

## 6. State migration — st.session_state → Zustand / useState

### Local state (per-page variables)

Streamlit's `st.session_state` is typically used for two different purposes. For values that belong to a single page (current tab, selected row, modal open), use React's `useState`:

```python
# Streamlit
if 'selected_dept' not in st.session_state:
    st.session_state.selected_dept = 'Engineering'
dept = st.selectbox("Department", options, index=options.index(st.session_state.selected_dept))
st.session_state.selected_dept = dept
```

```tsx
// React — local state, no boilerplate
const [dept, setDept] = useState('Engineering')
```

### Global state (shared across pages)

For values that multiple pages need — the selected scenario, the org size, whether demo mode is enabled — use Zustand:

```ts
// src/stores/demoStore.ts
import { create } from 'zustand'

type Scenario = 'A' | 'B' | 'C'
type OrgSize  = 'small' | 'medium' | 'large'

interface DemoStore {
  scenario:   Scenario
  size:       OrgSize
  enabled:    boolean
  setScenario: (s: Scenario) => void
  setSize:     (s: OrgSize)  => void
  setEnabled:  (e: boolean)  => void
}

export const useDemoStore = create<DemoStore>((set) => ({
  scenario:    'A',
  size:        'medium',
  enabled:     true,
  setScenario: (scenario) => set({ scenario }),
  setSize:     (size)     => set({ size }),
  setEnabled:  (enabled)  => set({ enabled }),
}))
```

Consume it in any component with one line:

```tsx
const { scenario, size } = useDemoStore()
```

### Migration mapping

| `st.session_state` usage | React equivalent |
|---|---|
| Current page or tab | `useState<Page>` in `App.tsx` |
| Form field values | `useState` inside the form component |
| Fetched data for a page | `useState<T \| null>` + `useEffect` for fetching |
| Cross-page scenario/config | Zustand store |
| Authentication token | Zustand `authStore` persisted to `localStorage` |
| Demo mode flag | Zustand `demoStore` |

---

## 7. API layer extraction — Python functions → FastAPI endpoints

This is the most significant architectural change. In Streamlit, your analysis functions are called directly from the same Python process:

```python
# Streamlit — direct function call
import streamlit as st
from services.impact_scorer import score_employees

data = score_employees(scenario='A', size='medium')
st.dataframe(data)
```

In the React stack, the frontend cannot call Python directly. Your analysis functions become FastAPI endpoint handlers, and the frontend fetches from them via HTTP:

### Step 1 — wrap the function in a FastAPI router

```python
# backend/routers/dashboard.py
from fastapi import APIRouter, Depends
from services.dashboard_service import build_dashboard_data
from auth.rbac import require_role

router = APIRouter(prefix='/api/dashboard', tags=['dashboard'])

@router.get('')
def get_dashboard(scenario: str = 'A', size: str = 'medium',
                  _: None = Depends(require_role('Viewer'))):
    return build_dashboard_data(scenario, size)
```

### Step 2 — move business logic to the service layer

```python
# backend/services/dashboard_service.py
from data_service import get_org

def build_dashboard_data(scenario: str, size: str) -> dict:
    org = get_org(scenario, size)
    # ... same logic as before, now returns a dict
    return {
        'headcount': len(org.employees),
        'totalPayroll': sum(e.salary for e in org.employees),
        # ...
    }
```

### Step 3 — create the API service in the frontend

```ts
// src/services/api.ts
const BASE = '/api'

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const token = localStorage.getItem('eibo_token')
  const res = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...opts?.headers,
    },
  })
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json() as Promise<T>
}

export const api = {
  dashboard: {
    get: (scenario: string, size: string) =>
      request<DashboardData>(`/dashboard?scenario=${scenario}&size=${size}`),
  },
  // ... other domains
}
```

### Step 4 — fetch in the page component

```tsx
// src/pages/DashboardPage.tsx
import { useEffect, useState } from 'react'
import { useDemoStore } from '../stores/demoStore'
import { api } from '../services/api'
import type { DashboardData } from '../services/api'

export default function DashboardPage() {
  const { scenario, size } = useDemoStore()
  const [data, setData]     = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.dashboard.get(scenario, size)
      .then(setData)
      .finally(() => setLoading(false))
  }, [scenario, size])

  if (loading) return <Spinner />
  if (!data)   return null

  return <DashboardView data={data} />
}
```

Every Streamlit page that calls a Python function needs this extraction: the Python function becomes a service function, the service function gets wrapped in a FastAPI router, and the frontend fetches it via `api.ts`.

---

## 8. Component mapping — every Streamlit widget and its React equivalent

### Text elements

```python
# Streamlit
st.title("Budget Optimizer")
st.header("Department Analysis")
st.subheader("Engineering Team")
st.write("Some body text.")
st.caption("A small note.")
st.markdown("**Bold** and *italic*")
```

```tsx
// React — OPB typography rules apply to all
<h1 style={{ fontFamily: 'var(--fd)', fontSize: 36, fontWeight: 300, color: '#fff' }}>
  Budget <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Optimizer</em>
</h1>
<h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300, color: 'var(--dark)' }}>
  Department Analysis
</h2>
<h3 style={{ fontFamily: 'var(--fb)', fontSize: 16, fontWeight: 600, color: 'var(--dark)' }}>
  Engineering Team
</h3>
<p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: '#475569', lineHeight: 1.75 }}>
  Some body text.
</p>
<p style={{ fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)' }}>
  A small note.
</p>
{/* Markdown: use JSX with inline formatting — no markdown renderer needed */}
<p><strong>Bold</strong> and <em>italic</em></p>
```

---

### Layout — st.columns

```python
# Streamlit
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Headcount", 500)
with col2:
    st.metric("Payroll", "$42M")
with col3:
    st.metric("Avg Risk", "23%")
```

```tsx
// React — CSS Grid
<div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
  <KpiCard label="Headcount" value="500" />
  <KpiCard label="Payroll"   value="$42M" />
  <KpiCard label="Avg Risk"  value="23%" />
</div>
```

Common column patterns:
- `st.columns(2)` → `gridTemplateColumns: '1fr 1fr'`
- `st.columns(3)` → `gridTemplateColumns: 'repeat(3, 1fr)'`
- `st.columns(4)` → `gridTemplateColumns: 'repeat(4, 1fr)'`
- `st.columns([2, 1])` (unequal) → `gridTemplateColumns: '2fr 1fr'`

---

### st.metric → KPI card

```python
# Streamlit
st.metric("Attrition Risk", "34%", delta="+4%")
```

```tsx
// React — OPB KPI card with left gold accent bar
function KpiCard({ label, value, delta, valueColor }: {
  label: string; value: string; delta?: string; valueColor?: string
}) {
  const card: React.CSSProperties = {
    backgroundColor: 'var(--white)',
    borderRadius: 'var(--radius-md)',
    padding: '28px',
    boxShadow: 'var(--shadow-card)',
    border: '1px solid var(--primary-10)',
    display: 'flex',
    alignItems: 'stretch',
    gap: 16,
  }
  return (
    <div style={card}>
      <div style={{ width: 3, backgroundColor: 'var(--gold)', borderRadius: 2, flexShrink: 0 }} />
      <div>
        <div style={{ fontFamily: 'var(--fd)', fontSize: 30, fontWeight: 300,
                      color: valueColor ?? 'var(--dark)' }}>{value}</div>
        <div style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase' as const,
                      letterSpacing: '3px', color: 'var(--mid)', marginTop: 5 }}>{label}</div>
        {delta && (
          <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginTop: 4 }}>
            {delta}
          </div>
        )}
      </div>
    </div>
  )
}
```

Note: the left accent bar (`width: 3px`) is always `var(--gold)` — never use a status colour for the structural bar. If the value is a critical KPI, express that in `valueColor` (e.g., `var(--status-red)`) on the number only.

---

### st.selectbox → select element

```python
# Streamlit
dept = st.selectbox("Department", ["Engineering", "Finance", "Sales"])
```

```tsx
// React — controlled select
function Select({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: string[]
}) {
  return (
    <div>
      <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500,
                      letterSpacing: '2px', textTransform: 'uppercase' as const,
                      color: 'var(--mid)', display: 'block', marginBottom: 6 }}>
        {label}
      </label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)',
                 border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)',
                 padding: '8px 12px', backgroundColor: 'var(--white)',
                 cursor: 'pointer', width: '100%' }}
      >
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  )
}
```

---

### st.slider → range input

```python
# Streamlit
budget = st.slider("Budget ($M)", min_value=1, max_value=50, value=25, step=1)
```

```tsx
// React — controlled range input
function Slider({ label, value, min, max, step, onChange, format }: {
  label: string; value: number; min: number; max: number; step: number;
  onChange: (v: number) => void; format?: (v: number) => string
}) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500,
                       letterSpacing: '2px', textTransform: 'uppercase' as const,
                       color: 'var(--mid)' }}>
          {label}
        </span>
        <span style={{ fontFamily: 'var(--fd)', fontSize: 16, fontWeight: 300,
                       color: 'var(--gold)' }}>
          {format ? format(value) : value}
        </span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        style={{ width: '100%', accentColor: 'var(--gold)', cursor: 'pointer' }}
      />
    </div>
  )
}
```

---

### st.tabs → tab bar

```python
# Streamlit
tab1, tab2 = st.tabs(["Overview", "Detail"])
with tab1:
    show_overview()
with tab2:
    show_detail()
```

```tsx
// React — OPB tab bar pattern (sits at bottom of hero, active tab has gold underline)
const tabs = ['Overview', 'Detail'] as const
type Tab = typeof tabs[number]

function MyPage() {
  const [activeTab, setActiveTab] = useState<Tab>('Overview')

  return (
    <div>
      {/* Hero section */}
      <div style={heroStyle}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto', padding: '48px 48px 0' }}>
          {/* ... hero content ... */}

          {/* Tab bar at bottom of hero */}
          <div style={{ display: 'flex', gap: 4, marginTop: 32 }}>
            {tabs.map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  fontFamily: 'var(--fb)', fontSize: 11, fontWeight: 500,
                  letterSpacing: '1.5px', textTransform: 'uppercase' as const,
                  padding: '10px 20px', marginBottom: -1,
                  borderBottom: `2px solid ${activeTab === tab ? 'var(--gold-light)' : 'transparent'}`,
                  color: activeTab === tab ? 'var(--gold-light)' : 'rgba(255,255,255,0.4)',
                  transition: 'color 0.15s',
                }}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab content */}
      <div style={{ backgroundColor: 'var(--light)', padding: '40px 48px' }}>
        {activeTab === 'Overview' && <OverviewContent />}
        {activeTab === 'Detail'   && <DetailContent />}
      </div>
    </div>
  )
}
```

---

### st.spinner → loading state

```python
# Streamlit
with st.spinner("Loading..."):
    data = fetch_data()
```

```tsx
// React — boolean loading state
const [loading, setLoading] = useState(true)

useEffect(() => {
  setLoading(true)
  api.dashboard.get(scenario, size).then(setData).finally(() => setLoading(false))
}, [scenario, size])

// Render loading indicator
{loading && (
  <div style={{ display: 'flex', alignItems: 'center', gap: 10,
                fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)',
                padding: '40px 0' }}>
    <div style={{
      width: 16, height: 16, borderRadius: '50%',
      border: '2px solid var(--primary-10)',
      borderTopColor: 'var(--gold)',
      animation: 'spin 0.8s linear infinite',
    }} />
    Loading...
  </div>
)}
```

Add to `tokens.css`:
```css
@keyframes spin { to { transform: rotate(360deg); } }
```

---

### st.success / st.error / st.warning → Toast

```python
# Streamlit
st.success("Simulation complete.")
st.error("An error occurred.")
st.warning("Budget threshold reached.")
```

```tsx
// React — Toast component
function Toast({ message, type }: { message: string; type: 'success' | 'error' | 'warning' }) {
  const palette = {
    success: { text: '#22943a', bg: 'rgba(34,148,58,0.07)', border: 'rgba(34,148,58,0.2)' },
    error:   { text: '#b03535', bg: 'rgba(176,53,53,0.07)', border: 'rgba(176,53,53,0.2)' },
    warning: { text: '#92520a', bg: 'rgba(240,112,32,0.07)', border: 'rgba(240,112,32,0.2)' },
  }[type]

  return (
    <div style={{
      fontFamily: 'var(--fb)', fontSize: 12, color: palette.text,
      backgroundColor: palette.bg, border: `1px solid ${palette.border}`,
      borderRadius: 8, padding: '10px 16px', marginTop: 16,
    }}>
      {message}
    </div>
  )
}
```

---

### st.form → controlled form

```python
# Streamlit
with st.form("config_form"):
    name  = st.text_input("Scenario name")
    budget = st.number_input("Budget", value=10000000, step=100000)
    submitted = st.form_submit_button("Save")
    if submitted:
        save_scenario(name, budget)
```

```tsx
// React — controlled form
function ConfigForm() {
  const [name,   setName]   = useState('')
  const [budget, setBudget] = useState(10_000_000)
  const [msg,    setMsg]    = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.scenarios.save({ name, budget })
      setMsg('Saved successfully.')
    } catch {
      setMsg('Save failed.')
    }
  }

  const inputStyle: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)',
    border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)',
    padding: '8px 12px', backgroundColor: 'var(--white)', width: '100%',
  }
  const labelStyle: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500, letterSpacing: '2px',
    textTransform: 'uppercase', color: 'var(--mid)', display: 'block', marginBottom: 6,
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <label style={labelStyle}>Scenario Name</label>
        <input style={inputStyle} value={name} onChange={e => setName(e.target.value)} />
      </div>
      <div>
        <label style={labelStyle}>Budget</label>
        <input type="number" style={inputStyle}
               value={budget} onChange={e => setBudget(Number(e.target.value))} step={100000} />
      </div>
      <button type="submit" style={{
        fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 700,
        letterSpacing: '2px', textTransform: 'uppercase' as const,
        backgroundColor: 'var(--gold)', color: '#fff',
        border: 'none', borderRadius: 'var(--radius-sm)', padding: '10px 20px',
        cursor: 'pointer', alignSelf: 'flex-start',
      }}>
        Save
      </button>
      {msg && <Toast message={msg} type={msg.includes('fail') ? 'error' : 'success'} />}
    </form>
  )
}
```

---

### st.expander → collapsible section

```python
# Streamlit
with st.expander("Advanced configuration"):
    st.write("Hidden content here.")
```

```tsx
// React — toggle with useState
function Expander({ label, children }: { label: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{ border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-md)' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', textAlign: 'left' as const, background: 'none', border: 'none',
          fontFamily: 'var(--fb)', fontSize: 12, fontWeight: 500, color: 'var(--dark)',
          padding: '14px 16px', cursor: 'pointer', display: 'flex',
          justifyContent: 'space-between', alignItems: 'center',
        }}
      >
        {label}
        <span style={{ fontSize: 10, transform: open ? 'rotate(180deg)' : 'none',
                        transition: 'transform 0.15s', display: 'inline-block' }}>▾</span>
      </button>
      {open && (
        <div style={{ padding: '0 16px 16px', borderTop: '1px solid var(--primary-10)' }}>
          {children}
        </div>
      )}
    </div>
  )
}
```

---

### st.sidebar → removed entirely

Streamlit's sidebar is a fixed left panel for page-wide controls. In the EIBO stack, there is no sidebar. Page-wide controls (scenario selector, size selector, filters) appear either:

1. **In the hero section** — as a control row beneath the title, inside the dark navy hero
2. **At the top of the body** — as a card with controls before the first data section

The nav bar handles page routing. The hero handles page context and primary filters. There is no persistent side panel.

---

## 9. OPB design system applied to migrated components

When translating each Streamlit element, apply these rules consistently:

### Typography rules (non-negotiable)

| What | Font | Weight | Size | Notes |
|---|---|---|---|---|
| Page hero title | Fraunces (`var(--fd)`) | 300 | 36–48px | Key word in italic + `var(--gold-light)` |
| Section heading (H2) | Fraunces | 300 | 22px | Italic on emphasis word when needed |
| Widget header (H3) | Plus Jakarta (`var(--fb)`) | 600 | 16px | Not Fraunces |
| Body / description text | Plus Jakarta | 400 | 13–15px | `line-height: 1.7–1.75` |
| Labels, eyebrows, tags | Plus Jakarta | 500–700 | 9–11px | UPPERCASE + `letterSpacing: '2–4px'` |
| KPI value numbers | Fraunces | 300 | 28–34px | On cards; `var(--gold-light)` on dark backgrounds |
| Table headers | Plus Jakarta | 600 | 10px | UPPERCASE + `letterSpacing: '2px'` |

**Never bold Fraunces** (no weight 600 or 700). Use 300 or 400 only.

**Never use Fraunces for body text, labels, or captions.** Fraunces is display-only.

### Colour rules (non-negotiable)

| Element | Required colour | Prohibited |
|---|---|---|
| Hero section background | `var(--primary)` (`#003366`) | Any other colour |
| Nav background | `rgba(0,51,102,0.97)` | — |
| Page body background | `var(--light)` | Hardcoded `#f4f6f9` |
| Card background | `var(--white)` | Hardcoded `#ffffff` |
| KPI card left accent bar | `var(--gold)` only | Status colours, any other |
| KPI card top accent border | `var(--gold)` only | Status colours, any other |
| KPI value text (critical) | `var(--status-red)` or `var(--status-orange)` on the numeral only | Border, bar, label |
| Chart categorical series | `#003366, #1a4d80, #336699, #99bbdd, #c8982a` | Green, purple, orange for series |
| Eyebrow on dark bg | `var(--gold-light)` | `var(--gold)` on dark |
| Eyebrow on light bg | `var(--gold)` | `var(--gold-light)` on light |
| Active nav tab underline | `var(--gold-light)` | Status colours |

### The Eyebrow component — use before every section

Every content section in the body (not the hero) begins with the Eyebrow component:

```tsx
// src/components/Eyebrow.tsx
export default function Eyebrow({ children, light = false }: {
  children: React.ReactNode; light?: boolean
}) {
  const color = light ? 'var(--gold-light)' : 'var(--gold)'
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8,
                  fontFamily: 'var(--fb)', fontSize: 9, fontWeight: 500,
                  letterSpacing: '4px', textTransform: 'uppercase' as const,
                  color, marginBottom: 10 }}>
      <div style={{ width: 24, height: 1, flexShrink: 0, backgroundColor: color }} />
      {children}
    </div>
  )
}
```

Max 4 words in the eyebrow label. No numbers ("01 · Metrics"). No promotional language ("Amazing Insights"). Just the section name.

---

## 10. Page structure migration — from st.write to the hero + body pattern

Every Streamlit page that begins with `st.title` should become a page following the standard EIBO hero + body structure.

### Streamlit page (before)

```python
# pages/1_Dashboard.py
import streamlit as st

st.title("Dashboard")
st.write("Overview of workforce health.")

col1, col2, col3 = st.columns(3)
col1.metric("Headcount", 500)
col2.metric("Payroll", "$42M")
col3.metric("Avg Risk", "23%")

st.header("Department Breakdown")
st.dataframe(dept_data)

st.header("Attrition Risk Distribution")
st.plotly_chart(risk_chart)
```

### React page (after)

```tsx
// src/pages/DashboardPage.tsx
import Eyebrow from '../components/Eyebrow'

const heroStyle: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  backgroundImage: `
    linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)
  `,
  backgroundSize: '48px 48px',
  padding: '56px 48px',
}

export default function DashboardPage() {
  const { scenario, size } = useDemoStore()
  const [data, setData]     = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.dashboard.get(scenario, size).then(setData).finally(() => setLoading(false))
  }, [scenario, size])

  if (loading) return <Spinner />
  if (!data)   return null

  return (
    <div>
      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <div style={heroStyle}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto' }}>
          <Eyebrow light>Workforce Overview</Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 36, fontWeight: 300,
                       color: '#fff', margin: '0 0 12px' }}>
            Where do we <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>stand?</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14,
                      color: 'rgba(255,255,255,0.55)', maxWidth: 560 }}>
            Overview of workforce health across all departments.
          </p>

          {/* Hero stat row */}
          <div style={{ display: 'flex', gap: 32, marginTop: 36 }}>
            {[
              { value: data.headcount.toString(), label: 'Headcount' },
              { value: `$${(data.totalPayroll / 1e6).toFixed(1)}M`, label: 'Total Payroll' },
              { value: `${data.avgRisk}%`, label: 'Avg Attrition Risk' },
            ].map(stat => (
              <div key={stat.label} style={{ borderLeft: '2px solid var(--gold)', paddingLeft: 18 }}>
                <div style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300,
                              color: 'var(--gold-light)', lineHeight: 1, marginBottom: 8 }}>
                  {stat.value}
                </div>
                <div style={{ fontFamily: 'var(--fb)', fontSize: 12,
                              color: 'rgba(255,255,255,0.5)' }}>
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Body ──────────────────────────────────────────────────────── */}
      <div style={{ backgroundColor: 'var(--light)', minHeight: '60vh' }}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto',
                      padding: '40px 48px', display: 'flex', flexDirection: 'column', gap: 40 }}>

          {/* Department breakdown */}
          <section>
            <Eyebrow>Department Breakdown</Eyebrow>
            <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300,
                         color: 'var(--dark)', marginBottom: 20 }}>
              Headcount and budget by department
            </h2>
            <DeptTable rows={data.departments} />
          </section>

          {/* Risk distribution */}
          <section>
            <Eyebrow>Attrition Risk</Eyebrow>
            <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300,
                         color: 'var(--dark)', marginBottom: 20 }}>
              Risk distribution across workforce
            </h2>
            <RiskChart data={data.riskDistribution} />
          </section>

        </div>
      </div>
    </div>
  )
}
```

---

## 11. Worked example — migrating a Streamlit dashboard page end to end

This is a full migration walkthrough for a Streamlit page that has a selectbox, two metrics, a chart, and a dataframe.

### Original Streamlit file

```python
# pages/2_Compensation.py
import streamlit as st
from services.compensation_service import get_comp_data

st.title("Compensation Analysis")
st.write("Pay equity and compensation benchmarking.")

dept = st.selectbox("Filter by Department", ["All", "Engineering", "Finance", "Sales"])
data = get_comp_data(dept)

col1, col2 = st.columns(2)
col1.metric("Avg Comp Ratio", f"{data['avg_comp_ratio']:.2f}")
col2.metric("Below Market", f"{data['below_market_count']} employees")

st.header("Compensation Distribution")
st.plotly_chart(data['distribution_chart'])

st.header("Employee Comp Detail")
st.dataframe(data['employees'])
```

### Step 1 — extract the service function to FastAPI

```python
# backend/services/compensation_service.py
from data_service import get_org

def build_compensation_data(scenario: str, size: str, dept_filter: str) -> dict:
    org = get_org(scenario, size)
    emps = [e for e in org.employees if dept_filter == 'All' or e.department == dept_filter]
    comp_ratios = [e.salary / e.market_median for e in emps]
    return {
        'avgCompRatio':     round(sum(comp_ratios) / len(comp_ratios), 2),
        'belowMarketCount': sum(1 for r in comp_ratios if r < 0.85),
        'buckets':          build_distribution_buckets(comp_ratios),
        'employees':        [emp_to_dict(e) for e in emps],
    }
```

```python
# backend/routers/compensation.py
from fastapi import APIRouter
from services.compensation_service import build_compensation_data

router = APIRouter(prefix='/api/compensation', tags=['compensation'])

@router.get('')
def get_compensation(scenario: str = 'A', size: str = 'medium', dept: str = 'All'):
    return build_compensation_data(scenario, size, dept)
```

### Step 2 — add to api.ts

```ts
// src/services/api.ts
compensation: {
  get: (scenario: string, size: string, dept: string) =>
    request<CompensationData>(`/compensation?scenario=${scenario}&size=${size}&dept=${encodeURIComponent(dept)}`),
}
```

### Step 3 — write the React page

```tsx
// src/pages/CompensationPage.tsx
import { useState, useEffect } from 'react'
import { useDemoStore } from '../stores/demoStore'
import { api } from '../services/api'
import Eyebrow from '../components/Eyebrow'

const DEPTS = ['All', 'Engineering', 'Finance', 'Sales']

const heroStyle: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  backgroundImage: `linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)`,
  backgroundSize: '48px 48px',
  padding: '56px 48px',
}

const card: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius: 'var(--radius-md)',
  padding: '28px',
  boxShadow: 'var(--shadow-card)',
  border: '1px solid var(--primary-10)',
}

export default function CompensationPage() {
  const { scenario, size } = useDemoStore()
  const [dept,    setDept]    = useState('All')
  const [data,    setData]    = useState<CompensationData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.compensation.get(scenario, size, dept)
      .then(setData)
      .finally(() => setLoading(false))
  }, [scenario, size, dept])

  return (
    <div>
      {/* Hero */}
      <div style={heroStyle}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto' }}>
          <Eyebrow light>Pay Equity</Eyebrow>
          <h1 style={{ fontFamily: 'var(--fd)', fontSize: 36, fontWeight: 300, color: '#fff', marginBottom: 12 }}>
            Compensation <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>analysis</em>
          </h1>
          <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'rgba(255,255,255,0.55)', maxWidth: 520 }}>
            Pay equity and compensation benchmarking across the organization.
          </p>
        </div>
      </div>

      {/* Body */}
      <div style={{ backgroundColor: 'var(--light)', minHeight: '60vh' }}>
        <div style={{ maxWidth: 'var(--max-width-dashboard)', margin: '0 auto', padding: '40px 48px' }}>

          {/* Filter */}
          <div style={{ marginBottom: 32 }}>
            <label style={{ fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 500,
                            letterSpacing: '2px', textTransform: 'uppercase' as const,
                            color: 'var(--mid)', display: 'block', marginBottom: 6 }}>
              Department
            </label>
            <select
              value={dept} onChange={e => setDept(e.target.value)}
              style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)',
                       border: '1px solid var(--primary-10)', borderRadius: 'var(--radius-sm)',
                       padding: '8px 12px', backgroundColor: 'var(--white)', cursor: 'pointer' }}
            >
              {DEPTS.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>

          {loading && <Spinner />}

          {data && (
            <>
              {/* KPI row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 32 }}>
                <div style={{ ...card, display: 'flex', alignItems: 'stretch', gap: 16 }}>
                  <div style={{ width: 3, backgroundColor: 'var(--gold)', borderRadius: 2, flexShrink: 0 }} />
                  <div>
                    <div style={{ fontFamily: 'var(--fd)', fontSize: 30, fontWeight: 300, color: 'var(--dark)' }}>
                      {data.avgCompRatio.toFixed(2)}
                    </div>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase' as const,
                                  letterSpacing: '3px', color: 'var(--mid)', marginTop: 5 }}>
                      Avg Comp Ratio
                    </div>
                  </div>
                </div>
                <div style={{ ...card, display: 'flex', alignItems: 'stretch', gap: 16 }}>
                  <div style={{ width: 3, backgroundColor: 'var(--gold)', borderRadius: 2, flexShrink: 0 }} />
                  <div>
                    <div style={{ fontFamily: 'var(--fd)', fontSize: 30, fontWeight: 300,
                                  color: data.belowMarketCount > 0 ? 'var(--status-orange)' : 'var(--dark)' }}>
                      {data.belowMarketCount}
                    </div>
                    <div style={{ fontFamily: 'var(--fb)', fontSize: 10, textTransform: 'uppercase' as const,
                                  letterSpacing: '3px', color: 'var(--mid)', marginTop: 5 }}>
                      Below Market Employees
                    </div>
                  </div>
                </div>
              </div>

              {/* Distribution chart section */}
              <section style={{ marginBottom: 40 }}>
                <Eyebrow>Distribution</Eyebrow>
                <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300,
                             color: 'var(--dark)', marginBottom: 20 }}>
                  Compensation ratio distribution
                </h2>
                <div style={card}>
                  <CompRatioBarChart buckets={data.buckets} />
                </div>
              </section>

              {/* Employee detail table */}
              <section>
                <Eyebrow>Employee Detail</Eyebrow>
                <h2 style={{ fontFamily: 'var(--fd)', fontSize: 22, fontWeight: 300,
                             color: 'var(--dark)', marginBottom: 20 }}>
                  Individual compensation records
                </h2>
                <EmployeeTable rows={data.employees} />
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
```

---

## 12. Charts — from st.plotly_chart to hand-coded SVG

Streamlit uses Plotly (or Altair, Matplotlib) for charts. This stack uses hand-coded SVG elements rendered by React.

### Why not keep Plotly in React?

You can use `react-plotly.js` in a React app. The reason not to: Plotly charts look like Plotly charts — the default toolbar, the hover tooltips, the font, the color schemes. Making a Plotly chart match the OPB design system requires fighting the library's defaults on every property. Hand-coded SVG gives you exact control.

### Bar chart example

```tsx
// Comp ratio distribution bar chart
interface Bucket { label: string; count: number }

function CompRatioBarChart({ buckets }: { buckets: Bucket[] }) {
  const maxCount = Math.max(...buckets.map(b => b.count))
  const w = 560
  const h = 200
  const barW = Math.floor((w - 40) / buckets.length) - 8
  const colors = ['#e03448', '#f07020', '#27b97c', '#1a4d80', '#003366']

  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" style={{ display: 'block', maxWidth: w }}>
      {buckets.map((b, i) => {
        const barH = maxCount > 0 ? Math.max(4, Math.round((b.count / maxCount) * (h - 40))) : 4
        const x    = 20 + i * (barW + 8)
        const y    = h - 24 - barH
        return (
          <g key={b.label}>
            <rect x={x} y={y} width={barW} height={barH}
                  fill={colors[i % colors.length]} rx={4} />
            <text x={x + barW / 2} y={h - 8}
                  textAnchor="middle" fill="#6b7280"
                  fontSize={9} fontFamily="'Plus Jakarta Sans', sans-serif"
                  textTransform="uppercase" letterSpacing={1}>
              {b.label}
            </text>
            {b.count > 0 && (
              <text x={x + barW / 2} y={y - 4}
                    textAnchor="middle" fill="#1c1c2e"
                    fontSize={10} fontFamily="'Plus Jakarta Sans', sans-serif">
                {b.count}
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}
```

SVG cannot use CSS custom properties in `fill` or `stroke` attributes — use raw hex values from the design token list. `#003366`, `#1a4d80`, `#336699`, `#99bbdd`, `#c8982a` are the only valid series colours. Do not use green, purple, or orange for categorical chart bars — those imply semantic meaning (success, analytics, warning).

### Sparkline example

```tsx
function Sparkline({ values, color = '#003366', width = 120, height = 36 }: {
  values: number[]; color?: string; width?: number; height?: number
}) {
  if (values.length < 2) return null
  const min  = Math.min(...values)
  const max  = Math.max(...values)
  const range = max - min || 1
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width
    const y = height - ((v - min) / range) * (height - 4) - 2
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height}
         style={{ display: 'block' }}>
      <polyline points={pts.join(' ')} fill="none"
                stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
```

---

## 13. Data tables — from st.dataframe to a styled HTML table

```tsx
interface Row { name: string; dept: string; salary: number; compRatio: number; risk: number }

function EmployeeTable({ rows }: { rows: Row[] }) {
  const [sortKey, setSortKey] = useState<keyof Row>('name')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const sorted = [...rows].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey]
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sortDir === 'asc' ? cmp : -cmp
  })

  const toggleSort = (key: keyof Row) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('asc') }
  }

  const thStyle: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 10, fontWeight: 600,
    letterSpacing: '2px', textTransform: 'uppercase' as const,
    color: '#fff', padding: '12px 16px', textAlign: 'left' as const, cursor: 'pointer',
  }
  const tdStyle: React.CSSProperties = {
    fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--dark)',
    padding: '10px 16px',
  }

  return (
    <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)',
                  boxShadow: 'var(--shadow-card)', border: '1px solid var(--primary-10)' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' as const }}>
        <thead>
          <tr style={{ backgroundColor: 'var(--primary)' }}>
            {(['name', 'dept', 'salary', 'compRatio', 'risk'] as (keyof Row)[]).map(key => (
              <th key={key} style={thStyle} onClick={() => toggleSort(key)}>
                {key === 'compRatio' ? 'Comp Ratio' : key.charAt(0).toUpperCase() + key.slice(1)}
                {' '}{sortKey === key ? (sortDir === 'asc' ? '▴' : '▾') : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={row.name}
                style={{ backgroundColor: i % 2 === 0 ? 'var(--white)' : 'var(--primary-10)' }}>
              <td style={tdStyle}>{row.name}</td>
              <td style={tdStyle}>{row.dept}</td>
              <td style={tdStyle}>${row.salary.toLocaleString()}</td>
              <td style={{ ...tdStyle, fontWeight: 500,
                color: row.compRatio < 0.85 ? 'var(--status-orange)' :
                       row.compRatio > 1.15 ? 'var(--status-green)' : 'var(--dark)' }}>
                {row.compRatio.toFixed(2)}
              </td>
              <td style={{ ...tdStyle,
                color: row.risk > 60 ? 'var(--status-red)' :
                       row.risk > 35 ? 'var(--status-orange)' : 'var(--dark)' }}>
                {row.risk}%
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

Key rules:
- `thead` background is always `var(--primary)` with white text
- Row striping: `var(--white)` / `var(--primary-10)` via `i % 2`
- Status colours apply only to value text in data cells — never to row backgrounds, borders, or headers

---

## 14. Dark mode

Copy `useTheme.ts` from the existing frontend:

```ts
// src/hooks/useTheme.ts
import { useState, useEffect } from 'react'

type Theme = 'light' | 'dark'

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute('data-theme', theme)
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    return (localStorage.getItem('eibo-theme') as Theme) ?? 'light'
  })

  useEffect(() => {
    applyTheme(theme)
    localStorage.setItem('eibo-theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')
  return { theme, toggleTheme }
}
```

Dark mode works automatically for any component that uses `var(--white)` and `var(--light)` tokens. Components that use hardcoded `#ffffff` or `#f4f6f9` will not respond to dark mode — those are bugs.

---

## 15. Migration checklist

Work through this list for each Streamlit page you migrate.

### Setup (once, not per page)
- [ ] Vite project created with `--template react-ts`
- [ ] `zustand` installed; no other UI or charting libraries installed
- [ ] `vite.config.ts` proxy configured for `/api` → FastAPI port
- [ ] `tsconfig.json` strict mode enabled (`strict`, `noUnusedLocals`, `noUnusedParameters`)
- [ ] `tokens.css` copied and imported once in `main.tsx`
- [ ] Google Fonts `<link>` added to `index.html`
- [ ] `Eyebrow.tsx` component created
- [ ] `Nav.tsx` component created with OPB monogram and grouped dropdowns
- [ ] `Footer.tsx` component created
- [ ] `App.tsx` has `Page` union type and routing switch
- [ ] `api.ts` service created with base `request()` function

### Per-page migration
- [ ] Python service function extracted from Streamlit page into `backend/services/`
- [ ] FastAPI router created in `backend/routers/` wrapping the service function
- [ ] Router registered in `backend/main.py`
- [ ] TypeScript interface created in `api.ts` matching the FastAPI response shape
- [ ] `api.domain.get()` method added to `api.ts`
- [ ] Page string literal added to `Page` union in `App.tsx`
- [ ] `case` added to `renderPage()` switch in `App.tsx`
- [ ] Nav entry added to `GROUPS` in `Nav.tsx`
- [ ] Page component file created in `src/pages/`

### Per-page design system compliance
- [ ] Hero section uses dark navy background with grid texture
- [ ] Hero title uses Fraunces weight 300 with one word in italic + `var(--gold-light)`
- [ ] Hero has `<Eyebrow light>` label (not in the hero, before the title)
- [ ] Hero stat row uses `borderLeft: '2px solid var(--gold)'` with Fraunces value
- [ ] Body sits on `var(--light)` background
- [ ] Each body section begins with `<Eyebrow>` (not light)
- [ ] Each section has a Fraunces H2 heading
- [ ] KPI cards use left accent bar in `var(--gold)` only
- [ ] No hardcoded `#ffffff` — use `var(--white)`
- [ ] No hardcoded `#f4f6f9` — use `var(--light)`
- [ ] No status colour on structural borders (card `borderTop`, `borderLeft`, eyebrow bar)
- [ ] Chart series use navy gradient + gold only (no green/purple/orange as categorical series)
- [ ] SVG `fill`/`stroke` attributes use raw hex from the design palette (not `var()`)
- [ ] Table `thead` uses `var(--primary)` background with white text
- [ ] Table rows alternate `var(--white)` / `var(--primary-10)`
- [ ] All text 11px and below is uppercase with `letterSpacing: '2px'` minimum
- [ ] Fraunces never used for body text, labels, captions, or interface copy
- [ ] Fraunces never used at weight 600 or 700
- [ ] `npx tsc --noEmit` passes with zero errors

---

## 16. Common mistakes

| Mistake | What goes wrong | Correct approach |
|---|---|---|
| Keeping `st.session_state` logic in mind when designing React state | Trying to mimic "re-run on widget change" with `useEffect` on every possible trigger | React re-renders are component-scoped and automatic — just call `setState` in the handler |
| Putting all state in Zustand | A store with 40 fields, most of which are only used by one page | Use `useState` for local state; Zustand only for values shared across pages |
| Importing `fetch` directly in a component | HTTP calls scattered everywhere, no single place to update auth headers | All HTTP goes through `api.ts`; no component imports `fetch` |
| Using a charting library | Bundle bloat, design system conflicts, library-specific hover behavior | Hand-coded SVG for all charts |
| Hardcoding `#ffffff` in card styles | Card does not darken in dark mode | `var(--white)` |
| Using `var(--status-red)` for a card `borderLeft` | Looks like the card itself has an error | `var(--gold)` for all structural accent bars; status colour only for value text |
| Using `var()` in SVG `fill` attribute | SVG attributes do not inherit CSS custom properties — renders as invalid colour | Use raw hex: `fill="#003366"` not `fill="var(--primary)"` |
| Using green, orange, or purple as a chart series colour | Implies success/warning/analytics meaning to the reader | Use navy gradient sequence: `#003366, #1a4d80, #336699, #99bbdd` + `#c8982a` for emphasis |
| Bolding a Fraunces heading (`fontWeight: 700`) | Looks heavy and wrong — Fraunces is designed for light weights | `fontWeight: 300` or `fontWeight: 400` only |
| Using Fraunces for a label or caption | Looks decorative where it should be functional | Plus Jakarta Sans for all interface copy |
| Forgetting `backgroundColor: 'transparent'` on nav link base style | White flash when transitioning from active to inactive state | Always include it in `navLinkBase` |
| Returning different component trees conditionally before hooks | React error: "Rendered more hooks than the previous render" | All `useState`/`useEffect` calls before any conditional returns |
| Applying the Eyebrow `light` prop on a light background | Gold-light on white is too low contrast | `light` prop only on dark (navy) backgrounds; default (gold) on light backgrounds |
| Missing `noUnusedLocals` TypeScript error in CI | A declared variable that is not used blocks the build | Remove the variable or use it — do not use `// @ts-ignore` |

---

*This guide was written against the EIBO stack (React 18 + TypeScript 5.5 + Vite 5 + Zustand 4 + OPB design system). The Streamlit baseline described here reflects the original architecture documented in `planning/CLAUDE.md`. Questions about specific design token values, component patterns, or API structure should be resolved by reading `planning/BRAND.md` and `planning/UI_Decisions.md`.*
