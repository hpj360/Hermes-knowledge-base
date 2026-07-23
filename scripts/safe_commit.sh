#!/usr/bin/env bash
# scripts/safe_commit.sh
#
# 根治代码丢失：commit 后自动 push 到远端，并校验推送成功。
#
# 用法：
#   ./scripts/safe_commit.sh "feat: 描述"          # commit + push 当前分支
#   ./scripts/safe_commit.sh                       # 同上，使用 $1 描述
#
# 设计目标：
# 1. 每次本地 commit 必伴随 push，杜绝"未推送的本地 commit"
# 2. push 失败立即告警，不静默继续
# 3. 输出最终远端 commit hash 用于核对
# 4. 沙箱重置/换机后，远端永远有完整副本

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
  echo "ERROR: 缺少 commit message" >&2
  echo "用法: $0 \"feat: 描述\"" >&2
  exit 2
fi

MSG="$1"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
REMOTE="$(git config "branch.${BRANCH}.remote" || echo origin)"

# 已暂存的修改先合并到本次
echo "[1/5] git add -A"
git add -A

# 没有改动？
if git diff --cached --quiet; then
  echo "[1/5] 无暂存改动，检查是否有未暂存改动..."
  if git diff --quiet && git ls-files --others --exclude-standard | grep -q .; then
    echo "ERROR: 有未跟踪文件但未 add（可能 .gitignore 漏配）" >&2
    git status --short
    exit 3
  fi
  echo "[1/5] 完全无改动，跳过 commit"
  exit 0
fi

echo "[2/5] git commit -m \"$MSG\""
git commit -m "$MSG"

# 确保上游分支已设置，否则用 -u 推送
UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)
PUSH_ARGS=(push)
if [ -z "$UPSTREAM" ]; then
  PUSH_ARGS+=(--set-upstream "$REMOTE" "$BRANCH")
fi

echo "[3/5] git ${PUSH_ARGS[*]}"
if ! git "${PUSH_ARGS[@]}"; then
  echo "=============================================" >&2
  echo "ERROR: push 失败！本地 commit 已创建但未推送" >&2
  echo "本地分支: $BRANCH  远端: $REMOTE" >&2
  echo "请手动检查：git push -u $REMOTE $BRANCH" >&2
  echo "=============================================" >&2
  exit 4
fi

echo "[4/5] 校验远端已收到 commit"
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git rev-parse "$REMOTE/$BRANCH" 2>/dev/null || echo "")

if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]; then
  echo "ERROR: 本地与远端 SHA 不一致" >&2
  echo "  local:  $LOCAL_SHA" >&2
  echo "  remote: $REMOTE_SHA" >&2
  exit 5
fi

echo "[5/5] ✓ commit 已成功推送到远端"
echo "  branch: $BRANCH"
echo "  sha:    $LOCAL_SHA"
echo "  msg:    $MSG"
