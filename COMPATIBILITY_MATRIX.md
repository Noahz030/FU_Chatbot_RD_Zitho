# Compatibility Matrix: Arena + Chatbot Versions

## Overview

Diese Matrix zeigt die Kompatibilität zwischen Arena-Versionen und Chatbot-Versionen vom original Repository.

## Version Mapping

| Arena Version | Chatbot Version | Status | Notes | Tested |
|---------------|-----------------|--------|-------|--------|
| **v0.1** (current) | v1 (original) | ✅ Stable | 10-message context | ✅ 9 Jan 2026 |
| **v0.1** (current) | v1-improved | ✅ Stable | 15-message context | ✅ 9 Jan 2026 |
| **v0.1** (current) | v2 | 🔄 Testing | New version (Jan 2026) | ❌ Pending |
| **v0.2** (planned) | v1-v2 | 📋 Planned | Multi-version support | ❌ Future |

## Chatbot Version Details

### KI-Campus v1 (Original)

```
Repository: upstream/main (at da5d553)
File: src/llm/assistant.py
Class: KICampusAssistant
Context Window: 10 messages
Model: GPT-4
Release Date: Original (baseline)
Status: Production
Arena Integration: ✅ Full support
```

**Known Issues:** None identified

**Last Tested:** 9 Jan 2026 (local deployment successful)

### KI-Campus v1-Improved

```
Repository: this repository (feature/openwebui-arena)
File: src/llm/assistant_improved.py
Class: KICampusAssistantImproved
Context Window: 15 messages
Model: GPT-4
Release Date: ~June 2025
Status: Production
Arena Integration: ✅ Full support
```

**Improvements over v1:**
- Extended context window (10 → 15 messages)
- Better long-form conversation support

**Known Issues:** None identified

**Last Tested:** 9 Jan 2026 (local deployment successful)

### KI-Campus v2 (Planned)

```
Repository: upstream (TBD)
File: src/llm/assistant_v2.py (expected)
Class: KICampusAssistantV2 (expected)
Context Window: 20 messages (expected)
Model: GPT-4 (expected)
Release Date: TBD
Status: In Development
Arena Integration: ⚠️ Requires testing
```

**Expected Changes:**
- Larger context window (20 messages)
- Improved reasoning capabilities
- New RAG features (pending verification)

**Compatibility Concerns:**
- [ ] RAG pipeline compatibility check needed
- [ ] New dependencies evaluation
- [ ] Performance baseline required
- [ ] Health check verification needed

**Testing Status:** Pending

## Dependency Compatibility

### Python & Core Framework

| Component | v1 | v1-improved | v2 | Notes |
|-----------|----|-----------|----|-------|
| Python | 3.11 | 3.11 | 3.11 (expected) | Pin to 3.11.x |
| FastAPI | 0.109.0 | 0.109.0 | TBD | Monitor for breaking changes |
| Pydantic | 2.5.3 | 2.5.3 | TBD | v2 API stable |

### LLM & RAG Stack

| Component | v1 | v1-improved | v2 | Status |
|-----------|----|-----------|----|--------|
| llama-index | 0.10.68 | 0.10.68 | TBD | Monitor breaking changes |
| OpenAI SDK | ~1.51.0 | ~1.51.0 | TBD | Azure OpenAI compatible |
| Qdrant | 1.10.1 | 1.10.1 | TBD | Vector DB stable |
| Azure OpenAI | ✅ | ✅ | ✅ (expected) | Primary backend |

## API Contract Compatibility

### Input Compatibility

```python
# ChatCompletionRequest structure (OpenAI compatible)
class ChatCompletionRequest(BaseModel):
    model: str              # e.g., "kicampus-v1"
    messages: list          # Chat history
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
```

**Status:** All v1, v1-improved, and v2 (expected) support this contract ✅

### Output Compatibility

```python
# ChatCompletionResponse structure
class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "text_completion"
    created: int
    model: str
    choices: list[Choice]
    usage: CompletionUsage
```

**Status:** Consistent across versions ✅

### Arena-Specific Endpoints

