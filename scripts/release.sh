#!/usr/bin/env bash
set -euo pipefail

usage() {
	cat <<'EOF'
Usage:
  bash scripts/release.sh tag --release-version vX.Y.Z
  bash scripts/release.sh sync-tag --release-version vX.Y.Z
  bash scripts/release.sh --help

Stages:
  tag       Verify and synchronize main, then create the GitLab tag.
  sync-tag  After the GitLab tag pipeline passes, sync that tag to GitHub.

The script asks you to confirm the relevant GitLab pipeline passed. It does
not use glab, force-push, or push all tags.
EOF
}

die() {
	printf 'Error: %s\n' "$1" >&2
	exit 1
}

remote_ref() {
	local remote=$1
	local ref=$2
	git ls-remote "$remote" "$ref" |
		awk -v ref="$ref" '$2 == ref { print $1 }'
}

validate_gitlab_url() {
	case "$1" in
	git@gitlab.dwd.de:ku/libraries/pyku.git | \
		https://gitlab.dwd.de/ku/libraries/pyku.git | \
		https://gitlab.dwd.de/ku/libraries/pyku/ | \
		ssh://git@gitlab.dwd.de/ku/libraries/pyku.git)
		;;
	*) die "unexpected GitLab remote URL: $1" ;;
	esac
}

validate_github_url() {
	case "$1" in
	git@github.com:DeutscherWetterdienst/pyku.git | \
		https://github.com/DeutscherWetterdienst/pyku.git | \
		ssh://git@github.com/DeutscherWetterdienst/pyku.git)
		;;
	*) die "unexpected GitHub remote URL: $1" ;;
	esac
}

