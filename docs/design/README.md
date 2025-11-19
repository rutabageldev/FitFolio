# FitFolio Design System

This directory is the single source of truth for brand, foundations, components,
patterns, content, flows, and research. It pairs with Storybook for interactive examples
and usage.

## Structure

```
docs/design/
├── 00-brand/           # Logos, naming, imagery guidelines
├── 01-foundations/     # Tokens, color, type, spacing, elevation, grid, motion, iconography, a11y
├── 02-components/      # One folder per component with a spec and examples
├── 03-patterns/        # Reusable UX patterns (forms, empty/error, navigation, notifications)
├── 04-content/         # Voice & tone, microcopy, capitalization, glossary
├── 05-flows/           # User journeys and IA (Mermaid diagrams welcome)
├── 06-research/        # Personas, insights, usability notes, synthesis
├── templates/          # Spec and RFC templates
└── BACKLOG.md          # Design backlog and labels guidance
```

## How we work

- Keep design docs in this folder; keep component code and stories in `frontend/src/`.
- Use PRs for any change here. Tag with `design` and request a design review.
- Cross-cutting decisions: create a Design RFC using the template in `templates/` and
  link it from `docs/adr/` if architectural.
- Keep the backlog in `BACKLOG.md` focused and prioritized; promote to ROADMAP only when
  cross-team or cross-release.

## Storybook

- Storybook lives in the `frontend/.storybook/` directory and renders components from
  `frontend/src/**`.
- Every component in `02-components` should have a matching Storybook entry with states
  and a11y notes.

## Accessibility baseline

- Meet WCAG AA contrast, provide visible focus, and ensure keyboard operability.
- Document keyboard interactions and ARIA where relevant in each component spec.
