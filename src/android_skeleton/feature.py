from __future__ import annotations

import json
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from xml.sax.saxutils import escape

from .metadata import MetadataError, ProjectMetadata, validate_project_metadata
from .validation import (
    InputValidationError,
    validate_android_application_id,
    validate_android_package,
)

_FEATURE_SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)*$")
_METADATA_FILENAME = ".android-skeleton.json"
_FEATURE_TEMPLATE_ROOT = files("android_skeleton").joinpath(
    "templates", "v1", "add-feature"
)
_INITIAL_FEATURE_TEMPLATE_ROOT = files("android_skeleton").joinpath(
    "templates", "v1", "initial-feature"
)
_TEXT_SUFFIXES = {".json", ".kt", ".kts", ".xml"}

# Feature slugs a generated project already occupies. `create` renders these, so `add-feature`
# must refuse them explicitly: relying on the metadata match alone would report a confusing
# "already registered" instead of naming the reason.
RESERVED_FEATURE_SLUGS = ("home",)

# Where each template tree of `add-feature` lands in the generated project. The domain and data layers
# are shared by every feature, so they render into the common modules rather than into the feature
# module; each feature still gets its own package inside them, so two features may declare types with
# the same name.
_FEATURE_MODULE_ROOTS = {
    "module": "feature/{slug}",
    "api-module": "feature/{slug}-api",
    "common-domain": "common/domain",
    "common-data": "common/data",
}


class FeatureValidationError(ValueError):
    """Raised when a feature request cannot be applied to this project."""


@dataclass(frozen=True)
class FeatureIdentity:
    slug: str
    package_segment: str
    type_name: str


@dataclass(frozen=True)
class FeatureRequest:
    identity: FeatureIdentity
    metadata: ProjectMetadata


@dataclass(frozen=True)
class FeaturePlan:
    new_files: Mapping[Path, bytes]
    updated_files: Mapping[Path, bytes]
    original_files: Mapping[Path, bytes]


def parse_feature_slug(value: str) -> FeatureIdentity:
    if not _FEATURE_SLUG_PATTERN.fullmatch(value):
        raise FeatureValidationError(
            "Feature name must be a lowercase kebab-case slug "
            "with each segment starting with a letter"
        )

    words = value.split("-")
    return FeatureIdentity(
        slug=value,
        package_segment="".join(words),
        type_name="".join(word[0].upper() + word[1:] for word in words),
    )


def validate_feature_request(
    project_directory: Path,
    feature_slug: str,
    *,
    force: bool = False,
) -> FeatureRequest:
    identity = parse_feature_slug(feature_slug)
    if identity.slug in RESERVED_FEATURE_SLUGS:
        raise FeatureValidationError(
            f"Feature name {identity.slug!r} is reserved for the initial "
            "screen of the application; choose a different name"
        )
    metadata_path = project_directory / _METADATA_FILENAME
    if metadata_path.is_symlink():
        raise FeatureValidationError(
            f"Project metadata must not be a symbolic link: {_METADATA_FILENAME}"
        )
    if not metadata_path.is_file():
        raise FeatureValidationError(
            f"Unsupported project: required metadata file {_METADATA_FILENAME} is missing"
        )

    try:
        raw_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FeatureValidationError(
            f"Unsupported project metadata in {_METADATA_FILENAME}: {error}"
        ) from error

    try:
        # `force` still requires the metadata to be structurally sound; only the template
        # compatibility rule is skipped, because that is the single check the user overrides.
        metadata = validate_project_metadata(
            raw_metadata, enforce_template_version=not force
        )
        validate_android_package(metadata.package_name, "metadata package_name")
        validate_android_application_id(metadata.application_id)
    except (MetadataError, InputValidationError) as error:
        raise FeatureValidationError(f"Unsupported project metadata: {error}") from error

    for existing_slug in metadata.features:
        try:
            existing_identity = parse_feature_slug(existing_slug)
        except FeatureValidationError as error:
            raise FeatureValidationError(
                f"Unsupported project metadata: invalid feature slug {existing_slug!r}"
            ) from error
        if existing_identity.slug == identity.slug:
            raise FeatureValidationError(
                f"Feature {identity.slug!r} is already registered in project metadata"
            )

    feature_root = project_directory / "feature"
    if feature_root.is_symlink() or (
        feature_root.exists() and not feature_root.is_dir()
    ):
        raise FeatureValidationError(
            "Feature destination conflicts with an existing path: feature"
        )
    for destination in (
        feature_root / identity.slug,
        feature_root / f"{identity.slug}-api",
    ):
        if destination.exists() or destination.is_symlink():
            raise FeatureValidationError(
                f"Feature destination already exists: {destination.relative_to(project_directory)}"
            )

    return FeatureRequest(identity=identity, metadata=metadata)


