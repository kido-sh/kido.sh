#!/bin/sh
# Download, verify, and run the standalone kido-probe binary on ARM64 Linux.
# Leaves nothing installed on the host.
#
#   curl -fsSL https://kido.sh/probe.sh | sh
#   curl -fsSL https://kido.sh/probe.sh | sh -s -- --json

set -eu

release_key='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEQuRAYSAENI7qS+YLpWLf6EGKUAjjeNz1e++6ShGcuh'

say() { printf '%s\n' "$*" >&2; }
die() { say "probe.sh: $*"; exit 1; }

sha256_of() {
	if command -v shasum >/dev/null 2>&1; then
		shasum -a 256 "$1" | awk '{print $1}'
	elif command -v sha256sum >/dev/null 2>&1; then
		sha256sum "$1" | awk '{print $1}'
	else
		die "need shasum or sha256sum to verify downloads"
	fi
}

sum_for() { awk -v n="$2" '$2 == n || $2 == "*" n { print $1; exit }' "$1"; }

verify_sums() {
	command -v ssh-keygen >/dev/null 2>&1 || die "need ssh-keygen to verify the release signature"
	printf 'kido namespaces="release@kido.sh" %s\n' "$release_key" >"$tmp/allowed_signers"
	ssh-keygen -Y verify -f "$tmp/allowed_signers" -I kido -n release@kido.sh -s "$1.sig" <"$1" >/dev/null 2>&1 ||
		die "$1 does not carry a valid kido release signature"
}

download() {
	curl -fsSL --proto '=https' --tlsv1.2 --retry 2 -o "$2" "$1" || die "download failed: $1"
}

latest_version() {
	url=$(curl -fsSLI --proto '=https' --tlsv1.2 -o /dev/null -w '%{url_effective}' \
		"https://github.com/$1/releases/latest") || die "cannot reach https://github.com/$1/releases/latest"
	tag=${url##*/tag/}
	[ "$tag" != "$url" ] || die "no release found at https://github.com/$1/releases"
	printf '%s\n' "${tag#v}"
}

main() {
	host_os=$(uname -s)
	[ "$host_os" = Linux ] || die "kido-probe runs on ARM64 Linux hosts only (got $host_os)"
	case $(uname -m) in
	aarch64 | arm64) ;;
	*) die "kido-probe requires an arm64 (aarch64) Linux host (got $(uname -m))" ;;
	esac

	repo=${KIDO_REPO:-kido-sh/kido}
	version=${KIDO_VERSION:-latest}
	[ "$version" != latest ] || version=$(latest_version "$repo")
	version=${version#v}

	tmp=$(mktemp -d "${TMPDIR:-/tmp}/kido-probe.XXXXXX") || die "mktemp failed"
	trap 'rm -rf "$tmp"' EXIT
	trap 'exit 130' INT TERM

	name="kido-probe-$version-linux-arm64"
	base="https://github.com/$repo/releases/download/v$version"
	download "$base/$name" "$tmp/$name"
	download "$base/SHA256SUMS" "$tmp/SHA256SUMS"
	download "$base/SHA256SUMS.sig" "$tmp/SHA256SUMS.sig"

	verify_sums "$tmp/SHA256SUMS"
	want=$(sum_for "$tmp/SHA256SUMS" "$name")
	[ -n "$want" ] || die "SHA256SUMS does not list $name"
	[ "$(sha256_of "$tmp/$name")" = "$want" ] || die "$name does not match its published SHA-256"

	chmod 0755 "$tmp/$name"
	"$tmp/$name" "$@"
}

main "$@"
