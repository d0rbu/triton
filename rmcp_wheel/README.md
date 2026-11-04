# Direct backend entry-point selection

This branch changes only backend discovery to call
`entry_points(group="triton.backends")`. This retains entry-point order,
external plugins, duplicate-name replacement and import/class errors while
avoiding a redundant unfiltered `EntryPoints.select()` pass. The opt-in
in-tree discovery path is unchanged.

Base: upstream Triton v3.6.0, commit
`7c56a5e40f7fd928dfd5c72902d5def0097db73a`.

`repack.py` requires the official CPython 3.12 Linux x86-64 wheel, size
188266850 bytes, SHA256
`74caf5e34b66d9f3a429af689c1c7128daba1d8208df60e81106b115c00d6fca`.
It streams and checks every original member against RECORD, changes only
`triton/backends/__init__.py`, adds the wheel build tag, and regenerates RECORD.
Every native binary and all other member bytes remain unchanged. It adds no
runtime validation, caching or instrumentation.

```sh
python -I -S -B rmcp_wheel/repack.py /path/to/upstream.whl /new/output/directory
```

CPU-only plugin regression tests cover ordered external plugins, irrelevant
groups, duplicate names and propagated import failures in
`python/test/unit/runtime/test_backend_discovery.py`.

The initial source experiment on a Ryzen 9 9950X, Python 3.12.11, compared
16 alternating pairs of 64 real discoveries, with normal GC and the actual
194 installed entry points. Median CPU fell from 152.200521 to 149.1009655 ms
(2.0365%); all 16 CPU and wall pairs improved. Actual AMD/NVIDIA classes and
208 plugin/error controls matched exactly. This is a discovery-component
result, not an end-to-end pre-commit, GPU kernel or training speed claim.
Installed-package and complete RMCP gate validation are recorded separately.

## Source installation

The `rmcp_wheel` subdirectory also supplies a standard PEP 517 build backend.
It downloads the exact official PyPI wheel above, then runs this same repacker.
The resulting wheel is byte-for-byte identical to the standalone build. This
avoids requiring a separate large binary upload and preserves all native bytes.
It runs once during normal installation/build caching; there is no runtime
hook, source overlay or startup validation. The subdirectory is self-contained:
the single source edit is applied to the hash-pinned original member.

Pin the immutable source archive and `subdirectory = "rmcp_wheel"` through
[UV's URL sources](https://docs.astral.sh/uv/concepts/projects/dependencies/#url).
Select this artifact only for Linux CPython 3.12 x86-64; other platforms retain
the ordinary registry source. A source build needs the pinned PyPI URL reachable.
Direct standalone rebuilds can instead use an already downloaded exact wheel.
