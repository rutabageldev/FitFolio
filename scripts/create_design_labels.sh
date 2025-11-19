#!/usr/bin/env bash
set -euo pipefail

# Creates/updates GitHub labels used by the design workflow.
# Usage: REPO=owner/repo ./scripts/create_design_labels.sh
# If REPO is not provided, the script will try to infer it from git remote origin.
# Requires: gh CLI authenticated (preferred) OR GITHUB_TOKEN with 'repo' scope.

infer_repo() {
  local url
  url="$(git config --get remote.origin.url || true)"
  if [[ -z "${url}" ]]; then
    echo ""
    return 0
  fi
  # Handle SSH: git@github.com:owner/repo.git
  if [[ "${url}" =~ ^git@github\.com:(.*)\.git$ ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  # Handle HTTPS: https://github.com/owner/repo.git or without .git
  if [[ "${url}" =~ ^https://github\.com/(.*)(\.git)?$ ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  echo ""
}

REPO="${REPO:-$(infer_repo)}"
if [[ -z "${REPO}" ]]; then
  echo "ERROR: REPO is not set and could not be inferred. Set REPO=owner/repo and retry." >&2
  exit 1
fi

declare -a NAMES=(
  "design"
  "design:foundations"
  "design:components"
  "design:patterns"
  "design:content"
  "design:flows"
  "design:a11y"
  "design:rfc"
)
declare -a COLORS=(
  "1f6feb"   # design
  "0ea5e9"   # foundations
  "22c55e"   # components
  "a78bfa"   # patterns
  "f59e0b"   # content
  "06b6d4"   # flows
  "ef4444"   # a11y
  "d946ef"   # rfc
)
declare -a DESCS=(
  "Design-related changes"
  "Design foundations (tokens, typography, spacing, etc.)"
  "Component specs and implementation"
  "Cross-component UX patterns"
  "Copy, voice & tone, microcopy"
  "User journeys and IA"
  "Accessibility work"
  "Design request for comments"
)

use_gh="false"
if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then
    use_gh="true"
  fi
fi

echo "Creating/updating labels in ${REPO} ..."
for i in "${!NAMES[@]}"; do
  name="${NAMES[$i]}"
  color="${COLORS[$i]}"
  desc="${DESCS[$i]}"
  if [[ "${use_gh}" == "true" ]]; then
    # --force updates if it exists
    gh label create "${name}" --color "${color}" --description "${desc}" --repo "${REPO}" --force >/dev/null 2>&1 || true
    echo "✓ ${name}"
  else
    if [[ -z "${GITHUB_TOKEN:-}" ]]; then
      echo "ERROR: Neither gh auth nor GITHUB_TOKEN is available. Cannot create labels." >&2
      exit 1
    fi
    # Try update (PATCH), then create (POST) if not found
    api="https://api.github.com/repos/${REPO}/labels"
    # URL-encode name for PATCH path (basic: replace spaces)
    enc_name="${name// /%20}"
    patch_status=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH -H "Authorization: Bearer ${GITHUB_TOKEN}" -H "Accept: application/vnd.github+json" "${api}/${enc_name}" -d "{\"new_name\":\"${name}\",\"color\":\"${color}\",\"description\":\"${desc}\"}")
    if [[ "${patch_status}" == "200" ]]; then
      echo "✓ ${name}"
    else
      post_status=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Authorization: Bearer ${GITHUB_TOKEN}" -H "Accept: application/vnd.github+json" "${api}" -d "{\"name\":\"${name}\",\"color\":\"${color}\",\"description\":\"${desc}\"}")
      if [[ "${post_status}" == "201" || "${post_status}" == "200" ]]; then
        echo "✓ ${name}"
      else
        echo "✗ ${name} (HTTP ${post_status})"
      fi
    fi
  fi
done

echo "Done."