| Endpoint | v1 | v1-improved | v2 | Notes |
|----------|----|-----------|----|-------|
| `/arena/save-comparison` | ✅ | ✅ | ✅ (expected) | Version-agnostic |
| `/arena/submit-vote` | ✅ | ✅ | ✅ (expected) | Stores version in metadata |
| `/arena/statistics` | ✅ | ✅ | ✅ (expected) | Filters by version |
| `/arena/list-comparisons` | ✅ | ✅ | ✅ (expected) | Includes version info |

## Known Issues & Workarounds

### Issue #1: Context Window Differences
- **Problem:** v1 uses 10 messages, v1-improved uses 15
- **Impact:** Same query might have different context
- **Status:** ✅ Expected behavior, Arena tracks this
- **Workaround:** Vote data tagged with version

### Issue #2: Model Parameter Differences
- **Problem:** Different context window sizes
- **Impact:** Responses may differ in length/depth
- **Status:** ✅ Expected, tests pass
- **Workaround:** Compare only same-version models for fairness

### Issue #3: Upstream Breaking Changes (v2)
- **Problem:** New version might require API changes
- **Impact:** Arena integration might break
- **Status:** 🔄 To be verified
- **Workaround:** Use model registry pattern (see CHATBOT_VERSIONING.md)

## Testing Procedures

### Test Case: New Version Integration

```bash
# 1. Fetch latest from upstream
git fetch upstream

# 2. Check changes
git diff origin/main upstream/main -- src/llm/

# 3. Merge if compatible
git checkout feature/openwebui-arena
git merge upstream/main

# 4. Update config/models.yaml with new version
# Add entry for kicampus-v2

# 5. Enable in Arena (disable in production until ready)
# Uncomment in arena.enabled_models

# 6. Run full test
./scripts/test-deployment.sh --clean

# 7. Verify specific version
curl -k https://localhost/v1/models | grep v2
curl -k https://localhost/arena/statistics

# 8. Run voting tests
# See ARENA_IMPLEMENTATION.md test section
```

### Test Case: Multi-Version Voting

```bash
# Start local deployment
./scripts/test-deployment.sh --clean

# Generate comparison with v1
curl -X POST https://localhost/arena/save-comparison \
  -k -H "Content-Type: application/json" \
  -d '{
    "model_a": "kicampus-v1",
    "model_b": "kicampus-v2",
    "query": "Explain AI ethics"
  }'

# Check that vote data includes version info
curl -k https://localhost/arena/statistics | python3 -m json.tool

# Verify version in comparison data
curl -k https://localhost/arena/list-comparisons | python3 -m json.tool
```

## Upgrade Path

### From v0.1 → v0.2 (When v2 is ready)

```
1. Merge upstream/main with v2
2. Update config/models.yaml
3. Enable v2 in arena.enabled_models
4. Run full test suite
5. Deploy to staging
6. Run voting tests
7. Deploy to production
```

**Timeline:** TBD (depends on upstream v2 release)

## Rollback Procedures

### If New Version Breaks Arena

```bash
# Option 1: Disable in config
# Edit config/models.yaml, remove from arena.enabled_models
git add config/models.yaml
git commit -m "Disable v2 due to compatibility issues"

# Option 2: Revert merge
git revert -m 1 <merge-commit>

# Option 3: Create hotfix
git checkout -b hotfix/arena-v2-compat
# Fix compatibility
git push origin hotfix/arena-v2-compat
```

## Maintenance Schedule

| Task | Frequency | Owner | Status |
|------|-----------|-------|--------|
| Check upstream updates | Weekly | Team | 🔄 |
| Dependency updates | Monthly | Team | 🔄 |
| Compatibility testing | Per release | Team | 🔄 |
| Matrix updates | Per version | Team | 🔄 |

## References

- [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - Git synchronization procedures
- [CHATBOT_VERSIONING.md](CHATBOT_VERSIONING.md) - Version management system
- [ARENA_IMPLEMENTATION.md](ARENA_IMPLEMENTATION.md) - Arena implementation details
- Upstream: https://github.com/KI-Campus/FU_Chatbot

## Contact & Questions

For compatibility issues:
1. Check this matrix first
2. Review CHATBOT_VERSIONING.md
3. Check upstream repository for breaking changes
4. Run diagnostic tests (see ARENA_IMPLEMENTATION.md)
