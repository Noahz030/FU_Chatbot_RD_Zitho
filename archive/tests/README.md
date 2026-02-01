# Test & Diagnostic Files Archive

**Archived:** February 1, 2026  
**Reason:** Root directory cleanup - consolidating test and diagnostic utilities

## Contents

### Diagnostic Scripts (2 files)
- `diagnostic_qdrant.py` (1.7K) - Qdrant connection test
  - Tests Qdrant Cloud connection
  - Lists all collections and vector counts
  - Checks `web_assistant` collection configuration
  - Usage: `python diagnostic_qdrant.py` (requires PROD_QDRANT_URL, PROD_QDRANT_API_KEY)

- `diagnostic_retriever.py` (793B) - Retriever initialization test
  - Tests VectorDBQdrant import and instantiation
  - Validates collection name configuration
  - Usage: `python diagnostic_retriever.py`

### Test Files (4 files)
- `test_phase2_security.sh` (8.1K) - Arena security and rate limiting tests
  - Tests CSRF token validation
  - Tests rate limiting (10 requests/burst)
  - Tests input validation (max 2000 chars)
  - Tests vote enum validation
  - Requires running Arena API at $API_URL

- `test_subset.html` (7.4K) - Arena subset frontend test
  - HTML UI for testing Arena question subsets
  - Interactive buttons for subset selection
  - Uses fetch API to test /arena/generate endpoint
  - Open in browser and point to localhost:8001

- `test_validation.py` (5.3K) - Input validation test suite
  - Tests valid question generation
  - Tests question length limits (>2000 chars)
  - Tests invalid vote enum values
  - Tests missing required fields
  - Usage: `python test_validation.py` (requires Arena API on localhost:8001)

- `fresh_test_questions.txt` (685B) - 10 test questions
  - German language learning-related questions
  - Used for Arena testing and evaluation
  - Topics: online learning, motivation, study strategies

## Retrieval

These files can be copied back to the root directory if needed for debugging or testing:

```bash
# Copy specific diagnostic script
cp archive/tests/diagnostic_qdrant.py .

# Copy all test files
cp archive/tests/test_*.* .
```

## Notes

- All tests assume Arena API running on localhost:8001
- Diagnostic scripts require production Qdrant credentials
- Test scripts are compatible with current Arena architecture (post-rename from openwebui)
- HTML test file can be served via `python -m http.server 8080`

## Related

- Active tests: [src/tests/](../../src/tests/) - Unit and integration tests
- Arena documentation: [docs/VOTING.md](../../docs/VOTING.md)
- Security testing: See [docs/DEPLOYMENT_COMPLETE.md](../../docs/DEPLOYMENT_COMPLETE.md) for production security checklist
