#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024 Linux Foundation
# SPDX-License-Identifier: Apache-2.0
"""Test script to verify PR blocking logic matches between pull-request-fixer and dependamerge."""

import asyncio
import sys
from pathlib import Path


# Add both projects to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "dependamerge" / "src"))


async def test_pr_blocking_logic() -> bool:
    """Test that both tools identify the same PRs as blocked."""

    # Sample PR data structures matching GraphQL responses
    test_cases = [
        {
            "name": "PR with merge conflicts",
            "pr_data": {
                "number": 1,
                "title": "Test PR with conflicts",
                "mergeable": "CONFLICTING",
                "mergeStateStatus": "dirty",
                "isDraft": False,
                "author": {"login": "testuser"},
                "commits": {
                    "nodes": [
                        {
                            "commit": {
                                "statusCheckRollup": {"contexts": {"nodes": []}}
                            }
                        }
                    ]
                },
            },
            "expected_blocked": True,
            "expected_reasons": ["merge_conflict"],
        },
        {
            "name": "PR behind base branch",
            "pr_data": {
                "number": 2,
                "title": "Test PR behind base",
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "behind",
                "isDraft": False,
                "author": {"login": "testuser"},
                "commits": {
                    "nodes": [
                        {
                            "commit": {
                                "statusCheckRollup": {"contexts": {"nodes": []}}
                            }
                        }
                    ]
                },
            },
            "expected_blocked": True,
            "expected_reasons": ["behind_base"],
        },
        {
            "name": "PR with failing checks",
            "pr_data": {
                "number": 3,
                "title": "Test PR with failing checks",
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "clean",
                "isDraft": False,
                "author": {"login": "testuser"},
                "commits": {
                    "nodes": [
                        {
                            "commit": {
                                "statusCheckRollup": {
                                    "contexts": {
                                        "nodes": [
                                            {
                                                "__typename": "CheckRun",
                                                "name": "test-check",
                                                "conclusion": "failure",
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    ]
                },
            },
            "expected_blocked": True,
            "expected_reasons": ["failing_checks"],
        },
        {
            "name": "PR with multiple issues",
            "pr_data": {
                "number": 4,
                "title": "Test PR with multiple issues",
                "mergeable": "CONFLICTING",
                "mergeStateStatus": "behind",
                "isDraft": False,
                "author": {"login": "testuser"},
                "commits": {
                    "nodes": [
                        {
                            "commit": {
                                "statusCheckRollup": {
                                    "contexts": {
                                        "nodes": [
                                            {
                                                "__typename": "StatusContext",
                                                "context": "ci/test",
                                                "state": "FAILURE",
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    ]
                },
            },
            "expected_blocked": True,
            "expected_reasons": [
                "merge_conflict",
                "behind_base",
                "failing_checks",
            ],
        },
        {
            "name": "Clean PR (not blocked)",
            "pr_data": {
                "number": 5,
                "title": "Test PR clean",
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "clean",
                "isDraft": False,
                "author": {"login": "testuser"},
                "commits": {
                    "nodes": [
                        {
                            "commit": {
                                "statusCheckRollup": {"contexts": {"nodes": []}}
                            }
                        }
                    ]
                },
            },
            "expected_blocked": False,
            "expected_reasons": [],
        },
        {
            "name": "Draft PR (blocked by draft only)",
            "pr_data": {
                "number": 6,
                "title": "Test draft PR",
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "clean",
                "isDraft": True,
                "author": {"login": "testuser"},
                "commits": {
                    "nodes": [
                        {
                            "commit": {
                                "statusCheckRollup": {"contexts": {"nodes": []}}
                            }
                        }
                    ]
                },
            },
            "expected_blocked": False,  # Draft-only PRs are not counted as blocked by default
            "expected_reasons": [],
        },
        {
            "name": "Draft PR with conflicts (should be blocked)",
            "pr_data": {
                "number": 7,
                "title": "Test draft PR with conflicts",
                "mergeable": "CONFLICTING",
                "mergeStateStatus": "dirty",
                "isDraft": True,
                "author": {"login": "testuser"},
                "commits": {
                    "nodes": [
                        {
                            "commit": {
                                "statusCheckRollup": {"contexts": {"nodes": []}}
                            }
                        }
                    ]
                },
            },
            "expected_blocked": True,  # Has non-draft blocking reasons
            "expected_reasons": ["merge_conflict"],
        },
    ]

    # Import both implementations
    from typing import Any, cast

    from dependamerge.github_service import (
        GitHubService,  # type: ignore[import-untyped]
    )

    from pull_request_fixer.github_client import GitHubClient
    from pull_request_fixer.pr_scanner import PRScanner

    class StubGitHubClient:
        """Minimal stub for testing PRScanner without real GitHub access."""

    # Create instances (without real GitHub client for testing)
    pr_fixer_scanner = PRScanner(cast(GitHubClient, StubGitHubClient()))
    dependamerge_service = GitHubService(token="fake-token-for-testing")

    print("Testing PR blocking logic consistency\n")
    print("=" * 80)

    passed = 0
    failed = 0

    for test_case in test_cases:
        pr_data = cast("dict[str, Any]", test_case["pr_data"])
        print(f"\n🧪 Test: {test_case['name']}")
        print(f"   PR #{pr_data['number']}: {pr_data['title']}")

        # Test pull-request-fixer
        is_blocked_fixer, reasons_fixer = pr_fixer_scanner.is_pr_blocked(
            pr_data
        )

        # Test dependamerge (using _analyze_pr_node)
        # Note: _analyze_pr_node returns UnmergeablePR or None
        result_dependamerge = await dependamerge_service._analyze_pr_node(
            "test/repo", pr_data, include_drafts=False
        )
        is_blocked_dependamerge = result_dependamerge is not None
        reasons_dependamerge = []
        if result_dependamerge:
            reasons_dependamerge = [r.type for r in result_dependamerge.reasons]

        # Compare results
        expected_blocked = test_case["expected_blocked"]

        fixer_match = is_blocked_fixer == expected_blocked
        dependamerge_match = is_blocked_dependamerge == expected_blocked
        both_match = is_blocked_fixer == is_blocked_dependamerge

        if fixer_match and dependamerge_match and both_match:
            print(f"   ✅ PASS - Both tools agree: blocked={expected_blocked}")
            passed += 1
        else:
            print("   ❌ FAIL")
            print(f"      Expected blocked: {expected_blocked}")
            print(
                f"      pull-request-fixer: {is_blocked_fixer} (reasons: {reasons_fixer})"
            )
            print(
                f"      dependamerge: {is_blocked_dependamerge} (reasons: {reasons_dependamerge})"
            )
            failed += 1

    print("\n" + "=" * 80)
    print(
        f"\n📊 Results: {passed} passed, {failed} failed out of {len(test_cases)} tests"
    )

    if failed > 0:
        print("\n❌ Tests failed - tools are not consistent!")
        return False
    else:
        print("\n✅ All tests passed - tools are consistent!")
        return True


if __name__ == "__main__":
    success = asyncio.run(test_pr_blocking_logic())
    sys.exit(0 if success else 1)
