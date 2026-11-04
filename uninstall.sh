#!/usr/bin/env bash
set -Eeuo pipefail
package_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec python3 "$package_root/payload/kenoforge/tools/uninstall.py" "$@"
