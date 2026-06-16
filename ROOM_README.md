# Handoff: Bancroft Air — Room Detail View (Option B)

## Overview

This is the per-room detail view for Bancroft Air. It replaces (or supplements) the existing detail section inside `templates/index.html`. The chosen layout is **Option B — Metric Focus**: one metric prominently at a time, with a large chart for that metric and a mini grid of all other readings below.

Navigation: tap any room card on the dashboard (map or list view) → this screen slides in. A ← back button returns to the dashboard.

---

## About the Design File

`Bancroft Air - Room Detail.dc.html` is an **interactive HTML prototype** showing three phones side by side:
- **Dashboard** — tap any room card to switch the active room across both detail screens
- **Option A** (discard) — card stack layout, not chosen
- **Option B** ← **this is what to build**

The prototype uses hardcoded mock data. Wire everything to `/api/now` and `/api/history` in production.

---

## Screen Layout — Option B

```
┌────────────────────────────────────┐
│ 9:41                          ● live│  ← status bar
├────────────────────────────────────┤
│ ← Bedroom                    [Bad] │  ← back + room name + status badge
├────────────────────────────────────┤
│ [CO₂] [Temp] [Humidity] [AQI] …   │  ← metric selector pill row (scrollable)
├────────────────────────────────────┤
│ ┌──────────────────────────────┐   │
│ │ CO₂                          │   │  ← colored hero container (status-tinted)
│ │ 1520  ppm                    │   │
│ │      ▲ trending              │   │
│ │ Updated 8s ago · stable      │   │
│ └──────────────────────────────┘   │
│ ┌──────────────────────────────┐   │
│ │ CO₂ history       6H 1D 1W  │   │  ← main chart card w/ inline range picker
│ │  [filled area chart]         │   │
│ │ 6h ago      3h ago      now  │   │
│ └──────────────────────────────┘   │
│                                    │
│ ALL READINGS                       │  ← mini 2-col grid (tap to promote)
│ ┌───────────┐  ┌───────────┐      │
│ │Temp       │  │Humidity   │      │
│ │[sparkline]│  │[sparkline]│      │
│ │68.2°F     │  │52%        │      │
│ └───────────┘  └───────────┘      │
└────────────────────────────────────┘
```

---

## Components

### 1. Status Bar
Identical to the dashboard. See dashboard handoff README.

---

### 2. Detail Header

```
[ ← ]  Bedroom                    [Bad]
```

- Container: `display:flex`, `align-items:center`, `gap:8px`, `padding:8px 18px 10px`, `border-bottom:1px solid #f4efe8`, `flex-shrink:0`
- Back button: transparent bg, no border, `cursor:pointer`. On tap → `history.back()` (or pop the route stack)
- Back icon: SVG chevron left, `stroke:#3a322a`, 22px
- Room name: `font-size:18px`, `font-weight:800`, `letter-spacing:-.01em`, `color:#3a322a`, `flex:1`
- Status badge: `font-size:11px`, `font-weight:800`, `color:{rS.num}`, `background:{rS.bg}`, `border-radius:20px`, `padding:3px 10px`
  - Text: "Good" / "OK" / "Poor" / "Bad" / "Offline"

---

### 3. Metric Selector Pills

A horizontally scrollable row of pill buttons, one per metric available in the room.

- Container: `display:flex`, `gap:5px`, `padding:10px 16px 0`, `overflow-x:auto`, `flex-shrink:0`
- Hide scrollbar (`::-webkit-scrollbar { display:none }`, `scrollbar-width:none`)
- Each pill: `border:none`, `cursor:pointer`, `border-radius:20px`, `padding:6px 12px`, `font-size:11.5px`, `font-weight:800`, `flex-shrink:0`, `white-space:nowrap`, `transition:all .15s`
  - **Active:** `background:{metric.color}`, `color:#fff`
  - **Inactive:** `background:#f0e9e0`, `color:#a99a88`

**Metrics shown per node** (from `config.NODE_SENSORS`):

| Node | Metrics |
|---|---|
| office | CO₂, Temperature, Humidity, AQI, TVOC |
| bedroom | CO₂, Temperature, Humidity, AQI, TVOC |
| toddler | CO₂, Temperature, Humidity, AQI, TVOC |
| wifesoffice | CO₂, Temperature, Humidity, AQI, TVOC |
| basement | CO₂, Temperature, Humidity |
| kitchen | PM2.5, Temperature, Humidity, AQI, TVOC |

**Default selected metric:** primary metric for the room (CO₂ for all except Kitchen → PM2.5).

