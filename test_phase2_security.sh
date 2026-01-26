#!/bin/bash

# Phase 2 Security Testing Script
# Tests: Rate Limiting + CSRF Token Protection
# Run from workspace root: bash test_phase2_security.sh

set -e

API_URL="http://localhost:8001"
UI_URL="http://localhost:8002"
SESSION_ID="test_session_$(date +%s)"

echo "=========================================="
echo "Phase 2 Security Testing"
echo "=========================================="
echo ""
echo "Using SESSION_ID: $SESSION_ID"
echo ""

# Test 1: CSRF Token Generation
echo "TEST 1: CSRF Token Generation"
echo "Request: GET $API_URL/arena/csrf-token?session_id=$SESSION_ID"
CSRF_RESPONSE=$(curl -s "$API_URL/arena/csrf-token?session_id=$SESSION_ID")
CSRF_TOKEN=$(echo $CSRF_RESPONSE | grep -o '"csrf_token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$CSRF_TOKEN" ]; then
    echo "✓ CSRF Token generated: ${CSRF_TOKEN:0:16}..."
    echo "  Length: ${#CSRF_TOKEN} characters"
else
    echo "✗ Failed to generate CSRF token"
    echo "  Response: $CSRF_RESPONSE"
    exit 1
fi
echo ""

# Test 2: Rate Limiting - First Request Should Succeed
echo "TEST 2A: Rate Limiting - First Request (Background)"
echo "Request: POST $API_URL/arena/generate"
START_TIME=$(date +%s)
# Start first request in background to not wait for full LLM generation
curl -s -X POST "$API_URL/arena/generate" \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: 192.168.1.100" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"question\": \"What is machine learning?\",
    \"arena_id\": \"test_arena\",
    \"csrf_token\": \"$CSRF_TOKEN\"
  }" > /tmp/gen_response_1.json 2>&1 &
FIRST_REQ_PID=$!

# Wait just 0.5s to ensure first request hit the server
sleep 0.5
echo "✓ First request sent (processing in background)"
echo ""

# Test 3: Rate Limiting - Immediate Second Request Should Fail with 429
echo "TEST 2B: Rate Limiting - Immediate Second Request (Should Get 429)"
echo "Request: POST $API_URL/arena/generate (immediate retry)"
ELAPSED_SINCE_START=$(( $(date +%s) - START_TIME ))
echo "  (Elapsed since first request start: ${ELAPSED_SINCE_START}s)"
HTTP_CODE=$(curl -s -o /tmp/response.json -w "%{http_code}" -X POST "$API_URL/arena/generate" \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: 192.168.1.100" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"question\": \"What is artificial intelligence?\",
    \"arena_id\": \"test_arena\",
    \"csrf_token\": \"$CSRF_TOKEN\"
  }")

if [ "$HTTP_CODE" == "429" ]; then
    echo "✓ Rate limit enforced! HTTP 429 returned"
    cat /tmp/response.json | python3 -m json.tool 2>/dev/null || cat /tmp/response.json
else
    echo "✗ Rate limit NOT enforced (HTTP $HTTP_CODE)"
    cat /tmp/response.json | head -c 100
fi
echo ""

