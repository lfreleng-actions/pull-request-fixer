#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

# Demo script for pull-request-fixer
# Shows the tool's capabilities for fixing PRs via GitHub integration

set -e

echo "🛠️  Pull Request Fixer Demo"
echo "============================"
echo ""

# Check if tool is installed
if ! command -v pull-request-fixer &> /dev/null; then
    echo "❌ pull-request-fixer is not installed"
    echo "   Install it with: uv tool install ."
    exit 1
fi

echo "✅ pull-request-fixer is installed"
echo ""

# Check if GITHUB_TOKEN is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN environment variable is not set"
    echo "   Set it with: export GITHUB_TOKEN=your_token_here"
    exit 1
fi

echo "✅ GITHUB_TOKEN is configured"
echo ""

echo "This tool fixes pull request titles, descriptions and files, for one"
echo "pull request or across a GitHub organization. By default it only acts"
echo "on blocked pull requests (conflicts, behind base, or failing checks)."
echo ""
echo "Usage examples:"
echo ""
echo "1. Preview a title fix for a specific PR:"
echo "   pull-request-fixer https://github.com/owner/repo/pull/123 --fix-title --dry-run"
echo ""
echo "2. Scan an organization and preview title and description fixes:"
echo "   pull-request-fixer ORG_NAME --fix-title --fix-body --dry-run"
echo ""
echo "3. Fix titles across an organization:"
echo "   pull-request-fixer ORG_NAME --fix-title"
echo ""
echo "4. Preview a regex fix to a file in a PR:"
echo "   pull-request-fixer https://github.com/owner/repo/pull/123 --fix-files \\"
echo "     --file-pattern '^\./README\.md\$' --search-pattern 'teh' --replacement 'the' \\"
echo "     --dry-run --show-diff"
echo ""
echo "For more information, run: pull-request-fixer --help"
echo ""
echo "Demo complete! 🎉"
