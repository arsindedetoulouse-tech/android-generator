from __future__ import annotations

import json
import os
from collections.abc import Iterator, Mapping, Sequence
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from xml.sax.saxutils import escape

from .feature import FeatureValidationError, render_reserved_feature
from .metadata import create_project_metadata, validate_project_metadata
from .validation import normalize_locale_tags

_TEMPLATE_ROOT = files("android_skeleton").joinpath("templates", "v1")
_TEXT_SUFFIXES = {".bat", ".kt", ".kts", ".properties", ".toml", ".xml"}

# The start screen is a feature like any other: it has its own route, section and resources, and is
# the only destination the composition root does not own.
_INITIAL_FEATURE_SLUG = "home"


class ProjectCreationError(ValueError):
    """Raised when a project cannot be created safely."""


def create_project(
    *,
    output_directory: Path,
    project_name: str,
    package_name: str,
    application_id: str,
    locales: Sequence[str] = (),
    network: bool = False,
) -> None:
    locales = normalize_locale_tags(locales)
    if not output_directory.is_dir():
        raise ProjectCreationError(
            f"Project directory does not exist: {output_directory}"
        )
    if any(output_directory.iterdir()):
        raise ProjectCreationError(
            "Project creation requires an empty current directory"
        )
    if not project_name or not project_name.strip():
        raise ProjectCreationError("--name must not be empty")
    if not all(_is_xml_character(ord(character)) for character in project_name):
        raise ProjectCreationError("--name contains characters that cannot be rendered")

    metadata = create_project_metadata(
        project_name=project_name,
        package_name=package_name,
        application_id=application_id,
        options={"network": network, "locales": list(locales)},
    )
    metadata["features"] = [_INITIAL_FEATURE_SLUG]
    feature_metadata = validate_project_metadata(metadata)
    planned_files = _render_template(
        project_name=project_name,
        package_name=package_name,
        application_id=application_id,
        locales=locales,
        network=network,
    )
    try:
        initial_feature_files = render_reserved_feature(
            feature_metadata, _INITIAL_FEATURE_SLUG
        )
    except FeatureValidationError as error:
        raise ProjectCreationError(str(error)) from error
    # `dict.update` would silently overwrite a template file that collided with a generated
    # feature path, hiding a template layout that no longer matches the generator.
    collisions = sorted(
        relative_path.as_posix()
        for relative_path in initial_feature_files.keys() & planned_files.keys()
    )
    if collisions:
        raise ProjectCreationError(
            "Template layout collides with the initial feature at: "
            + ", ".join(collisions)
        )
    planned_files.update(initial_feature_files)
    planned_files.update(_render_locale_resources(project_name, locales))
    planned_files[Path(".android-skeleton.json")] = (
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")

    _write_new_files(output_directory, planned_files)


def _render_template(
    *,
    project_name: str,
    package_name: str,
    application_id: str,
    locales: Sequence[str],
    network: bool,
) -> dict[Path, bytes]:
    rendered: dict[Path, bytes] = {}
    package_path = package_name.replace(".", "/")
    selected_modules = {"network"} if network else set()
    replacements = _optional_replacements(network=network)
    for relative_parts, resource in _template_files(_TEMPLATE_ROOT):
        if relative_parts == ("manifest.json",) or relative_parts[0] in (
            "add-feature",
            "initial-feature",
        ):
            continue
        if relative_parts[0] == "optional":
            if relative_parts[1] not in selected_modules:
                continue
            relative_parts = relative_parts[2:]

        destination_parts: list[str] = []
        for part in relative_parts:
            if part == "__PACKAGE_PATH__":
                destination_parts.extend(package_path.split("/"))
            else:
                destination_parts.append(part)
        relative_path = Path(*destination_parts)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ProjectCreationError(
                f"Unsafe template path: {'/'.join(relative_parts)}"
            )

        content = resource.read_bytes()
        if relative_path.suffix in _TEXT_SUFFIXES:
            text = _apply_replacements(content.decode("utf-8"), replacements)
            text = text.replace("__PACKAGE__", package_name)
            text = text.replace("__APPLICATION_ID__", application_id)
            text = text.replace("__PROJECT_NAME__", _escape_project_name(project_name))
            text = text.replace(
                "__PROJECT_NAME_XML__",
                escape(project_name, {'"': "&quot;", "'": "&apos;"}),
            )
            text = text.replace(
                "__LOCALE_CONFIG__",
                'android:localeConfig="@xml/locale_config"' if locales else "",
            )
            content = text.encode("utf-8")
        if relative_path in rendered:
            raise ProjectCreationError(f"Duplicate template path: {relative_path}")
        rendered[relative_path] = content
    return rendered


def _apply_replacements(text: str, replacements: Mapping[str, str]) -> str:
    """Substitute optional placeholders, dropping lines that become empty.

    A placeholder that occupies a whole line and renders to nothing would otherwise leave a blank
    line behind, which is invisible in Gradle but breaks version catalogs and any check that expects
    every emitted line to carry content.
    """
    rendered: list[str] = []
    for line in text.split("\n"):
        placeholder = line.strip()
        if placeholder in replacements:
            replacement = replacements[placeholder]
            if replacement:
                rendered.extend(replacement.split("\n"))
            continue
        for name, replacement in replacements.items():
            line = line.replace(name, replacement)
        rendered.append(line)
    return "\n".join(rendered)


def _optional_replacements(*, network: bool) -> dict[str, str]:
    includes: list[str] = []
    dependencies: list[str] = []
    imports: list[str] = []
    koin_modules: list[str] = []
    ktor_version = ""
    ktor_libraries = ""
    permissions = ""
    koin_libraries = ""
    if network:
        includes.append('    ":core:network",')
        dependencies.append('    implementation(project(":core:network"))')
        imports.append("import __PACKAGE__.core.network.coreNetworkModule")
        koin_modules.append("coreNetworkModule")
        permissions = (
            '    <uses-permission android:name="android.permission.INTERNET" />'
        )
        ktor_version = 'ktor = "3.5.2"'
        koin_libraries = (
            'koin-core = { module = "io.insert-koin:koin-core", version.ref = "koin" }'
        )
        ktor_libraries = "\n".join(
            (
                'ktor-client-content-negotiation = { module = "io.ktor:ktor-client-content-negotiation", version.ref = "ktor" }',
                'ktor-client-core = { module = "io.ktor:ktor-client-core", version.ref = "ktor" }',
                'ktor-client-okhttp = { module = "io.ktor:ktor-client-okhttp", version.ref = "ktor" }',
                'ktor-serialization-kotlinx-json = { module = "io.ktor:ktor-serialization-kotlinx-json", version.ref = "ktor" }',
            )
        )

    return {
        "__OPTIONAL_MODULE_INCLUDES__": (
            "\n" + "\n".join(includes) if includes else ""
        ),
        "__OPTIONAL_APP_DEPENDENCIES__": "\n".join(dependencies),
        "__OPTIONAL_KOIN_IMPORTS__": (
            ("\n" + "\n".join(imports)) if imports else ""
        ),
        "__OPTIONAL_KOIN_MODULES__": (
            ", " + ", ".join(koin_modules) if koin_modules else ""
        ),
        "__OPTIONAL_PERMISSIONS__": permissions,
        "__OPTIONAL_KTOR_VERSION__": ktor_version,
        "__OPTIONAL_KOIN_LIBRARIES__": koin_libraries,
        "__OPTIONAL_KTOR_LIBRARIES__": ktor_libraries,
    }


def _render_locale_resources(
    project_name: str,
    locales: Sequence[str],
) -> dict[Path, bytes]:
    if not locales:
        return {}

    localized_name = escape(
        project_name,
        {'"': "&quot;", "'": "&apos;"},
    )
    resources = {
        Path("app/src/main/res/xml/locale_config.xml"): (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<locale-config xmlns:android="http://schemas.android.com/apk/res/android">\n'
            + "".join(
                f'    <locale android:name="{locale}" />\n' for locale in locales
            )
            + "</locale-config>\n"
        ).encode("utf-8")
    }
    for locale in locales:
        qualifier = locale.replace("-", "+")
        resources[
            Path(f"app/src/main/res/values-b+{qualifier}/strings.xml")
        ] = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<resources>\n"
            f'    <string name="app_name">{localized_name}</string>\n'
            "</resources>\n"
        ).encode("utf-8")
    return resources


