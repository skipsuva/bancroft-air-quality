# Handoff: Bancroft Air — Mobile Dashboard Redesign

## Overview

This is a redesigned mobile dashboard for the Bancroft Air home air quality monitor. The new design replaces the existing `templates/index.html` Flask template with a phone-native mobile UI (390×812px). It surfaces the most actionable information first — a single top recommendation, a live mesh map of nodes, and a compact suggested-actions list — rather than raw sensor tables.

## About the Design Files

The files in this bundle are **HTML design references** — high-fidelity prototypes showing intended look, layout, and interactions. They are **not** production code to copy directly. The task is to **recreate this design inside the existing Flask/Jinja2 codebase** (`templates/index.html`), replacing the current desktop layout with this mobile-first design, wired to the existing `/api/now` and `/api/history` endpoints.

## Fidelity

**High-fidelity.** Colors, typography, spacing, and interaction states are final. Recreate pixel-precisely. The only things to adapt are:
- Replace hardcoded mock data with real API calls to `/api/now` and `/api/history`
- Replace the hardcoded "hero" recommendation with logic derived from the worst live reading
- Map/List toggle state can be persisted in `localStorage`

---

## Screens / Views

### 1. Dashboard (single screen, two sub-views)

The entire app is one screen inside a phone bezel (for the prototype). In production this is a full-viewport mobile page.

**Outer container**
- `min-height: 100vh`, `background: #e9eaee`, `font-family: 'Nunito', sans-serif`
- `padding: 38px 24px 70px`, `color: #3a322a`
- Inner max-width `520px`, centered

**Phone shell** (prototype only — omit in production)
- `width: 390px`, `background: #000`, `border-radius: 48px`, `padding: 11px`
- `box-shadow: 0 34px 70px -24px rgba(20,22,34,.5)`

**Screen inner**
- `background: #fbf7f2`, `border-radius: 38px`, `overflow: hidden`
- `height: 812px`, `display: flex`, `flex-direction: column`

---

### 2. Status Bar

```
9:41                          ● live
```

- `padding: 14px 28px 4px`
- Time: `font-size: 13px`, `font-weight: 700`, `color: #4a4036`
- Live indicator: 7×7px circle, `background: #34c759`, animated pulse (see Animations)
- "live" text: `font-size: 11px`, `color: #a99a88`, `font-weight: 700`

---

### 3. Header

```
Bancroft Air                    2
5/6 online · 8s ago          to fix
```

- Title: `font-size: 22px`, `font-weight: 800`, `letter-spacing: -0.02em`, `color: #3a322a`
- Online status: `font-size: 11.5px`, `font-weight: 700`, `color: #5a8a6c`
  - Green dot: 6×6px, `background: #34a853`
  - Format: `{online}/{total} online`
- Last updated: `font-size: 11.5px`, `font-weight: 600`, `color: #a99a88`
- Attention count (right): `font-size: 20px`, `font-weight: 800`, `color: #c63b30`
  - Count of online nodes with status POOR or BAD
  - Label "to fix": `font-size: 9.5px`, `color: #a99a88`, `font-weight: 700`, `text-transform: uppercase`, `letter-spacing: 0.04em`

**Data source:** `/api/now` — count keys with data (online), count those with CO₂ > 1000 (attention)

---

### 4. Hero Card

The single most urgent recommended action based on the worst live reading.

```
┌─────────────────────────────────────┐  ← gradient bg
│  [icon]  Open a window in           │
│          the Bedroom                │
│                                     │
│  It's stuffy — CO₂ is 1520 ppm      │
│  and still climbing.                │
└─────────────────────────────────────┘
```

- `background: linear-gradient(135deg, #ff8a5c, #ef5e4e)`
- `border-radius: 22px`, `padding: 15px 17px`, `margin-bottom: 13px`
- `box-shadow: 0 14px 24px -13px rgba(239,94,78,.6)`
- Decorative circle (top-right): 84×84px, `border-radius: 50%`, `background: rgba(255,255,255,.12)`, `position: absolute`, `right: -20px`, `top: -20px`
- Icon circle: 46×46px, `border-radius: 50%`, `background: rgba(255,255,255,.24)`, contains a window/open icon in white
- Title: `font-size: 16.5px`, `font-weight: 800`, `color: #fff`, `letter-spacing: -0.01em`
- Subtitle: `font-size: 12px`, `color: #fff`, `opacity: 0.94`, `font-weight: 600`, `margin-top: 10px`