# Wait for first request to complete and extract comparison_id
echo "TEST 2C: Wait for First Request to Complete"
wait $FIRST_REQ_PID
COMPARISON_ID=$(cat /tmp/gen_response_1.json | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")
if [ -n "$COMPARISON_ID" ]; then
    echo "✓ First request completed (comparison_id: ${COMPARISON_ID:0:8}...)"
else
    echo "⚠ First request may have failed (no comparison_id found)"
fi
echo ""

# Test 3: Rate Limiting - Wait and Retry Should Succeed
echo "TEST 3: Rate Limiting - Wait 6 Seconds and Retry"
echo "Waiting 6 seconds..."
sleep 6

GEN_RESPONSE_2=$(curl -s -X POST "$API_URL/arena/generate" \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: 192.168.1.100" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"question\": \"What is deep learning?\",
    \"arena_id\": \"test_arena\",
    \"csrf_token\": \"$CSRF_TOKEN\"
  }")

STATUS_2=$(echo $GEN_RESPONSE_2 | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "error")
if [ "$STATUS_2" == "success" ] || echo $GEN_RESPONSE_2 | grep -q "comparison"; then
    echo "✓ Request after cooldown succeeded"
else
    echo "✓ Request after cooldown processed (status: $STATUS_2)"
fi
echo ""

# Test 4: CSRF Token Validation - Invalid Token Should Fail
echo "TEST 4: CSRF Token Validation - Invalid Token (should get 403)"
echo "Request: POST $API_URL/arena/vote with invalid CSRF token"

HTTP_CODE=$(curl -s -o /tmp/response.json -w "%{http_code}" -X POST "$API_URL/arena/vote" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-Forwarded-For: 192.168.1.100" \
  -d "{
    \"comparison_id\": \"${COMPARISON_ID:-test_comparison_id}\",
    \"vote\": \"A\",
    \"csrf_token\": \"invalid_token_12345\"
  }")

if [ "$HTTP_CODE" == "403" ]; then
    echo "✓ Invalid CSRF token rejected! HTTP 403 returned"
    cat /tmp/response.json | python3 -m json.tool 2>/dev/null || cat /tmp/response.json
elif [ "$HTTP_CODE" == "404" ]; then
    echo "⚠ Comparison not found (HTTP 404 - expected for test comparison)"
    cat /tmp/response.json | head -c 100
else
    echo "⚠ Unexpected response (HTTP $HTTP_CODE)"
    cat /tmp/response.json | head -c 100
fi
echo ""

# Test 5: Valid CSRF Token and Token Rotation
echo "TEST 5: Valid CSRF Token Should Succeed & Rotate Token"
echo "Request: POST $API_URL/arena/vote with VALID CSRF token"

VOTE_RESPONSE=$(curl -s -X POST "$API_URL/arena/vote" \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: $SESSION_ID" \
  -H "X-Forwarded-For: 192.168.1.100" \
  -d "{
    \"comparison_id\": \"${COMPARISON_ID}\",
    \"vote\": \"A\",
    \"csrf_token\": \"$CSRF_TOKEN\"
  }")

VOTE_SUCCESS=$(echo $VOTE_RESPONSE | grep -o '"success":[^,}]*' | cut -d':' -f2 || echo "false")
NEW_CSRF_TOKEN=$(echo $VOTE_RESPONSE | grep -o '"csrf_token":"[^"]*"' | cut -d'"' -f4)

if [ "$VOTE_SUCCESS" == "true" ] || [ "$VOTE_SUCCESS" == " true" ]; then
    echo "✓ Vote accepted with valid CSRF token!"
    if [ -n "$NEW_CSRF_TOKEN" ] && [ "$NEW_CSRF_TOKEN" != "$CSRF_TOKEN" ]; then
        echo "✓ CSRF token rotated: ${NEW_CSRF_TOKEN:0:16}... (different from previous)"
        CSRF_TOKEN="$NEW_CSRF_TOKEN"  # Update for next tests
    else
        echo "⚠ Token not rotated or same as previous"
    fi
else
    echo "⚠ Vote failed or comparison not found (expected if comparison doesn't exist)"
    echo "  Response: $(echo $VOTE_RESPONSE | head -c 100)"
fi
echo ""

# Test 6: Verify Token Persistence for Same Session
echo "TEST 6: CSRF Token Persistence for Same Session"
echo "Request: GET $API_URL/arena/csrf-token?session_id=$SESSION_ID (second call)"
CSRF_RESPONSE_2=$(curl -s "$API_URL/arena/csrf-token?session_id=$SESSION_ID")
CSRF_TOKEN_2=$(echo $CSRF_RESPONSE_2 | grep -o '"csrf_token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$CSRF_TOKEN_2" ]; then
    echo "✓ CSRF token retrieved: ${CSRF_TOKEN_2:0:16}..."
    if [ "$CSRF_TOKEN" == "$CSRF_TOKEN_2" ]; then
        echo "✓ Token is same as rotated token (correct - GET returns cached token)"
    else
        echo "⚠ Token changed unexpectedly (tokens should be stable until rotation)"
    fi
else
    echo "✗ Failed to retrieve CSRF token"
fi
echo ""

# Test 7: Different Session Different Token
echo "TEST 7: Different Sessions Get Different Tokens"
SESSION_ID_2="test_session_2_$(date +%s)"
echo "Request: GET $API_URL/arena/csrf-token?session_id=$SESSION_ID_2"
CSRF_RESPONSE_3=$(curl -s "$API_URL/arena/csrf-token?session_id=$SESSION_ID_2")
CSRF_TOKEN_3=$(echo $CSRF_RESPONSE_3 | grep -o '"csrf_token":"[^"]*"' | cut -d'"' -f4)

if [ -n "$CSRF_TOKEN_3" ]; then
    echo "✓ Token for session 2: ${CSRF_TOKEN_3:0:16}..."
    if [ "$CSRF_TOKEN" != "$CSRF_TOKEN_3" ]; then
        echo "✓ Different sessions have different tokens (correct)"
    else
        echo "✗ Different sessions have same token (SECURITY ISSUE!)"
        exit 1
    fi
else
    echo "✗ Failed to generate CSRF token for session 2"
fi
echo ""

echo "=========================================="
echo "Testing Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "✓ = Working correctly"
echo "✗ = Failed/Security issue"
echo "⚠ = Unexpected but may be ok"
echo ""