def _escape_project_name(project_name: str) -> str:
    return json.dumps(project_name, ensure_ascii=False)[1:-1].replace("$", "\\$")


def _template_files(
    directory: Traversable,
    parent_parts: tuple[str, ...] = (),
) -> Iterator[tuple[tuple[str, ...], Traversable]]:
    for entry in directory.iterdir():
        relative_parts = (*parent_parts, entry.name)
        if entry.is_dir():
            yield from _template_files(entry, relative_parts)
        elif entry.is_file():
            yield relative_parts, entry


def _write_new_files(output_directory: Path, planned_files: Mapping[Path, bytes]) -> None:
    created_files: list[Path] = []
    created_directories: list[Path] = []
    try:
        if any(output_directory.iterdir()):
            raise ProjectCreationError(
                "Project creation requires an empty current directory"
            )
        for relative_path, content in planned_files.items():
            destination = output_directory / relative_path
            missing_parents: list[Path] = []
            parent = destination.parent
            while parent != output_directory and not parent.exists():
                missing_parents.append(parent)
                parent = parent.parent
            for directory in reversed(missing_parents):
                directory.mkdir()
                created_directories.append(directory)
            try:
                with destination.open("xb") as output_file:
                    created_files.append(destination)
                    output_file.write(content)
            except FileExistsError as error:
                raise ProjectCreationError(
                    f"Project creation conflict at {relative_path}"
                ) from error
            if relative_path == Path("gradlew") and os.name == "posix":
                destination.chmod(0o755)
    except (OSError, ProjectCreationError) as error:
        rollback_errors: list[OSError] = []
        for created_file in reversed(created_files):
            try:
                created_file.unlink(missing_ok=True)
            except OSError as rollback_error:
                rollback_errors.append(rollback_error)
        for created_directory in reversed(created_directories):
            try:
                created_directory.rmdir()
            except OSError as rollback_error:
                rollback_errors.append(rollback_error)
        if rollback_errors:
            details = "; ".join(str(rollback_error) for rollback_error in rollback_errors)
            raise ProjectCreationError(
                f"Failed to create project files and rollback was incomplete: {details}"
            ) from error
        if isinstance(error, ProjectCreationError):
            raise
        raise ProjectCreationError(f"Failed to create project files: {error}") from error


def _is_xml_character(codepoint: int) -> bool:
    return (
        codepoint in (0x9, 0xA, 0xD)
        or 0x20 <= codepoint <= 0xD7FF
        or 0xE000 <= codepoint <= 0xFFFD
        or 0x10000 <= codepoint <= 0x10FFFF
    )