**Hero logic:**
1. Find the node with the highest CO₂ reading (or worst AQI for kitchen)
2. If CO₂ > 1500: "Open a window in {room}" + "It's stuffy — CO₂ is {val} ppm and still climbing."
3. If CO₂ 1000–1500: "Air out the {room}" + "CO₂ is elevated at {val} ppm."
4. If PM2.5 > 35: "Run the kitchen hood" + "PM2.5 is {val} µg/m³."

---

### 5. Map / List Toggle

```
[ Map ]  [ List ]
```

- Container: `background: #f0e9e0`, `border-radius: 13px`, `padding: 4px`, `display: flex`, `gap: 4px`
- Each button: `flex: 1`, `border: none`, `border-radius: 10px`, `padding: 8px 0`
- Font: Nunito, `font-size: 13px`, `font-weight: 800`
- **Active:** `background: #fff`, `color: #3a322a`, `box-shadow: 0 2px 6px -3px rgba(120,90,60,.4)`
- **Inactive:** `background: transparent`, `color: #a99a88`

---

### 6a. Map View

A schematic house floor plan with positioned room cards and animated mesh lines showing connectivity.

**Container**
- `background: #fff`, `border-radius: 24px`, `padding: 13px 12px 9px`
- `box-shadow: 0 8px 20px -12px rgba(120,90,60,.28)`
- Legend row (top): "Your home" label left, color key right
  - Label: `font-size: 12px`, `font-weight: 800`, `color: #8a7c6c`
  - Legend items: 13×2.5px rounded lines — green `#8fcfa6` "live", red `#ef6b62` "offline"

**SVG Floor Plan** (100×100 viewBox, `preserveAspectRatio: none`)

House outline (lines, `stroke: #efe7dc`, `stroke-width: 1.4`):
```
Roof ridge:   polyline points="8,28 50,7 92,28"
Left wall:    line (8,28)→(8,96)
Right wall:   line (92,28)→(92,96)
Floor:        line (8,96)→(92,96)
Floor lines:  y=44 and y=72 (stroke: #f6f1ea, width: 1.2)
```

**Mesh connectivity lines** (one per non-hub node, hub = Office at 30%,55%):

| From (hub) | To node | % position |
|---|---|---|
| Office 30,55 | Bedroom 18,22 | online → green dashed animated |
| Office 30,55 | Mari's 50,22 | online → green dashed animated |
| Office 30,55 | Em's 82,22 | online → green dashed animated |
| Office 30,55 | Kitchen 72,55 | online → green dashed animated |
| Office 30,55 | Basement 50,83 | offline → red static dashed |

Line styles:
- **Live:** `stroke: #8fcfa6`, `stroke-dasharray: "1 6"`, `stroke-linecap: round`, `animation: flow 2.6s linear infinite`
- **Offline:** `stroke: #ef6b62`, `stroke-dasharray: "4 5"`, `stroke-linecap: round`, no animation

Flow animation (`@keyframes flow { to { stroke-dashoffset: -14; } }`)

**Room Cards** (absolutely positioned over the SVG, `transform: translate(-50%,-50%)`, width `104px`)

Each card:
- `background: {statusBg}`, `border-radius: 17px`, `padding: 7px 11px 8px`
- `box-shadow: 0 6px 13px -7px rgba(120,90,60,.3)`
- `opacity: 1` if online, `0.66` if offline

Card interior:
- Status icon circle: 16×16px, `border-radius: 50%`, `background: {dotBg}`
- Room short name: `font-size: 10px`, `font-weight: 800`, `color: {statusText}`, truncated
- Primary value: `font-size: 18px`, `font-weight: 800`, `letter-spacing: -0.02em`, `color: {statusNum}`
- Unit: `font-size: 8px`, `color: {statusText}`, `font-weight: 700`, `opacity: 0.7`
- Age: `font-size: 8.5px`, `font-weight: 800`, right-aligned — `color: #cbbfb0` if live, `#ef6b62` if offline

**Node positions (% of container):**

| Node | x% | y% | Short name | Primary metric |
|---|---|---|---|---|
| office | 30 | 55 | Office | CO₂ ppm |
| bedroom | 18 | 22 | Bedroom | CO₂ ppm |
| toddler | 50 | 22 | Mari's | CO₂ ppm |
| wifesoffice | 82 | 22 | Em's | CO₂ ppm |
| kitchen | 72 | 55 | Kitchen | PM2.5 µg/m³ |
| basement | 50 | 83 | Basement | CO₂ ppm |

