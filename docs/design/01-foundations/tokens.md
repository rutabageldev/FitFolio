# Design Tokens (Skeleton)

Single source of truth for visual decisions. Implemented as CSS custom properties under
`frontend/src/styles/tokens.css`.

Do not define the palette/type here yet—this is structure only.

## Token Categories

- Color: `--color-<role>-<scale>`
- Typography: `--font-family-<name>`, `--font-size-<step>`, `--line-height-<step>`
- Spacing: `--space-<step>`
- Radius: `--radius-<step>`
- Elevation: `--elevation-<step>`
- Z-index: `--z-<layer>`

## Usage

Reference tokens in CSS with `var(--token-name)`; avoid hard-coded values in component
styles.
