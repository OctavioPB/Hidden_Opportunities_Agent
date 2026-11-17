# UI Decisions — Employee Impact & Budget Optimizer (EIBO)

> This document is the definitive reference for the OPB design system as implemented in EIBO. It captures every decision made for the UI — philosophy, tokens, typography, colour, navigation, hero sections, footer, data visualizations, component patterns, and dark mode. Anyone who reads this document can replicate the look and feel of the platform exactly, without looking at the code.

---

## Table of Contents

1. [Philosophy](#1-philosophy)
2. [Technology Choices](#2-technology-choices)
3. [Design Tokens](#3-design-tokens)
4. [Typography System](#4-typography-system)
5. [Color Palette](#5-color-palette)
6. [Spacing and Layout Scale](#6-spacing-and-layout-scale)
7. [The Navigation Bar — complete reference](#7-the-navigation-bar--complete-reference)
8. [The Hero Section — complete reference](#8-the-hero-section--complete-reference)
9. [The Footer — complete reference](#9-the-footer--complete-reference)
10. [Body Page Structure](#10-body-page-structure)
11. [Component Catalogue — cards, eyebrows, badges](#11-component-catalogue--cards-eyebrows-badges)
12. [Data Visualizations and Charts](#12-data-visualizations-and-charts)
13. [Data Tables](#13-data-tables)
14. [Dark Mode](#14-dark-mode)
15. [State Management](#15-state-management)
16. [API Layer](#16-api-layer)
17. [Inline Styles vs CSS Modules vs Tailwind](#17-inline-styles-vs-css-modules-vs-tailwind)
18. [Migration Guide](#18-migration-guide)

---

## 1. Philosophy

The visual identity is **OPB** — Octavio Pérez Bravo, Data & AI Strategy Architect. The design goal:

> "Corporate authority without excess decoration. Technical precision + executive clarity."

This translates into four practical rules applied everywhere.

**Restraint over decoration.** No gradients on fills. No shadows heavier than `0 1px 6px`. No border-radius above `14px`. Every decorative element — the gold eyebrow line, the `48px` grid texture on hero sections, the ghosted large numerals — serves a structural purpose rather than adding visual noise.

**Typography does the hierarchy work.** Two font families carry the entire visual weight. Fraunces (variable serif) handles titles and display text. Plus Jakarta Sans handles all interface copy, labels, and data. Weight and size variation within these two fonts eliminates the need for colour-based hierarchy beyond a handful of defined tokens.

**Colour signals meaning, not style.** The primary navy (`#003366`) and gold (`#c8982a`) are brand colours. All other colours in the system are semantic — green for on-track, orange for warning, red for critical. Using a colour outside this system requires explicit justification.

**Navy is dominant; gold is the only structural accent.** Navy fills backgrounds, hero sections, table headers, and primary text. Gold marks structural accent lines (card `borderTop`, stat card `borderLeft`), eyebrows, active states, and the primary action button. Status colours (green, orange, red) are reserved exclusively for KPI values that communicate a risk or performance signal — they are **never** applied to structural elements like card borders, eyebrow bars, or categorical labels.

---

## 2. Technology Choices

### React 18 + TypeScript strict mode

React 18 concurrent rendering prevents the UI from freezing during heavy state updates (e.g., the simulation recalculating 5,000 employees). `useTransition` marks expensive updates as non-urgent. TypeScript strict mode (`noUnusedLocals`, `noUnusedParameters`, `strictNullChecks`) catches type mismatches between API responses and component interfaces at compile time — before they reach a browser.

### Vite 5

Native ES module development server. Hot module replacement completes in 50–200ms. The proxy configuration in `vite.config.ts` forwards `/api/*` to the FastAPI backend, eliminating CORS issues during development.

### Zustand

Global state: selected scenario (`A`/`B`/`C`), org size (`small`/`medium`/`large`), and demo mode flag. All other state is component-local via `useState`. Zustand re-renders only the components that subscribed to a specific state slice, not the entire tree.

### No external UI library

No Shadcn, no MUI, no Ant Design. Every component is hand-coded with inline styles and the design token system. This maintains full design fidelity to the OPB brand system without fighting a third-party library's opinions on spacing, colour, or typography.

---

## 3. Design Tokens

All values live in `frontend/src/styles/tokens.css` as CSS custom properties. **No value is ever hardcoded anywhere else in the application.** Using a raw hex colour in a component instead of a token is a bug.

```css
:root {
  /* ── Colour ──────────────────────────────────────────────────────────── */
  --primary:    #003366;   /* Navy — primary brand, nav bg, hero bg, thead bg */
  --primary-80: #1a4d80;   /* Navy 80% — hover states on dark surfaces      */
  --primary-60: #336699;   /* Navy 60% — links, avatar gradient              */
  --primary-30: #99bbdd;   /* Navy 30% — decorative accents, ghosted borders */
  --primary-10: #e0eaf4;   /* Navy 10% — card bg alt, table stripes, dividers */
  --gold:       #c8982a;   /* Brand gold — eyebrows, borderLeft accent bars  */
  --gold-light: #e8c46a;   /* Gold light — active nav, hero italic, hero stat values */
  --dark:       #1c1c2e;   /* Near-black — primary body text                 */
  --mid:        #6b7280;   /* Grey — secondary text, captions, metadata      */
  --light:      #f4f6f9;   /* Off-white — page background                    */
  --white:      #ffffff;   /* Pure white — card surfaces                     */

  /* ── Semantic status colours — data signals only, never structural ────── */
  --status-green:    #27b97c;
  --status-red:      #e03448;
  --status-orange:   #f07020;
  --status-purple:   #7c4dbd;
  --status-blue:     #003366;

  /* ── Status backgrounds (10% opacity equivalents for badges) ─────────── */
  --status-green-bg:  rgba(39,185,124,0.08);
  --status-red-bg:    rgba(224,52,72,0.08);
  --status-orange-bg: rgba(240,112,32,0.08);

  /* ── Typography ─────────────────────────────────────────────────────── */
  --fd: 'Fraunces', Georgia, serif;      /* display / titles only */
  --fb: 'Plus Jakarta Sans', sans-serif; /* interface / body / labels */

  /* ── Spacing (8-point grid) ──────────────────────────────────────────── */
  --space-4:  4px;  --space-8:   8px;  --space-12: 12px;
  --space-16: 16px; --space-24: 24px;  --space-32: 32px;
  --space-40: 40px; --space-48: 48px;  --space-64: 64px;

  /* ── Border radius ───────────────────────────────────────────────────── */
  --radius-sm:   6px;
  --radius-md:  12px;
  --radius-lg:  14px;
  --radius-pill: 20px;

  /* ── Shadows ─────────────────────────────────────────────────────────── */
  --shadow-card: 0 1px 4px rgba(0,51,102,0.08);
  --shadow-soft: 0 1px 6px rgba(0,51,102,0.09);

  /* ── Layout ──────────────────────────────────────────────────────────── */
  --max-width-content:   1200px;   /* Info / content-heavy pages */
  --max-width-dashboard: 1300px;   /* Data dashboard pages       */
  --nav-height: 52px;
}
```

### Dark mode overrides (applied at `html[data-theme="dark"]`)

```css
html[data-theme="dark"] {
  --light:      #0f1117;
  --white:      #1a1d27;
  --dark:       #e2e8f0;
  --mid:        #8b9099;
  --primary-10: rgba(255,255,255,0.07);
  --shadow-card: 0 1px 4px rgba(0,0,0,0.35);
  --shadow-soft: 0 1px 6px rgba(0,0,0,0.30);
}
/* Navy, gold, and status colours do NOT change in dark mode */
```

### Base reset (also in tokens.css)

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background-color: var(--light);
  font-family: var(--fb);
  font-size: 15px;
  line-height: 1.7;
  color: var(--dark);
}
```

---

## 4. Typography System

Two fonts are loaded via a single Google Fonts `<link>` in `index.html`:

```html
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,600;1,9..144,300;1,9..144,400&display=swap" rel="stylesheet">
```

### Fraunces — display font (`var(--fd)`)

Used exclusively for page titles, hero headings, KPI callout numbers, section H2 headings, and large decorative numerals. **Never** for body copy, labels, captions, or interface controls.

| Context | Size | Weight | Notes |
|---|---|---|---|
| Hero / page titles | 34–36px | 300 | Key word in italic + `var(--gold-light)` |
| Section H2 headings | 21–22px | 300 | Italic on emphasis word when applicable |
| Hero stat values | 32–34px | 300 | `var(--gold-light)` on dark backgrounds |
| Body KPI card values | 28–30px | 300 | `var(--dark)` on white cards |
| In-card metric values | 16–20px | 300–400 | |
| Decorative numerals | 44px | 300 | `var(--primary-30)` — ghosted watermark |

**Critical rule:** Never bold Fraunces. Use weight 300 or 400. The optical size axis (`opsz`) handles visual weight at small sizes automatically.

### Plus Jakarta Sans — interface font (`var(--fb)`)

Used for everything else: body copy, labels, buttons, captions, table cells, form inputs, nav links, footer text.

| Context | Size | Weight | Style |
|---|---|---|---|
| Body text | 13–15px | 400 | `line-height: 1.7–1.75`, `color: #475569` |
| Section captions / sub-text | 13px | 400 | `color: var(--mid)` |
| Labels / eyebrows | 9–11px | 500–700 | UPPERCASE, `letterSpacing: '2–4px'` |
| Table headers (`th`) | 9px | 600 | UPPERCASE, `letterSpacing: '2px'`, white on navy |
| Nav group labels | 9px | 500 | UPPERCASE, `letterSpacing: '2px'` |
| Dropdown items | 11px | 400–600 | `letterSpacing: '0.5px'` |
| Button text | 9–11px | 700 | UPPERCASE, `letterSpacing: '1.5–2px'` |
| Badge / pill labels | 8–10px | 600–700 | UPPERCASE or capitalized |
| Metadata / timestamps | 10–12px | 400 | `color: var(--mid)` |

**Letter spacing rule:** Any text rendered at ≤11px uppercase **must** have `letterSpacing` of at least `'2px'`. Below 11px, zero letter spacing makes uppercase text illegible.

### The italic Fraunces signature mark

The italic Fraunces variant is the single most identifiable element of the OPB brand. Apply it to the key word or phrase in every hero title and section heading:

```tsx
// Hero title
<h1 style={{ fontFamily: 'var(--fd)', fontSize: 34, fontWeight: 300, color: '#fff' }}>
  {orgName} — <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Executive Dashboard</em>
</h1>

// Section heading
<h2 style={{ fontFamily: 'var(--fd)', fontSize: 21, fontWeight: 300, color: 'var(--dark)' }}>
  Budget variance by <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>department</em>
</h2>
```

On dark (hero) backgrounds: italic word uses `var(--gold-light)`.
On light (body) backgrounds: italic word uses `var(--gold)`.

---

## 5. Color Palette

### Primary colour usage

| Token | Hex | Where it goes |
|---|---|---|
| `var(--primary)` | `#003366` | Nav background, hero backgrounds, table `<thead>`, footer |
| `var(--primary-80)` | `#1a4d80` | Avatar gradient end, hover on dark surfaces |
| `var(--primary-60)` | `#336699` | Avatar gradient start, link colour |
| `var(--primary-30)` | `#99bbdd` | Decorative ghosted borders, diagram arrows, lowest histogram bucket |
| `var(--primary-10)` | `#e0eaf4` | Card border, table row stripe, progress bar track, section divider |

### Gold usage

| Token | Hex | Where it goes |
|---|---|---|
| `var(--gold)` | `#c8982a` | Eyebrow lines and text (on light bg), `borderLeft` on hero stats (always `2px`), `borderTop` on body KPI cards (always `3px`), section italic words, accent bars |
| `var(--gold-light)` | `#e8c46a` | Active nav links, hero italic words, hero stat values, active tab underline |

Gold is **never** used as a button fill except for the primary action button. It is **never** varied by metric type or severity — structural gold elements are always gold.

### Semantic status colours — ONLY for data values

| Token | Hex | Use |
|---|---|---|
| `var(--status-green)` | `#27b97c` | Positive, on-track, low risk, under-budget |
| `var(--status-red)` | `#e03448` | Critical, error, high risk, severe overspend |
| `var(--status-orange)` | `#f07020` | Warning, pending, moderate risk, mild overspend |
| `var(--status-purple)` | `#7c4dbd` | Analytics, projections, AI-generated content |

These four colours appear in: KPI value text, progress bar fills, status badge backgrounds, chart dots (when encoding a semantic state). They **never** appear in structural elements: card borders, eyebrow bars, nav items, section dividers, categorical chart series.

### Chart series palette (for multi-series data)

Use this sequence in order. Never use green, purple, or orange as categorical series colours.

```ts
const PALETTE = [
  '#003366',  // navy — primary
  '#1a4d80',  // navy 80%
  '#336699',  // navy 60%
  '#4d7099',  // navy muted
  '#99bbdd',  // navy 30%
  '#c8982a',  // gold — emphasis / top bucket only
  '#e8c46a',  // gold light — highlight
  '#b07820',  // gold dark
  '#ccdde8',  // very light blue
]
```

SVG `fill` and `stroke` attributes cannot use CSS `var()` — use raw hex values from this list.

### Color hierarchy and restriction rules

| Tier | Colours | Purpose |
|---|---|---|
| **1 — Navy (dominant)** | `--primary` through `--primary-10` | Structural mass: hero bg, nav, table headers, body text, decorative accents |
| **2 — Gold (structural accent)** | `--gold`, `--gold-light` | Accent-only: eyebrow bars, `borderLeft` on stat cards, `borderTop` on KPI cards, active states |
| **3 — Status (data signals only)** | `--status-green/red/orange/purple` | KPI value text, progress bar fills, badge backgrounds — only when the value communicates a specific risk or performance signal |

**Permitted and prohibited use:**

| Element | Permitted | Prohibited |
|---|---|---|
| Hero stat card `borderLeft` | `var(--gold)` only | Any status colour |
| Body KPI card `borderTop` | `var(--gold)` only | Any status colour |
| KPI value numeral | `var(--gold-light)` on dark; `var(--dark)` on light; status colour if critical | Purple, orange as decoration |
| Chart categorical series | Navy gradient + gold highlight | Green, purple, orange, pink |
| Status badge | Status colours matched to semantic meaning | Gold or navy as badge colour |
| Section eyebrow bar | `var(--gold)` / `var(--gold-light)` | Any status colour |
| Nav active state | `var(--gold-light)` | Green, red, purple |
| Progress bar track | `var(--primary-10)` | Status colours on the track |
| Progress bar fill | Status colour matching the metric's severity | Gold on non-KPI bars |

---

## 6. Spacing and Layout Scale

### 8-point spacing grid

All margins and paddings come from this scale: `4 / 8 / 12 / 16 / 24 / 32 / 40 / 48 / 64 / 96px`. Never use arbitrary values like `7px`, `11px`, or `23px`. In inline styles, use the raw pixel value from this scale — `var(--space-N)` is available but the raw number is more common in practice.

### Content width constraints

Every page body wraps its content with a `maxWidth` constraint and `margin: 0 auto`:

- `var(--max-width-dashboard)` — 1300px for data-heavy pages
- `var(--max-width-content)` — 1200px for reading-oriented pages

### Grid patterns

| Columns | Use case |
|---|---|
| `1fr 1fr` | Two-panel: chart + detail, chart + legend |
| `1fr 260px` | Wide chart + narrow donut or legend |
| `repeat(3, 1fr)` | Three equal cards in a row |
| `repeat(4, 1fr)` | KPI stat row |
| `repeat(auto-fill, minmax(200px, 1fr))` | Nexus spotlight cards, responsive |
| `300px 1fr` | Filter sidebar + main content |

### Card padding

Standard body cards: `padding: 28px`. Information/content cards: `padding: 32px`. Compact cards: `padding: 18–24px`. Never less than `16px` for any interactive card.

### Section vertical rhythm

Body sections stack with a `gap` of `32px` on the flex container. This is the `sectionGap` constant in dashboard pages. Individual section padding from the page edges: `padding: '44px 48px'`.

---

## 7. The Navigation Bar — complete reference

The nav is a 52px-tall sticky bar anchored to the top of the viewport on a deep navy background. It contains three zones: left (OPB monogram), centre (app title), right (grouped navigation + DEMO badge + theme toggle).

### Outer nav shell

```tsx
const navStyle: React.CSSProperties = {
  backgroundColor: 'rgba(0,51,102,0.97)',  // navy at 97% — slight transparency
  backdropFilter:  'blur(12px)',            // frosted glass on scroll
  height:          'var(--nav-height)',     // 52px
  position:        'sticky',
  top:             0,
  zIndex:          999,
  borderBottom:    '1px solid rgba(255,255,255,0.08)',  // hairline separator
  padding:         '0 40px',
  display:         'flex',
  alignItems:      'center',
  justifyContent:  'space-between',
}
```

**Why `rgba(0,51,102,0.97)` and not `var(--primary)`?** The 97% opacity + `backdropFilter: blur` creates a frosted glass effect — page content scrolling beneath the nav is blurred, reinforcing the sticky behaviour visually. Full opacity would lose this effect.

### Left zone — OPB monogram

```tsx
<div style={{ display: 'flex', alignItems: 'baseline', gap: 1, flexShrink: 0 }}>
  <span style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, color: '#fff', lineHeight: 1 }}>
    O
  </span>
  <em style={{ fontFamily: 'var(--fd)', fontSize: 20, fontWeight: 300, fontStyle: 'italic', color: 'var(--gold-light)', lineHeight: 1 }}>
    PB
  </em>
</div>
```

The `O` is roman (upright), the `PB` is italic. Both are Fraunces weight 300 at 20px. The `alignItems: 'baseline'` ensures the two spans share the same baseline. The 1px gap is intentional — it makes the monogram feel like a single connected mark rather than two separate characters.

### Centre — app title

```tsx
<span style={{
  fontFamily:    'var(--fb)',
  fontSize:      9,
  letterSpacing: '3px',
  textTransform: 'uppercase',
  color:         'rgba(255,255,255,0.4)',
}}>
  EMPLOYEE IMPACT &amp; BUDGET OPTIMIZER
</span>
```

The title is deliberately muted (`rgba(255,255,255,0.4)`) — it labels the application without competing with the navigation controls.

### Right zone — navigation groups

The right cluster uses 5 grouped dropdown menus. Each group (`Analytics`, `Workforce`, `Strategy`, `Engagement`, `Operations`) opens on hover and contains 3–4 pages. A theme toggle button sits to the far right.

#### Group definition

```tsx
type NavGroupDef = {
  label: string
  pages: { id: Page; label: string }[]
}

const GROUPS: NavGroupDef[] = [
  {
    label: 'Analytics',
    pages: [
      { id: 'dashboard',  label: 'Dashboard'  },
      { id: 'drilldown',  label: 'Drill-Down' },
      { id: 'predictive', label: 'Predictive' },
      { id: 'forecast',   label: 'Forecast'   },
    ],
  },
  {
    label: 'Workforce',
    pages: [
      { id: 'compensation', label: 'Compensation' },
      { id: 'knowledge',    label: 'Knowledge'    },
      { id: 'mobility',     label: 'Mobility'     },
      { id: 'fairness',     label: 'Fairness'     },
    ],
  },
  {
    label: 'Strategy',
    pages: [
      { id: 'simulation', label: 'Simulation' },
      { id: 'strategic',  label: 'Strategic'  },
      { id: 'resilience', label: 'Resilience' },
      { id: 'ld',         label: 'L&D'        },
    ],
  },
  {
    label: 'Engagement',
    pages: [
      { id: 'pulse',     label: 'Pulse'     },
      { id: 'ohi',       label: 'OHI'       },
      { id: 'narrative', label: 'Narrative' },
    ],
  },
  {
    label: 'Operations',
    pages: [
      { id: 'decision-room', label: 'Decision Room' },
      { id: 'notifications', label: 'Alerts'        },
      { id: 'admin',         label: 'Admin'         },
      { id: 'info',          label: 'Overview'      },
    ],
  },
]
```

#### Group button (the trigger)

```tsx
const btnStyle: React.CSSProperties = {
  background:      'none',
  border:          'none',
  cursor:          'pointer',
  fontFamily:      'var(--fb)',
  fontSize:        9,
  fontWeight:      500,
  letterSpacing:   '2px',
  textTransform:   'uppercase',
  padding:         '5px 10px',
  borderRadius:    'var(--radius-sm)',
  color:           isActive ? 'var(--gold-light)' : open ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.45)',
  backgroundColor: isActive ? 'rgba(201,168,76,0.12)' : open ? 'rgba(255,255,255,0.05)' : 'transparent',
  display:         'flex',
  alignItems:      'center',
  gap:             5,
  transition:      'color 0.15s, background-color 0.15s',
  whiteSpace:      'nowrap',
}
```

The chevron rotates on open:
```tsx
<span style={{
  fontSize:   7,
  opacity:    0.55,
  display:    'inline-block',
  transform:  open ? 'rotate(180deg)' : 'none',
  transition: 'transform 0.15s',
}}>
  ▾
</span>
```

**Active group state:** when `currentPage` is one of the group's pages, the label shows in `var(--gold-light)` with a `rgba(201,168,76,0.12)` background — same active treatment as individual nav links.

#### Group wrapper — critical positioning pattern

```tsx
<div
  style={{
    position:  'relative',
    alignSelf: 'stretch',   // ← fills full nav height, not just button height
    display:   'flex',
    alignItems:'center',
  }}
  onMouseEnter={() => setOpen(true)}
  onMouseLeave={() => setOpen(false)}
>
```

`alignSelf: 'stretch'` is the key property. The wrapper div fills the full 52px nav height. Since `position: relative` is on this full-height div, the `top: 'calc(100% + 1px)'` on the dropdown panel positions it at the exact bottom edge of the nav bar — not at the bottom edge of the button (which would leave a gap).

#### Dropdown panel

```tsx
{open && (
  <div style={{
    position:        'absolute',
    top:             'calc(100% + 1px)',  // 1px below nav bottom edge
    left:            0,
    backgroundColor: 'rgba(0,32,76,0.98)',
    backdropFilter:  'blur(16px)',
    border:          '1px solid rgba(255,255,255,0.1)',
    borderRadius:    'var(--radius-md)',
    boxShadow:       '0 8px 32px rgba(0,0,0,0.45)',
    padding:         '6px',
    minWidth:        156,
    zIndex:          1000,
    display:         'flex',
    flexDirection:   'column',
    gap:             2,
  }}>
    {group.pages.map(p => (
      <DropdownItem ... />
    ))}
  </div>
)}
```

The panel uses a slightly different shade (`rgba(0,32,76,0.98)`) from the nav (`rgba(0,51,102,0.97)`) — darker and more blue. This distinguishes the dropdown from the nav bar visually while maintaining the navy family. The heavy `boxShadow` grounds the dropdown in space.

#### Dropdown item

```tsx
<button style={{
  background:      'none',
  border:          'none',
  cursor:          'pointer',
  width:           '100%',
  textAlign:       'left',
  fontFamily:      'var(--fb)',
  fontSize:        11,
  fontWeight:      isActive ? 600 : 400,
  letterSpacing:   '0.5px',
  color:           isActive ? 'var(--gold-light)' : hovered ? '#fff' : 'rgba(255,255,255,0.65)',
  backgroundColor: isActive ? 'rgba(201,168,76,0.10)' : hovered ? 'rgba(255,255,255,0.06)' : 'transparent',
  padding:         '7px 12px',
  borderRadius:    6,
  transition:      'background-color 0.1s, color 0.1s',
  whiteSpace:      'nowrap',
}}>
  {label}
</button>
```

Hover state is tracked with `useState(false)` + `onMouseEnter`/`onMouseLeave` — not CSS `:hover`, because inline styles cannot use pseudo-selectors.

#### DEMO badge

Appears to the left of the theme toggle when demo mode is active:

```tsx
{demoEnabled && (
  <span style={{
    fontFamily:    'var(--fb)',
    fontSize:      8,
    letterSpacing: '2px',
    textTransform: 'uppercase',
    color:         'rgba(232,196,106,0.55)',
    marginLeft:    12,
    whiteSpace:    'nowrap',
    alignSelf:     'center',
  }}>
    DEMO
  </span>
)}
```

#### Theme toggle

```tsx
<button
  style={{
    background:      'none',
    backgroundColor: 'transparent',
    border:          'none',
    color:           'rgba(255,255,255,0.45)',
    cursor:          'pointer',
    fontSize:        14,
    padding:         '3px 8px',
    borderRadius:    'var(--radius-sm)',
    marginLeft:      8,
    alignSelf:       'center',
  }}
  onClick={toggleTheme}
  title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
>
  {theme === 'dark' ? '☀' : '◑'}
</button>
```

---

## 8. The Hero Section — complete reference

Every page opens with a dark navy hero section. The hero establishes the page's identity, shows the primary metadata and stats, and optionally hosts a tab bar when the page has multiple views.

### Hero shell — the grid texture

```tsx
const hero: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  backgroundImage: `
    linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)
  `,
  backgroundSize: '48px 48px',
  padding: '52px 48px 40px',  // use '56px 48px' if no tab bar at bottom
}
```

The grid texture is two orthogonal `linear-gradient` layers, each drawing lines at `rgba(255,255,255,0.025)` — barely visible, just enough to give the navy field a woven structure without looking like graph paper. The grid cell size is `48px` on both axes, which matches the horizontal padding.

**Padding variants:**
- Standard (no tab bar): `padding: '56px 48px'`
- With tab bar at bottom: `padding: '52px 48px 40px'` (tab bar gets its own spacing)

### Inner content wrapper

```tsx
const wrap: React.CSSProperties = {
  maxWidth: 'var(--max-width-dashboard)',
  margin: '0 auto',
}
```

Always wrap hero content in this div so the text does not extend beyond the dashboard max-width on wide viewports.

### Hero content structure

```tsx
<div style={hero}>
  <div style={wrap}>

    {/* 1. Eyebrow — context label */}
    <Eyebrow light>
      {size.toUpperCase()} · SCENARIO {scenarioId} — {scenarioName}
    </Eyebrow>

    {/* 2. Title */}
    <h1 style={{
      fontFamily: 'var(--fd)',
      fontSize:   34,
      fontWeight: 300,
      color:      '#fff',
      margin:     '0 0 6px',
      lineHeight: 1.2,
    }}>
      {orgName} — <em style={{ fontStyle: 'italic', color: 'var(--gold-light)' }}>Executive Dashboard</em>
    </h1>

    {/* 3. Subtitle */}
    <p style={{
      fontFamily: 'var(--fb)',
      fontSize:   13,
      color:      'rgba(255,255,255,0.45)',
      margin:     '0 0 32px',
    }}>
      People analytics · budget health · talent risk · network intelligence
    </p>

    {/* 4. Stat row */}
    <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
      <HeroStat value="500"   label="Employees" />
      <HeroStat value="$42M"  label="Annual Budget" />
      <HeroStat value="$38M"  label="Total Spend" sub="+3.2% vs budget" />
    </div>

  </div>
</div>
```

### The HeroStat component

Hero stats are the primary data callouts in the dark hero. Each one has a `2px solid var(--gold)` left border, a large Fraunces value in `var(--gold-light)`, an optional sub-text (e.g., budget variance), and a label below.

```tsx
function HeroStat({ value, label, sub }: {
  value: string; label: string; sub?: string
}) {
  return (
    <div style={{
      borderLeft: '2px solid var(--gold)',
      paddingLeft: 18,
      minWidth: 120,
    }}>
      {/* Primary value */}
      <div style={{
        fontFamily: 'var(--fd)',
        fontSize:   32,
        fontWeight: 300,
        color:      'var(--gold-light)',
        lineHeight: 1,
      }}>
        {value}
      </div>

      {/* Optional sub-text — appears between value and label */}
      {sub && (
        <div style={{
          fontFamily: 'var(--fb)',
          fontSize:   10,
          color:      'rgba(255,255,255,0.5)',
          marginTop:  3,
        }}>
          {sub}
        </div>
      )}

      {/* Label */}
      <div style={{
        fontFamily:    'var(--fb)',
        fontSize:      10,
        letterSpacing: '2px',
        textTransform: 'uppercase',
        color:         'rgba(255,255,255,0.4)',
        marginTop:     4,
      }}>
        {label}
      </div>
    </div>
  )
}
```

**Critical constraints:**
- `borderLeft` is always `2px solid var(--gold)` — never varied by metric type or severity
- Value is always `var(--gold-light)` — never a status colour
- Sub-text is always `rgba(255,255,255,0.5)` — lighter than the label
- Label is always `rgba(255,255,255,0.4)` uppercase — the most muted element

### Hero with tab bar (multi-view pages)

When a page has multiple views (e.g., Business / Engineering on Info, or multiple analysis tabs), the tab bar attaches to the bottom of the hero section:

```tsx
<div style={{ ...hero, padding: '52px 48px 0' }}>  {/* bottom padding = 0 */}
  <div style={wrap}>
    {/* ... eyebrow, title, subtitle ... */}

    {/* Tab bar — sits at bottom of hero with bottom: 0 padding */}
    <div style={{
      display:    'flex',
      gap:        4,
      marginTop:  36,
      borderBottom: '1px solid rgba(255,255,255,0.1)',
    }}>
      {TABS.map(tab => (
        <button
          key={tab.id}
          onClick={() => setActiveTab(tab.id)}
          style={{
            background:   'none',
            border:       'none',
            cursor:       'pointer',
            fontFamily:   'var(--fb)',
            fontSize:     11,
            fontWeight:   500,
            letterSpacing:'1.5px',
            textTransform:'uppercase',
            padding:      '10px 20px',
            marginBottom: -1,   // ← merges tab bottom border with hero bottom edge
            borderBottom: `2px solid ${activeTab === tab.id ? 'var(--gold-light)' : 'transparent'}`,
            color:        activeTab === tab.id ? 'var(--gold-light)' : 'rgba(255,255,255,0.4)',
            transition:   'color 0.15s',
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  </div>
</div>
```

`marginBottom: -1` on each tab button is the critical detail — it pulls the active tab's 2px bottom border into the hero's bottom hairline, creating a visual connection between the active tab and the content section below.

### Loading state

When data is loading, show a centred single-line message rather than a spinner or skeleton:

```tsx
if (loading) return (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
    <p style={{ fontFamily: 'var(--fb)', fontSize: 14, color: 'var(--mid)' }}>
      Loading analytics data…
    </p>
  </div>
)
```

### Error state

```tsx
if (error || !data) return (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
    <div style={{ textAlign: 'center' }}>
      <p style={{ fontFamily: 'var(--fd)', fontSize: 18, color: 'var(--status-orange)', marginBottom: 6 }}>
        Could not load data.
      </p>
      <p style={{ fontFamily: 'var(--fb)', fontSize: 13, color: 'var(--mid)' }}>
        {error} — ensure the backend is running.
      </p>
    </div>
  </div>
)
```

---

## 9. The Footer — complete reference

The footer uses the same navy as the nav bar — visually bookending the page. It is minimal: brand attribution on the left, current month and year on the right.

```tsx
// frontend/src/components/Footer.tsx
const month = new Date()
  .toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  .toUpperCase()

const style: React.CSSProperties = {
  backgroundColor: 'var(--primary)',
  padding:         '20px 48px',
  display:         'flex',
  justifyContent:  'space-between',
  alignItems:      'center',
  fontFamily:      'var(--fb)',
  fontSize:        9,
  letterSpacing:   '3px',
  textTransform:   'uppercase',
  color:           'rgba(255,255,255,0.35)',
  marginTop:       64,   // separates footer from last body section
}

export default function Footer() {
  return (
    <footer style={style}>
      <span>OPB · OCTAVIO PÉREZ BRAVO · EIBO</span>
      <span>{month}</span>
    </footer>
  )
}
```

**Design decisions:**
- `marginTop: 64` — the 64px gap between the last body section and the footer gives the page visual closure without adding a separator line
- `rgba(255,255,255,0.35)` — footer text is the most muted text on the page; it is attribution, not content
- `letterSpacing: '3px'` — maximum letter spacing for max visual reduction of the text
- Left: "OPB · OCTAVIO PÉREZ BRAVO · EIBO" — separator dots (·) created with `·` (middle dot), not hyphens or pipes
- Right: `new Date().toLocaleDateString(...)` — computed at render time, always shows the current month

The footer appears in `App.tsx` below `<main>`:
```tsx
<div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
  <Nav currentPage={page} onNavigate={setPage} />
  <main style={{ flex: 1 }}>{renderPage(page)}</main>
  <Footer />
</div>
```

---

## 10. Body Page Structure

Every page follows this vertical structure:

```
┌──────────────────────────────────────────┐
│  NAV (sticky, 52px, var(--primary))      │
├──────────────────────────────────────────┤
│  HERO (var(--primary) + grid texture)    │
│  ─ Eyebrow light variant                 │
│  ─ H1 with italic gold keyword           │
│  ─ Subtitle in rgba white                │
│  ─ Stat row (HeroStat components)        │
│  ─ [Optional: tab bar at bottom edge]    │
├──────────────────────────────────────────┤
│  BODY (var(--light) background)          │
│                                          │
│  maxWidth wrapper, padding 44px 48px     │
│  flex column, gap 32px                   │
│                                          │
│  SECTION BLOCK                           │
│  ─ SectionHead (Eyebrow + H2 + sub)      │
│  ─ Card content                          │
│                                          │
│  SECTION BLOCK                           │
│  ─ ...                                   │
├──────────────────────────────────────────┤
│  FOOTER (var(--primary), marginTop 64px) │
└──────────────────────────────────────────┘
```

### Body wrapper

```tsx
<div style={{ backgroundColor: 'var(--light)' }}>
  <div style={{
    maxWidth:      'var(--max-width-dashboard)',
    margin:        '0 auto',
    padding:       '44px 48px',
    display:       'flex',
    flexDirection: 'column',
    gap:           32,        // sectionGap constant
  }}>
    {/* sections here */}
  </div>
</div>
```

### SectionHead — the standard section header

Every content section in the body starts with this pattern:

```tsx
function SectionHead({ eyebrow, title, sub }: {
  eyebrow: string;
  title:   React.ReactNode;  // ReactNode to allow italic em elements
  sub?:    string;
}) {
  return (
    <div style={{ marginBottom: 20 }}>
      <Eyebrow>{eyebrow}</Eyebrow>
      <h2 style={{
        fontFamily: 'var(--fd)',
        fontSize:   21,
        fontWeight: 300,
        color:      'var(--dark)',
        margin:     '6px 0 0',
      }}>
        {title}
      </h2>
      {sub && (
        <p style={{
          fontFamily: 'var(--fb)',
          fontSize:   13,
          color:      'var(--mid)',
          marginTop:  4,
        }}>
          {sub}
        </p>
      )}
    </div>
  )
}

// Usage:
<SectionHead
  eyebrow="Financial Health"
  title={<>Budget variance by <em style={{ fontStyle: 'italic', color: 'var(--gold)' }}>department</em></>}
  sub="Green = under budget (favorable). Orange/red = overspend requiring attention."
/>
```

**Rules for SectionHead:**
- Eyebrow: max 4 words, no numbering, no promotional language
- H2 title: italic `em` on the semantically important word, `color: 'var(--gold)'` (not gold-light — gold-light is for dark backgrounds only)
- Sub: plain Jakarta Sans 13px in `var(--mid)`, no italic, purely descriptive

---

## 11. Component Catalogue — cards, eyebrows, badges

### Eyebrow component

```tsx
// frontend/src/components/Eyebrow.tsx
export default function Eyebrow({ children, light = false }: {
  children: React.ReactNode; light?: boolean
}) {
  const color = light ? 'var(--gold-light)' : 'var(--gold)'
  return (
    <div style={{
      display:       'inline-flex',
      alignItems:    'center',
      gap:           8,
      fontFamily:    'var(--fb)',
      fontSize:      9,
      fontWeight:    500,
      letterSpacing: '4px',
      textTransform: 'uppercase',
      color,
      marginBottom:  10,
    }}>
      <div style={{ width: 24, height: 1, flexShrink: 0, backgroundColor: color }} />
      {children}
    </div>
  )
}
```

Use `light` on hero (dark navy) backgrounds. Use default (no prop) on body (light) backgrounds. Never apply the light variant on a light background or the default variant on a dark background — contrast ratios are designed for their specific context.

### Standard body card

```tsx
const card: React.CSSProperties = {
  backgroundColor: 'var(--white)',
  borderRadius:    'var(--radius-md)',   // 12px
  boxShadow:       'var(--shadow-card)', // 0 1px 4px rgba(0,51,102,0.08)
  border:          '1px solid var(--primary-10)',
}

// Usage — always add padding inline:
<div style={{ ...card, padding: 28 }}>...</div>

// Callout / annotated variant (left gold bar):
<div style={{ ...card, padding: 28, borderLeft: '3px solid var(--gold)' }}>...</div>
```

### KPI card — body variant (top gold border)

```tsx
function KpiCard({ label, value, sub, valueColor }: {
  label: string; value: string; sub?: string; valueColor?: string
}) {
  return (
    <div style={{
      ...card,
      padding:    28,
      borderTop:  '3px solid var(--gold)',   // structural gold — always gold
      paddingTop: 20,
    }}>
      <div style={{
        fontFamily:    'var(--fb)',
        fontSize:      9,
        textTransform: 'uppercase',
        letterSpacing: '3px',
        color:         'var(--mid)',
        marginBottom:  8,
      }}>
        {label}
      </div>
      <div style={{
        fontFamily: 'var(--fd)',
        fontSize:   28,
        fontWeight: 300,
        color:      valueColor ?? 'var(--dark)',
      }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', marginTop: 6 }}>
          {sub}
        </div>
      )}
    </div>
  )
}
```

### KPI card — dashboard variant (left accent bar)

Used in multi-column dashboard rows. The accent bar is a `3px wide div` that fills the card height through `alignItems: 'stretch'`:

```tsx
function DashboardKpiCard({ label, value, sub, valueColor }: {
  label: string; value: string; sub?: string; valueColor?: string
}) {
  return (
    <div style={{
      ...card,
      padding:     28,
      display:     'flex',
      alignItems:  'stretch',
      gap:         16,
    }}>
      {/* Left accent bar */}
      <div style={{ width: 3, backgroundColor: 'var(--gold)', borderRadius: 2, flexShrink: 0 }} />

      {/* Content */}
      <div>
        <div style={{
          fontFamily: 'var(--fd)',
          fontSize:   30,
          fontWeight: 300,
          color:      valueColor ?? 'var(--dark)',
        }}>
          {value}
        </div>
        {sub && (
          <div style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'rgba(255,255,255,0.5)', marginTop: 3 }}>
            {sub}
          </div>
        )}
        <div style={{
          fontFamily:    'var(--fb)',
          fontSize:      10,
          letterSpacing: '3px',
          textTransform: 'uppercase',
          color:         'var(--mid)',
          marginTop:     5,
        }}>
          {label}
        </div>
      </div>
    </div>
  )
}
```

### Status badge / pill

```tsx
// Generic status badge — semantic colour
<span style={{
  fontFamily:   'var(--fb)',
  fontSize:     10,
  fontWeight:   700,
  color:        statusColor,          // e.g. 'var(--status-red)'
  backgroundColor: statusBg,          // e.g. 'rgba(224,52,72,0.08)'
  borderRadius: 'var(--radius-pill)', // 20px
  padding:      '2px 9px',
}}>
  {label}
</span>

// With border (for variance badges):
<span style={{
  fontFamily:   'var(--fb)',
  fontSize:     10,
  fontWeight:   700,
  color:        vColor,
  backgroundColor: varianceBg,
  borderRadius: 'var(--radius-pill)',
  padding:      '2px 9px',
  border:       `1px solid ${varianceBorder}`,
}}>
  {r.budget_variance_pct >= 0 ? '+' : ''}{r.budget_variance_pct.toFixed(1)}%
</span>
```

**Badge colour helpers** for budget variance data:

```ts
function varianceColor(v: number) {
  return v > 10 ? 'var(--status-red)'
       : v > 4  ? 'var(--status-orange)'
       : v < -4 ? 'var(--status-green)'
       : 'var(--gold)'
}
function varianceBg(v: number) {
  return v > 10 ? 'rgba(224,52,72,0.08)'
       : v > 4  ? 'rgba(240,112,32,0.08)'
       : v < -4 ? 'rgba(39,185,124,0.08)'
       : 'rgba(200,152,42,0.10)'
}
function varianceBorder(v: number) {
  return v > 10 ? 'rgba(224,52,72,0.25)'
       : v > 4  ? 'rgba(240,112,32,0.25)'
       : v < -4 ? 'rgba(39,185,124,0.25)'
       : 'rgba(200,152,42,0.25)'
}
```

### Outline badge (e.g., Nexus flag)

Used for structural flags (Nexus, SKH) where the badge must be recognizable but not alarming:

```tsx
<span style={{
  fontFamily:    'var(--fb)',
  fontSize:      8,
  fontWeight:    700,
  letterSpacing: '1px',
  textTransform: 'uppercase',
  color:         'var(--gold)',
  border:        '1px solid var(--gold)',
  borderRadius:  'var(--radius-pill)',
  padding:       '2px 7px',
}}>
  Nexus
</span>
```

### Employee avatar / initials circle

```tsx
const initials = fullName.split(' ').map(n => n[0]).join('').slice(0, 2)

<div style={{
  width:           42,
  height:          42,
  borderRadius:    '50%',
  flexShrink:      0,
  background:      'linear-gradient(135deg, var(--primary) 0%, var(--primary-60) 100%)',
  display:         'flex',
  alignItems:      'center',
  justifyContent:  'center',
  border:          '2px solid var(--gold)',
}}>
  <span style={{ fontFamily: 'var(--fd)', fontSize: 15, fontWeight: 700, color: '#fff' }}>
    {initials}
  </span>
</div>
```

The gradient goes from `var(--primary)` (navy) to `var(--primary-60)` (lighter navy), and the `2px gold border` marks the avatar as belonging to the OPB brand system. Initials are Fraunces 700 — the one place where bold Fraunces is used, because it is a display character inside a constrained circular space.

### Progress bar (standalone)

```tsx
// Track + fill pattern used throughout
<div style={{ height: 4, backgroundColor: 'var(--primary-10)', borderRadius: 2 }}>
  <div style={{
    height:          '100%',
    borderRadius:    2,
    backgroundColor: fillColor,           // a status or semantic colour
    width:           `${percentage}%`,
    transition:      'width 0.4s',        // smooth on data change
  }} />
</div>
```

### Progress bar with label (key signal row)

```tsx
{signals.map(({ label, value, total, color, caption }) => (
  <div key={label}>
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
      <span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--dark)' }}>
        {label}
      </span>
      <div>
        <span style={{ fontFamily: 'var(--fd)', fontSize: 16, fontWeight: 700, color }}>
          {value}
        </span>
        <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', marginLeft: 4 }}>
          / {total}
        </span>
      </div>
    </div>
    <div style={{ height: 4, backgroundColor: 'var(--primary-10)', borderRadius: 2 }}>
      <div style={{
        height:          '100%',
        borderRadius:    2,
        backgroundColor: color,
        width:           `${Math.min(100, value / total * 100)}%`,
      }} />
    </div>
    <div style={{ fontFamily: 'var(--fb)', fontSize: 9, color: 'var(--mid)', marginTop: 3 }}>
      {caption}
    </div>
  </div>
))}
```

### Inline bar (in table cells)

For columns like "Avg Impact" or "Fragility" in department tables:

```tsx
<div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
  <div style={{ flex: 1, height: 4, background: 'var(--primary-10)', borderRadius: 2 }}>
    <div style={{
      width:      `${r.avg_impact}%`,
      height:     '100%',
      background: impactColor(r.avg_impact),
      borderRadius: 2,
    }} />
  </div>
  <span style={{
    fontFamily: 'var(--fb)',
    fontSize:   11,
    fontWeight: 600,
    color:      impactColor(r.avg_impact),
    minWidth:   26,
    textAlign:  'right',
  }}>
    {r.avg_impact.toFixed(0)}
  </span>
</div>
```

---

## 12. Data Visualizations and Charts

All charts are hand-coded SVG elements — no Recharts, D3, Chart.js, or Plotly. SVG is a vector format native to the browser that React renders exactly like HTML. This gives pixel-perfect control over every element.

### Critical SVG rules

1. **Always use `viewBox`** — `viewBox="0 0 W H"` makes the chart responsive. Pair with `width="100%"` so the SVG scales to its container.
2. **SVG attributes cannot use `var()`** — `fill="var(--primary)"` does not work in SVG attributes. Use raw hex values from the design palette.
3. **Use `display: 'block'`** — SVG is inline by default, which introduces a 3px baseline gap below the element. `display: 'block'` eliminates it.
4. **Axis labels use `fontFamily` and `fontSize` attributes** — not CSS, because SVG `<text>` elements use presentation attributes.
5. **Valid hex values for SVG** (from the palette):

```
#003366  #1a4d80  #336699  #4d7099  #99bbdd  #c8982a  #e8c46a
#27b97c  #e03448  #f07020  #7c4dbd  #6b7280  #9ca3af  #1c1c2e
rgba(0,51,102,0.04) through rgba(0,51,102,0.18)  ← for gridlines
rgba(0,0,0,0)  ← fully transparent
```

---

### Chart 1 — Horizontal diverging bar (budget variance)

Used for showing positive/negative values against a centred zero line (budget variance by department).

```tsx
function BudgetVarianceChart({ rows }: { rows: DepartmentRow[] }) {
  const sorted  = [...rows].sort((a, b) => b.budget_variance_pct - a.budget_variance_pct)
  const maxAbs  = Math.max(15, ...sorted.map(r => Math.abs(r.budget_variance_pct)))

  // Layout constants
  const ROW_H  = 38    // height per data row
  const PAD_L  = 148   // left padding for department labels
  const BAR_W  = 320   // total bar zone width (divided into + and - halves)
  const PAD_R  = 64    // right padding for percentage value labels
  const W      = PAD_L + BAR_W + PAD_R
  const H      = sorted.length * ROW_H + 28  // 28 for bottom axis labels
  const ZERO_X = PAD_L + BAR_W / 2           // x position of zero line
  const scale  = (BAR_W / 2) / maxAbs        // pixels per 1% variance

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>

      {/* ── Zero line (vertical centred) ── */}
      <line x1={ZERO_X} y1={0} x2={ZERO_X} y2={H - 24}
            stroke="rgba(0,51,102,0.12)" strokeWidth={1} />

      {/* ── Axis ticks and labels ── */}
      {[-1, -0.5, 0, 0.5, 1].map(t => {
        const x = ZERO_X + t * (BAR_W / 2)
        return (
          <g key={t}>
            <line x1={x} y1={0} x2={x} y2={H - 24}
                  stroke="rgba(0,51,102,0.06)" strokeWidth={1} />
            <text x={x} y={H - 6} fontSize={8} fill="#9ca3af" textAnchor="middle">
              {t > 0 ? '+' : ''}{(t * maxAbs).toFixed(0)}%
            </text>
          </g>
        )
      })}

      {/* ── Data rows ── */}
      {sorted.map((r, i) => {
        const y     = i * ROW_H + ROW_H / 2
        const barW  = Math.abs(r.budget_variance_pct) * scale
        const barX  = r.budget_variance_pct >= 0 ? ZERO_X : ZERO_X - barW
        const color = r.budget_variance_pct > 10 ? '#e03448'   // critical overspend
                    : r.budget_variance_pct > 4  ? '#f07020'   // moderate overspend
                    : r.budget_variance_pct < -4 ? '#27b97c'   // favorable underspend
                    : '#c8982a'                                 // near-budget (gold)
        return (
          <g key={r.department}>
            {/* Department label */}
            <text x={PAD_L - 10} y={y + 4} fontSize={11} fill="#1c1c2e"
                  textAnchor="end"
                  fontFamily="'Plus Jakarta Sans', sans-serif">
              {r.department.length > 16 ? r.department.slice(0, 15) + '…' : r.department}
            </text>

            {/* Full-width track bar (background) */}
            <rect x={PAD_L} y={y - 8} width={BAR_W} height={16}
                  fill="rgba(0,51,102,0.04)" rx={3} />

            {/* Actual variance bar */}
            <rect x={barX} y={y - 8} width={Math.max(3, barW)} height={16}
                  fill={color} rx={3} opacity={0.82} />

            {/* Percentage label — right of bar zone */}
            <text x={PAD_L + BAR_W + 8} y={y + 4} fontSize={10} fill={color}
                  fontFamily="'Plus Jakarta Sans', sans-serif" fontWeight="600">
              {r.budget_variance_pct >= 0 ? '+' : ''}{r.budget_variance_pct.toFixed(1)}%
            </text>
          </g>
        )
      })}
    </svg>
  )
}
```

**Key design choices:**
- Track bar (`rgba(0,51,102,0.04)`) is barely visible — just enough to show the scale
- `Math.max(3, barW)` — prevents bars from disappearing at very small values
- `opacity={0.82}` on bars — slight translucency makes overlapping values readable
- Bar colour encodes semantic severity using raw hex (not `var()`)
- Axis ticks are at -100%, -50%, 0, +50%, +100% of maxAbs scale
- Label truncated at 15 chars with `…` to prevent overflow into bar zone

---

### Chart 2 — Donut chart (spend allocation)

Used for part-to-whole breakdowns (e.g., payroll by department).

```tsx
function SpendDonut({ rows }: { rows: DepartmentRow[] }) {
  const sorted  = [...rows].sort((a, b) => b.total_spend - a.total_spend)
  const total   = rows.reduce((s, r) => s + r.total_spend, 0)

  // Donut geometry
  const R = 36                    // radius of donut centre line
  const C = 2 * Math.PI * R       // circumference = 226.2px
  let   cum = 0                   // cumulative percentage tracker

  const segments = sorted.map((r, i) => {
    const pct    = r.total_spend / total
    const dash   = C * pct           // length of this segment's arc
    const offset = C * (1 - cum)     // rotation offset (CSS trick)
    cum += pct
    return { ...r, dash, offset, color: PALETTE[i % PALETTE.length] }
  })

  return (
    <div>
      <svg viewBox="0 0 100 100" width="100%" style={{ display: 'block', maxHeight: 180 }}>

        {/* Background ring */}
        <circle cx="50" cy="50" r={R}
          fill="none"
          stroke="var(--primary-10)"   {/* ← var() works in style prop, not SVG attr */}
          strokeWidth={20} />

        {/* Segments — each overrides part of the circle */}
        {segments.map(s => (
          <circle key={s.department}
            cx="50" cy="50" r={R}
            fill="none"
            stroke={s.color}             // raw hex
            strokeWidth={20}
            strokeDasharray={`${s.dash} ${C - s.dash}`}
            strokeDashoffset={s.offset}
            transform="rotate(-90 50 50)"  // start from 12-o'clock position
            opacity={0.88}
          />
        ))}

        {/* Centre labels */}
        <text x="50" y="46" textAnchor="middle" fontSize="6.5"
              fill="#6b7280"
              fontFamily="'Plus Jakarta Sans', sans-serif">
          Total Spend
        </text>
        <text x="50" y="57" textAnchor="middle" fontSize="9"
              fill="#003366"
              fontFamily="Fraunces, serif"
              fontWeight="700">
          {fmt$M(total)}
        </text>
      </svg>

      {/* Legend */}
      <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 5 }}>
        {segments.slice(0, 6).map(s => (
          <div key={s.department} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 8, height: 8, borderRadius: 2,
              backgroundColor: s.color, flexShrink: 0,
            }} />
            <div style={{
              fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--dark)',
              flex: 1, minWidth: 0, overflow: 'hidden',
              textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {s.department}
            </div>
            <div style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)', flexShrink: 0 }}>
              {(s.total_spend / total * 100).toFixed(0)}%
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

**How the donut works:** Each segment is a full `<circle>` with `strokeDasharray` that makes only `pct × circumference` of the stroke visible. `strokeDashoffset` rotates where the visible portion starts. The `transform="rotate(-90 50 50)"` rotates the starting point from 3-o'clock (SVG default) to 12-o'clock.

**Legend:** 8×8px squares (borderRadius 2, not circles) — the square shape distinguishes legend markers from dot markers used in scatter plots.

---

### Chart 3 — Histogram / vertical bar chart

Used for score distributions (impact score buckets, comp-ratio distribution).

```tsx
function ImpactHistogram({ employees }: { employees: EmployeeRow[] }) {
  // Define buckets with navy-to-gold progression
  const buckets = [
    { label: '0–20',   min: 0,  max: 20,  color: '#99bbdd' },  // lightest navy
    { label: '20–40',  min: 20, max: 40,  color: '#4d7099' },
    { label: '40–60',  min: 40, max: 60,  color: '#336699' },
    { label: '60–80',  min: 60, max: 80,  color: '#1a4d80' },
    { label: '80–100', min: 80, max: 101, color: '#c8982a' },  // gold for top bucket
  ]

  const counts = buckets.map(b =>
    employees.filter(e => e.impact_score >= b.min && e.impact_score < b.max).length
  )
  const maxC = Math.max(...counts, 1)

  // Layout constants
  const W  = 260, H = 150
  const PB = 28   // bottom padding (axis labels)
  const PT = 12   // top padding (count labels above bars)
  const PL = 8    // left padding
  const PR = 8    // right padding
  const bW = (W - PL - PR) / buckets.length  // width per bucket slot

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>

      {/* Baseline */}
      <line x1={PL} y1={H - PB} x2={W - PR} y2={H - PB}
            stroke="rgba(0,51,102,0.12)" strokeWidth={1} />

      {buckets.map((b, i) => {
        const barH = (counts[i] / maxC) * (H - PB - PT)  // proportional height
        const x    = PL + i * bW + bW * 0.12             // 12% inner margin
        const bw   = bW * 0.76                            // 76% of slot = bar width
        const y    = PT + (H - PB - PT) - barH           // top of bar

        return (
          <g key={b.label}>
            <rect x={x} y={y} width={bw} height={barH}
                  fill={b.color} rx={3} opacity={0.83} />

            {/* Count label above bar (only when non-zero) */}
            {counts[i] > 0 && (
              <text x={x + bw / 2} y={y - 3}
                    fontSize={8.5} fill={b.color}
                    textAnchor="middle" fontWeight="700">
                {counts[i]}
              </text>
            )}

            {/* Bucket range label below baseline */}
            <text x={x + bw / 2} y={H - 6}
                  fontSize={8} fill="#9ca3af" textAnchor="middle">
              {b.label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
```

**Bar colour rule:** The histogram uses the navy gradient (lightest to darkest) for the lower buckets, with gold reserved for the highest-performing bucket only. This reinforces the "gold is the best" semantic without using status colours.

---

### Chart 4 — Scatter plot / strategic quadrant

Used for two-dimensional employee distribution (impact vs attrition risk).

```tsx
function QuadrantChart({ employees }: { employees: EmployeeRow[] }) {
  // Sample for performance on large datasets
  const sample = employees.length > 400
    ? employees.filter((_, i) => i % Math.ceil(employees.length / 400) === 0)
    : employees

  // Layout
  const W  = 540, H  = 300
  const PL = 40,  PR = 20, PT = 22, PB = 38
  const pW = W - PL - PR          // plot area width
  const pH = H - PT - PB          // plot area height

  // Quadrant thresholds
  const RX = 0.50   // x-axis split (attrition risk)
  const IY = 60     // y-axis split (impact score)
  const qx = PL + pW * RX
  const qy = PT + pH * (1 - IY / 100)

  // Data-to-SVG coordinate transforms
  const toX = (r: number) => PL + r * pW          // risk 0-1 → x
  const toY = (s: number) => PT + (1 - s / 100) * pH  // score 0-100 → y (inverted)

  // Dot colour by quadrant
  const dotColor = (e: EmployeeRow) => {
    if (e.attrition_risk >= RX && e.impact_score >= IY) return '#e03448'  // Act Now
    if (e.attrition_risk <  RX && e.impact_score >= IY) return '#27b97c'  // Protect
    if (e.attrition_risk >= RX && e.impact_score <  IY) return '#f07020'  // Review
    return '#99bbdd'                                                        // Monitor
  }

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>

        {/* ── Quadrant background fills ── */}
        <rect x={PL}  y={PT}         width={qx - PL}    height={qy - PT}     fill="rgba(39,185,124,0.05)"  />  {/* Protect */}
        <rect x={qx}  y={PT}         width={W - PR - qx} height={qy - PT}    fill="rgba(224,52,72,0.06)"   />  {/* Act Now */}
        <rect x={PL}  y={qy}         width={qx - PL}    height={H - PB - qy} fill="rgba(0,51,102,0.03)"    />  {/* Monitor */}
        <rect x={qx}  y={qy}         width={W - PR - qx} height={H - PB - qy} fill="rgba(240,112,32,0.05)" />  {/* Review */}

        {/* ── Quadrant labels ── */}
        <text x={PL + 6}  y={PT + 13} fontSize={8.5} fill="#27b97c" fontWeight="700" letterSpacing="1"
              fontFamily="'Plus Jakarta Sans',sans-serif">
          PROTECT ({qCounts.protect})
        </text>
        <text x={qx + 6}  y={PT + 13} fontSize={8.5} fill="#e03448" fontWeight="700" letterSpacing="1"
              fontFamily="'Plus Jakarta Sans',sans-serif">
          ACT NOW ({qCounts.actNow})
        </text>
        <text x={PL + 6}  y={H - PB - 6} fontSize={8.5} fill="#99bbdd" letterSpacing="1"
              fontFamily="'Plus Jakarta Sans',sans-serif">
          MONITOR ({qCounts.monitor})
        </text>
        <text x={qx + 6}  y={H - PB - 6} fontSize={8.5} fill="#f07020" letterSpacing="1"
              fontFamily="'Plus Jakarta Sans',sans-serif">
          REVIEW ({qCounts.review})
        </text>

        {/* ── Quadrant dividers (dashed) ── */}
        <line x1={qx} y1={PT} x2={qx} y2={H - PB}
              stroke="rgba(0,51,102,0.18)" strokeWidth={1} strokeDasharray="4 3" />
        <line x1={PL} y1={qy} x2={W - PR} y2={qy}
              stroke="rgba(0,51,102,0.18)" strokeWidth={1} strokeDasharray="4 3" />

        {/* ── Employee dots ── */}
        {sample.map(e => {
          const cx = toX(e.attrition_risk)
          const cy = toY(e.impact_score)
          const c  = dotColor(e)
          const r  = e.is_nexus ? 5 : 3

          return (
            <g key={e.employee_id}>
              {/* Nexus employees get an outer gold ring */}
              {e.is_nexus && (
                <circle cx={cx} cy={cy} r={r + 3}
                        fill="none" stroke="#c8982a" strokeWidth={1.5} opacity={0.65} />
              )}
              <circle cx={cx} cy={cy} r={r} fill={c} opacity={0.72} />
            </g>
          )
        })}

        {/* ── Axes ── */}
        <line x1={PL} y1={H - PB} x2={W - PR} y2={H - PB}
              stroke="rgba(0,51,102,0.15)" strokeWidth={1} />
        <line x1={PL} y1={PT}     x2={PL}     y2={H - PB}
              stroke="rgba(0,51,102,0.15)" strokeWidth={1} />

        {/* ── Axis labels ── */}
        <text x={PL + pW / 2} y={H - 4}
              fontSize={9} fill="#6b7280" textAnchor="middle"
              fontFamily="'Plus Jakarta Sans',sans-serif">
          Attrition Risk →
        </text>
        <text x={12} y={PT + pH / 2}
              fontSize={9} fill="#6b7280" textAnchor="middle"
              fontFamily="'Plus Jakarta Sans',sans-serif"
              transform={`rotate(-90 12 ${PT + pH / 2})`}>
          Impact Score →
        </text>

        {/* ── Axis tick labels ── */}
        <text x={PL}     y={H - PB + 11} fontSize={8} fill="#9ca3af" textAnchor="middle">0%</text>
        <text x={W - PR} y={H - PB + 11} fontSize={8} fill="#9ca3af" textAnchor="middle">100%</text>
        <text x={PL - 4} y={PT + 4}      fontSize={8} fill="#9ca3af" textAnchor="end">100</text>
        <text x={PL - 4} y={H - PB + 4}  fontSize={8} fill="#9ca3af" textAnchor="end">0</text>
      </svg>

      {/* ── Legend ── */}
      <div style={{ display: 'flex', gap: 20, justifyContent: 'center', marginTop: 10, flexWrap: 'wrap' }}>
        {[
          { color: '#27b97c', label: 'Protect — high impact, low risk'  },
          { color: '#e03448', label: 'Act Now — high impact, high risk' },
          { color: '#f07020', label: 'Review — low impact, high risk'   },
          { color: '#99bbdd', label: 'Monitor — low impact, low risk'   },
        ].map(({ color, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: color }} />
            <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>{label}</span>
          </div>
        ))}

        {/* Nexus legend item — shows the ring pattern */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <svg width="14" height="14" viewBox="0 0 14 14">
            <circle cx="7" cy="7" r="5" fill="none" stroke="#c8982a" strokeWidth="1.5" />
            <circle cx="7" cy="7" r="2.5" fill="#c8982a" opacity="0.72" />
          </svg>
          <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)' }}>Nexus employee</span>
        </div>
      </div>
    </div>
  )
}
```

**Quadrant design details:**
- Fills use very low opacity (0.03–0.06) — just enough to tint the quadrant without obscuring dots
- Divider lines are dashed (`strokeDasharray="4 3"`) and muted (`rgba(0,51,102,0.18)`) — they guide the eye without dominating
- Nexus dots are `r=5` (larger) with an outer gold ring at `r+3` — they are identifiable without a separate symbol
- All dot opacity is `0.72` — overlapping dots remain individually visible rather than merging into opaque masses
- Axis labels use serif arrows (`→`) on both axes

---

### Chart 5 — Attrition tier breakdown (HTML progress bars)

Not SVG — uses HTML `div` elements. Used when the primary data is a set of counts by category, not a continuous distribution.

```tsx
function AttritionTiers({ employees }: { employees: EmployeeRow[] }) {
  const tiers = [
    { label: 'Critical', min: 0.70, color: 'var(--status-red)',    bg: 'rgba(224,52,72,0.08)'  },
    { label: 'High',     min: 0.50, color: 'var(--status-orange)', bg: 'rgba(240,112,32,0.08)' },
    { label: 'Moderate', min: 0.30, color: 'var(--gold)',           bg: 'rgba(200,152,42,0.08)' },
    { label: 'Low',      min: 0.00, color: 'var(--status-green)',   bg: 'rgba(39,185,124,0.08)' },
  ]
  const total  = employees.length || 1
  const counts = tiers.map((t, i) => {
    const max = i === 0 ? 1.01 : tiers[i - 1].min
    return employees.filter(e => e.attrition_risk >= t.min && e.attrition_risk < max).length
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {tiers.map((t, i) => (
        <div key={t.label}>
          {/* Header row: pill label + count + percentage */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{
              fontFamily:      'var(--fb)',
              fontSize:        11,
              fontWeight:      600,
              color:           t.color,
              backgroundColor: t.bg,
              borderRadius:    'var(--radius-pill)',
              padding:         '2px 9px',
            }}>
              {t.label}
            </span>
            <div style={{ textAlign: 'right' }}>
              <span style={{ fontFamily: 'var(--fd)', fontSize: 18, fontWeight: 700, color: t.color }}>
                {counts[i]}
              </span>
              <span style={{ fontFamily: 'var(--fb)', fontSize: 10, color: 'var(--mid)', marginLeft: 4 }}>
                {(counts[i] / total * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {/* Progress bar */}
          <div style={{ height: 5, backgroundColor: 'var(--primary-10)', borderRadius: 3 }}>
            <div style={{
              height:          '100%',
              borderRadius:    3,
              backgroundColor: t.color,
              width:           `${counts[i] / total * 100}%`,
              transition:      'width 0.4s',
            }} />
          </div>
        </div>
      ))}
    </div>
  )
}
```

**Ordering:** Tiers go from worst (Critical) to best (Low) — the most urgent information is at the top, consistent with how risk registers are read.

---

### Chart 6 — Sparkline

A minimal line chart used inside table cells or KPI cards to show trend direction.

```tsx
function Sparkline({ values, color = '#003366', width = 120, height = 36 }: {
  values: number[]; color?: string; width?: number; height?: number
}) {
  if (values.length < 2) return null

  const min   = Math.min(...values)
  const max   = Math.max(...values)
  const range = max - min || 1

  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width
    const y = height - ((v - min) / range) * (height - 4) - 2  // 2px padding top/bottom
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height}
         style={{ display: 'block' }}>
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
```

Sparklines use `strokeLinecap="round"` and `strokeLinejoin="round"` for smooth, professional appearance. Width is fixed (not responsive) when used inside table cells to maintain column width consistency.

---

### Chart 7 — Radar / spider chart (for OHI dimensions)

Used for multi-dimensional composite scores (OHI, resilience scores).

```tsx
function RadarChart({ dimensions, scores, maxScore = 100 }: {
  dimensions: string[];
  scores:     number[];
  maxScore?:  number;
}) {
  const N    = dimensions.length
  const CX   = 120, CY = 120, R = 90  // centre and radius
  const rings = [0.25, 0.5, 0.75, 1.0]

  const angleFor = (i: number) => (Math.PI * 2 * i) / N - Math.PI / 2  // start at top

  const pt = (i: number, r: number) => {
    const a = angleFor(i)
    return { x: CX + r * Math.cos(a), y: CY + r * Math.sin(a) }
  }

  // Ring gridlines
  const ringPaths = rings.map(f => {
    const pts = Array.from({ length: N }, (_, i) => {
      const { x, y } = pt(i, R * f)
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    return pts.join(' ') + 'Z'
  })

  // Spoke lines
  const spokes = Array.from({ length: N }, (_, i) => {
    const outer = pt(i, R)
    return `M${CX},${CY} L${outer.x.toFixed(1)},${outer.y.toFixed(1)}`
  })

  // Data polygon
  const dataPts = Array.from({ length: N }, (_, i) => {
    const { x, y } = pt(i, R * (scores[i] / maxScore))
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ') + 'Z'

  return (
    <svg viewBox={`0 0 240 240`} width="100%" style={{ display: 'block', maxWidth: 240 }}>

      {/* Ring gridlines */}
      {ringPaths.map((d, i) => (
        <path key={i} d={d} fill="none" stroke="rgba(0,51,102,0.10)" strokeWidth={1} />
      ))}

      {/* Spokes */}
      {spokes.map((d, i) => (
        <path key={i} d={d} stroke="rgba(0,51,102,0.12)" strokeWidth={1} />
      ))}

      {/* Data fill */}
      <path d={dataPts} fill="rgba(200,152,42,0.12)" stroke="#c8982a" strokeWidth={2} />

      {/* Dimension labels */}
      {Array.from({ length: N }, (_, i) => {
        const outer = pt(i, R + 16)
        return (
          <text key={i}
            x={outer.x.toFixed(1)} y={outer.y.toFixed(1)}
            fontSize={8.5} fill="#6b7280"
            textAnchor={outer.x < CX - 5 ? 'end' : outer.x > CX + 5 ? 'start' : 'middle'}
            fontFamily="'Plus Jakarta Sans', sans-serif"
            dominantBaseline="central">
            {dimensions[i]}
          </text>
        )
      })}

      {/* Score dots */}
      {Array.from({ length: N }, (_, i) => {
        const { x, y } = pt(i, R * (scores[i] / maxScore))
        return <circle key={i} cx={x.toFixed(1)} cy={y.toFixed(1)} r={3} fill="#c8982a" />
      })}
    </svg>
  )
}
```

**Radar design rules:**
- Data fill: `rgba(200,152,42,0.12)` fill + `#c8982a` stroke (gold system)
- Grid rings: `rgba(0,51,102,0.10)` — extremely subtle
- Spokes: `rgba(0,51,102,0.12)` — slightly more visible than rings
- Labels: dynamically left/centre/right aligned based on x position relative to centre

---

### Chart 8 — Heatmap grid

Used for signal heatmaps (pulse monitoring, cross-team collaboration matrix).

```tsx
function Heatmap({ rows, cols, values, getColor }: {
  rows:     string[];
  cols:     string[];
  values:   number[][];      // [row][col]
  getColor: (v: number) => string;  // returns hex
}) {
  const CELL_W = 40, CELL_H = 28
  const PAD_L  = 120  // row label width
  const PAD_T  = 60   // column label height
  const W      = PAD_L + cols.length * CELL_W
  const H      = PAD_T + rows.length * CELL_H

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block', overflowX: 'auto' }}>

      {/* Column headers */}
      {cols.map((col, j) => (
        <text key={col}
          x={PAD_L + j * CELL_W + CELL_W / 2}
          y={PAD_T - 8}
          fontSize={8} fill="#6b7280" textAnchor="middle"
          fontFamily="'Plus Jakarta Sans', sans-serif"
          transform={`rotate(-45 ${PAD_L + j * CELL_W + CELL_W / 2} ${PAD_T - 8})`}>
          {col.length > 10 ? col.slice(0, 9) + '…' : col}
        </text>
      ))}

      {/* Row labels + cells */}
      {rows.map((row, i) => (
        <g key={row}>
          <text
            x={PAD_L - 6} y={PAD_T + i * CELL_H + CELL_H / 2 + 4}
            fontSize={10} fill="#1c1c2e" textAnchor="end"
            fontFamily="'Plus Jakarta Sans', sans-serif">
            {row.length > 14 ? row.slice(0, 13) + '…' : row}
          </text>
          {cols.map((_, j) => {
            const v = values[i]?.[j] ?? 0
            return (
              <rect key={j}
                x={PAD_L + j * CELL_W + 1}
                y={PAD_T + i * CELL_H + 1}
                width={CELL_W - 2}
                height={CELL_H - 2}
                fill={getColor(v)}
                rx={2}
              />
            )
          })}
        </g>
      ))}
    </svg>
  )
}
```

**Heatmap colour function example** (blue intensity for collaboration density):
```ts
const getHeatColor = (v: number): string => {
  // v = 0..1, low = light, high = dark navy
  const opacity = 0.08 + v * 0.80
  return `rgba(0,51,102,${opacity.toFixed(2)})`
}
```

---

## 13. Data Tables

All data tables follow the same pattern. No third-party table library.

### Table wrapper and overflow

```tsx
<div style={{ overflowX: 'auto' }}>
  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
    ...
  </table>
</div>
```

For tall tables with many rows, add `maxHeight` and `overflowY: 'auto'` with a sticky `<thead>`:

```tsx
<div style={{ overflowX: 'auto', maxHeight: 460, overflowY: 'auto' }}>
  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
    <thead style={{ position: 'sticky', top: 0 }}>
```

### Header row (`<thead>`)

```tsx
const th: React.CSSProperties = {
  fontFamily:    'var(--fb)',
  fontSize:      9,
  fontWeight:    600,
  letterSpacing: '2px',
  textTransform: 'uppercase',
  padding:       '11px 14px',
  color:         '#fff',
  background:    'var(--primary)',
  whiteSpace:    'nowrap',
  cursor:        'pointer',     // when sortable
}
```

Sortable column headers add `onClick` and a sort direction indicator:
```tsx
<th style={th} onClick={() => toggle('column_key')}>
  Column Label{sortKey === 'column_key' ? (sortAsc ? ' ▴' : ' ▾') : ''}
</th>
```

### Body rows

Row striping: `var(--white)` for even rows, `rgba(0,51,102,0.02)` for odd rows — a very subtle navy tint, not the `var(--primary-10)` token (which is too heavy for full-width rows in a large table).

```tsx
<tr style={{
  background:   i % 2 === 0 ? 'var(--white)' : 'rgba(0,51,102,0.02)',
  borderBottom: '1px solid var(--primary-10)',
}}>
```

### Cell typography

```tsx
// Primary cell (e.g., name column)
<td style={{ fontFamily: 'var(--fb)', fontSize: 13, padding: '11px 14px', fontWeight: 600, color: 'var(--dark)' }}>
  {value}
</td>

// Secondary cell (e.g., metadata column)
<td style={{ fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 14px', color: 'var(--mid)' }}>
  {value}
</td>

// Numeric cell (right-aligned)
<td style={{ fontFamily: 'var(--fb)', fontSize: 12, padding: '10px 14px', textAlign: 'right', color: 'var(--dark)' }}>
  {value}
</td>

// Score cell (Fraunces value with status colour)
<td style={{ padding: '10px 14px', textAlign: 'right' }}>
  <span style={{ fontFamily: 'var(--fd)', fontSize: 14, fontWeight: 700, color: impactColor(score) }}>
    {score.toFixed(0)}
  </span>
</td>
```

### Search input (above the table)

```tsx
<input
  value={query}
  onChange={e => setQuery(e.target.value)}
  placeholder="Search by name, department, role…"
  style={{
    fontFamily:   'var(--fb)',
    fontSize:     13,
    padding:      '8px 14px',
    borderRadius: 'var(--radius-sm)',
    border:       '1px solid var(--primary-10)',
    background:   'var(--white)',
    color:        'var(--dark)',
    width:        300,
    outline:      'none',
  }}
/>
```

### Row count display

```tsx
<span style={{ fontFamily: 'var(--fb)', fontSize: 11, color: 'var(--mid)' }}>
  {filtered.length.toLocaleString()} employees
</span>
```

### Truncation notice (large datasets)

When showing only the first N rows of a large filtered result:
```tsx
{filtered.length > 200 && (
  <div style={{
    fontFamily: 'var(--fb)', fontSize: 12, color: 'var(--mid)',
    padding: '12px', textAlign: 'center',
  }}>
    Showing 200 of {filtered.length.toLocaleString()} — refine your search to see more.
  </div>
)}
```

---

## 14. Dark Mode

### Implementation

Theme is stored in `localStorage` under the key `eibo-theme`. On mount, `useTheme.ts` reads the stored value (defaulting to `'light'`) and applies it by setting `data-theme` on `document.documentElement`:

```ts
// frontend/src/hooks/useTheme.ts
type Theme = 'light' | 'dark'

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute('data-theme', theme)
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() =>
    (localStorage.getItem('eibo-theme') as Theme) ?? 'light'
  )
  useEffect(() => {
    applyTheme(theme)
    localStorage.setItem('eibo-theme', theme)
  }, [theme])
  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')
  return { theme, toggleTheme }
}
```

The CSS overrides are applied via `html[data-theme="dark"]` in `tokens.css`. Only `--light`, `--white`, `--dark`, `--mid`, `--primary-10`, and the shadow tokens change. Navy, gold, and status colours remain identical in both modes — the nav and hero sections look the same in dark mode as in light mode.

### What components get for free

Any component that uses `var(--white)` for backgrounds and `var(--light)` for page backgrounds automatically responds to dark mode — no component-level changes needed.

### What breaks dark mode (bugs to avoid)

| Bug | Fix |
|---|---|
| Hardcoded `#ffffff` on a card | Use `var(--white)` |
| Hardcoded `#f4f6f9` as page bg | Use `var(--light)` |
| `rgba(0,51,102,0.05)` as table stripe | Use `rgba(0,51,102,0.02)` — already dark-mode safe (near-zero opacity) |
| Hardcoded `color: '#1c1c2e'` in SVG text | Use `fill="#1c1c2e"` in SVG — note SVG text does not inherit `var(--dark)` |

SVG text elements use presentation attributes (`fill="#6b7280"`), not CSS custom properties. SVG charts therefore do not change in dark mode — this is intentional. The chart colours are part of the design vocabulary, not part of the surface theme.

---

## 15. State Management

Three pieces of global state live in Zustand. Everything else is component-local `useState`.

### demoStore (global — all pages read this)

```ts
// frontend/src/stores/demoStore.ts
import { create } from 'zustand'

interface DemoStore {
  scenario:   'A' | 'B' | 'C'
  size:       'small' | 'medium' | 'large'
  enabled:    boolean
  setScenario: (s: 'A' | 'B' | 'C')             => void
  setSize:     (s: 'small' | 'medium' | 'large') => void
  setEnabled:  (e: boolean)                       => void
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

### No server state library

Pages fetch data with `useEffect` + `useState`. There is no React Query, SWR, or caching layer. On scenario or size change, `useEffect` re-fetches from the API. The backend's `lru_cache` handles repeated calls efficiently.

---

## 16. API Layer

All HTTP calls go through `frontend/src/services/api.ts`. No component imports `fetch` directly. This is a convention enforced by code review, not tooling.

### Base request function

```ts
async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      ...opts?.headers,
    },
  })
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json() as Promise<T>
}
```

### Domain grouping

```ts
export const api = {
  dashboard: {
    data: (scenario: string, size: string, demo: boolean) =>
      request<DashboardData>(`/dashboard?scenario=${scenario}&size=${size}&demo=${demo}`),
  },
  compensation: {
    data: (scenario: string, size: string, demo: boolean) =>
      request<CompensationData>(`/compensation?scenario=${scenario}&size=${size}&demo=${demo}`),
  },
  // ... one domain group per router
}
```

### TypeScript interface discipline

Interfaces in `api.ts` must exactly match the backend Pydantic response models. A field added to the interface but not present in the API response is typed correctly but `undefined` at runtime — TypeScript will not catch it. Before adding any field, verify it in the actual API JSON response.

---

## 17. Inline Styles vs CSS Modules vs Tailwind

The application uses **inline styles exclusively**, combined with CSS custom properties for design token values.

### Rationale

1. **Design token enforcement** — Inline styles that reference `var(--token)` make it immediately visible when a hardcoded value is used instead. In a Tailwind class, the actual hex value is invisible and cannot be audited.
2. **No specificity battles** — Every style is scoped to the exact element it is applied to. No class specificity cascade.
3. **TypeScript coverage** — `React.CSSProperties` catches misspelled property names at compile time. Class name strings have no type safety.
4. **Design fidelity** — The OPB design system uses precise values (`rgba(201,168,76,0.12)` for active nav backgrounds) that have no Tailwind equivalent. Approximating them with utility classes breaks the visual system.

### Style object pattern

Define style constants outside the component function (not inside — they recreate on every render):

```tsx
// Outside component
const hero: React.CSSProperties = { ... }
const card: React.CSSProperties = { ... }
const wrap: React.CSSProperties = { ... }

// Inside component — spread + extend for variants
<div style={card}>...</div>
<div style={{ ...card, padding: 18 }}>...</div>
<div style={{ ...card, borderLeft: '3px solid var(--gold)' }}>...</div>
```

Hover states use `useState(false)` + `onMouseEnter`/`onMouseLeave` because inline styles cannot use CSS pseudo-selectors. The state change triggers a re-render with the new style applied.

---

## 18. Migration Guide

This section explains how to apply the OPB design system to a new or existing React application.

### Step 1 — Fonts

Add to `<head>` in `index.html`:

```html
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,400;0,9..144,600;1,9..144,300;1,9..144,400&display=swap" rel="stylesheet">
```

### Step 2 — Tokens

Copy `frontend/src/styles/tokens.css` verbatim. Import it once in `main.tsx`. Do not modify the token values.

### Step 3 — Eyebrow component

Copy `frontend/src/components/Eyebrow.tsx` — no dependencies beyond React. Use it before every content section.

### Step 4 — Nav structure

Follow `frontend/src/components/Nav.tsx`:
- Outer nav: `rgba(0,51,102,0.97)`, blur 12px, sticky, 52px, `justifyContent: 'space-between'`
- OPB monogram: Fraunces 20px, O in white, PB in italic `var(--gold-light)`
- App title: Plus Jakarta 9px uppercase, `rgba(255,255,255,0.4)`
- Navigation: grouped dropdowns (see section 7)
- Theme toggle: right edge

### Step 5 — Hero structure

Every page opens with a dark hero (see section 8):
- `var(--primary)` background + `48px` grid texture
- `<Eyebrow light>` context label
- Fraunces H1 with italic gold keyword
- Plus Jakarta subtitle in `rgba(255,255,255,0.45)`
- HeroStat row with `2px solid var(--gold)` left borders

### Step 6 — Body structure

- Background: `var(--light)`
- Max-width wrapper: `var(--max-width-dashboard)` for data pages
- Flex column with `gap: 32px` between sections
- Each section: `<SectionHead>` + card content
- Cards: `var(--white)` bg, `var(--radius-md)`, `var(--shadow-card)`, `1px solid var(--primary-10)`

### Step 7 — Footer

Copy `frontend/src/components/Footer.tsx`:
- `var(--primary)` background, `padding: '20px 48px'`
- Flex space-between, 9px uppercase, `rgba(255,255,255,0.35)`
- Left: "OPB · NAME · PROJECT", Right: current month + year

### Step 8 — Wire routing

In `App.tsx`: `Page` union type + `renderPage()` switch + state. No router library.

### Common mistakes

| Mistake | Correct approach |
|---|---|
| Hardcoding `#ffffff` in a card | `var(--white)` |
| Hardcoding `#f4f6f9` as page bg | `var(--light)` |
| Status colour on card `borderLeft` or `borderTop` | `var(--gold)` always for structural borders |
| Status colour as categorical chart series | Navy gradient + gold only |
| `var()` in SVG `fill` or `stroke` attribute | Raw hex: `fill="#003366"` not `fill="var(--primary)"` |
| Bolding Fraunces (`fontWeight: 700`) in titles | Use 300 or 400 — never 700 on display headings |
| Fraunces for labels, captions, or body text | Plus Jakarta Sans for all interface copy |
| Missing `backgroundColor: 'transparent'` on nav link base | White flash on inactive buttons in light mode |
| Gold-light eyebrow on a light background | `light` prop only on dark (navy) backgrounds |
| Progress bar fill in gold for a risk metric | Status colour (red/orange/green) for fills that encode severity |
| Italic em word in gold on a dark hero bg | Use `var(--gold-light)` on dark, `var(--gold)` on light |

---

*Last updated: 2026-05-27. Maintained by Octavio Pérez Bravo.*
