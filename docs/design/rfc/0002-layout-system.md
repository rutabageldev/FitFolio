# Design RFC: Layout System (Breakpoints, Containers, Spacing)

Date: 2025-11-18 Status: Proposed Owners: Design Lead Related:
docs/design/01-foundations/grid.md, docs/design/01-foundations/spacing.md

## Context

We need a predictable responsive grid and spacing rhythm to support dashboards, detail
views, and forms. Decisions now reduce churn when we implement auth and core feature
pages.

## Proposal

Breakpoints (mobile-first):

- `--bp-sm: 640px`, `--bp-md: 768px`, `--bp-lg: 1024px`, `--bp-xl: 1280px`,
  `--bp-2xl: 1536px`

Containers:

- `--container-padding: var(--space-4)` mobile; increase to `--space-6` ≥ md
- Max widths: `--container-md: 720px`, `--container-lg: 960px`, `--container-xl: 1200px`
  (tokens; values TBD)

Grid primitives:

- CSS grid utilities for `Stack` (vertical gaps) and `Inline` (horizontal wrap with
  gaps)
- Content columns: responsive `grid-template-columns: repeat(auto-fit, minmax(…))`
  patterns

Spacing rhythm:

- Use `--space-{1..9}` exclusively for margins/padding/gaps
- Default page padding = `--space-6` (mobile), `--space-8` (≥ md) — TBD after token
  sizing

Page templates:

- Dashboard: header + toolbar + content grid (cards) + right rail (≥ lg)
- Details: header + meta bar + 2-col content (stack to 1-col < lg)
- Forms: full-width single column w/ `FormField` pattern; ≥ lg optional 2-col

Accessibility & motion:

- Respect reduced motion; avoid layout shifts; keep focus within scroll containers

## Alternatives Considered

- Utility framework (Tailwind) now: adds dependency and style surface; could be
  revisited later.
- Pure flexbox: acceptable but grid gives better implicit layouts for cards.

## Impact

- Users: consistent layout and spacing; easier scan.
- Technical: light CSS; React components (`Stack`, `Inline`, `Card`) get simple class
  usage.

## Open Questions

- Container max widths (confirm with program builder and workout logging mocks).
- Do we need a 12-column explicit grid for complex pages? Start implicit; add if needed.

## Decision

TBD (after review). If accepted, add tokens for breakpoints/containers and create
`Stack`, `Inline`, and `Card` primitives with stories.
