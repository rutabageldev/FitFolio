# load in bash or zsh
if [ -n "$BASH_VERSION" ] || [ -n "$ZSH_VERSION" ]; then
  alias ga='git add .'
  alias gc='git commit -m'
  alias gp='git push'
  alias gs="git status"
fi
