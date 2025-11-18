# Flows & IA (Skeleton)

Capture key user journeys, information architecture, and state transitions.

Use Mermaid for sequence/flow diagrams where helpful:

```mermaid
flowchart TD
  A[Enter email] --> B[Send magic link]
  B --> C[Open link]
  C --> D{Verified?}
  D -- yes --> E[Create session]
  D -- no --> F[Prompt verify email]
```

Link flow steps to relevant patterns and components.
