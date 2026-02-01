# 📦 Archived: Exploration R&D Folder

This folder contains archived research and development (R&D) notebooks and data that are no longer actively used in the Arena Voting System.

## Why This Was Archived (February 2026)

The `exploration/` folder originally served as an R&D workspace for:
- Evaluating LLM models and deployment options
- Exploring Moodle API data structures  
- Testing RAG retrieval techniques
- Analyzing course content types

**However**, it became obsolete because:

1. **Not Used in Production**: No code in `src/` or `tests/` imports or references these notebooks
2. **Outdated Technology Choices**:
   - LLM evaluation (Llama2, Mistral 7B) → System now uses Azure OpenAI GPT-4
   - Google Vertex AI deployment → System uses Azure infrastructure
   - Self-querying retrieval → System uses Qdrant Vector DB + Direct Search
3. **Historical Reference Only**: Git history preserves all changes for reference if needed

## Contents

### Jupyter Notebooks (R&D Experiments)

| Notebook | Purpose | Status |
|----------|---------|--------|
| **course-contents.ipynb** | Cataloging Moodle content types | Outdated reference |
| **data.ipynb** | Analyzing API data formats | Outdated reference |
| **llm.ipynb** | Evaluating LLM models (Llama2, Mistral) | ❌ Not used |
| **self-querying.ipynb** | LangChain self-querying experiment | ❌ Not used |
| **vertexai.ipynb** | Google Vertex AI deployment | ❌ Not used |

### Sample Data

**`data/api-examples/`** (264 KB)
- Sample Moodle/Moochup API responses
- Used for understanding data structures (historical reference)
- Can be recovered from Git if needed for debugging

## How to Recover Files

If you need to recover or review any of these files:

```bash
# View in git history
git show HEAD:exploration/llm.ipynb

# Restore a specific file
git checkout HEAD -- archive/exploration/llm.ipynb

# Browse in VS Code
# Open: archive/exploration/
```

## Migration Notes

- **Archival Date**: February 1, 2026
- **Reason**: Repository cleanup - removing unused R&D code
- **Impact**: No impact on production code (was never imported)
- **Size Freed**: ~428 KB (cleaned from root exploration/)
- **Git History**: All history preserved - 100% recoverable

## What Replaced These?

| Old Approach | Current Solution |
|--------------|------------------|
| LLM evaluation (Llama2, Mistral) | Azure OpenAI GPT-4 (configured in `.env`) |
| Vertex AI deployment | Azure Container Instances + Docker |
| Self-querying retrieval | Qdrant Vector DB + HTTPProxyAssistant |
| Manual data analysis | Automated loaders in `src/loaders/` |

## Related Documentation

- **Data Loading**: See [`src/loaders/`](../../src/loaders/) for current data integration
- **LLM Configuration**: See [ENVIRONMENT.md](../../docs/ENVIRONMENT.md) for model setup
- **Architecture**: See [ARCHITECTURE.md](../../docs/ARCHITECTURE.md) for current system design
- **RAG System**: See [VOTING.md](../../docs/VOTING.md) for current retrieval implementation

## Questions?

- These notebooks are **not meant to be used** - they're historical reference
- If you need the original exploration work: check Git history
- To understand current system: refer to documentation in `docs/` folder
- For API structure details: see sample responses in `data/api-examples/`

---

**Status**: ✅ Archived  
**Can be restored**: Yes, from Git  
**Recommended action**: Delete if not needed within 6 months  
**Last updated**: February 1, 2026
