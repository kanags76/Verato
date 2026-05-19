# Verato — Design Notes & Future Work

## Files

```
Verato.html              ← main desktop + mobile app (responsive in-place)
Verato Mobile.html       ← iPhone-bezel preview of Verato.html
USER_STORIES.md          ← product scope / user stories
DESIGN_README.md         ← this file

verato/
  data.js                ← mock commitments / meetings / people
  components.jsx         ← shared primitives (Btn, Avatar, Sidebar, StatusBadge, PriorityPicker, …) + dark theme `T`
  responsive.jsx         ← useViewport hook, mobile top bar, drawer, bottom nav, mobile commitment card, swipe-review stack, light theme
  tweaks-panel.jsx       ← Tweaks panel + controls (TweakRadio, TweakColor, …)
  screens-auth.jsx       ← Sign-up plan picker, sign-up form, onboarding (Slack, import)
  screens-dashboard.jsx  ← Dashboard, CommitmentDetail
  screens-meetings.jsx   ← Meetings list, Upload transcript, Extraction review, People, Settings/team
  ios-frame.jsx          ← starter iPhone frame component (unused — Verato Mobile.html uses inline bezel)
```

Load order in `Verato.html`: data → components → responsive → screens → tweaks-panel → app entry.

## Current prototype scope
- 9 screens implemented across the files above, all wired through a single `<App>` router in `Verato.html`
- Priority (High/Med/Low) and Tags are first-class on every commitment
- Dashboard supports priority filter + tag-driven smart filter
- Extraction review: LLM suggests starting priority; CoS overrides inline (desktop) or via swipe-card stack (mobile)
- **Fully responsive in-place**: same file, single breakpoint at 768px. Sidebar → hamburger drawer or bottom-tab nav; multi-column grids collapse; commitment rows become cards; review becomes a swipeable stack.

## Tweaks (toolbar → Tweaks)
- **Theme** — dark / light (full token swap via `applyTheme()` in `responsive.jsx`)
- **Mobile nav** — drawer (default) or bottom-tab bar
- **Accent colour** — live re-tints `T.accent`
- **Jump to screen** — quick nav between any of the 9 screens

## Key product decisions captured

### Priority
- 3 levels: High (P1) · Medium (P2) · Low (P3)
- Visual: 3-bar signal-strength icon + label, plus left-edge row accent on dashboard
- Editable everywhere via picker; defaults to LLM-suggested value during extraction

### Tags
- Free-form lowercase strings, deduped on add
- Autocomplete pulls from existing org-wide tag library
- Click any tag pill (anywhere — row, detail, review) → filtered dashboard view
- Tags drive a "smart filter" pattern: the org's tag vocabulary becomes its taxonomy

### Mobile
- Same source file — no separate mobile app — so feature parity is automatic
- Mobile review uses a card-stack approve/reject UX (one decision at a time) instead of a multi-row table — much higher-quality decisions on small screens
- Sticky top bar with hamburger menu (or bottom tabs); drawer holds nav + theme toggle + user identity

## Future work — LLM context learning (Phase 2+)

The LLM should learn the **organisation's context** and **user preferences** over time, so its priority suggestions and tag suggestions get sharper:

### Org-level learning signals
- Which tags are used most often → boost in autocomplete + suggestion ranking
- Which terms repeatedly co-occur with HIGH priority overrides (e.g. "board", "investor", "legal sign-off") → priors for new extractions
- Which owners/teams have commitments most often escalated → influences risk score weighting per-org
- Which meetings types produce which kinds of commitments → meeting-type-conditioned extraction

### User-level learning signals
- When CoS overrides a suggested priority, capture (raw_text, suggested, chosen) — fine-tune signal
- When CoS adds tags during review that the LLM didn't suggest → tag suggestion training pairs
- When CoS rejects an extracted item → negative example for "what counts as a commitment in this org"

### Implementation sketch
- Store `(suggestion, override, context_window)` triples in a new `extraction_feedback` table
- Periodic batch job (weekly) re-ranks tag suggestions per org based on usage frequency
- Per-org system prompt augmentation: include top-20 tags + recent priority override patterns as few-shot examples
- Out of scope for MVP — design partner phase will generate the training data

### What we cannot do immediately
- True fine-tuning (cost + complexity for design-partner phase)
- Cross-org learning (privacy / data isolation)
- Real-time online learning (latency budget for extraction is already tight)

## Design system reference

### Dark theme (default — defined in `components.jsx` as `T`)
- `#0c0c0f` base · `#13131a` surface · `#1a1a24` panels
- Borders `#23232e` / faint `#1c1c26`
- Text `#e6e6f0` / mid `#9a9aae` / faint `#6a6a82`

### Light theme (defined in `responsive.jsx` as `LIGHT_THEME`)
- `#f5f5f9` base · `#ffffff` surface
- Borders `#e2e2ec` / faint `#eef0f4`
- Text `#1a1a24` / mid `#5a5a72` / faint `#8a8a9e`

### Shared accents
- `#7c6af7` primary accent (tweakable)
- Status: rose overdue, amber at-risk, sage on-track
- Priority: red bar (HIGH), amber bar (MED), neutral (LOW) — distinct from status

### Type
- Plus Jakarta Sans 400/500/600/700/800 — UI
- JetBrains Mono 400/600/700 — data, status chips, timestamps

### Breakpoint
- `768px` — single breakpoint. Below: mobile shell + single column. Above: sidebar + multi-column.
