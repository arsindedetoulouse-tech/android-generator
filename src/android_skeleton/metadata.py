from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from . import TEMPLATE_VERSION, __version__

METADATA_SCHEMA_VERSION = 1
SUPPORTED_TEMPLATE_VERSIONS: dict[str, str] = {
    TEMPLATE_VERSION: "0.3.0",
}
_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class MetadataError(ValueError):
    """Raised when generated-project metadata is malformed or unsupported."""


@dataclass(frozen=True)
class ProjectMetadata:
    schema_version: int
    cli_version: str
    template_version: str
    project_name: str
    package_name: str
    application_id: str
    options: dict[str, object]
    features: tuple[str, ...]


def create_project_metadata(
    *,
    project_name: str,
    package_name: str,
    application_id: str,
    options: Mapping[str, object] | None = None,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "schema_version": METADATA_SCHEMA_VERSION,
        "cli_version": __version__,
        "template_version": TEMPLATE_VERSION,
        "project_name": project_name,
        "package_name": package_name,
        "application_id": application_id,
        "options": dict(options or {}),
        "features": [],
    }
    validate_project_metadata(metadata)
    return metadata


def validate_project_metadata(
    value: object,
    *,
    cli_version: str = __version__,
    supported_template_versions: Mapping[str, str] = SUPPORTED_TEMPLATE_VERSIONS,
) -> ProjectMetadata:
    if not isinstance(value, dict):
        raise MetadataError("Project metadata must be a JSON object")
    if type(value.get("schema_version")) is not int or value["schema_version"] != METADATA_SCHEMA_VERSION:
        raise MetadataError(f"Unsupported metadata schema version: {value.get('schema_version')!r}")

    template_version = _required_string(value, "template_version")
    minimum_cli_version = supported_template_versions.get(template_version)
    if minimum_cli_version is None:
        raise MetadataError(f"Unsupported template version: {template_version}")
    if _parse_version(cli_version) < _parse_version(minimum_cli_version):
        raise MetadataError(
            f"Template {template_version} requires CLI version {minimum_cli_version} or newer"
        )

    metadata_cli_version = _required_string(value, "cli_version")
    _parse_version(metadata_cli_version)
    options = value.get("options")
    if not isinstance(options, dict):
        raise MetadataError("Metadata field 'options' must be a JSON object")
    features = value.get("features")
    if not isinstance(features, list) or not all(isinstance(feature, str) for feature in features):
        raise MetadataError("Metadata field 'features' must be a list of strings")

    return ProjectMetadata(
        schema_version=METADATA_SCHEMA_VERSION,
        cli_version=metadata_cli_version,
        template_version=template_version,
        project_name=_required_string(value, "project_name"),
        package_name=_required_string(value, "package_name"),
        application_id=_required_string(value, "application_id"),
        options=options,
        features=tuple(features),
    )


def _required_string(value: Mapping[str, object], key: str) -> str:
    field = value.get(key)
    if not isinstance(field, str) or not field:
        raise MetadataError(f"Metadata field {key!r} must be a non-empty string")
    return field


def _parse_version(value: str) -> tuple[int, int, int]:
    match = _VERSION_PATTERN.fullmatch(value)
    if match is None:
        raise MetadataError(f"Invalid semantic version: {value!r}")
    return tuple(int(part) for part in match.groups())