def render_reserved_feature(
    metadata: ProjectMetadata,
    slug: str,
) -> dict[Path, bytes]:
    """Render the files of a feature the project ships with, keyed by relative path.

    Used by `create` so that a generated project starts with the same feature skeleton `add-feature`
    would produce, instead of a second, reduced template that would drift from it.
    """
    if slug not in RESERVED_FEATURE_SLUGS:
        raise FeatureValidationError(f"Feature name {slug!r} is not reserved")
    request = FeatureRequest(identity=parse_feature_slug(slug), metadata=metadata)
    rendered = _render_feature_tree(_FEATURE_TEMPLATE_ROOT, request)
    # The start screen is the one destination the user cannot navigate back from, so it ships its own
    # layout. Overriding single files keeps the rest of the chain identical to a regular feature.
    for relative_path, content in _render_feature_tree(
        _INITIAL_FEATURE_TEMPLATE_ROOT, request
    ).items():
        rendered[relative_path] = content
    return rendered


def prepare_feature_plan(
    project_directory: Path,
    request: FeatureRequest,
    *,
    force: bool = False,
) -> FeaturePlan:
    new_files = _render_feature_templates(request)
    original_files: dict[Path, bytes] = {}
    updated_files = _render_feature_project_updates(
        project_directory,
        request,
        original_files,
        force=force,
    )
    _validate_feature_plan(
        project_directory,
        new_files,
        updated_files,
        original_files,
    )
    return FeaturePlan(
        new_files=new_files,
        updated_files=updated_files,
        original_files=original_files,
    )


def apply_feature_plan(project_directory: Path, plan: FeaturePlan) -> None:
    all_paths = [*plan.new_files, *plan.updated_files]
    created_files: list[Path] = []
    created_directories: list[Path] = []
    staged_files: dict[Path, Path] = {}
    backup_files: dict[Path, Path] = {}
    succeeded = False
    rollback_incomplete = False
    try:
        _validate_feature_plan(
            project_directory,
            plan.new_files,
            plan.updated_files,
            plan.original_files,
        )
        for relative_path in all_paths:
            destination = project_directory / relative_path
            _ensure_parent_directories(
                project_directory,
                destination.parent,
                created_directories,
            )
            staged = _write_staged_file(
                destination,
                plan.new_files.get(relative_path, plan.updated_files.get(relative_path)),
                plan.original_files.get(relative_path),
            )
            staged_files[destination] = staged

        for relative_path in plan.updated_files:
            destination = project_directory / relative_path
            backup = _create_backup(destination)
            backup_files[destination] = backup

        _validate_feature_plan(
            project_directory,
            plan.new_files,
            plan.updated_files,
            plan.original_files,
        )
        for relative_path in all_paths:
            destination = project_directory / relative_path
            staged = staged_files[destination]
            if relative_path in plan.new_files:
                os.link(staged, destination)
                created_files.append(destination)
                staged.unlink()
                continue
            os.replace(staged, destination)
            created_files.append(destination)
        succeeded = True
    except (OSError, FeatureValidationError) as error:
        rollback_errors: list[OSError] = []
        for destination in reversed(created_files):
            try:
                destination.unlink(missing_ok=True)
            except OSError as rollback_error:
                rollback_errors.append(rollback_error)
        for destination, backup in reversed(tuple(backup_files.items())):
            try:
                if backup.exists():
                    os.replace(backup, destination)
            except OSError as rollback_error:
                rollback_errors.append(rollback_error)
        if rollback_errors:
            rollback_incomplete = True
            details = "; ".join(str(rollback_error) for rollback_error in rollback_errors)
            raise FeatureValidationError(
                f"Failed to apply feature plan and rollback was incomplete: {details}"
            ) from error
        if isinstance(error, FeatureValidationError):
            raise
        raise FeatureValidationError(f"Failed to apply feature plan: {error}") from error
    finally:
        cleanup_errors: list[OSError] = []
        for staged in staged_files.values():
            try:
                staged.unlink(missing_ok=True)
            except OSError as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if not rollback_incomplete:
            for backup in backup_files.values():
                try:
                    backup.unlink(missing_ok=True)
                except OSError as cleanup_error:
                    cleanup_errors.append(cleanup_error)
        if cleanup_errors:
            details = "; ".join(str(error) for error in cleanup_errors)
            raise FeatureValidationError(
                f"Feature plan applied but temporary files could not be removed: {details}"
            )
        if not succeeded and not rollback_incomplete:
            _remove_empty_directories(created_directories)