**Persistence:** store selected metric per-room in `localStorage` key `bancroft_metric_{node}`. Restore on revisit.

---

### 4. Hero Container (colored, status-tinted)

The large current-value display. Color is derived from the **room's overall status** (not the selected metric), so the tint stays consistent as the user switches metrics.

- Container: `margin:10px 16px 12px`, `background:{rS.bg}`, `border-radius:22px`, `padding:14px 18px`, `flex-shrink:0`

Interior:
```
CO₂                             ← metric label (uppercase, muted)
1520  ppm  ▲ trending           ← big number + unit + trend
Updated 8s ago · stable         ← staleness line
```

- Metric label: `font-size:10px`, `font-weight:800`, `color:{rS.text}`, `text-transform:uppercase`, `letter-spacing:.06em`, `margin-bottom:6px`
- Big number: `font-size:52px`, `font-weight:800`, `color:{rS.num}`, `letter-spacing:-.03em`, `line-height:1`
- Unit: `font-size:13px`, `font-weight:700`, `color:{rS.text}`, `opacity:.8`
- Trend line: `font-size:11px`, `font-weight:700`, `color:{rS.text}`, `opacity:.7`
  - "▲ trending" / "▼ trending" / "— stable" — derived from chart slope
- Staleness: `font-size:11.5px`, `font-weight:700`, `color:{rS.text}`, `opacity:.75`, `margin-top:8px`
  - "Updated {N}s ago · {trend-word}" or "Sensor offline"

**Temperature:** always display in °F. Convert: `(temp_c * 9/5 + 32)`.

---

### 5. Main Chart Card

The full-width chart for the currently selected metric.

- Container: `margin:0 16px`, `background:#fff`, `border-radius:22px`, `padding:13px 15px 11px`, `box-shadow:0 6px 16px -10px rgba(120,90,60,.3)`, `flex-shrink:0`

Header row:
- Left: metric label + " history" — `font-size:10.5px`, `font-weight:800`, `color:#bcae9e`, `text-transform:uppercase`, `letter-spacing:.05em`
- Right: **inline range picker** — 3 pills: `6H`, `1D`, `1W`
  - Active: `background:#3a322a`, `color:#fff`, `border-radius:12px`, `padding:3px 9px`, `font-size:10px`, `font-weight:800`
  - Inactive: transparent bg, `color:#c0b4a4`

**Chart spec:**
- Type: filled area (not a library — use SVG `<polyline>` + `<polygon>` fill + `<linearGradient>`)
- Canvas dimensions: full width of card × 128px tall
- Fill: `linearGradient` from `{metric.color}` at 20% opacity → 2% at bottom
- Line: `stroke:{metric.color}`, `stroke-width:1.8`, `stroke-linecap:round`, `stroke-linejoin:round`
- Endpoint dot: `r:2.8`, `fill:{metric.color}`, `stroke:#fbf7f2`, `stroke-width:1.4`
- Threshold lines: dashed horizontal lines at standard breakpoints — see threshold table below
  - `stroke-dasharray:2 4`, `stroke-width:0.8`, `opacity:0.55`

**Time axis** (3 labels below chart):
- 6H: "6h ago" · "3h ago" · "now"
- 1D: "24h ago" · "12h ago" · "now"
- 1W: "7d ago" · "3d ago" · "now"
- Label style: `font-size:9px`, `font-weight:700`, `color:#d0c6b8`

**API call:** `GET /api/history?range={range}&node={node}&smooth=1`
- Use `readings_10min` data (smooth=1) for 1D and 1W; `readings_1min` (smooth=0) works for 6H but smooth is fine too
- Downsample to ~44 points for rendering (take every Nth row)
- Scale Y axis: min × 0.9 → max × 1.1 (or use hard min/max for AQI: 0–5)

---

### 6. Mini Grid — All Readings

Shows all metrics **except the currently selected one**. Tap a mini card to promote it to the hero + main chart.

- Scroll container: `flex:1`, `overflow-y:auto`, hide scrollbar
- Padding: `10px 16px 20px`
- Section label "ALL READINGS": `font-size:10px`, `font-weight:800`, `color:#bcae9e`, `text-transform:uppercase`, `letter-spacing:.05em`, `margin-bottom:9px`
- Grid: `display:grid`, `grid-template-columns:1fr 1fr`, `gap:8px`

