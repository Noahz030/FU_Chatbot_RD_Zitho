#!/usr/bin/env python3
"""Test input validation and safety constraints."""

import requests
import json
import time

API_URL = "http://localhost:8001"

def test_valid_question():
    """Test 1: Valid question (within 2000 chars)"""
    print("=== Test 1: Valid question ===")
    resp = requests.post(
        f"{API_URL}/arena/generate",
        json={"question": "Was ist Maschinelles Lernen?", "session_id": "test-session-123"},
        timeout=30
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✓ Generated comparison ID: {data['id'][:20]}...")
        return data['id']
    else:
        print(f"✗ Error: {resp.json().get('detail', resp.text)}")
        return None

def test_question_too_long():
    """Test 2: Question exceeding max length (>2000 chars)"""
    print("\n=== Test 2: Question too long (>2000 chars) ===")
    resp = requests.post(
        f"{API_URL}/arena/generate",
        json={"question": "a" * 2001, "session_id": "test-session-123"}
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 422:
        print(f"✓ Correctly rejected: {resp.json().get('detail', [{}])[0].get('msg', 'validation error')}")
    else:
        print(f"✗ Expected 422, got {resp.status_code}")

def test_invalid_vote():
    """Test 3: Invalid vote enum value"""
    print("\n=== Test 3: Invalid vote enum ===")
    resp = requests.post(
        f"{API_URL}/arena/vote",
        json={"comparison_id": "test-id", "vote": "INVALID_VOTE"}
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 422:
        print(f"✓ Correctly rejected invalid vote enum")
    else:
        print(f"✗ Expected 422, got {resp.status_code}")

def test_valid_votes():
    """Test 4: Valid votes (A, B, tie, both_bad)"""
    print("\n=== Test 4: Valid votes (A, B, tie, both_bad) ===")
    # Create a comparison first
    comp_resp = requests.post(
        f"{API_URL}/arena/generate",
        json={"question": "Test question", "session_id": "test-session-124"},
        timeout=30
    )
    if comp_resp.status_code != 200:
        print(f"✗ Failed to create comparison: {comp_resp.status_code}")
        return
    
    comp_id = comp_resp.json()['id']
    print(f"Created comparison: {comp_id[:20]}...")
    
    for vote in ["A", "B", "tie", "both_bad"]:
        resp = requests.post(
            f"{API_URL}/arena/vote",
            json={"comparison_id": comp_id, "vote": vote}
        )
        success = "✓" if resp.status_code == 200 else "✗"
        print(f"  {success} Vote '{vote}': Status {resp.status_code}")
    
    return comp_id

def test_comment_too_long(comp_id):
    """Test 5: Comment exceeding max length (>1000 chars)"""
    print("\n=== Test 5: Comment too long (>1000 chars) ===")
    resp = requests.post(
        f"{API_URL}/arena/vote",
        json={"comparison_id": comp_id, "vote": "A", "comment": "x" * 1001}
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 422:
        print(f"✓ Correctly rejected long comment")
    else:
        print(f"✗ Expected 422, got {resp.status_code}")

def test_valid_comment(comp_id):
    """Test 6: Valid comment (<=1000 chars)"""
    print("\n=== Test 6: Valid comment (<=1000 chars) ===")
    resp = requests.post(
        f"{API_URL}/arena/vote",
        json={"comparison_id": comp_id, "vote": "B", "comment": "This is a valid comment"}
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print(f"✓ Successfully accepted valid comment")
    else:
        print(f"✗ Expected 200, got {resp.status_code}")

def test_session_id_too_long():
    """Test 7: Session ID too long (>100 chars)"""
    print("\n=== Test 7: Session ID too long (>100 chars) ===")
    resp = requests.post(
        f"{API_URL}/arena/generate",
        json={"question": "Test", "session_id": "s" * 101}
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 422:
        print(f"✓ Correctly rejected long session_id")
    else:
        print(f"✗ Expected 422, got {resp.status_code}")

def test_payload_size_limiting():
    """Test 8: Payload size limiting (1MB max)"""
    print("\n=== Test 8: Payload size limiting (1MB max) ===")
    # Try to send a ~2MB payload
    huge_payload = {"question": "q" * 2000000, "session_id": "s123"}
    try:
        resp = requests.post(
            f"{API_URL}/arena/generate",
            json=huge_payload,
            timeout=5
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 413:
            print(f"✓ Correctly rejected payload too large")
        else:
            print(f"Response: {resp.json().get('detail', resp.text)[:100]}")
    except requests.exceptions.Timeout:
        print("✗ Request timed out (payload might be processed)")
    except Exception as e:
        print(f"✗ Error: {str(e)[:100]}")

if __name__ == "__main__":
    print("🔒 Testing Input Validation & Safety Constraints\n")
    
    # Run tests
    comp_id = test_valid_question()
    time.sleep(0.5)
    
    test_question_too_long()
    test_invalid_vote()
    
    comp_id = test_valid_votes()
    if comp_id:
        test_comment_too_long(comp_id)
        test_valid_comment(comp_id)
    
    test_session_id_too_long()
    test_payload_size_limiting()
    
    print("\n✅ All validation tests complete!")
