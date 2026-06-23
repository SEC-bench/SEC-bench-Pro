#!/bin/bash
# Replace the move ctor + move assignment in ExclusiveData.h with `= delete`
# variants. Clang-19 rejects the original move ctor as ill-formed: the body
# references `rhs.lock` (data member) but ExclusiveData carries `lock_`
# (with trailing underscore), so `std::move(rhs.lock)` parses as
# `std::move(rhs.lock())` — taking the address of a non-static member function.
# Mozilla fixed this upstream in 2024-Q2; instance revisions before that
# need a local patch.
#
# Idempotent: if the marker `= delete` is already in the file we do nothing.
set -eu

f=js/src/threading/ExclusiveData.h
if grep -q 'ExclusiveData(ExclusiveData&&) = delete' "$f"; then
  echo "  $f: already patched"; exit 0
fi

python3 - <<'PY'
import re, sys
f = 'js/src/threading/ExclusiveData.h'
src = open(f).read()
# Replace the move ctor + move assign block (multi-line, brace-balanced).
old = (
    "  ExclusiveData(ExclusiveData&& rhs)\n"
    "      : lock_(std::move(rhs.lock)), value_(std::move(rhs.value_)) {\n"
    "    MOZ_ASSERT(&rhs != this, \"self-move disallowed!\");\n"
    "  }\n"
    "\n"
    "  ExclusiveData& operator=(ExclusiveData&& rhs) {\n"
    "    this->~ExclusiveData();\n"
    "    new (mozilla::KnownNotNull, this) ExclusiveData(std::move(rhs));\n"
    "    return *this;\n"
    "  }"
)
new = (
    "  ExclusiveData(ExclusiveData&&) = delete;\n"
    "  ExclusiveData& operator=(ExclusiveData&&) = delete;"
)
if old not in src:
    sys.stderr.write("  pattern not found; ExclusiveData.h may have a different layout — skipping\n")
    sys.exit(0)
src = src.replace(old, new, 1)
open(f, 'w').write(src)
print(f"  {f}: patched (move ctor/assign → =delete)")
PY