def _validate_feature_plan(
    project_directory: Path,
    new_files: Mapping[Path, bytes],
    updated_files: Mapping[Path, bytes],
    original_files: Mapping[Path, bytes],
) -> None:
    root = project_directory.resolve(strict=True)
    if not root.is_dir():
        raise FeatureValidationError(f"Project directory is not a directory: {root}")
    if set(new_files).intersection(updated_files):
        raise FeatureValidationError("Feature plan contains duplicate target paths")

    for relative_path in new_files:
        _validate_project_path(root, relative_path)
        destination = root / relative_path
        if destination.exists() or destination.is_symlink():
            raise FeatureValidationError(
                f"Feature destination already exists: {relative_path}"
            )
        _validate_parent_chain(root, destination.parent)

    for relative_path in updated_files:
        _validate_project_path(root, relative_path)
        destination = root / relative_path
        _validate_parent_chain(root, destination.parent)
        if destination.is_symlink() or not destination.is_file():
            raise FeatureValidationError(
                f"Unsupported or unsafe project file: {relative_path}"
            )
        try:
            current_contents = destination.read_bytes()
        except OSError as error:
            raise FeatureValidationError(
                f"Could not read project file {relative_path}: {error}"
            ) from error
        if current_contents != original_files.get(relative_path):
            raise FeatureValidationError(
                f"Project file changed while preparing feature plan: {relative_path}"
            )


def _validate_project_path(root: Path, relative_path: Path) -> None:
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise FeatureValidationError(f"Unsafe feature target path: {relative_path}")
    destination = root / relative_path
    try:
        resolved = destination.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise FeatureValidationError(
            f"Could not resolve feature target path {relative_path}: {error}"
        ) from error
    if not resolved.is_relative_to(root):
        raise FeatureValidationError(
            f"Feature target path escapes project directory: {relative_path}"
        )


def _validate_parent_chain(root: Path, parent: Path) -> None:
    current = parent
    while current != root:
        if current.is_symlink():
            raise FeatureValidationError(
                f"Feature target path contains a symbolic link: {current.relative_to(root)}"
            )
        if current.exists() and not current.is_dir():
            raise FeatureValidationError(
                f"Feature target parent is not a directory: {current.relative_to(root)}"
            )
        if current.parent == current:
            raise FeatureValidationError("Feature target path is outside the project")
        current = current.parent


def _ensure_parent_directories(
    root: Path,
    parent: Path,
    created_directories: list[Path],
) -> None:
    missing: list[Path] = []
    current = parent
    while current != root and not current.exists():
        missing.append(current)
        current = current.parent
    _validate_parent_chain(root, current)
    for directory in reversed(missing):
        directory.mkdir()
        created_directories.append(directory)


def _write_staged_file(
    destination: Path,
    content: bytes | None,
    original_content: bytes | None,
) -> Path:
    if content is None:
        raise FeatureValidationError(
            f"Feature plan has no content for {destination}"
        )
    staged: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".android-skeleton-stage-",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            staged = Path(temporary.name)
            temporary.write(content)
        if original_content is not None:
            staged.chmod(stat.S_IMODE(destination.stat().st_mode))
        else:
            staged.chmod(0o644)
        return staged
    except OSError:
        if staged is not None:
            staged.unlink(missing_ok=True)
        raise


def _create_backup(destination: Path) -> Path:
    with tempfile.NamedTemporaryFile(
        prefix=".android-skeleton-backup-",
        dir=destination.parent,
        delete=False,
    ) as temporary:
        backup = Path(temporary.name)
    try:
        shutil.copy2(destination, backup)
    except OSError:
        backup.unlink(missing_ok=True)
        raise
    return backup


def _remove_empty_directories(directories: list[Path]) -> None:
    errors: list[OSError] = []
    for directory in reversed(directories):
        try:
            directory.rmdir()
        except FileNotFoundError:
            continue
        except OSError as error:
            errors.append(error)
    if errors:
        details = "; ".join(str(error) for error in errors)
        raise FeatureValidationError(
            f"Feature files are in place but temporary directories remain: {details}"
        )


