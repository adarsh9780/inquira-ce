#!/bin/sh

set -eu

repository="$1"
visibility="$2"

case "$visibility" in
	private | public | internal)
		;;
	*)
		echo "VISIBILITY must be private, public, or internal"
		exit 1
	;;
esac

if gh repo view "$repository" >/dev/null 2>&1; then
	if ! git remote get-url origin >/dev/null 2>&1; then
		git remote add origin "https://github.com/$repository.git"
	fi
else
	gh repo create "$repository" "--$visibility" --source=. --remote=origin
fi

branch="$(git branch --show-current)"
git push --set-upstream origin "$branch"

printf 'Published %s branch %s\n' "$repository" "$branch"
