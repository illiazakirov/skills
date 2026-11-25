#!/bin/sh
# Fails if git tracks a working document or a path on someone's machine (see CLAUDE.md).
status=0

tracked=$(git ls-files -- docs/superpowers .agents/adr 'docs/*/*/*')
if [ -n "$tracked" ]; then
  echo "Working documents are tracked; they must stay local:"
  echo "$tracked"
  status=1
fi

paths=$(git grep -nIE '/Users/[A-Za-z]|/home/[a-z]|/private/(tmp|var)|/var/folders/|~/dev/|\.claude/projects/' -- . ':!scripts/check-local.sh')
if [ -n "$paths" ]; then
  echo "Local paths in tracked files:"
  echo "$paths"
  status=1
fi

[ $status -eq 0 ] && echo "No working documents or local paths in git."
exit $status