Each mini card:
- `background:#fff`, `border-radius:16px`, `padding:10px 12px`, `box-shadow:0 3px 8px -5px rgba(120,90,60,.2)`, `cursor:pointer`
- Metric label: `font-size:9px`, `font-weight:800`, `color:#bcae9e`, `text-transform:uppercase`, `letter-spacing:.04em`, `margin-bottom:4px`
- **Mini sparkline** (SVG, same technique): width fills card, 34px tall — same fill/line style but proportionally thinner line (~1.4px)
- Current value: `font-size:18px`, `font-weight:800`, `color:{metric.color}`, `letter-spacing:-.02em`, `margin-top:3px`
- Unit: `font-size:8px`, `font-weight:700`, `color:#bcae9e`, `margin-left:2px`

On tap: update selected metric → re-render hero + main chart. Persist to `localStorage`.

---

## Metric Configs

| Key | Label | Unit | Color | Thresholds (value → stroke color) |
|---|---|---|---|---|
| co2 | CO₂ | ppm | `#c2581f` | 800→`#2f7d52`, 1000→`#b5781f`, 1500→`#c63b30` |
| temp | Temperature | °F | `#4a7eb5` | none |
| hum | Humidity | %RH | `#5a8a6c` | 30→`#c2a21f`, 70→`#c2a21f` |
| aqi | AQI | index | `#7c5cbf` | 2→`#c2a21f`, 3→`#c2581f` (Y-axis 0–5 fixed) |
| tvoc | TVOC | ppb | `#b87333` | 150→`#34a853`, 250→`#c2a21f`, 500→`#c2581f` |
| pm25 | PM2.5 | µg/m³ | `#bd5a51` | 12→`#34a853`, 35→`#c2a21f` |

---

## Status Palette (rS — room level)

Derived from the room's **primary metric** (CO₂ for most rooms; PM2.5 for kitchen):

| Status | Trigger | bg | text | num | dot |
|---|---|---|---|---|---|
| GOOD | CO₂ < 800 / PM2.5 < 12 | `#e9f7ee` | `#5a8a6c` | `#2f7d52` | `#c4ead2` |
| OK | CO₂ 800–999 / PM2.5 12–34 | `#fdf4e3` | `#ab8748` | `#b5781f` | `#f6e3bb` |
| POOR | CO₂ 1000–1499 / PM2.5 35–54 | `#fdeede` | `#bd7048` | `#c2581f` | `#f8d4b2` |
| BAD | CO₂ ≥ 1500 / PM2.5 ≥ 55 | `#fde8e6` | `#bd5a51` | `#c63b30` | `#f7c5bf` |
| OFFLINE | No data > 5min | `#f3f1ed` | `#b3aa9e` | `#b3aa9e` | `#e6e0d6` |

---

## Staleness & Offline Detection

- Parse `timestamp` from `/api/now` as ISO 8601
- If `now - timestamp > 5 minutes` → treat as **OFFLINE**
  - Use OFFLINE palette
  - Show "Sensor offline" in hero container instead of staleness line
  - Big number shows "—"
- If online: show relative age ("8s ago", "2m ago") — update every second client-side

---

## Navigation

### Into the detail view

From the dashboard, when a user taps a room card (map or list):
- Push the detail view URL: e.g. `/room/bedroom` or use `?room=bedroom`
  - Alternatively: hide dashboard, show detail via JS (current `index.html` pattern) — your call
- Pass the node key as a parameter so the detail view knows which room to load

### Back

Tap the `←` button → `history.back()` or navigate to `/`.

### State to persist (localStorage)

| Key | Value | Purpose |
|---|---|---|
| `bancroft_view` | `"map"` or `"list"` | Dashboard map/list toggle |
| `bancroft_metric_{node}` | metric key e.g. `"co2"` | Last selected metric per room |
| `bancroft_range` | `"6h"`, `"1d"`, or `"1w"` | Last selected chart range |

---

## Data Wiring

### On page load / room entry

1. `GET /api/now` → populate hero container + mini grid current values
2. `GET /api/history?range=6h&node={node}&smooth=1` → render main chart + mini sparklines
3. Start 10-second polling for `/api/now` (update hero + mini grid values in place)
4. Re-fetch `/api/history` when range changes or on 60-second interval

### `/api/now` response shape

```json
{
  "bedroom": {
    "node": "bedroom",
    "timestamp": "2026-06-15T09:41:00",
    "co2_ppm": 1520,
    "temp_c": 20.1,
    "humidity_pct": 52.0,
    "aqi": 3,
    "tvoc": 410,
    "eco2": null,
    "pm25": null,
    "pm10": null
  }
}
```

Key mapping:

| API field | Metric key |
|---|---|
| `co2_ppm` | co2 |
| `temp_c` (→ convert to °F) | temp |
| `humidity_pct` | hum |
| `aqi` | aqi |
| `tvoc` | tvoc |
| `pm25` | pm25 |

