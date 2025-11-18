# Design RFC: Token Naming & Structure

Date: 2025-11-18 Status: Proposed Owners: Design Lead Related:
docs/design/01-foundations/tokens.md

## Context

We need a single, predictable tokens scheme to avoid hardcoded values and to enable
theming (incl. dark mode) later. CSS custom properties will be our initial single source
of truth.

## Proposal

Use role-based, scale-aware names, defined in `:root` via CSS custom properties (no
actual values yet):

- Color: `--color-{role}-{scale}`
  - Roles: `primary`, `neutral`, `success`, `warning`, `danger`, `info`, `background`,
    `surface`, `text`
  - Scales: `50..900` (100 steps typical)
  - Examples: `--color-primary-500`, `--color-neutral-900`, `--color-surface-100`
- Typography:
  - Families: `--font-family-sans`, `--font-family-mono`
  - Sizes: `--font-size-{step}` (e.g., `-2..6`), `--line-height-{step}`
  - Weights: `--font-weight-regular|medium|semibold|bold`
- Spacing: `--space-{step}` (`1..9`), base-4 or base-8 scale
- Radius: `--radius-{step}` (`1..4`), plus `--radius-full` for pills
- Elevation: `--elevation-{step}` (`0..5`) with shadow tokens
- Z-index: `--z-{layer}` (`dropdown`, `overlay`, `modal`, `toast`)

Authoring conventions:

- Reference tokens only: `color: var(--color-text); padding: var(--space-3);`
- No hex/px in component styles unless a temporary shim is documented.
- Theming later by scoping tokens to `[data-theme=dark]` or
  `@media (prefers-color-scheme: dark)`.

## Alternatives Considered

- Raw palette tokens (e.g., `--blue-500`) only: too low-level; encourages misuse of
  brand hues.
- JS token source with build step: adds infra; overkill for the current stage.

## Impact

- Users: consistent visual language, easier theme pivot later.
- Accessibility: enables contrast control by role (e.g., text/surface pairs).
- Technical: minimal; standard CSS variables; no runtime cost.

## Open Questions

- Base spacing: 4 vs 8?
- Type scale ratio (e.g., 1.125 vs 1.2)?
- Do we add semantic aliases (e.g., `--color-link`) now or after foundations v1?

## Decision

TBD (after review). If accepted, implement scaffolding in
`frontend/src/styles/tokens.css` and refactor new components to use tokens only.
