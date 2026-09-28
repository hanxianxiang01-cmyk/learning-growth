#!/usr/bin/env bash
set -euo pipefail

git init
git branch -M main
git add .
git commit -m "chore: establish Git-ready baseline at child-web v$(cat VERSION)"

echo
echo "Git repository initialized."
echo "Next:"
echo "  1. Create remote repository"
echo "  2. git remote add origin <URL>"
echo "  3. git push -u origin main"
echo "  4. Configure branch protection per docs/governance/GITHUB_SETUP.md"
