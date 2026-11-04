"""Repack the pinned upstream wheel with entry-point selection and explicit frozen-options tuple hashes.

This is an offline build tool, never imported by Triton. Native members are
streamed unchanged; the output contains exactly the upstream member roster.
"""

import argparse
import base64
import csv
import hashlib
import io
import zipfile
from pathlib import Path

UPSTREAM_SHA256 = "74caf5e34b66d9f3a429af689c1c7128daba1d8208df60e81106b115c00d6fca"
UPSTREAM_SIZE = 188266850
BASELINE_SHA256 = "c8bd4497720e736a2f8a7c01667a802d4945083a4aee77d3ac4bfe4305c47a89"
CANDIDATE_SHA256 = "5b0b27a71c43036faa5d01a59632104d7c3d2802e04a4b4dbb943d1fb8e35445"
BUILD = "2rmcp20261104"
SOURCE = "triton/backends/__init__.py"
DIST = "triton-3.6.0.dist-info/"
OUTPUT = f"triton-3.6.0-{BUILD}-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl"


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def record_hash(raw_digest):
    return "sha256=" + base64.urlsafe_b64encode(raw_digest).rstrip(b"=").decode("ascii")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    if args.upstream.stat().st_size != UPSTREAM_SIZE or digest(args.upstream) != UPSTREAM_SHA256:
        raise ValueError("upstream wheel size/SHA256 mismatch")
    args.output_directory.mkdir(parents=True, exist_ok=True)
    destination = args.output_directory / OUTPUT
    with zipfile.ZipFile(args.upstream) as source:
        infos = source.infolist()
        if len({info.filename for info in infos}) != len(infos):
            raise ValueError("duplicate upstream members")
        records = {row[0]: row[1:] for row in csv.reader(io.StringIO(source.read(DIST + "RECORD").decode()))}
        if set(records) != {info.filename for info in infos if not info.is_dir()}:
            raise ValueError("upstream RECORD roster mismatch")
        baseline = source.read(SOURCE)
        if hashlib.sha256(baseline).hexdigest() != BASELINE_SHA256:
            raise ValueError("baseline source SHA256 mismatch")
        before = b'for ep in entry_points().select(group="triton.backends"):'
        after = b'for ep in entry_points(group="triton.backends"):'
        if baseline.count(before) != 1:
            raise ValueError("backend entry-point patch does not apply exactly once")
        candidate = baseline.replace(before, after)
        if hashlib.sha256(candidate).hexdigest() != CANDIDATE_SHA256:
            raise ValueError("candidate source SHA256 mismatch")
        wheel = source.read(DIST + "WHEEL")
        if b"Build:" in wheel:
            raise ValueError("unexpected upstream build tag")
        replacements = {SOURCE: candidate, DIST + "WHEEL": wheel.rstrip(b"\n") + f"\nBuild: {BUILD}\n".encode()}
        # Build-time-only source payloads; no runtime patching or native changes.
        compiler_sources = [
            (
                "amd",
                "62556f905349ceed6286f9926f72ced9c5e990807e0791873945e93ca8e287d2",
                "1ceb3c66092c68022143e90eb6a8d20461faea9195671168c3ff222adb61d217",
            ),
            (
                "nvidia",
                "eea55698bab00c726b3d1d495b390b72a63aaa8d167781a65ea5212d394d76f6",
                "56be3e29375810b6d2e1ccd8d997ca5a2f91716cd27a94e993396c7ca6a7b80a",
            ),
        ]
        for backend, baseline_sha, candidate_sha in compiler_sources:
            member = f"triton/backends/{backend}/compiler.py"
            original = source.read(member)
            replacement = (
                Path(__file__).resolve().parent.parent / "third_party" / backend / "backend/compiler.py"
            ).read_bytes()
            if hashlib.sha256(original).hexdigest() != baseline_sha:
                raise ValueError(f"baseline compiler source mismatch: {member}")
            if hashlib.sha256(replacement).hexdigest() != candidate_sha:
                raise ValueError(f"candidate compiler source mismatch: {member}")
            replacements[member] = replacement
        rows = []
        with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
            for old in infos:
                name = old.filename
                if name == DIST + "RECORD":
                    continue
                info = zipfile.ZipInfo(name, date_time=(2026, 11, 4, 0, 0, 0))
                info.create_system = old.create_system
                info.external_attr = old.external_attr
                info.compress_type = zipfile.ZIP_DEFLATED
                if old.is_dir():
                    if old.file_size != 0:
                        raise ValueError(f"nonempty directory member: {name}")
                    target.writestr(info, b"")
                    continue
                original_hash = hashlib.sha256()
                original_size = 0
                output_hash = hashlib.sha256()
                output_size = 0
                with source.open(old) as src, target.open(info, "w", force_zip64=True) as dst:
                    while chunk := src.read(1024 * 1024):
                        original_hash.update(chunk)
                        original_size += len(chunk)
                        if name not in replacements:
                            dst.write(chunk)
                            output_hash.update(chunk)
                            output_size += len(chunk)
                    if name in replacements:
                        replacement = replacements[name]
                        dst.write(replacement)
                        output_hash.update(replacement)
                        output_size += len(replacement)
                if records[name] != [record_hash(original_hash.digest()), str(original_size)]:
                    raise ValueError(f"upstream RECORD mismatch: {name}")
                rows.append((name, record_hash(output_hash.digest()), str(output_size)))
            rows.append((DIST + "RECORD", "", ""))
            buffer = io.StringIO(newline="")
            csv.writer(buffer, lineterminator="\n").writerows(rows)
            info = zipfile.ZipInfo(DIST + "RECORD", date_time=(2026, 11, 4, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, buffer.getvalue().encode())
    print(f"{digest(destination)}  {destination}", flush=True)


if __name__ == "__main__":
    main()
