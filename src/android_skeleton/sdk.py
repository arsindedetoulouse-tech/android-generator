"""Detection of the Android SDK location required to build a generated project.

Gradle only reports a missing SDK after a full configuration attempt, and it reports it as a build
failure rather than as a setup problem. Everything here exists so that the CLI can tell the two
apart before Gradle runs.
"""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .validation import InputValidationError

_COMMAND_LINE_TOOLS_URL = "https://developer.android.com/studio#command-line-tools-only"

# A directory qualifies as an SDK only by its content. An empty or unrelated path in `ANDROID_HOME`
# would otherwise pass an existence check and still fail inside Gradle, which is the outcome this
# module exists to prevent. Both markers exist in every installation, including a minimal one.
_SDK_MARKERS = ("platforms", "platform-tools")

# `compileSdk` is declared by the convention plugins of the generated project rather than by the
# generator, so the required API levels are read from the project instead of being hardcoded here.
_COMPILE_SDK_PATTERN = re.compile(r"(?m)^[ \t]*compileSdk[ \t]*=[ \t]*(\d+)")

# Platform directories are named `android-<api>` and may carry a minor version suffix, as in
# `android-36.1` and `android-37.0`. Matching by prefix alone would let `android-36.1` satisfy
# `compileSdk = 37` and would accept levels that do not exist, such as `android-370`.
_PLATFORM_PATTERN = re.compile(r"^android-(\d+)(?:\.\d+)*$")

_ENVIRONMENT_VARIABLES = ("ANDROID_HOME", "ANDROID_SDK_ROOT")
_LOCAL_PROPERTIES = "local.properties"
_BUILD_LOGIC_DIRECTORY = Path("build-logic/src/main/kotlin")
_PLATFORMS_DIRECTORY = "platforms"


@dataclass(frozen=True)
class SdkLocation:
    """A usable SDK directory together with the source that named it."""

    path: Path
    source: str


@dataclass(frozen=True)
class InvalidSdkSource:
    """A source that names an SDK location which does not qualify as one."""

    source: str
    value: str


@dataclass(frozen=True)
class SdkResolution:
    """Outcome of looking for a usable SDK, including what was rejected on the way."""

    location: SdkLocation | None
    invalid_sources: tuple[InvalidSdkSource, ...] = ()

    @property
    def is_configured(self) -> bool:
        return self.location is not None


def looks_like_sdk(path: Path) -> bool:
    """Report whether a directory contains the markers every Android SDK installation has."""
    return path.is_dir() and any((path / marker).is_dir() for marker in _SDK_MARKERS)


def validate_sdk_directory(value: str) -> Path:
    """Validate a user-supplied SDK location before anything is written to the project."""
    if not value.strip():
        raise InputValidationError("--sdk-dir must not be empty")

    expanded = Path(value).expanduser()
    if not expanded.exists():
        raise InputValidationError(f"--sdk-dir does not exist: {expanded}")
    if not expanded.is_dir():
        raise InputValidationError(f"--sdk-dir is not a directory: {expanded}")
    if not looks_like_sdk(expanded):
        raise InputValidationError(
            f"--sdk-dir is not an Android SDK: {expanded} "
            f"(expected at least one of: {', '.join(_SDK_MARKERS)})"
        )
    return expanded


def _read_local_properties_sdk(project_directory: Path) -> str | None:
    path = project_directory / _LOCAL_PROPERTIES
    if not path.is_file():
        return None
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "!")):
            continue
        key, separator, raw_value = stripped.partition("=")
        if separator and key.strip() == "sdk.dir":
            return _unescape_property_value(raw_value.strip())
    return None


def _unescape_property_value(value: str) -> str:
    # Values in a Java properties file escape the separators of the format itself, so a Windows path
    # arrives as `C\:\\Users\\name`. Undo that rather than handing a mangled path to Gradle.
    unescaped: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character == "\\" and index + 1 < len(value):
            following = value[index + 1]
            if following in ("\\", ":", "=", " "):
                unescaped.append(following)
                index += 2
                continue
            if following == "u":
                code = value[index + 2 : index + 6]
                if len(code) == 4:
                    try:
                        unescaped.append(chr(int(code, 16)))
                        index += 6
                        continue
                    except ValueError:
                        pass
        unescaped.append(character)
        index += 1
    return "".join(unescaped)


