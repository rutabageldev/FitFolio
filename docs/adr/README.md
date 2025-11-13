# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for FitFolio. ADRs document
important architectural decisions along with their context and consequences.

## What is an ADR?

An ADR is a document that captures an important architectural decision made along with
its context and consequences. ADRs are lightweight documentation that help teams:

- Understand why decisions were made
- Avoid revisiting settled decisions
- Onboard new team members
- Track architectural evolution

## Quick Reference

| ADR                                                      | Status      | Date       | Topic                                   | Tags                                                 |
| -------------------------------------------------------- | ----------- | ---------- | --------------------------------------- | ---------------------------------------------------- |
| [ADR-0001](0001-directory-based-api-versioning.md)       | ✅ Accepted | 2025-10-29 | Directory-Based API Versioning          | architecture, api, backend, versioning               |
| [ADR-0002](0002-traefik-reverse-proxy-integration.md)    | ✅ Accepted | 2025-10-31 | Traefik Reverse Proxy Integration       | deployment, infrastructure, traefik, security, ssl   |
| [ADR-0003](0003-passwordless-authentication-strategy.md) | ✅ Accepted | 2025-10-26 | Passwordless Authentication Strategy    | security, authentication, backend, ux                |
| [ADR-0004](0004-opaque-server-side-sessions.md)          | ✅ Accepted | 2025-10-26 | Opaque Server-Side Sessions over JWT    | security, authentication, backend, sessions          |
| [ADR-0005](0005-redis-configuration-and-access.md)       | ✅ Accepted | 2025-11-06 | Redis Configuration and Access Patterns | infrastructure, redis, docker, testing, devcontainer |

## ADRs by Topic

### Architecture & API Design

- [ADR-0001: Directory-Based API Versioning](0001-directory-based-api-versioning.md)

### Deployment & Infrastructure

- [ADR-0002: Traefik Reverse Proxy Integration](0002-traefik-reverse-proxy-integration.md)
- [ADR-0005: Redis Configuration and Access Patterns](0005-redis-configuration-and-access.md)

### Security & Authentication

- [ADR-0003: Passwordless Authentication Strategy](0003-passwordless-authentication-strategy.md)
- [ADR-0004: Opaque Server-Side Sessions over JWT](0004-opaque-server-side-sessions.md)

## Status Definitions

- **Proposed** - Decision under consideration
- **Accepted** - Decision approved and implemented
- **Deprecated** - No longer relevant but kept for historical context
- **Superseded** - Replaced by a newer decision (links to superseding ADR)

## Creating a New ADR

1. Copy `TEMPLATE.md` to a new file with the next sequential number
2. Follow the naming convention: `XXXX-short-kebab-case-title.md`
3. Fill in all sections of the template
4. Update this README with the new ADR in the table and relevant topic section
5. Create a PR for review and discussion
6. Once accepted, update status to "Accepted" and merge

## Guidelines

- **Keep ADRs immutable** - Once accepted, don't edit. Create a new superseding ADR
  instead.
- **Be concise** - Focus on the decision and rationale, not implementation details
- **Explain "why"** - Context and reasoning are more important than "what"
- **Link related ADRs** - Show relationships between decisions
- **Tag appropriately** - Use consistent tags for easy filtering
- **Date consistently** - Use YYYY-MM-DD format

## References

- ADR concept by Michael Nygard:
  https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- GitHub ADR Organization: https://adr.github.io/
- ADR Tools: https://github.com/npryce/adr-tools
