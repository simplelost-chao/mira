# Safari-Style Tab Switcher for Mobile Dev Terminal

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current flat pane-switcher dropdown with a Safari-style 3D card stack view on mobile, showing terminal preview thumbnails.

**Scope:** Mobile only (`@media max-width: 900px`). Desktop pane list unchanged.

---

## Architecture

All changes are in `vibe/dev_page.py` (CSS + JS + HTML). No backend changes needed.

### Data: Pane Snapshot Cache

```js
var _paneSnapshots = {};  // { target: htmlString }
```

- **Save:** When switching away from a pane (in `selectPane()` before connecting new WS), capture `document.getElementById('mobile-term-output').innerHTML` into `_paneSnapshots[oldTarget]`.
- **Update:** On each WS `onmessage`, also update `_paneSnapshots[_currentTarget]` with current rendered HTML.
- **Delete:** When a pane is killed, delete its snapshot.
- **No extra API calls or network cost.**

### CSS: Card Stack Layout

**Overlay container:**
```css
.tab-switcher {
  position: fixed; inset: 0; z-index: 300;
  background: rgba(0,0,0,.85);
  backdrop-filter: blur(8px);
  overflow-y: auto; -webkit-overflow-scrolling: touch;
  padding: 60px 16px 32px;  /* top padding for topbar */
  display: none;
}
.tab-switcher.open { display: block; }
```

**Card:**
```css
.tab-card {
  position: relative;
  width: 100%;
  margin-bottom: -16px;  /* overlap for stack effect */
  border-radius: 12px;
  background: var(--bg);
  border: 1px solid var(--border);
  overflow: hidden;
  transform-origin: center bottom;
  transform: perspective(800px) rotateX(2deg);
  transition: transform .3s, opacity .3s;
  box-shadow: 0 4px 20px rgba(0,0,0,.4);
}
.tab-card:last-child { margin-bottom: 0; }
.tab-card.active { border-color: var(--accent); }
```

**Card header (project name + status + close):**
```css
.tab-card-header {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  font-size: 12px; font-weight: 600; color: var(--text);
}
.tab-card-close {
  margin-left: auto; width: 20px; height: 20px;
  background: none; border: none; color: var(--muted);
  cursor: pointer; font-size: 16px; line-height: 1;
  display: flex; align-items: center; justify-content: center;
}
```

**Card preview (scaled terminal snapshot):**
```css
.tab-card-preview {
  height: 140px;
  overflow: hidden;
  position: relative;
}
.tab-card-preview-inner {
  transform: scale(0.35);
  transform-origin: top left;
  width: 285%;   /* 100% / 0.35 */
  height: 400px; /* enough to show content */
  font-family: var(--mono);
  font-size: 12px;
  line-height: 1.4;
  color: var(--text);
  padding: 6px 8px;
  pointer-events: none;
}
```

### 3D Scroll Effect

On scroll, adjust each card's `rotateX` based on its position in the viewport:

```js
function _updateCardPerspective() {
  var cards = document.querySelectorAll('.tab-card');
  var scrollY = document.querySelector('.tab-switcher').scrollTop;
  var viewH = window.innerHeight;
  cards.forEach(function(card) {
    var rect = card.getBoundingClientRect();
    var center = rect.top + rect.height / 2;
    var ratio = (center / viewH);  // 0 = top, 1 = bottom
    var angle = 3 - ratio * 6;    // top cards tilt back, bottom cards tilt forward
    card.style.transform = 'perspective(800px) rotateX(' + angle.toFixed(1) + 'deg)';
  });
}
```

Throttled to `requestAnimationFrame` on scroll.

### JS: Open/Close/Select

**Open (`_openTabSwitcher()`):**
1. Fetch panes from `/api/dev/panes`
2. Build card HTML: for each pane, render header (dot + name + ✕) + preview (from `_paneSnapshots[target]` or "暂无预览")
3. Show overlay with fade-in
4. Attach scroll listener for 3D effect
5. Active pane card scrolled into view

**Close:**
- Click on a card → `selectPane(target, cmd)` → close overlay with fade-out
- Click ✕ on card → `killPane` → remove card with slide-up animation
- Click backdrop (empty area) → close overlay

**Entry point:** The existing topbar expand button (`_togglePaneSwitcher`) is rewired to call `_openTabSwitcher()` on mobile.

### Animations

- **Open:** overlay `opacity 0→1` over `.25s`, cards stagger in from bottom with `translateY(40px)→0` delay `i*50ms`
- **Close (select):** selected card scales up `scale(1)→scale(1.05)` then overlay fades out
- **Close (kill):** card slides left + fades out, remaining cards reflow
- **All transitions use `will-change: transform, opacity` for GPU acceleration**

### Skin Support

- Cards use `var(--bg)`, `var(--panel)`, `var(--border)`, `var(--accent)` → automatically themed
- Pixel-cyber: cards get `box-shadow: 0 0 12px rgba(0,212,255,.15)` via `[data-theme="pixel-cyber"] .tab-card`

### What NOT to build

- No drag-to-reorder
- No pinch-to-zoom
- No horizontal swipe between panes (tap only)
- Desktop unchanged — feature is `@media (max-width: 900px)` only