---

### 6b. List View

A scrollable list of all rooms.

**Container:** `background: #fff`, `border-radius: 24px`, `padding: 6px`
`box-shadow: 0 8px 20px -12px rgba(120,90,60,.28)`

Each row:
- `display: flex`, `align-items: center`, `gap: 11px`, `padding: 11px 13px`, `border-radius: 18px`
- `opacity: 1` online / `0.66` offline
- Separator: `height: 1px`, `background: #f4efe8`, `margin: 0 12px`

Row contents:
- Icon circle: 30×30px, `border-radius: 50%`, `background: {dotBg}`
- Name: `font-size: 13.5px`, `font-weight: 800`, `color: #3a322a`
- Sub-label + age: `font-size: 10.5px`, `font-weight: 700`, `color: #bcae9e` — e.g. "CO₂ · 8s"
- Primary value: `font-size: 18px`, `font-weight: 800`, `color: {statusNum}`, `letter-spacing: -0.02em`
- Unit: `font-size: 9px`, `font-weight: 700`, `color: {statusText}`, `opacity: 0.7`
- Connectivity dot: 7×7px circle, `background: #34a853` online / `#ef6b62` offline

---

### 7. Suggested Actions

```
SUGGESTED
┌──────────────────────────────────────┐
│ ■  Open a window    Bedroom  CO₂ 1520 ▲ │
│ ■  Run the hood     Kitchen  PM2.5 38 ▲ │
│ ■  Air it out       Em's     TVOC 410 ▲ │
└──────────────────────────────────────┘
```

- Section label: `font-size: 11px`, `font-weight: 800`, `color: #bcae9e`, `text-transform: uppercase`, `letter-spacing: 0.04em`
- Container: `background: #fff`, `border-radius: 18px`, `overflow: hidden`, `box-shadow: 0 6px 14px -10px rgba(120,90,60,.3)`

Each action row:
- `display: flex`, `align-items: center`, `gap: 10px`, `padding: 10px 13px`
- `border-top: 1px solid #f4efe8` (first row: `transparent`)
- Color square: 9×9px, `border-radius: 3px`, `background: {actionColor}`
- Action title: `font-size: 13px`, `font-weight: 800`, `color: #3a322a`
- Room: `font-size: 13px`, `font-weight: 700`, `color: #a99a88`
- Code (right): `font-size: 11px`, `font-weight: 700`, `color: {actionColor}`, `font-family: 'IBM Plex Mono'`, `margin-left: auto`

**Action colors:**
- BAD (CO₂ > 1500): `#c63b30`
- POOR (CO₂ 1000–1500, TVOC > 250, PM2.5 > 35): `#c2581f`

**Action derivation logic:**
1. Collect all online nodes where a reading exceeds a warning threshold
2. Sort by severity (BAD > POOR)
3. Show top 3 as action rows
4. Code format: `"CO₂ 1520 ▲"`, `"PM2.5 38 ▲"`, `"TVOC 410 ▲"`

---

## Air Quality Status Palette

Used for room cards in both Map and List views. Derive status from the node's primary metric:

| Status | Trigger | bg | text | num | dotBg |
|---|---|---|---|---|---|
| GOOD | CO₂ < 800 | `#e9f7ee` | `#5a8a6c` | `#2f7d52` | `#c4ead2` |
| OK | CO₂ 800–999 | `#fdf4e3` | `#ab8748` | `#b5781f` | `#f6e3bb` |
| POOR | CO₂ 1000–1499 | `#fdeede` | `#bd7048` | `#c2581f` | `#f8d4b2` |
| BAD | CO₂ ≥ 1500 | `#fde8e6` | `#bd5a51` | `#c63b30` | `#f7c5bf` |
| OFFLINE | No recent data (>5min) | `#f3f1ed` | `#b3aa9e` | `#b3aa9e` | `#e6e0d6` |

Kitchen uses PM2.5 thresholds instead (< 12 GOOD, < 35 OK, < 55 POOR, else BAD).

Status icons (inline SVG, ~11–15px):
- GOOD → checkmark polyline
- OK → horizontal line
- POOR / BAD → exclamation (two lines)
- OFFLINE → × (two crossed lines)

---

## Interactions & Behavior

