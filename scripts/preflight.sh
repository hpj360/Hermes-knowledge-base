#!/usr/bin/env bash
# scripts/preflight.sh
#
# 会话启动预检脚本：检测工作区是否与远端同步，避免在过时/重置的工作区上工作。
#
# 用法：./scripts/preflight.sh

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
REMOTE="$(git config "branch.${BRANCH}.remote" || echo origin)"

echo "=== 工作区预检 ==="
echo "分支: $BRANCH"
echo "远端: $REMOTE"

# 1. fetch 最新远端
echo "[1/4] 拉取远端最新状态..."
git fetch --all --prune --tags 2>/dev/null

LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git rev-parse "$REMOTE/$BRANCH" 2>/dev/null || echo "")

echo "[2/4] 本地 HEAD:  $LOCAL_SHA"
echo "[2/4] 远端 HEAD:  $REMOTE_SHA"

if [ -z "$REMOTE_SHA" ]; then
  echo "⚠️  远端无此分支，首次推送请运行: git push -u $REMOTE $BRANCH"
  exit 0
fi

# 2. 比较 SHA
if [ "$LOCAL_SHA" = "$REMOTE_SHA" ]; then
  echo "[3/4] ✓ 本地与远端完全一致"
else
  # 是本地领先还是落后？
  AHEAD=$(git rev-list --count "$REMOTE_SHA".."$LOCAL_SHA" 2>/dev/null || echo 0)
  BEHIND=$(git rev-list --count "$LOCAL_SHA".."$REMOTE_SHA" 2>/dev/null || echo 0)
  if [ "$AHEAD" -gt 0 ] && [ "$BEHIND" -eq 0 ]; then
    echo "[3/4] ⚠️  本地领先 $AHEAD 个 commit 但未推送（可能丢失风险）"
    echo "  建议立即: git push"
  elif [ "$BEHIND" -gt 0 ] && [ "$AHEAD" -eq 0 ]; then
    echo "[3/4] ⚠️  本地落后远端 $BEHIND 个 commit"
    echo "  建议立即: git pull --rebase"
  else
    echo "[3/4] ❌ 本地与远端已分叉（本地 +$AHEAD / 远端 +$BEHIND）"
    echo "  请手动处理：git pull --rebase 或 git reset --hard $REMOTE_SHA"
    exit 1
  fi
fi

# 3. 检查未提交改动
UNSTAGED=$(git status --short | wc -l | tr -d ' ')
if [ "$UNSTAGED" -gt 0 ]; then
  echo "[4/4] ⚠️  有 $UNSTAGED 个未提交改动："
  git status --short | head -10
else
  echo "[4/4] ✓ 工作区干净"
fi

# 4. 校验关键目录存在（防止重置后裸奔）
MISSING_DIRS=()
for d in src/hermes_kb tests/test_kb web/src docs/product; do
  [ -d "$d" ] || MISSING_DIRS+=("$d")
done
if [ ${#MISSING_DIRS[@]} -gt 0 ]; then
  echo ""
  echo "❌ 警告：关键目录缺失：${MISSING_DIRS[*]}"
  echo "  可能发生工作区重置，请立即恢复代码（参考 docs/product/04-代码丢失根因分析与根治.md）"
  exit 2
fi

echo ""
echo "✓ 预检通过，可以开始工作"
