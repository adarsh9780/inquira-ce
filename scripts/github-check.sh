#!/bin/sh

set -eu

repository="$1"

if [ -z "$repository" ] || [ "${repository#*/}" = "$repository" ]; then
	echo "GITHUB_REPOSITORY must be in owner/name form"
	exit 1
fi

gh auth status >/dev/null

if [ -n "$(git status --porcelain)" ]; then
	echo "Refusing to publish a dirty working tree"
	exit 1
fi

branch="$(git branch --show-current)"
if [ -z "$branch" ]; then
	echo "Refusing to publish a detached HEAD"
	exit 1
fi

if git ls-files -u | grep -q .; then
	echo "Refusing to publish with unresolved merge conflicts"
	exit 1
fi

if origin_url="$(git remote get-url origin 2>/dev/null)"; then
	case "$origin_url" in
		"https://github.com/$repository" | "https://github.com/$repository.git" | "git@github.com:$repository.git")
			;;
		*)
			printf 'origin points to %s, expected %s\n' "$origin_url" "$repository"
			exit 1
			;;
	esac
fi

printf 'GitHub publication check passed for %s on branch %s\n' "$repository" "$branch"
