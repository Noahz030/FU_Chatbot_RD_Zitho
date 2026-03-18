#!/usr/bin/env python3
"""
Quick Matrix Testing Protocol
==============================
Simplified version: runs load tests directly with human-like prefetch profiles
for u2, u3, u4 (realistic user counts) with multiple repetitions.

Skips config deployment automation and focuses on gathering performance data.
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path(__file__).parent.parent
RESULTS_DIR = Path(__file__).parent / "loadtest_results"

# Realistic user profiles (human-like prefetch)
PROFILES = {
    "u2": {
        "users": 8,
        "rounds": 3,
        "stagger": 2,
        "think": 3,
        "description": "Light load: 8 users × 3 rounds",
    },
    "u3": {
        "users": 12,
        "rounds": 3,
        "stagger": 2,
        "think": 3,
        "description": "Medium load: 12 users × 3 rounds",
    },
    "u4": {
        "users": 16,
        "rounds": 3,
        "stagger": 2,
        "think": 3,
        "description": "Heavy load: 16 users × 3 rounds",
    },
}

def run_test(profile_key: str, repetition: int) -> bool:
    """Run one load test with human-like prefetch profile."""
    profile = PROFILES[profile_key]
    label = f"baseline-{profile_key}-rep{repetition}"
    config_str = f"Baseline config A (c4/a45/p42) | {profile['description']}"
    
    cmd = [
        sys.executable,
        str(WORKSPACE / "exploration" / "progressive_load_test.py"),
        "--profile", "human-like-prefetch",
        "--label", label,
        "--config", config_str,
        "--human-users", str(profile["users"]),
        "--human-rounds", str(profile["rounds"]),
        "--human-stagger", str(profile["stagger"]),
        "--human-think", str(profile["think"]),
    ]
    
    print(f"\n[Test] {profile_key} × rep{repetition}")
    print(f"  Label: {label}")
    print(f"  Users: {profile['users']}, Rounds: {profile['rounds']}")
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode == 0

def main():
    """Run quick matrix of realistic load profiles with repetitions."""
    print("\n" + "="*80)
    print("QUICK MATRIX TEST: Baseline Config with Realistic Load Profiles")
    print("="*80)
    print(f"Start: {datetime.now(timezone.utc).isoformat()}\n")
    
    results = {profile: [] for profile in PROFILES}
    
    # Run 3 reps for each profile
    for profile_key in ["u2", "u3", "u4"]:
        print(f"\n" + "="*80)
        print(f"PROFILE: {profile_key} ({PROFILES[profile_key]['description']})")
        print("="*80)
        
        for rep in range(1, 4):
            success = run_test(profile_key, rep)
            results[profile_key].append(success)
            
            if rep < 3:
                print(f"  Waiting before next repetition...")
                import time
                time.sleep(5)  # Wait between reps
        
        # Wait between profiles
        if profile_key != "u4":
            print(f"\n  Cooling down between profiles...")
            import time
            time.sleep(10)
    
    print(f"\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for profile_key, profile_results in results.items():
        success_count = sum(profile_results)
        print(f"\n{profile_key}: {success_count}/3 successful")
        print(f"  {PROFILES[profile_key]['description']}")
    
    print(f"\nEnd: {datetime.now(timezone.utc).isoformat()}")
    print(f"Results logged to: {RESULTS_DIR}/summary.csv")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
