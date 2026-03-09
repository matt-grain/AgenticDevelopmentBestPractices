# Threat Model

> Copy this template to your project root as `THREAT_MODEL.md` and fill in the sections.
> This file is read by agents during `/review-architecture` and `/implement-phase` to provide security context.

**Project:** [Project Name]
**Last Updated:** [Date]
**Author:** [Name]

---

## Overview

Brief description of what the system does and its security posture.

---

## Assets

What are we protecting? Rate each by sensitivity.

| Asset | Sensitivity | Description |
|-------|-------------|-------------|
| User credentials | CRITICAL | Passwords, auth tokens, API keys |
| Payment data | CRITICAL | Credit cards, bank accounts |
| PII | HIGH | Names, emails, addresses, phone numbers |
| Business data | MEDIUM | Orders, invoices, inventory |
| Public content | LOW | Published articles, product listings |

---

## Trust Boundaries

Where does trust change in the system?

```
┌─────────────────────────────────────────────────────────┐
│  UNTRUSTED                                              │
│  ┌─────────────────┐                                    │
│  │  Public Internet │                                   │
│  │  - Browsers      │                                   │
│  │  - Mobile apps   │                                   │
│  │  - Third-party   │                                   │
│  └────────┬─────────┘                                   │
│           │ HTTPS                                       │
│           ▼                                             │
│  ┌─────────────────┐                                    │
│  │  API Gateway     │  ◄── Authentication boundary      │
│  │  - Rate limiting │                                   │
│  │  - Auth check    │                                   │
│  └────────┬─────────┘                                   │
│           │                                             │
│  SEMI-TRUSTED                                           │
│  ┌─────────────────┐                                    │
│  │  Application     │                                   │
│  │  - Business logic│                                   │
│  │  - Authorization │  ◄── Authorization boundary       │
│  └────────┬─────────┘                                   │
│           │                                             │
│  TRUSTED                                                │
│  ┌─────────────────┐                                    │
│  │  Database        │                                   │
│  │  - Encrypted     │                                   │
│  └──────────────────┘                                   │
└─────────────────────────────────────────────────────────┘
```

---

## Threat Actors

Who might attack us?

| Actor | Motivation | Capability | Likelihood |
|-------|------------|------------|------------|
| Script kiddies | Fun, notoriety | Low (automated tools) | HIGH |
| Competitors | Business advantage | Medium | MEDIUM |
| Insiders | Disgruntlement, money | High (access) | LOW |
| Nation-state | Espionage | Very high | LOW |
| Criminals | Financial gain | Medium-high | MEDIUM |

---

## Attack Surfaces

### External Attack Surface

| Entry Point | Exposure | Controls |
|-------------|----------|----------|
| Public API (`/api/v1/*`) | Internet | Auth required, rate limited |
| Webhooks (`/webhooks/*`) | Internet | Signature verification |
| Admin panel (`/admin/*`) | Internet | MFA, IP allowlist |
| File uploads | Internet | Type validation, size limits, virus scan |

### Internal Attack Surface

| Entry Point | Exposure | Controls |
|-------------|----------|----------|
| Database | VPC only | IAM auth, encrypted |
| Message queue | VPC only | TLS, credentials |
| Internal APIs | VPC only | Service mesh auth |

---

## Known Risks & Mitigations

### CRITICAL

| Risk | Description | Mitigation | Status |
|------|-------------|------------|--------|
| SQL Injection | User input in queries | Parameterized queries only | Enforced by rules |
| Auth bypass | Missing auth checks | Auth middleware on all routes | Code review required |
| Secrets in code | Hardcoded credentials | Environment variables + secret scanning | CI gate |

### HIGH

| Risk | Description | Mitigation | Status |
|------|-------------|------------|--------|
| IDOR | Direct object reference | Ownership checks in service layer | Code review required |
| XSS | Unsanitized output | React escaping, CSP headers | Partial |
| CSRF | Cross-site requests | CSRF tokens on mutations | Implemented |

### MEDIUM

| Risk | Description | Mitigation | Status |
|------|-------------|------------|--------|
| Rate limiting bypass | Distributed attacks | IP + user rate limiting | Implemented |
| Dependency vulns | CVEs in packages | Weekly `pip-audit` / `npm audit` | CI gate |

---

## Sensitive Endpoints

Endpoints requiring extra scrutiny during code review:

| Endpoint | Risk | Required Controls |
|----------|------|-------------------|
| `POST /auth/login` | Credential stuffing | Rate limit, account lockout |
| `POST /auth/password-reset` | Account takeover | Token expiry, email verification |
| `GET /users/{id}` | IDOR | Ownership or admin check |
| `POST /payments` | Financial fraud | Strong auth, audit logging |
| `DELETE /users/{id}` | Data destruction | Soft delete, admin only |
| `GET /admin/*` | Privilege escalation | Admin role check, MFA |

---

## Compliance Requirements

| Requirement | Scope | Status |
|-------------|-------|--------|
| GDPR | EU user data | Partial |
| PCI-DSS | Payment processing | N/A (using Stripe) |
| SOC 2 | Enterprise customers | Not started |
| HIPAA | Health data | N/A |

---

## Security Testing

| Test Type | Frequency | Tool | Last Run |
|-----------|-----------|------|----------|
| SAST | Every commit | Bandit, Semgrep | CI |
| SCA | Every commit | pip-audit | CI |
| DAST | Weekly | OWASP ZAP | [Date] |
| Penetration test | Annually | External vendor | [Date] |
| Bug bounty | Continuous | HackerOne | Active |

---

## Incident Response

| Severity | Response Time | Escalation |
|----------|---------------|------------|
| CRITICAL (data breach) | 1 hour | CEO, Legal, Security |
| HIGH (active exploit) | 4 hours | Engineering Lead, Security |
| MEDIUM (vulnerability found) | 24 hours | Security team |
| LOW (hardening opportunity) | Sprint planning | Engineering |

---

## Agent Instructions

When implementing features that touch sensitive areas:

1. **Before writing code**: Check if the endpoint/feature is in "Sensitive Endpoints" above
2. **During implementation**: Apply all "Required Controls" listed
3. **During review**: Flag any new endpoints that should be added to this list
4. **Security questions to ask**:
   - What's the worst thing an attacker could do with this feature?
   - What if the input is malicious?
   - What if the user isn't who they claim to be?
   - What if this data leaks?