def _configured_sources(project_directory: Path) -> list[tuple[str, str]]:
    """Sources in the order the Android Gradle Plugin consults them."""
    sources = [
        (name, os.environ.get(name, "").strip())
        for name in _ENVIRONMENT_VARIABLES
    ]
    sources.append((_LOCAL_PROPERTIES, _read_local_properties_sdk(project_directory) or ""))
    return sources


def resolve_sdk(project_directory: Path) -> SdkResolution:
    """Find a usable SDK, reporting sources that named a location which is not one."""
    location: SdkLocation | None = None
    invalid: list[InvalidSdkSource] = []
    for source, raw_value in _configured_sources(project_directory):
        if not raw_value:
            continue
        candidate = Path(raw_value).expanduser()
        if looks_like_sdk(candidate):
            if location is None:
                location = SdkLocation(path=candidate, source=source)
            continue
        invalid.append(InvalidSdkSource(source=source, value=str(candidate)))
    return SdkResolution(location=location, invalid_sources=tuple(invalid))


def required_api_levels(project_directory: Path) -> tuple[int, ...]:
    """API levels the generated project compiles against, read from its convention plugins."""
    directory = project_directory / _BUILD_LOGIC_DIRECTORY
    levels: list[int] = []
    if not directory.is_dir():
        return ()
    for plugin in sorted(directory.glob("*.gradle.kts")):
        try:
            content = plugin.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        levels.extend(int(match) for match in _COMPILE_SDK_PATTERN.findall(content))
    return tuple(sorted(set(levels)))


def installed_api_levels(sdk_directory: Path) -> tuple[int, ...]:
    """API levels installed in an SDK, with or without a minor version suffix."""
    platforms = sdk_directory / _PLATFORMS_DIRECTORY
    if not platforms.is_dir():
        return ()
    levels: set[int] = set()
    for entry in platforms.iterdir():
        match = _PLATFORM_PATTERN.fullmatch(entry.name)
        if match is not None:
            levels.add(int(match.group(1)))
    return tuple(sorted(levels))


def missing_api_levels(sdk_directory: Path, project_directory: Path) -> tuple[int, ...]:
    """Required API levels that the SDK does not provide."""
    required = required_api_levels(project_directory)
    installed = set(installed_api_levels(sdk_directory))
    return tuple(level for level in required if level not in installed)


def _sdk_from_adb() -> Path | None:
    """Recover an SDK directory from the location of `adb` on PATH.

    This is the shape of a partially configured machine: the tools are reachable but the variables
    the Android Gradle Plugin reads are not set.
    """
    adb = shutil.which("adb")
    if adb is None:
        return None
    platform_tools = Path(adb).resolve().parent
    if platform_tools.name != "platform-tools":
        return None
    return platform_tools.parent


def _well_known_locations() -> list[Path]:
    home = Path.home()
    local_app_data = os.environ.get("LOCALAPPDATA")
    candidates = [
        home / "Android" / "Sdk",
        home / "Android" / "sdk",
        home / "Library" / "Android" / "sdk",
        home / "android-sdk",
        Path("/opt/android-sdk"),
        Path("/usr/local/lib/android/sdk"),
        Path("/usr/lib/android-sdk"),
    ]
    if local_app_data:
        candidates.append(Path(local_app_data) / "Android" / "Sdk")
    return candidates


def discover_candidates() -> tuple[Path, ...]:
    """Directories on this machine that look like an SDK, for the setup message.

    The result is informational only. A machine can hold more than one SDK and they are not
    equivalent, so the CLI lists them and lets the user pass the one they mean explicitly.
    """
    found: list[Path] = []
    seen: set[Path] = set()

    def add(candidate: Path | None) -> None:
        if candidate is None or not looks_like_sdk(candidate):
            return
        resolved = candidate.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        found.append(resolved)

    add(_sdk_from_adb())
    for candidate in _well_known_locations():
        add(candidate)
    return tuple(found)


