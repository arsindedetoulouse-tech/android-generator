"""A fake Android SDK for verification tests.

The CLI checks that an SDK is configured before it starts Gradle, so tests that exercise
verification must not depend on what happens to be installed on the host machine.
"""

from __future__ import annotations

from pathlib import Path


def create_fake_sdk(root: Path, *, api_levels: tuple[str, ...] = ("37",)) -> Path:
    """Create a directory that qualifies as an SDK and provides the given API levels."""
    directory = root / "fake-android-sdk"
    (directory / "platform-tools").mkdir(parents=True)
    (directory / "platforms").mkdir(parents=True)
    for level in api_levels:
        (directory / "platforms" / f"android-{level}").mkdir()
    return directory