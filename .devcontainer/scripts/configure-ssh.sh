set -euo pipefail

ensure_agent() {
  if [[ -f ~/.ssh/agent.env ]]; then
    # shellcheck disable=SC1090
    source ~/.ssh/agent.env >/dev/null 2>&1 || true
    ssh-add -l >/dev/null 2>&1 && return 0 || rm -f ~/.ssh/agent.env
  fi
  eval "$(ssh-agent -s)" >/dev/null
  {
    echo "export SSH_AUTH_SOCK=$SSH_AUTH_SOCK"
    echo "export SSH_AGENT_PID=$SSH_AGENT_PID"
  } > ~/.ssh/agent.env
  chmod 600 ~/.ssh/agent.env
}

ensure_base() {
  mkdir -p ~/.ssh
  chmod 700 ~/.ssh
  touch ~/.ssh/known_hosts
  ssh-keyscan -H github.com >> ~/.ssh/known_hosts 2>/dev/null || true
  cat > ~/.ssh/config <<'CFG'
Host github.com
  User git
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
CFG
  chmod 600 ~/.ssh/config ~/.ssh/known_hosts
}

maybe_make_key() {
  if [[ ! -f ~/.ssh/id_ed25519 ]]; then
    if [[ "${1:-}" == "--noninteractive" ]]; then
      ssh-keygen -t ed25519 -N "" -C "fitfolio-devcontainer" -f ~/.ssh/id_ed25519
    else
      echo "🔐 Generating ED25519 key (you'll be prompted for a passphrase)..."
      ssh-keygen -t ed25519 -C "fitfolio-devcontainer" -f ~/.ssh/id_ed25519
    fi
    chmod 600 ~/.ssh/id_ed25519 ~/.ssh/id_ed25519.pub
    echo "📎 Public key (add to GitHub → Settings → SSH and GPG keys):"
    cat ~/.ssh/id_ed25519.pub
  fi
}

maybe_add_key() {
  ensure_agent
  ssh-add -l >/dev/null 2>&1 || ssh-add ~/.ssh/id_ed25519
}

main() {
  ensure_base
  maybe_make_key "${1:-}"
  maybe_add_key
}
main "$@"
