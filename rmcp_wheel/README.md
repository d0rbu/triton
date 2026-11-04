# Backend discovery and frozen-options import cost

This branch retains direct backend discovery with
`entry_points(group="triton.backends")` and adds explicit tuple hashes to
`HIPOptions` and `CUDAOptions`. The explicit hashes use the same ordered fields
as the frozen dataclasses' generated hashes. Constructor, equality, repr,
frozen behavior, defaults, field metadata and compiler `hash()` methods remain
unchanged. External plugins and the opt-in in-tree discovery path remain supported.

Base: upstream Triton v3.6.0, commit
`7c56a5e40f7fd928dfd5c72902d5def0097db73a`.

`repack.py` requires the official CPython 3.12 Linux x86-64 wheel, size
188266850 bytes, SHA256
`74caf5e34b66d9f3a429af689c1c7128daba1d8208df60e81106b115c00d6fca`.
It checks every original member against RECORD, changes only backend discovery
and the two compiler Python sources, adds the build tag, and regenerates RECORD.
All native binaries and other member bytes remain unchanged. This is a build
operation; it adds no runtime validation, caching or instrumentation.

```sh
python -I -S -B rmcp_wheel/repack.py /path/to/upstream.whl /new/output/directory
```

CPU-only regression tests cover discovery in
`python/test/unit/runtime/test_backend_discovery.py` and frozen-options hashing
in `python/test/unit/runtime/test_backend_options_hash.py`. The latter uses
Hypothesis to check ordered field hashes, each unhashable field, real
constructors, dataclass replacement and inherited hashing with extra attributes.
Install the test requirements when running these tests.

Source-only measurements on Ryzen 9 9950X/Python 3.12.11 attributed about
0.977 ms and 1.039 ms to AMD/NVIDIA options class creation. A fixed 16-pair
screen executing each compiler body 1024 times reduced median component CPU
by 5.37% and wall time by 5.42%; 15/16 pairs improved. The adverse pair was
11.82% CPU and 13.51% wall slower. The earlier shorter screen remains retained.
These are source-component results; installed, native-workload and complete
RMCP gate qualification are separate requirements, not implied speedups.

## Source installation

The `rmcp_wheel` subdirectory supplies a standard PEP 517 build backend.
It downloads the exact official PyPI wheel and runs the same repacker.
Include `third_party/amd/backend/compiler.py` and
`third_party/nvidia/backend/compiler.py` beside this subdirectory in the source
archive. Their exact source hashes are checked by the build helper. The normal
build cache amortizes this packaging work; Triton runtime does not import it.

Pin the immutable source archive with `subdirectory = "rmcp_wheel"` through
[UV's URL sources](https://docs.astral.sh/uv/concepts/projects/dependencies/#url).
Select it only for Linux CPython 3.12 x86-64; other platforms retain the registry
source. Building needs the pinned PyPI URL reachable. Standalone rebuilds can
instead use an already downloaded exact wheel.