### `/api/history` response shape

Array of rows, same fields as above plus `timestamp` (ISO string):

```json
[
  { "timestamp": "2026-06-15T03:41:00", "node": "bedroom", "co2_ppm": 1340, "temp_c": 20.4, ... },
  ...
]
```

Filter to the requested `node` (the endpoint accepts `?node=bedroom` directly).

### Trend calculation

From the history array (last N points):
- `last > first * 1.06` → "▲ trending"
- `last < first * 0.94` → "▼ trending"
- else → "— stable"

---

## Chart Implementation (SVG — no library needed)

The existing `index.html` uses Chart.js. The new design uses **inline SVG** for charts — lighter weight, works without any library. Here is the exact algorithm:

```js
function buildChart(rows, field, color, width, height) {
  const vals = rows.map(r => r[field]).filter(v => v != null);
  if (!vals.length) return null;

  // Downsample to ~44 pts
  const step = Math.max(1, Math.floor(vals.length / 44));
  const pts  = vals.filter((_, i) => i % step === 0 || i === vals.length - 1);

  const mn = Math.min(...pts) * 0.9;
  const mx = Math.max(...pts) * 1.1;
  const span = (mx - mn) || 1;

  const coords = pts.map((v, i) => ({
    x: (i / (pts.length - 1)) * width,
    y: height - ((Math.min(mx, Math.max(mn, v)) - mn) / span) * (height - 5) - 2.5,
  }));

  const lineStr = coords.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const fillStr = `0,${height} ${lineStr} ${width},${height}`;

  // Return SVG elements (using your framework of choice)
  // gradient id must be unique per chart instance
  return { lineStr, fillStr, lastPt: coords[coords.length - 1] };
}
```

SVG structure per chart:
```html
<svg viewBox="0 0 {W} {H}" width="100%" height="{H}" style="display:block;overflow:visible">
  <defs>
    <linearGradient id="grad-{uid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"   stop-color="{color}" stop-opacity="0.2"/>
      <stop offset="100%" stop-color="{color}" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  <!-- threshold lines, one per threshold within visible range -->
  <line x1="0" y1="{ty}" x2="{W}" y2="{ty}"
        stroke="{threshColor}" stroke-width="0.8"
        stroke-dasharray="2 4" opacity="0.55"/>
  <!-- fill area -->
  <polygon points="{fillStr}" fill="url(#grad-{uid})"/>
  <!-- line -->
  <polyline points="{lineStr}" fill="none"
            stroke="{color}" stroke-width="1.8"
            stroke-linecap="round" stroke-linejoin="round"/>
  <!-- endpoint dot -->
  <circle cx="{lastX}" cy="{lastY}" r="2.8"
          fill="{color}" stroke="#fbf7f2" stroke-width="1.4"/>
</svg>
```

**Ensure gradient IDs are unique** — e.g. `grad-bedroom-co2-main`, `grad-bedroom-temp-mini`.

---

## Typography & Global Tokens

```
Font: 'Nunito' (weights 400, 600, 700, 800) + 'IBM Plex Mono' (500, 600)

<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
```

| Token | Value |
|---|---|
| Page bg | `#e9eaee` |
| Card bg | `#fbf7f2` |
| White card | `#ffffff` |
| Toggle bg | `#f0e9e0` |
| Divider | `#f4efe8` |
| Text primary | `#3a322a` |
| Text secondary | `#a99a88` |
| Text muted | `#bcae9e` |
| Green online | `#34a853` |
| Red offline | `#ef6b62` |

Animations:
```css
@keyframes livepulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.35; }
}
```

---

## Integration Notes (existing codebase)

The existing `templates/index.html` has a `#detail-view` div that's shown/hidden by JS. Options for integration:

**Option 1 — Extend in place (recommended for minimal change):**
- Add a new `#detail-view-b` div styled per this spec
- When a room is selected, hide `#detail-view`, show `#detail-view-b`
- Reuse the existing `switchToRoom(node)` function to trigger it
- Replace Chart.js charts in the new view with SVG charts per the algorithm above

**Option 2 — Separate route:**
- Add `@app.route("/room/<node>")` in `web_app.py`
- New template `templates/room.html` implementing this spec fully
- Dashboard room cards link to `/room/{node}` instead of toggling JS

Either works. Option 2 is cleaner for future expansion (e.g. bookmarking a room).

---

## Files in This Package

| File | Description |
|---|---|
| `README.md` | This document |
| `Bancroft Air - Room Detail.dc.html` | Interactive prototype showing both variations. Option B is the rightmost phone. |
