# OSS Hygiene

This repo must be deployable by anyone with **config-only changes — no code edits**.
Company-specific values never belong in source, default config, tests, or docs.

## The rule
- No employer/company names, no internal hostnames, no real cloud account IDs,
  no personal emails anywhere in tracked files.
- Use generic placeholders only.

## Pattern library
| Instead of | Use |
| --- | --- |
| any real employer/company name | `acme-corp`, `your-org`, `customer-xyz` |
| any personal/work email | `alice.dev@example.com`, `sre-oncall@example.com` |
| any real internal hostname | `db01.prod.internal`, `api.cluster.corp` |
| any real cloud account id | `123456789012`, `111122223333` |

## CI
`.github/workflows/oss-hygiene.yml` greps tracked files for configured patterns and
fails the build on a match. **Set your own past-employer / domain patterns in that
workflow's `EMPLOYER_PATTERNS` / `EMAIL_PATTERNS` (kept generic in this public repo).**

## When the author changes jobs
Update the workflow's pattern list (keep prior employers in it) and this doc's date.