### Map / List Toggle
- Clicking "List" hides the map container and shows the list container (and vice versa)
- Persist choice in `localStorage` key `bancroft_view` — read on page load

### Live Data Refresh
- Call `/api/now` every **10 seconds** (matches existing behavior)
- Update all room cards, header counts, and suggested actions in place
- Update relative timestamps ("8s ago", "2m ago") every second client-side

### Staleness
- If a node's `timestamp` is > 5 minutes old, treat it as **OFFLINE** (use OFFLINE palette, show "offline" instead of age)

### Animations
```css
@keyframes flow {
  to { stroke-dashoffset: -14; }
}
@keyframes livepulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.35; }
}
```
- Mesh lines for live nodes: `animation: flow 2.6s linear infinite`
- Status bar live dot: `animation: livepulse 2.4s ease-in-out infinite`

---

## Typography

| Use | Family | Weight | Size |
|---|---|---|---|
| App title, room names, values | Nunito | 800 | varies |
| Body, labels | Nunito | 700 | varies |
| Secondary text | Nunito | 600 | varies |
| Action codes | IBM Plex Mono | 600 | 11px |

Google Fonts import:
```html
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
```

---

## Design Tokens

```
Background (page):    #e9eaee
Background (card):    #fbf7f2
Background (toggle):  #f0e9e0
Background (white):   #ffffff
Divider:              #f4efe8

Text primary:         #3a322a
Text secondary:       #a99a88
Text muted:           #bcae9e
Text label:           #6b6f7d

Green online:         #34a853
Green text:           #5a8a6c
Green num:            #2f7d52

Red alert:            #c63b30
Red offline:          #ef6b62

Hero gradient start:  #ff8a5c
Hero gradient end:    #ef5e4e

Status GOOD:          see palette table above
Status OK:            see palette table above
Status POOR:          see palette table above
Status BAD:           see palette table above
Status OFFLINE:       see palette table above
```

---

## API Wiring

### `/api/now` (poll every 10s)
Returns dict keyed by node name. Each value:
```json
{
  "node": "bedroom",
  "timestamp": "2026-06-15T09:41:00",
  "co2_ppm": 1520,
  "temp_c": 21.3,
  "humidity_pct": 52.1,
  "aqi": 2,
  "tvoc": 410,
  "eco2": null,
  "pm25": null,
  "pm10": null
}
```

Node key → display label mapping (from `config.py`):
```
office      → Office
bedroom     → Bedroom
toddler     → Mari's Room
wifesoffice → Em's Office (or Wife's Office — confirm with owner)
basement    → Basement
kitchen     → Kitchen
```

Node capabilities (determines which metric to show as primary):
```
office:      co2 + aqi + tvoc
bedroom:     co2 + aqi + tvoc
toddler:     co2 + aqi + tvoc
wifesoffice: co2 + aqi + tvoc
basement:    co2 only
kitchen:     pm25 + aqi + tvoc (no real CO₂ — use pm25 as primary)
```

### `/api/history` (load on demand, refresh every 60s while visible)
`GET /api/history?range={range}&node={node}&smooth=1`

Used for the detail chart view — not shown in this redesign yet, but keep the endpoint wired for a future detail screen.

---

## Node Positions (Map View)

These are percentage positions within the SVG/map container. Adjust if you add a real floor plan image.

| Node | left% | top% |
|---|---|---|
| office | 30 | 55 |
| bedroom | 18 | 22 |
| toddler | 50 | 22 |
| wifesoffice | 82 | 22 |
| kitchen | 72 | 55 |
| basement | 50 | 83 |

Office is the **hub node** — mesh lines radiate from it to all others.

---

## Assets

- No image assets required
- Icons are inline SVG (no library needed) — see design file's `ic()` function for the shape paths
- Fonts loaded from Google Fonts CDN

---

## Files in This Package

| File | Description |
|---|---|
| `README.md` | This document |
| `Bancroft Air - Dashboard.dc.html` | High-fidelity HTML prototype of the new dashboard |

The prototype uses mock data. All room values, timestamps, and action suggestions are hardcoded for illustration. Wire them to `/api/now` in production.

---

## What's Not in This Design (Future Work)

- **Detail / per-room view** — tapping a room card could navigate to charts (the existing detail view logic in `index.html` can be adapted)
- **History charts** — Chart.js charts from the existing template are not included in this redesign yet
- **Notifications / alert history** — not addressed
- **Settings / threshold editing** — not addressed