def _describe_checked_sources(project_directory: Path) -> list[str]:
    descriptions = []
    local_value = _read_local_properties_sdk(project_directory)
    for name, value in _configured_sources(project_directory):
        if value:
            descriptions.append(f"  {name} = {value}")
        elif name == _LOCAL_PROPERTIES:
            reason = (
                "sdk.dir is not set"
                if (project_directory / _LOCAL_PROPERTIES).is_file()
                else "no local.properties in the project"
            )
            descriptions.append(f"  {name}: {reason}")
        else:
            descriptions.append(f"  {name}: not set")
    return descriptions


def build_unconfigured_sdk_message(
    project_directory: Path,
    resolution: SdkResolution,
    *,
    context: str,
) -> str:
    """Explain that no usable SDK was found and how to point the build at one."""
    lines = [
        f"Android SDK location is not configured, so {context} cannot start.",
        "",
        "Checked, in the order the Android Gradle Plugin reads them:",
        *_describe_checked_sources(project_directory),
        "",
    ]

    invalid = [
        f"  {source.source} names {source.value}, which is not an Android SDK"
        for source in resolution.invalid_sources
    ]
    if invalid:
        lines += [
            "Rejected as SDK locations:",
            *invalid,
            f"  (an SDK directory contains at least one of: {', '.join(_SDK_MARKERS)})",
            "",
        ]

    candidates = discover_candidates()
    lines.append("Pass the SDK location explicitly:")
    if candidates:
        lines.append(
            "  Found SDK candidates on this machine; a machine can hold more than "
            "one, so the CLI does not choose for you:"
        )
        lines += [f"    {candidate}" for candidate in candidates]
    lines += [
        "",
        "  --sdk-dir /path/to/sdk writes sdk.dir into local.properties,",
        "  which stays out of version control.",
        "",
        "Or set a variable for your shell:",
        "  zsh:          echo 'export ANDROID_HOME=/path/to/sdk' >> ~/.zshrc",
        "  bash:         echo 'export ANDROID_HOME=/path/to/sdk' >> ~/.bashrc",
        "  fish:         echo 'set -x ANDROID_HOME /path/to/sdk' >> "
        "~/.config/fish/config.fish",
        "  cmd:          setx ANDROID_HOME C:\\path\\to\\sdk",
        "  PowerShell:   $env:ANDROID_HOME = 'C:\\path\\to\\sdk'",
        "  Start a new terminal afterwards, since the current one already ran.",
        "",
    ]
    if not candidates:
        lines += [
            "No SDK was found on this machine. Install the command-line tools;",
            f"Android Studio is not required: {_COMMAND_LINE_TOOLS_URL}",
            "",
        ]
    return "\n".join(lines)


def build_invalid_sdk_message(resolution: SdkResolution) -> str:
    """Explain that a location is configured but does not qualify as an SDK."""
    lines = ["Android SDK is configured, but the configured location is not an SDK:"]
    for source in resolution.invalid_sources:
        lines.append(f"  {source.source} = {source.value}")
    lines += [
        f"  An SDK directory contains at least one of: {', '.join(_SDK_MARKERS)}.",
        "",
        "Fix the value that points at it, or pass a valid one with --sdk-dir.",
    ]
    return "\n".join(lines)


def build_missing_platform_message(
    sdk_directory: Path,
    missing: Sequence[int],
    installed: Sequence[int],
) -> str:
    """Explain that the SDK lacks a platform the generated project compiles against."""
    required = ", ".join(str(level) for level in missing)
    return "\n".join(
        (
            f"Android SDK at {sdk_directory} is missing a required platform.",
            f"  The generated project compiles against API: {required}.",
            f"  Installed platforms: {_describe_levels(installed)}",
            f'  Install it with: sdkmanager "platforms;android-{missing[0]}"',
        )
    )


def _describe_levels(levels: Sequence[int]) -> str:
    return ", ".join(str(level) for level in levels) if levels else "none"


def write_local_properties(project_directory: Path, sdk_directory: Path) -> Path:
    """Record an explicitly chosen SDK location in the project's local settings file."""
    path = project_directory / _LOCAL_PROPERTIES
    content = (
        "# This file is machine-specific and must NOT be committed.\n"
        f"sdk.dir={sdk_directory}\n"
    )
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as error:
        raise InputValidationError(
            f"Could not write {_LOCAL_PROPERTIES}: {error}"
        ) from error
    return path