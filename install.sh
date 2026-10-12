#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ ! -x /usr/bin/python3 ]; then
    printf '%s\n' 'Python 3 is needed to start guided setup. Install python3 (python on Arch), then run this script again.' >&2
    exit 1
fi
if [ "$#" -eq 0 ]; then
    exec /usr/bin/python3 "$base/setup.py"
fi
if [ "$1" = '--setup' ]; then
    if [ "$#" -ne 1 ]; then
        printf '%s\n' 'Use --setup on its own, or use the advanced installer flags shown by --help.' >&2
        exit 1
    fi
    exec /usr/bin/python3 "$base/setup.py"
fi
exec /usr/bin/python3 "$base/install.py" "$@"
