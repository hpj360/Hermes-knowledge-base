#!/usr/bin/env bash
# scripts/verify_pushed.sh
#
# 工作完成校验：确保所有本地 commit 已推送到远端，防止会话结束时丢失。
#
# 用法：./scripts/verify_pushed.sh
# 退出码：0=已推送 1=未推送

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
REMOTE="$(git config "branch.${BRANCH}.remote" || echo origin)"

LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git rev-parse "$REMOTE/$BRANCH" 2>/dev/null || echo "")

echo "分支: $BRANCH"
echo "本地: $LOCAL_SHA"
echo "远端: ${REMOTE_SHA:-（无）}"

# 是否有未推送的 commit
AHEAD=0
if [ -n "$REMOTE_SHA" ]; then
  AHEAD=$(git rev-list --count "$REMOTE_SHA".."$LOCAL_SHA" 2>/dev/null || echo 0)
fi

# 是否有未提交改动
UNSTAGED=$(git status --short | wc -l | tr -d ' ')

FAIL=0
if [ "$AHEAD" -gt 0 ]; then
  echo "❌ 本地有 $AHEAD 个 commit 未推送到 $REMOTE/$BRANCH"
  git log "$REMOTE_SHA..$LOCAL_SHA" --oneline
  FAIL=1
fi

if [ "$UNSTAGED" -gt 0 ]; then
  echo "❌ 有 $UNSTAGED 个未提交改动"
  git status --short
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then
  echo "✓ 所有改动已提交并推送"
  exit 0
else
  echo ""
  echo "建议立即执行：./scripts/safe_commit.sh \"补提交\""
  exit 1
fi
