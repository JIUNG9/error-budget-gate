# Security Policy

## Reporting a vulnerability

**Please don't open a public issue for a security problem.**

Report it privately through GitHub:
[**Report a vulnerability**](https://github.com/JIUNG9/error-budget-gate/security/advisories/new)

That opens an advisory visible only to you and the maintainer — no email address to
track down, and nothing public until there's a fix.

> **Maintainer note:** that link requires *Private vulnerability reporting* to be
> switched on under **Settings → Advanced Security**. It's one checkbox and it's
> free on public repos. Until it's enabled the URL 404s for outside reporters, so
> turn it on before pointing anyone at this policy.

### What helps

- What the issue is, and what an attacker gets out of it
- Steps to reproduce, or a proof of concept
- The affected version or commit
- A suggested fix, if you have one in mind

### What to expect

This is a personally maintained project rather than a funded product, so response is
best-effort: acknowledgement within a few days, and a fix prioritised by severity.
If something is being actively exploited, say so in the first line.

## Supported versions

Pre-1.0 and alpha. Only the latest release gets fixes; there are no maintenance
branches yet.

## Scope

The gate is a pure function with no I/O, no network calls and no dependencies, so
the interesting failure mode isn't memory safety — it's a **decision** bug. Reports
in scope include anything that makes `evaluate()` return `allow` when it should
return `block` or `require-human`: an action that slips past the reversible
allow-list, a destructive verb that isn't caught, budget arithmetic that reads as
healthy when the budget is exhausted, or an environment string that bypasses the
production gate.

A wrong `allow` here means automation acts unattended during an incident it should
have escalated, so those reports are treated as security issues rather than bugs.