def _render_feature_templates(request: FeatureRequest) -> dict[Path, bytes]:
    return _render_feature_tree(_FEATURE_TEMPLATE_ROOT, request)


def _render_feature_tree(
    template_root: Traversable,
    request: FeatureRequest,
) -> dict[Path, bytes]:
    identity = request.identity
    package_name = request.metadata.package_name
    package_path = package_name.replace(".", "/")
    feature_title = " ".join(word.capitalize() for word in identity.slug.split("-"))
    replacements = {
        "__PACKAGE__": package_name,
        "__PACKAGE_PATH__": package_path,
        "__FEATURE_PACKAGE_SEGMENT__": identity.package_segment,
        "__FEATURE_TYPE__": identity.type_name,
        "__FEATURE_SLUG__": identity.slug,
        "__FEATURE_LOWER_CAMEL__": (
            identity.type_name[0].lower() + identity.type_name[1:]
        ),
        "__FEATURE_API_MODULE__": f":feature:{identity.slug}-api",
        # Resource names are merged across every feature library, so they must carry the slug:
        # two features declaring `feature_title` would silently resolve to whichever library is
        # merged last, and the start screen would show another feature's title.
        "__FEATURE_STRING_PREFIX__": f"feature_{identity.slug.replace('-', '_')}",
        "__FEATURE_TITLE_XML__": escape(
            feature_title,
            {'"': "&quot;", "'": "&apos;"},
        ),
    }
    rendered: dict[Path, bytes] = {}
    for relative_parts, resource in _feature_template_files(template_root):
        if len(relative_parts) < 2 or relative_parts[0] not in _FEATURE_MODULE_ROOTS:
            raise FeatureValidationError(
                f"Invalid feature template path: {'/'.join(relative_parts)}"
            )
        module_root = _FEATURE_MODULE_ROOTS[relative_parts[0]].format(
            slug=identity.slug
        )
        destination_parts = [module_root]
        for part in relative_parts[1:]:
            expanded = part.replace("__PACKAGE_PATH__", package_path)
            for placeholder, replacement in replacements.items():
                expanded = expanded.replace(placeholder, replacement)
            destination_parts.extend(expanded.split("/"))
        relative_path = Path(*destination_parts)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise FeatureValidationError(
                f"Unsafe feature template path: {'/'.join(relative_parts)}"
            )

        content = resource.read_bytes()
        if relative_path.suffix in _TEXT_SUFFIXES:
            text = content.decode("utf-8")
            for placeholder, replacement in replacements.items():
                text = text.replace(placeholder, replacement)
            content = text.encode("utf-8")
        if relative_path in rendered:
            raise FeatureValidationError(f"Duplicate feature template path: {relative_path}")
        rendered[relative_path] = content
    return rendered