check_remote_urls() {
	local remote
	local key
	local url
	local -a urls

	for remote in gitlab github; do
		key="remote.$remote.url"
		mapfile -t urls < <(git config --get-all "$key" || true)
		if [[ ${#urls[@]} -ne 1 ]]; then
			die "expected one configured URL for the $remote remote"
		fi
		url=${urls[0]}
		if [[ $remote == gitlab ]]; then
			validate_gitlab_url "$url"
		else
			validate_github_url "$url"
		fi

		key="remote.$remote.pushurl"
		mapfile -t urls < <(git config --get-all "$key" || true)
		if [[ ${#urls[@]} -gt 1 ]]; then
			die "expected at most one push URL for the $remote remote"
		fi
		if [[ ${#urls[@]} -eq 1 ]]; then
			url=${urls[0]}
			if [[ $remote == gitlab ]]; then
				validate_gitlab_url "$url"
			else
				validate_github_url "$url"
			fi
		fi
	done
}

require_clean_worktree() {
	if [[ -n $(git status --porcelain) ]]; then
		die 'working tree is not clean; commit or move local changes first'
	fi
}

fetch_main() {
	git fetch gitlab refs/heads/main:refs/remotes/gitlab/main
	git fetch github refs/heads/main:refs/remotes/github/main
}

verify_main_matches() {
	local gitlab_main
	local github_main

	gitlab_main=$(remote_ref gitlab refs/heads/main)
	github_main=$(remote_ref github refs/heads/main)
	if [[ -z $gitlab_main || -z $github_main ]]; then
		die 'could not find main on both remotes'
	fi
	if [[ $gitlab_main != "$github_main" ]]; then
		die 'GitLab and GitHub main do not match'
	fi
}

confirm_pipeline() {
	local description=$1
	local sha=$2
	local answer

	read -r -p \
		"Confirm the GitLab $description pipeline passed for $sha? [y/N] " \
		answer
	case "$answer" in
	y | Y | yes | YES | Yes) ;;
	*) die 'confirmation not given; no release action taken' ;;
	esac
}

validate_changelog() {
	local release_version=$1
	local heading

	heading=$(head -n 1 CHANGELOG.rst)
	if [[ $heading != "$release_version" ]]; then
		die "CHANGELOG.rst must start with $release_version; found $heading"
	fi
}

sync_main_to_github() {
	local gitlab_main
	local github_main

	gitlab_main=$(remote_ref gitlab refs/heads/main)
	github_main=$(remote_ref github refs/heads/main)
	if [[ -z $gitlab_main || -z $github_main ]]; then
		die 'could not find main on both remotes'
	fi
	if ! git merge-base --is-ancestor \
		refs/remotes/github/main refs/remotes/gitlab/main; then
		die 'GitHub main is not an ancestor of GitLab main; stop'
	fi
	if [[ $gitlab_main != "$github_main" ]]; then
		git push --no-follow-tags github \
			refs/remotes/gitlab/main:refs/heads/main
	fi

	verify_main_matches
	if [[ $(remote_ref gitlab refs/heads/main) != "$gitlab_main" ]]; then
		die 'GitLab main changed during synchronization; stop'
	fi
}

tag_release() {
	local release_version=$1
	local main_sha
	local tag_ref

	require_clean_worktree
	check_remote_urls
	fetch_main
	git switch main
	git pull --ff-only gitlab main
	fetch_main

	main_sha=$(remote_ref gitlab refs/heads/main)
	if [[ -z $main_sha || $(git rev-parse HEAD) != "$main_sha" ]]; then
		die 'local main does not match GitLab main; stop'
	fi
	validate_changelog "$release_version"

	if git show-ref --verify --quiet "refs/tags/$release_version"; then
		die "local tag $release_version already exists; stop"
	fi
	if [[ -n $(remote_ref gitlab "refs/tags/$release_version") ||
	-n $(remote_ref github "refs/tags/$release_version") ]]; then
		die "tag $release_version already exists on a remote; stop"
	fi

	if ! git merge-base --is-ancestor \
		refs/remotes/github/main refs/remotes/gitlab/main; then
		die 'GitHub main is not an ancestor of GitLab main; stop'
	fi

	confirm_pipeline main "$main_sha"
	sync_main_to_github
	git tag -a "$release_version" "$main_sha" \
		-m "pyku $release_version"
	git push --no-follow-tags gitlab "$release_version"

	tag_ref="refs/tags/$release_version"
	if [[ -z $(remote_ref gitlab "$tag_ref") ||
	$(remote_ref gitlab "$tag_ref") == "$main_sha" ]]; then
		die "GitLab did not receive an annotated $release_version tag"
	fi
	if [[ $(remote_ref gitlab "$tag_ref^{}") != "$main_sha" ]]; then
		die "$release_version does not point to the expected main commit"
	fi

	printf '\nGitLab tag pushed. Wait for its pipeline to pass, then run:\n'
	printf '  bash scripts/release.sh sync-tag --release-version %s\n' \
		"$release_version"
}

sync_release_tag() {
	local release_version=$1
	local gitlab_tag
	local gitlab_commit
	local github_tag
	local github_commit
	local local_ref

	require_clean_worktree
	check_remote_urls
	fetch_main
	verify_main_matches

	gitlab_tag=$(remote_ref gitlab "refs/tags/$release_version")
	gitlab_commit=$(remote_ref gitlab "refs/tags/$release_version^{}")
	if [[ -z $gitlab_tag || -z $gitlab_commit ||
		$gitlab_tag == "$gitlab_commit" ]]; then
		die "annotated $release_version tag not found on GitLab; stop"
	fi

	local_ref="refs/pyku-release/tags/$release_version"
	git fetch gitlab "refs/tags/$release_version:$local_ref"
	if [[ $(git cat-file -t "$local_ref") != tag ||
	$(git rev-parse "$local_ref^{}") != "$gitlab_commit" ]]; then
		die "fetched $release_version tag does not match GitLab; stop"
	fi

	github_tag=$(remote_ref github "refs/tags/$release_version")
	if [[ -n $github_tag && $github_tag != "$gitlab_tag" ]]; then
		die "GitHub $release_version tag differs from GitLab; stop"
	fi
	if [[ $github_tag == "$gitlab_tag" ]]; then
		printf 'GitHub already has the matching %s tag.\n' "$release_version"
		return
	fi

	confirm_pipeline "$release_version" "$gitlab_commit"
	git push --no-follow-tags github "$local_ref:refs/tags/$release_version"
	github_tag=$(remote_ref github "refs/tags/$release_version")
	github_commit=$(remote_ref github "refs/tags/$release_version^{}")
	if [[ $github_tag != "$gitlab_tag" ||
		$github_commit != "$gitlab_commit" ]]; then
		die "GitHub $release_version tag does not match GitLab after push"
	fi

	printf 'GitLab and GitHub now have the same %s tag.\n' "$release_version"
}

main() {
	local action
	local release_version=
	local script_dir
	local repo_root

	if [[ $# -eq 1 && $1 == --help ]]; then
		usage
		return 0
	fi
	if [[ $# -eq 0 ]]; then
		usage >&2
		return 2
	fi

	action=$1
	shift
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--release-version)
			if [[ $# -lt 2 ]]; then
				printf 'Error: --release-version requires a value\n' >&2
				return 2
			fi
			release_version=$2
			shift 2
			;;
		--help)
			usage
			return 0
			;;
		*)
			printf 'Error: unexpected argument: %s\n' "$1" >&2
			usage >&2
			return 2
			;;
		esac
	done

	if [[ $action != tag && $action != sync-tag ]]; then
		printf 'Error: expected tag or sync-tag action\n' >&2
		usage >&2
		return 2
	fi
	if [[ ! $release_version =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
		printf 'Error: release version must use vX.Y.Z format\n' >&2
		return 2
	fi

	script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
	repo_root=$(git -C "$script_dir/.." rev-parse --show-toplevel) ||
		die 'could not locate the pyku Git repository'
	cd "$repo_root"

	case "$action" in
	tag) tag_release "$release_version" ;;
	sync-tag) sync_release_tag "$release_version" ;;
	esac
}

main "$@"
