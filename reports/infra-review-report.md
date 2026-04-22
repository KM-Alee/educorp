# Infra Review Report

Requested path: `/home/kali/proj/educorp/reports/infra-review-report.md`

## Summary

The repo’s infra and operability setup is generally solid: there is a single root compose file, Linux and Windows entrypoints, monitoring config, Traefik routing, and a reasonable dev startup flow.

The safest improvements are mostly cleanup and consistency fixes rather than runtime changes. The main themes are:

- minor command parity issues between `Makefile`, `make.ps1`, and startup scripts
- stale tracked backup artifacts (`*.bak`)
- documentation drift versus the actual repo layout
- a few portable-script issues and config mismatches that look accidental rather than intentional

## High-confidence minor improvements

1. **Add `build-service` to `.PHONY` in `/home/kali/proj/educorp/Makefile`.**
   - The target exists, but it is missing from the phony list.
   - This is a zero-runtime, very safe cleanup.

2. **Align seed behavior across `/home/kali/proj/educorp/Makefile`, `/home/kali/proj/educorp/make.ps1`, `/home/kali/proj/educorp/scripts/start-stack.sh`, and `/home/kali/proj/educorp/scripts/start-stack.ps1`.**
   - Current behavior is inconsistent:
     - `Makefile` `seed` runs `scripts/seed_data.py`
     - `make.ps1` `seed` runs `python -m scripts.seed` in `auth-service`
     - startup scripts run both

3. **Make wording consistent for “up” commands.**
   - `/home/kali/proj/educorp/docker-compose.yml` comments say plain `docker compose up -d` starts core infra plus gateway.
   - `/home/kali/proj/educorp/Makefile` describes `make up` as “core infrastructure only”.
   - This is documentation/help-text drift, not a runtime bug.

4. **Make `/home/kali/proj/educorp/scripts/run_e2e.sh` repo-relative instead of hard-coding `/home/kali/proj/educorp`.**
   - Hard-coded absolute paths are brittle and look machine-specific.

5. **Add `*.bak` to `/home/kali/proj/educorp/.gitignore` to prevent future accidental backup-file commits.**
   - This will not affect tracked files already in git, but it reduces repeat clutter.

## Suspicious inconsistencies/stale files

1. **Tracked backup artifacts likely stale**
   - `/home/kali/proj/educorp/Makefile.bak`
   - `/home/kali/proj/educorp/docker-compose.yml.bak`
   - `/home/kali/proj/educorp/scripts/start-stack.sh.bak`
   - `/home/kali/proj/educorp/infra/docker/Dockerfile.service.bak`
   - `/home/kali/proj/educorp/apps/web/Dockerfile.bak`
   - `/home/kali/proj/educorp/apps/web/src/app/router.tsx.bak`
   - `/home/kali/proj/educorp/apps/web/src/styles/components.css.bak`
   - `/home/kali/proj/educorp/apps/web/src/styles/reset.css.bak`
   - `/home/kali/proj/educorp/apps/web/src/styles/tokens.css.bak`
   - `/home/kali/proj/educorp/apps/web/src/styles/utilities.css.bak`

2. **Docs reference files that do not exist**
   - `/home/kali/proj/educorp/docs/ARCHITECTURE.md` references:
     - `scripts/seed-data.sh`
     - `scripts/run-tests.sh`
     - `docker-compose.infra.yml`
   - None of those files were present.

3. **`dev-setup` docs drift**
   - `/home/kali/proj/educorp/docs/PHASES.md` says `scripts/dev-setup.sh` creates topics.
   - Current `/home/kali/proj/educorp/scripts/dev-setup.sh` and `/home/kali/proj/educorp/scripts/dev-setup.ps1` do not create topics, run migrations, or seed data.

4. **Seed-command inconsistency across platforms/tools**
   - `/home/kali/proj/educorp/Makefile`
   - `/home/kali/proj/educorp/make.ps1`
   - `/home/kali/proj/educorp/scripts/start-stack.sh`
   - `/home/kali/proj/educorp/scripts/start-stack.ps1`

5. **Qdrant collection naming drift**
   - `/home/kali/proj/educorp/.env.example` uses `course_chunks_v2`
   - service configs also default to `course_chunks_v2`
   - `/home/kali/proj/educorp/scripts/e2e_ai_test.py` hard-codes `course_chunks`
   - local `/home/kali/proj/educorp/.env` currently also uses `course_chunks`
   - This looks like a stale test/local-config mismatch.

6. **Possibly unused Temporal init artifact**
   - `/home/kali/proj/educorp/infra/temporal/init.sh` exists
   - current compose uses inline `temporal-init` command instead
   - it may be an unused leftover

## Verification ideas

1. Before removing any stale artifacts, search for references to each candidate file:
   - especially `*.bak`, `infra/temporal/init.sh`, and missing documented files.

2. Compare command behavior across:
   - `/home/kali/proj/educorp/Makefile`
   - `/home/kali/proj/educorp/make.ps1`
   - `/home/kali/proj/educorp/scripts/start-stack.sh`
   - `/home/kali/proj/educorp/scripts/start-stack.ps1`

3. After any doc/help cleanup, verify command summaries still match actual compose behavior:
   - `make help`
   - `.\make.ps1 help`
   - compose comments in `/home/kali/proj/educorp/docker-compose.yml`

4. If Qdrant naming is normalized, verify the affected smoke/E2E scripts still target the intended collection.

## Single safest improvement recommendation

**Add `build-service` to the `.PHONY` list in `/home/kali/proj/educorp/Makefile`.**

Why this is the safest:
- it has effectively no runtime impact
- it is clearly correct because the target already exists
- it prevents edge-case make behavior if a file or directory named `build-service` ever appears
- it is much less risky than touching compose, startup sequencing, monitoring, or dependency config
