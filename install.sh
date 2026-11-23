#!/bin/sh
# Install kido for the current user, without sudo: kido goes into PREFIX (default ~/.local), then
# `kido setup` pulls the Darwin image into KIDO_HOME (default ~/.kido). Nothing else on the system
# changes.
#
#   curl -fsSL https://kido.sh/install.sh | sh
#   curl -fsSL https://github.com/kido-sh/kido/releases/latest/download/install.sh | sh
#   curl -fsSL https://kido.sh/install.sh | sh -s -- --prefix ~/opt/kido --version 0.1.0 --no-setup
#   sh install.sh --tarball dist/kido-0.1.0-darwin-arm64.tar.gz    # a local `make dist`
#
# Options (or environment): --prefix DIR (KIDO_PREFIX), --version V (KIDO_VERSION, default: the
# latest release), --repo OWNER/NAME (KIDO_REPO), --tarball FILE, --image REMOTE_REF (KIDO_IMAGE:
# the base image `kido setup` pulls, default ghcr.io/kido-sh/darwin), --no-setup (KIDO_NO_SETUP=1).
#
# A download is installed only if its SHA256SUMS carries the kido release signature and lists its
# SHA-256. Everything runs inside main, so a download cut short executes nothing.

set -eu

release_key='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEQuRAYSAENI7qS+YLpWLf6EGKUAjjeNz1e++6ShGcuh'

say() { printf '%s\n' "$*" >&2; }
die() { say "install.sh: $*"; exit 1; }

usage() {
	cat >&2 <<'USAGE'
usage: install.sh [--prefix DIR] [--version V] [--repo OWNER/NAME] [--tarball FILE]
                  [--image REMOTE_REF] [--no-setup]
Installs kido into PREFIX/bin (default ~/.local/bin), then runs `kido setup`.
USAGE
	exit 2
}

sha256_of() { shasum -a 256 "$1" | awk '{print $1}'; }

sum_for() { awk -v n="$2" '$2 == n || $2 == "*" n { print $1; exit }' "$1"; }

verify_sums() {
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
	prefix=${KIDO_PREFIX:-${PREFIX:-$HOME/.local}}
	version=${KIDO_VERSION:-latest}
	repo=${KIDO_REPO:-kido-sh/kido}
	tarball=
	image=${KIDO_IMAGE:-}
	run_setup=1
	[ "${KIDO_NO_SETUP:-0}" = 1 ] && run_setup=0

	while [ $# -gt 0 ]; do
		case $1 in
		--prefix) [ $# -ge 2 ] || usage; prefix=$2; shift 2 ;;
		--version) [ $# -ge 2 ] || usage; version=${2#v}; shift 2 ;;
		--repo) [ $# -ge 2 ] || usage; repo=$2; shift 2 ;;
		--tarball) [ $# -ge 2 ] || usage; tarball=$2; shift 2 ;;
		--image) [ $# -ge 2 ] || usage; image=$2; shift 2 ;;
		--no-setup) run_setup=0; shift ;;
		-h | --help) usage ;;
		*) say "install.sh: unknown option $1"; usage ;;
		esac
	done

	[ "$(uname -s)" = Darwin ] || die "kido runs on macOS only"
	[ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = 1 ] || die "kido needs an Apple Silicon Mac"
	[ "$(id -u)" != 0 ] || die "run this as your own user, not root: kido needs no sudo"
	case $prefix in
	/*) ;;
	*) die "--prefix must be an absolute path, got: $prefix" ;;
	esac

	tmp=$(mktemp -d "${TMPDIR:-/tmp}/kido-install.XXXXXX") || die "mktemp failed"
	trap 'rm -rf "$tmp"' EXIT
	trap 'exit 130' INT TERM

	if [ -n "$tarball" ]; then
		[ -f "$tarball" ] || die "no such file: $tarball"
		sums=$(dirname "$tarball")/SHA256SUMS
		if [ -f "$sums" ]; then
			if [ -f "$sums.sig" ]; then
				verify_sums "$sums"
			fi
			want=$(sum_for "$sums" "$(basename "$tarball")")
			[ -n "$want" ] || die "$sums does not list $(basename "$tarball")"
			[ "$(sha256_of "$tarball")" = "$want" ] || die "$tarball does not match $sums"
			say "Verified $tarball against $sums"
		else
			say "note: no SHA256SUMS next to $tarball; installing without a checksum"
		fi
		archive=$tarball
	else
		[ "$version" != latest ] || version=$(latest_version "$repo")
		name=kido-$version-darwin-arm64.tar.gz
		base=https://github.com/$repo/releases/download/v$version
		say "Downloading kido $version from $base"
		download "$base/$name" "$tmp/$name"
		download "$base/SHA256SUMS" "$tmp/SHA256SUMS"
		download "$base/SHA256SUMS.sig" "$tmp/SHA256SUMS.sig"
		verify_sums "$tmp/SHA256SUMS"
		want=$(sum_for "$tmp/SHA256SUMS" "$name")
		[ -n "$want" ] || die "SHA256SUMS does not list $name"
		[ "$(sha256_of "$tmp/$name")" = "$want" ] || die "$name does not match its published SHA-256"
		say "Verified the release signature and SHA-256 $want"
		archive=$tmp/$name
	fi

	mkdir "$tmp/x"
	tar -xzf "$archive" -C "$tmp/x" || die "cannot unpack $archive"
	[ -f "$tmp/x/bin/kido" ] || die "$archive has no bin/kido"

	install -d "$prefix/bin" "$prefix/libexec/kido" "$prefix/share/doc/kido"
	install -m 0755 "$tmp/x/bin/kido" "$prefix/bin/kido"
	for helper in kido-agent kido-vmm; do
		if [ -f "$tmp/x/libexec/kido/$helper" ]; then
			install -m 0755 "$tmp/x/libexec/kido/$helper" "$prefix/libexec/kido/$helper"
		fi
	done
	for doc in "$tmp"/x/share/doc/kido/*; do
		if [ -f "$doc" ]; then
			install -m 0644 "$doc" "$prefix/share/doc/kido/"
		fi
	done
	say "Installed $("$prefix/bin/kido" --version) as $prefix/bin/kido"

	case ":$PATH:" in
	*":$prefix/bin:"*) ;;
	*) say "note: $prefix/bin is not on PATH; add it, e.g.: echo 'export PATH=\"$prefix/bin:\$PATH\"' >> ~/.zprofile" ;;
	esac

	if [ "$run_setup" = 0 ]; then
		say "Next: $prefix/bin/kido setup   (pulls the Darwin image into KIDO_HOME, ~/.kido by default)"
		return 0
	fi
	set -- setup
	[ -z "$image" ] || set -- "$@" --image "$image"
	if ! "$prefix/bin/kido" "$@"; then
		say "kido is installed, but \`kido $*\` failed (see above); fix that and run it again"
		exit 1
	fi
}

main "$@"
