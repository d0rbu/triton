"""Build the reproducible binary-preserving wheel from the pinned PyPI input.

Only dependency installation imports this PEP 517 backend. Triton runtime does
not import it or run any downloads, repacking, checks or instrumentation.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen

from repack import OUTPUT

UPSTREAM_URL = (
    "https://files.pythonhosted.org/packages/ab/a8/"
    "cdf8b3e4c98132f965f88c2313a4b493266832ad47fb52f23d14d4f86bb5/"
    "triton-3.6.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl"
)


def get_requires_for_build_wheel(
    config_settings: dict[str, str | list[str]] | None = None,
) -> list[str]:
    return []


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, str | list[str]] | None = None,
    metadata_directory: str | None = None,
) -> str:
    output = Path(wheel_directory).resolve()
    with tempfile.TemporaryDirectory(prefix="triton-upstream-wheel-") as temporary:
        upstream = Path(temporary) / "upstream.whl"
        with urlopen(UPSTREAM_URL, timeout=30) as response, upstream.open("wb") as target:
            shutil.copyfileobj(response, target, length=1024 * 1024)
        subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(Path(__file__).with_name("repack.py")), str(upstream), str(output)],
            check=True,
        )
    return OUTPUT
