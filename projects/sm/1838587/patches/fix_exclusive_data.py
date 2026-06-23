"""Delete the broken move ctor/assignment in js/src/threading/ExclusiveData.h.
clang-19 rejects calling a non-static member function on the move-ctor's value_.
The pre-2024 form had a copy-then-move semantics that triggered this.
Marking = delete is safe — ExclusiveData is never actually move-constructed."""
import os, sys

p = 'js/src/threading/ExclusiveData.h'
if not os.path.exists(p):
    sys.exit(0)

src = open(p).read()
needle = (
    '  ExclusiveData(ExclusiveData&& rhs)\n'
    '      : lock_(std::move(rhs.lock)), value_(std::move(rhs.value_)) {\n'
    '    MOZ_ASSERT(&rhs != this, "self-move disallowed!");\n'
    '  }\n'
    '\n'
    '  ExclusiveData& operator=(ExclusiveData&& rhs) {\n'
    '    this->~ExclusiveData();\n'
    '    new (mozilla::KnownNotNull, this) ExclusiveData(std::move(rhs));\n'
    '    return *this;\n'
    '  }'
)
if needle not in src:
    print('WARN: needle not found — file may have different formatting', file=sys.stderr)
    sys.exit(0)

new = src.replace(
    needle,
    '  ExclusiveData(ExclusiveData&&) = delete;\n  ExclusiveData& operator=(ExclusiveData&&) = delete;',
    1
)
open(p, 'w').write(new)
print('patched:', p)
