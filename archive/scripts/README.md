# Archived: scripts/ - Obsolete Deployment & Utility Scripts

## Archive Date
February 1, 2026

## Why Archived

These scripts were part of earlier Arena development phases but have been superseded by the current on-demand generation architecture and refined deployment pipelines.

## Contents

### Arena Seeding Scripts (OBSOLETE - On-Demand Generation Now Used)

**`arena_seed_external.py`** (4.0 KB)
- Purpose: Seed Arena with pre-generated comparisons between v1 and v1-improved
- Status: Obsolete - Current architecture generates answers on-demand via API
- Reference: `src/arena/openwebui_api_llm.py` handles generation now

**`arena_seed_with_llm.py`** (9.3 KB)
- Purpose: LLM-based seeding from CSV/JSON input files
- Status: Obsolete - Replaced by on-demand API generation
- Reference: `POST /arena/comparison` endpoint generates answers dynamically

**`create_real_answers.py`** (20 KB)
- Purpose: Replace dummy answers with hardcoded Q&A pairs
- Status: Obsolete - Hardcoded pairs not maintainable; not used in current system
- Reference: Not referenced anywhere in production

**`migrate_subset_ids.py`** (1.9 KB)
- Purpose: One-time migration to assign subset_id (1-4) to existing comparisons
- Status: Legacy - Migration completed January 9, 2025
- Reference: Not reusable; already executed

### Deployment Scripts (SUPERSEDED)

**`deploy.sh`** (6.9 KB)
- Purpose: Local/basic deployment (older version)
- Status: Superseded by `deploy-production.sh` (Jan 9 update)
- Reason: New version has better error handling, logging, health checks

**`test-deployment.sh`** (6.3 KB)
- Purpose: Test suite for deployment
- Status: Not used - Testing handled via docker-compose
- Reason: No references in current CI/CD, docker-compose handles orchestration

### SSL/Certificate Scripts (SUPERSEDED)

**`init-ssl.sh.old`** (5.7 KB)
- Purpose: Old SSL certificate initialization
- Status: Superseded by `init-ssl.sh` (Jan 9 update)
- Reason: New version has better domain handling and error messages

### Monitoring Scripts (DUPLICATE)

**`health-check.sh`** (3.4 KB)
- Purpose: Basic service health checking
- Status: Superseded by `healthcheck.sh`
- Reason: `healthcheck.sh` is more comprehensive with alert integration and logging

## Current Architecture

### On-Demand Generation
The Arena now uses **on-demand answer generation** instead of pre-seeding:

1. User visits Arena UI
2. `/arena/assign-subset` assigns them a subset via round-robin (subset with fewest votes)
3. User selects question
4. `POST /arena/comparison?question=...` generates answers on-demand
5. Both answers generated, cached in `arena_votes.jsonl` with `is_generated_on_demand=True`

### Fixed Question Set
- **Source:** `src/arena/arena_questions.py`
- **Total:** 60 questions (same set used for Ragas evaluation)
- **Organization:** 4 subsets × 15 questions each
- **Assignment:** Round-robin by vote count (new users get subset with fewest votes)

### Active Scripts (Kept)
- ✅ `setup-env.sh` - Environment configuration
- ✅ `gen-secrets.sh` - Secure secret generation
- ✅ `gen-local-certs.sh` - Local SSL certs for testing
- ✅ `init-ssl.sh` - Production Let's Encrypt certs
- ✅ `backup.sh` - Backup with retention
- ✅ `healthcheck.sh` - Advanced monitoring with alerting
- ✅ `deploy-production.sh` - Production deployment orchestration
- ✅ `sample_questions.csv` - Reference question examples

## Recovery

All archived scripts are recoverable from Git:

```bash
# View previous version
git show HEAD~N:scripts/arena_seed_with_llm.py

# Restore if needed
git checkout HEAD~N -- scripts/arena_seed_with_llm.py
```

## Decision Rationale

- **Seeding scripts:** Replaced by `is_generated_on_demand` flag + API endpoint
- **Old deployment:** Consolidated into single `deploy-production.sh` with better error handling
- **Old SSL:** Improved in new `init-ssl.sh` with better domain support
- **Basic health-check:** Superseded by feature-richer `healthcheck.sh`

These consolidations keep the `scripts/` directory focused on **actively maintained, production-ready utilities**.
