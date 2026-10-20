#!/bin/sh
# Fetch the MicroPython release tarball and build the unix port (VARIANT=standard).
# The result is .cache/micropython-$VERSION/ports/unix/build-standard/micropython.
set -eu

VERSION=1.29.0
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CACHE="$ROOT/.cache"
SRC="$CACHE/micropython-$VERSION"
TARBALL="$CACHE/micropython-$VERSION.tar.xz"
URL="https://github.com/micropython/micropython/releases/download/v$VERSION/micropython-$VERSION.tar.xz"

mkdir -p "$CACHE"
if [ ! -f "$SRC/.fetched" ]; then
    curl -fL -o "$TARBALL.part" "$URL"
    mv "$TARBALL.part" "$TARBALL"
    rm -rf "$SRC" "$SRC.tmp"
    mkdir "$SRC.tmp"
    tar -xJf "$TARBALL" -C "$SRC.tmp" --strip-components=1
    mv "$SRC.tmp" "$SRC"
    rm -f "$TARBALL"
    touch "$SRC/.fetched"
fi

make -C "$SRC/mpy-cross" -j"$(nproc)"
# FFI/SSL/btree are not used by bc and need extra host libraries.
make -C "$SRC/ports/unix" VARIANT=standard MICROPY_PY_FFI=0 MICROPY_PY_SSL=0 MICROPY_PY_BTREE=0 -j"$(nproc)"
echo "$SRC/ports/unix/build-standard/micropython"
