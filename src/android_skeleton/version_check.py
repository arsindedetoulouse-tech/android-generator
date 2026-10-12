"""Checks that run before the generator writes anything.

A generator installed as a plain copy of the files has no way to know that the repository it came
from moved on. These checks make that visible instead of letting a stale template generate a
project that only fails later, at build time.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

from . import TEMPLATE_VERSION, __version__
from .metadata import SUPPORTED_TEMPLATE_VERSIONS, MetadataError, parse_version

PACKAGE_NAME = "android-skeleton"
_GITHUB_API = "https://api.github.com"
_PYPI_API = "https://pypi.org/pypi"

# Short, because `create` writes a project and returns: two sequential requests must not dominate it.
_NETWORK_TIMEOUT_SECONDS = 2.0

_UP_TO_DATE = "up-to-date"
_NEWER_AVAILABLE = "newer-available"
_NOT_PUBLISHED = "not-published"
_UNVERIFIED = "unverified"


@dataclass(frozen=True)
class VersionCheck:
    """One check's outcome.

    `detail` carries what the message needs: the compared versions, or the reason the check could
    not answer. `warning` is `None` when there is nothing worth telling the user.
    """

    name: str
    status: str
    detail: str = ""
    warning: str | None = None


def package_version() -> str:
    """Version recorded when the package was installed, which may lag a source tree."""
    try:
        return importlib_metadata.version(PACKAGE_NAME)
    except importlib_metadata.PackageNotFoundError:
        return __version__


def package_url() -> str | None:
    """Homepage declared in the package metadata, from which the repository is derived."""
    try:
        project_urls = importlib_metadata.metadata(PACKAGE_NAME).get_all("Project-URL") or []
    except importlib_metadata.PackageNotFoundError:
        return None
    for entry in project_urls:
        label, separator, url = entry.partition(",")
        if separator and label.strip().lower() in ("homepage", "repository", "source"):
            return url.strip()
    return None


def is_newer(candidate: str, current: str) -> bool:
    """Compare two versions numerically, so 0.10.0 sorts above 0.9.0."""
    try:
        return parse_version(candidate) > parse_version(current)
    except MetadataError:
        return False


def _normalize_tag(tag: str) -> str:
    return tag.strip().lstrip("vV")


def _fetch_json(url: str) -> tuple[int, object] | None:
    """Return `(status, payload)`, or `None` when the request could not be completed."""
    request = urllib_request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": PACKAGE_NAME},
    )
    try:
        with urllib_request.urlopen(
            request, timeout=_NETWORK_TIMEOUT_SECONDS
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, payload
    except urllib_error.HTTPError as failure:
        return failure.code, None
    except (urllib_error.URLError, OSError, TimeoutError, json.JSONDecodeError):
        return None


def check_internal_consistency() -> VersionCheck:
    """The shipped constants must agree, or the package was built from a mixed state."""
    inconsistencies: list[str] = []
    manifest = _read_manifest().get("template_version")
    if manifest is not None and manifest != TEMPLATE_VERSION:
        inconsistencies.append(
            f"code reports template {TEMPLATE_VERSION}, manifest declares {manifest}"
        )
    supported = SUPPORTED_TEMPLATE_VERSIONS.get(TEMPLATE_VERSION)
    if supported is None:
        inconsistencies.append(
            f"template {TEMPLATE_VERSION} is not listed in the supported template versions"
        )
    elif supported != __version__:
        inconsistencies.append(
            f"template {TEMPLATE_VERSION} requires CLI {supported}, "
            f"but this CLI is {__version__}"
        )
    if not inconsistencies:
        return VersionCheck("internal", _UP_TO_DATE)
    return VersionCheck(
        "internal",
        _NEWER_AVAILABLE,
        detail="; ".join(inconsistencies),
        warning=(
            "The installed package is internally inconsistent: "
            + "; ".join(inconsistencies)
            + ". Projects generated from it may not build."
        ),
    )


def _read_manifest() -> dict[str, object]:
    """Read the template manifest shipped next to the code, or an empty mapping."""
    manifest_path = Path(__file__).parent / "templates" / "v1" / "manifest.json"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def check_minimum_cli_version() -> VersionCheck:
    """Warn when the installed CLI is older than its own template requires."""
    required = _read_manifest().get("minimum_cli_version")
    if not isinstance(required, str) or not required:
        return VersionCheck("minimum-cli", _UNVERIFIED)
    if not is_newer(required, __version__):
        return VersionCheck("minimum-cli", _UP_TO_DATE)
    return VersionCheck(
        "minimum-cli",
        _NEWER_AVAILABLE,
        detail=required,
        warning=(
            f"The template shipped with this CLI requires android-skeleton {required}, "
            f"but {__version__} is installed. A newer CLI may be required to work with "
            "projects this one generates."
        ),
    )


def check_source_tree() -> VersionCheck:
    """Compare the installed version with the sources it was installed from.

    Only meaningful when the package was installed from a checkout: a plain copy of the files has
    no tree to compare against, and claiming otherwise would be misleading.
    """
    package_directory = Path(__file__).parent
    repository_root = _find_repository_root(package_directory)
    if repository_root is None:
        return VersionCheck("source-tree", _UP_TO_DATE)
    source_version = _read_project_version(repository_root / "pyproject.toml")
    installed = package_version()
    if source_version is None or source_version == installed:
        return VersionCheck("source-tree", _UP_TO_DATE)
    if is_newer(source_version, installed):
        return VersionCheck(
            "source-tree",
            _NEWER_AVAILABLE,
            detail=f"{installed} -> {source_version}",
            warning=(
                f"This CLI reads its code from {repository_root}, which declares version "
                f"{source_version}, while the installed package metadata says {installed}. "
                "The working tree is ahead of the installed copy."
            ),
        )
    return VersionCheck(
        "source-tree",
        _UP_TO_DATE,
        detail=f"{installed} vs {source_version}",
    )


def _find_repository_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "src"
        ).is_dir():
            return candidate
    return None


def _read_project_version(path: Path) -> str | None:
    try:
        with path.open("rb") as project_file:
            import tomllib

            return tomllib.load(project_file)["project"]["version"]
    except (OSError, KeyError, ValueError):
        return None


def check_github_release() -> VersionCheck:
    """Compare with the newest GitHub release, when the repository declares one."""
    url = package_url()
    if url is None:
        return VersionCheck("github-release", _UNVERIFIED)
    slug = _repository_slug(url)
    if slug is None:
        return VersionCheck("github-release", _UNVERIFIED)
    response = _fetch_json(f"{_GITHUB_API}/repos/{slug}/releases/latest")
    if response is None:
        return VersionCheck("github-release", _UNVERIFIED)
    status, payload = response
    if status == 404:
        return VersionCheck("github-release", _NOT_PUBLISHED)
    if status != 200 or not isinstance(payload, Mapping):
        return VersionCheck("github-release", _UNVERIFIED)
    tag = payload.get("tag_name")
    if not isinstance(tag, str) or not tag:
        return VersionCheck("github-release", _UNVERIFIED)
    latest = _normalize_tag(tag)
    if not is_newer(latest, __version__):
        return VersionCheck("github-release", _UP_TO_DATE, detail=latest)
    return VersionCheck(
        "github-release",
        _NEWER_AVAILABLE,
        detail=latest,
        warning=_newer_warning(f"GitHub release {latest}", latest),
    )


def check_published_package() -> VersionCheck:
    """Compare with the version published to the package index, when there is one."""
    response = _fetch_json(f"{_PYPI_API}/{PACKAGE_NAME}/json")
    if response is None:
        return VersionCheck("published-package", _UNVERIFIED)
    status, payload = response
    if status == 404:
        return VersionCheck("published-package", _NOT_PUBLISHED)
    if status != 200 or not isinstance(payload, Mapping):
        return VersionCheck("published-package", _UNVERIFIED)
    info = payload.get("info")
    latest = info.get("version") if isinstance(info, Mapping) else None
    if not isinstance(latest, str) or not latest:
        return VersionCheck("published-package", _UNVERIFIED)
    if not is_newer(latest, __version__):
        return VersionCheck("published-package", _UP_TO_DATE, detail=latest)
    return VersionCheck(
        "published-package",
        _NEWER_AVAILABLE,
        detail=latest,
        warning=_newer_warning(f"published version {latest}", latest),
    )


def _repository_slug(url: str) -> str | None:
    trimmed = url.strip().rstrip("/")
    for prefix in ("https://github.com/", "http://github.com/", "git@github.com:"):
        if trimmed.startswith(prefix):
            remainder = trimmed[len(prefix) :]
            parts = remainder.split("/")
            if len(parts) >= 2 and parts[0] and parts[1]:
                return f"{parts[0]}/{parts[1].removesuffix('.git')}"
    return None


def _newer_warning(source: str, latest: str) -> str:
    return (
        f"android-skeleton {latest} is available ({source}), but {__version__} is "
        "installed. Update with: pipx install --force .  "
        "Generation continues; a newer release may generate a better template."
    )


def project_template_version(project_directory: Path) -> str | None:
    """Template version recorded in a generated project, read without validating the rest."""
    metadata_path = project_directory / ".android-skeleton.json"
    if not metadata_path.is_file():
        return None
    try:
        raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = raw.get("template_version")
    return value if isinstance(value, str) and value else None


def build_template_mismatch_message(project_version: str) -> str:
    """Explain a project whose template this CLI cannot serve, and how to proceed anyway."""
    return "\n".join(
        (
            f"This project was created by template {project_version}, but the installed "
            f"android-skeleton {__version__} ships template {TEMPLATE_VERSION}.",
            "",
            "The feature files would be written where this CLI's Gradle layout does not expect",
            "them, so the project would not build. Either:",
            "  - regenerate the project with this CLI, or",
            "  - install an android-skeleton that supports template "
            f"{project_version}, or",
            "  - pass --force to write the files anyway and accept that they may not build.",
        )
    )


def collect_checks(*, include_network: bool = True) -> list[VersionCheck]:
    """Run every check that does not need a project directory."""
    checks = [
        check_internal_consistency(),
        check_minimum_cli_version(),
        check_source_tree(),
    ]
    if include_network:
        checks.append(check_github_release())
        checks.append(check_published_package())
    return checks


def format_version_header() -> str:
    return (
        f"android-skeleton {__version__} (Android template {TEMPLATE_VERSION})"
    )


def format_warnings(checks: Sequence[VersionCheck]) -> list[str]:
    """Render warnings and the 'could not verify' notices, skipping the silent states."""
    lines = [check.warning for check in checks if check.warning is not None]
    unverified = [check.name for check in checks if check.status == _UNVERIFIED]
    if unverified:
        lines.append(
            "Could not confirm whether a newer android-skeleton is available "
            f"({', '.join(unverified)}). Generation continues."
        )
    return lines