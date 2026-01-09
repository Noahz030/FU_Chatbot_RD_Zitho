# Git Workflow: Arena + Original Repository Synchronization

## Overview

Diese Repository ist ein **Fork** des original [KI-Campus/FU_Chatbot](https://github.com/KI-Campus/FU_Chatbot) mit zusätzlicher Chatbot Arena Funktionalität. Der Workflow synchronisiert Arena-Entwicklung mit Verbesserungen vom original Repository.

## Remote Configuration

```bash
origin     → https://github.com/Noahz030/FU_Chatbot_RD_Zitho.git    (Dein Fork)
upstream   → https://github.com/KI-Campus/FU_Chatbot.git             (Original)
```

**Aktueller Status (9. Jan 2026):**
- Origin main: `da5d553` (in sync mit upstream)
- Upstream main: `da5d553` (latest)
- Feature branch: `feature/openwebui-arena` (4 commits ahead)

## Branch Strategy

### 1. **main** - Production-ready code
- Synced mit upstream/main
- Only fast-forward merges from upstream
- All Arena features must be in feature branches

### 2. **feature/openwebui-arena** - Arena Integration
- Contains: voting system, model comparisons, voting UI, deployment infrastructure
- Derived from: origin/main (at time of creation)
- Status: Ready for production testing
- Does NOT modify core chatbot logic

### 3. **feature/meine-experimente** - Local Experiments
- Contains: User experiments and prototyping
- Do not merge into main without review

## Synchronization Workflow

### Step 1: Fetch Latest from Upstream

```bash
git fetch upstream
```

This retrieves:
- `upstream/main` - latest production release
- `upstream/feat/ragas-eval` - evaluation framework (optional feature)

### Step 2: Update Local main

```bash
# Checkout main branch
git checkout main

# Rebase on upstream/main (preserves linear history)
git rebase upstream/main

# Push to origin/main
git push origin main
```

### Step 3: Merge Upstream Changes into feature/openwebui-arena

```bash
git checkout feature/openwebui-arena

# Merge upstream changes (preserves Arena commits)
git merge upstream/main

# Resolve conflicts (if any)
# - Arena code should NOT conflict with core chatbot
# - If conflicts occur, check CONFLICT_RESOLUTION.md

git push origin feature/openwebui-arena
```

## Dependency Management

### Python Version
- **Target:** Python 3.11 (per pyproject.toml)
- **Constraint:** `~3.11` (allows 3.11.0 to 3.11.x)

### Critical Dependencies

| Package | Version | Purpose | Change Strategy |
|---------|---------|---------|-----------------|
| fastapi | 0.109.0 | REST API framework | Minor version updates OK |
| llama-index | 0.10.68 | RAG pipeline | Monitor breaking changes |
| openai | ~1.51.0 | Azure OpenAI client | Auto-update compatible versions |
| qdrant-client | 1.10.1 | Vector DB | Pin versions, test carefully |
| pydantic | 2.5.3 | Data validation | Monitor upstream changes |
| azure-keyvault-secrets | ~4.8.0 | Secret management | Auto-update safe |

### Dependency Update Strategy

**When upstream updates dependencies:**

1. **Check pyproject.toml** in upstream/main
2. **Compare with origin/main:**
   ```bash
   git diff upstream/main -- pyproject.toml
   ```
3. **Evaluate impact:**
   - **Safe updates:** patch versions (2.5.3 → 2.5.4)
   - **Caution needed:** minor versions (0.10.x → 0.11.x)
   - **Review carefully:** major versions (1.x → 2.x)

4. **Test in feature/openwebui-arena:**
   ```bash
   poetry update <package>
   pytest src/tests/
   docker compose -f docker-compose.local.yml up --build
   ./scripts/test-deployment.sh
   ```

## Common Workflows

### Scenario A: Pull Latest Upstream Changes

```bash
# Step 1: Ensure main is clean
git checkout main
git status

# Step 2: Fetch and rebase on upstream
git fetch upstream
git rebase upstream/main

# Step 3: Push to origin
git push origin main

# Step 4: Update feature branch
git checkout feature/openwebui-arena
git merge main
git push origin feature/openwebui-arena
```

### Scenario B: Original Repo Has Chatbot Improvements

```bash
# 1. Fetch upstream changes
git fetch upstream

# 2. Compare what changed in core chatbot
git diff main..upstream/main -- src/llm/ src/api/

# 3. Update main
git checkout main
git rebase upstream/main
git push origin main

# 4. Merge into Arena feature
git checkout feature/openwebui-arena
git merge main

# 5. Test that Arena still works with improved chatbot
./scripts/test-deployment.sh

# 6. If tests pass, push
git push origin feature/openwebui-arena

# 7. If tests fail, see COMPATIBILITY_MATRIX.md
```

### Scenario C: Create New Chatbot Version for Arena

When original repo introduces new chatbot version (e.g., v2.0):

```bash
# 1. Update feature/openwebui-arena to track upstream
git checkout feature/openwebui-arena
git merge upstream/main

# 2. Create version-specific implementation
# See VERSIONING.md for version management

# 3. Update Arena API to support new version
# See CHATBOT_VERSIONING.md

# 4. Test all versions
./scripts/test-deployment.sh

# 5. Push when verified
git push origin feature/openwebui-arena
```

## Conflict Resolution

### When Conflicts Occur

Conflicts should be **rare** because:
- Arena code is in `src/openwebui/` (isolated)
- Original chatbot code is in `src/llm/`, `src/api/` (may change)
- Arena only **depends on** chatbot APIs, doesn't modify them

### If Conflicts Happen

1. **Identify conflicting files:**
   ```bash
   git status | grep "both"
   ```

2. **Analyze conflict type:**
   - **Arena-side conflict** (src/openwebui/): Safe to resolve locally
   - **Chatbot-side conflict** (src/llm/): Needs careful review
   - **API contract conflict**: Requires version management

3. **Resolve strategy:**
   ```bash
   # Review conflict
   git diff <file>
   
   # Edit to resolve
   vim <file>
   
   # Test
   ./scripts/test-deployment.sh
   
   # Complete merge
   git add <file>
   git commit -m "Merge upstream: resolve <conflict-reason>"
   ```

## Rollback Procedures

### If Upstream Merge Breaks Arena

```bash
# Option 1: Hard reset (if not yet pushed)
git reset --hard HEAD~1

# Option 2: Revert (if already pushed)
git revert -m 1 <commit-hash>

# Option 3: Create hotfix branch
git checkout -b hotfix/arena-<issue>
# Fix issue
git push origin hotfix/arena-<issue>
# Create pull request
```

## Checking Compatibility

```bash
# 1. Verify Python version
python --version  # Should be 3.11.x

# 2. Check dependency alignment
diff -u <(poetry show) <(git show upstream/main:pyproject.toml | poetry show -)

# 3. Run test suite
pytest src/tests/

# 4. Full deployment test
./scripts/test-deployment.sh --clean

# 5. Check Arena functionality
curl -k https://localhost/arena/statistics
```

## Documentation Files

See companion documentation:
- `VERSIONING.md` - Managing multiple chatbot versions
- `COMPATIBILITY_MATRIX.md` - Version compatibility table
- `CHATBOT_VERSIONING.md` - Version-specific implementation patterns
- `DEPLOYMENT_SCRIPTS.md` - Deployment procedures
- `DEPLOYMENT_ENV.md` - Environment configuration

## Timeline & Milestones

| Date | Status | Action |
|------|--------|--------|
| **9 Jan 2026** | ✅ Complete | Git workflow + upstream remote configured |
| **TBD** | 🔄 Pending | Build versioning/abstraction system |
| **TBD** | 🔄 Pending | Implement plug-and-play model loading |
| **TBD** | 🔄 Pending | Create compatibility matrix |
| **TBD** | 🔄 Pending | Test with upstream improvements |

## Quick Reference

```bash
# Sync with upstream
git fetch upstream && git checkout main && git rebase upstream/main && git push origin main

# Update feature branch
git checkout feature/openwebui-arena && git merge main && git push origin feature/openwebui-arena

# Check status
git log --oneline -5 origin/main..upstream/main
git diff origin/main upstream/main

# Full test
docker compose -f docker-compose.local.yml down -v
./scripts/test-deployment.sh --clean
```
