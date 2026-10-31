#!/bin/sh
# vishlang installer: CLI via uv, skill + MCP server into Claude Code and Codex.
set -e

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) ;;
  *) echo "vishlang needs an Apple Silicon Mac (mlx). Found: $(uname -s) $(uname -m)"; exit 1 ;;
esac

if ! command -v uv >/dev/null 2>&1; then
  echo "installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

echo "installing vishlang..."
# archive URL, not git+: a clean Mac has no git until the Xcode command line tools are installed
uv tool install --force --python 3.12 "vishlang @ https://github.com/VishiATChoudhary/vishlang/archive/refs/heads/main.zip"
uv tool update-shell >/dev/null 2>&1 || true

"$HOME/.local/bin/vishlang" install

cat <<MSG

done. open a new terminal (PATH was updated), then:
  vishlang init --name "Your Name" --email you@example.com
  vishlang build        # trains on your Claude Code + Codex prompts, 30 to 60 min
  vishlang test         # blind A/B

then open a new Claude Code or Codex session and ask it to draft something.
MSG