def _render_feature_project_updates(
    project_directory: Path,
    request: FeatureRequest,
    original_files: dict[Path, bytes],
    *,
    force: bool = False,
) -> dict[Path, bytes]:
    identity = request.identity
    slug = identity.slug
    feature_module = f":feature:{slug}"
    api_module = f":feature:{slug}-api"
    package = request.metadata.package_name
    module_name = identity.type_name[0].lower() + identity.type_name[1:] + "Module"

    def read_project_file(relative_path: Path) -> str:
        raw = _read_project_bytes(project_directory, relative_path)
        original_files[relative_path] = raw
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise FeatureValidationError(
                f"Could not decode project file {relative_path}: {error}"
            ) from error

    metadata_path = Path(_METADATA_FILENAME)
    try:
        current_metadata = validate_project_metadata(
            json.loads(read_project_file(metadata_path)),
            enforce_template_version=not force,
        )
    except (json.JSONDecodeError, MetadataError) as error:
        raise FeatureValidationError(
            f"Unsupported project metadata in {_METADATA_FILENAME}: {error}"
        ) from error
    if current_metadata != request.metadata:
        raise FeatureValidationError(
            "Project metadata changed while preparing feature plan"
        )

    settings_path = Path("settings.gradle.kts")
    settings = read_project_file(settings_path)
    if feature_module in settings or api_module in settings:
        raise FeatureValidationError(f"Feature {slug!r} is already registered in Gradle")
    include_anchor = '    ":feature:home-api",'
    if settings.count(include_anchor) != 1:
        raise FeatureValidationError(
            "Unsupported project: could not locate feature module registration in settings.gradle.kts"
        )
    settings = settings.replace(
        include_anchor,
        include_anchor
        + f'\n    "{feature_module}",\n    "{api_module}",',
        1,
    )

    app_build_path = Path("app/build.gradle.kts")
    app_build = read_project_file(app_build_path)
    app_dependency = f'implementation(project("{feature_module}"))'
    if app_dependency in app_build:
        raise FeatureValidationError(f"Feature {feature_module} is already registered in app")
    app_anchor = '    implementation(project(":app:navigation"))'
    if app_build.count(app_anchor) != 1:
        raise FeatureValidationError(
            "Unsupported project: could not locate app dependencies in app/build.gradle.kts"
        )
    app_build = app_build.replace(
        app_anchor,
        f"{app_anchor}\n    {app_dependency}",
        1,
    )

    navigation_build_path = Path("app/navigation/build.gradle.kts")
    navigation_build = read_project_file(navigation_build_path)
    api_dependency = f'api(project("{api_module}"))'
    if api_dependency in navigation_build:
        raise FeatureValidationError(f"Feature API {api_module} is already registered")
    navigation_build = _append_gradle_dependency(navigation_build, api_dependency)

    app_source_path = Path("app/src/main/kotlin") / Path(
        *package.split(".")
    ) / "App.kt"
    app_source = read_project_file(app_source_path)
    module_import = (
        f"import {package}.feature.{identity.package_segment}."
        f"di.{module_name}"
    )
    if module_import in app_source or module_name in app_source:
        raise FeatureValidationError(
            f"Feature Koin module {module_name} is already registered"
        )
    app_import_anchor = "import org.koin.android.ext.koin.androidContext"
    if app_source.count(app_import_anchor) != 1:
        raise FeatureValidationError(
            "Unsupported project: could not locate Koin imports in the application"
        )
    app_source = app_source.replace(
        app_import_anchor,
        f"{module_import}\n{app_import_anchor}",
        1,
    )
    module_call = re.search(
        r"(?m)^([ \t]*modules\()([^\n]*)(\)[ \t]*)$",
        app_source,
    )
    if module_call is None:
        raise FeatureValidationError(
            "Unsupported project: could not locate Koin module registration in the application"
        )
    app_source = (
        app_source[: module_call.start()]
        + module_call.group(1)
        + module_call.group(2).rstrip()
        + f", {module_name}"
        + module_call.group(3)
        + app_source[module_call.end() :]
    )

    metadata = {
        "schema_version": request.metadata.schema_version,
        "cli_version": request.metadata.cli_version,
        "template_version": request.metadata.template_version,
        "project_name": request.metadata.project_name,
        "package_name": request.metadata.package_name,
        "application_id": request.metadata.application_id,
        "options": request.metadata.options,
        "features": [*request.metadata.features, slug],
    }
    return {
        settings_path: settings.encode("utf-8"),
        app_build_path: app_build.encode("utf-8"),
        navigation_build_path: navigation_build.encode("utf-8"),
        app_source_path: app_source.encode("utf-8"),
        metadata_path: (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode(
            "utf-8"
        ),
    }


def _append_gradle_dependency(source: str, dependency: str) -> str:
    match = re.search(r"(?m)^([ \t]*dependencies[ \t]*\{)", source)
    if match is not None:
        return (
            source[: match.end()]
            + f"\n    {dependency}"
            + source[match.end() :]
        )
    return source.rstrip() + f"\n\ndependencies {{\n    {dependency}\n}}\n"


def _read_project_bytes(project_directory: Path, relative_path: Path) -> bytes:
    root = project_directory.resolve(strict=True)
    _validate_project_path(root, relative_path)
    path = root / relative_path
    _validate_parent_chain(root, path.parent)
    if path.is_symlink() or not path.is_file():
        raise FeatureValidationError(
            f"Unsupported project: required file is missing or unsafe: {relative_path}"
        )
    try:
        return path.read_bytes()
    except OSError as error:
        raise FeatureValidationError(
            f"Could not read project file {relative_path}: {error}"
        ) from error


def _feature_template_files(
    directory: Traversable,
    parent_parts: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], Traversable]]:
    entries: list[tuple[tuple[str, ...], Traversable]] = []
    for entry in directory.iterdir():
        relative_parts = (*parent_parts, entry.name)
        if entry.is_dir():
            entries.extend(_feature_template_files(entry, relative_parts))
        elif entry.is_file():
            entries.append((relative_parts, entry))
    return entries
