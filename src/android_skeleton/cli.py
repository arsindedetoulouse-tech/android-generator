from __future__ import annotations

import argparse
from collections.abc import Sequence
import os
from pathlib import Path
import subprocess
import sys

from .feature import (
    FeatureRequest,
    FeatureValidationError,
    apply_feature_plan,
    prepare_feature_plan,
    validate_feature_request,
)
from .project import ProjectCreationError, create_project
from .sdk import (
    build_invalid_sdk_message,
    build_missing_platform_message,
    build_unconfigured_sdk_message,
    installed_api_levels,
    missing_api_levels,
    resolve_sdk,
    validate_sdk_directory,
    write_local_properties,
)
from .validation import (
    InputValidationError,
    validate_android_application_id,
    validate_android_package,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="android-skeleton",
        description="Generate a modular Android application project.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser(
        "create", help="Generate a project in the current directory"
    )
    create.add_argument("--package", required=True, help="Kotlin/Android namespace")
    create.add_argument(
        "--application-id", required=True, help="Android application ID"
    )
    create.add_argument("--name", help="Override the project and app display name")
    create.add_argument("--network", action="store_true", help="Include core:network")
    create.add_argument(
        "--locale", action="append", default=[], help="Add a locale; may be repeated"
    )
    create.add_argument("--git-init", action="store_true", help="Initialize Git")
    create.add_argument(
        "--verify", action="store_true", help="Run Gradle verification after creation"
    )
    create.add_argument(
        "--sdk-dir",
        help="Android SDK location to record in the project's local.properties",
    )
    feature = commands.add_parser("add-feature", help="Add a feature module")
    feature.add_argument("name", help="Feature slug")
    feature.add_argument(
        "--dry-run", action="store_true", help="Show changes without writing"
    )
    feature.add_argument(
        "--verify",
        action="store_true",
        help="Run Gradle verification after adding the feature",
    )
    feature.add_argument(
        "--sdk-dir",
        help="Android SDK location to record in the project's local.properties",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command == "create":
        try:
            validate_android_package(arguments.package, "--package")
            validate_android_application_id(arguments.application_id)
            # The location is validated before anything is written, so an unusable path cannot
            # leave a broken value behind in a project that was already generated.
            sdk_directory = (
                validate_sdk_directory(arguments.sdk_dir)
                if arguments.sdk_dir is not None
                else None
            )
            project_name = (
                arguments.name if arguments.name is not None else Path.cwd().name
            )
            project_directory = Path.cwd()
            create_project(
                output_directory=project_directory,
                project_name=project_name,
                package_name=arguments.package,
                application_id=arguments.application_id,
                locales=arguments.locale,
                network=arguments.network,
            )
            if sdk_directory is not None:
                write_local_properties(project_directory, sdk_directory)
            if arguments.git_init:
                _initialize_git(project_directory)
            if arguments.verify:
                _verify_gradle(project_directory)
            else:
                _warn_about_unconfigured_sdk(project_directory)
        except (InputValidationError, ProjectCreationError, OSError) as error:
            parser.error(str(error))
        print(f"Created Android project {project_name!r} in {project_directory}")
        if arguments.git_init:
            print("Initialized Git repository.")
        if arguments.verify:
            print("Gradle verification passed.")
    elif arguments.command == "add-feature":
        try:
            project_directory = Path.cwd()
            sdk_directory = (
                validate_sdk_directory(arguments.sdk_dir)
                if arguments.sdk_dir is not None
                else None
            )
            request = validate_feature_request(project_directory, arguments.name)
            plan = prepare_feature_plan(project_directory, request)
            if not arguments.dry_run:
                apply_feature_plan(project_directory, plan)
                if sdk_directory is not None:
                    write_local_properties(project_directory, sdk_directory)
                if arguments.verify:
                    _verify_gradle(project_directory)
                else:
                    _warn_about_unconfigured_sdk(project_directory)
        except (FeatureValidationError, ProjectCreationError, OSError) as error:
            parser.error(str(error))
        snippet = _feature_section_snippet(request)
        if arguments.dry_run:
            print(f"Would add feature {request.identity.slug!r}:")
            for relative_path in sorted(plan.new_files):
                print(f"  create {relative_path.as_posix()}")
            for relative_path in sorted(plan.updated_files):
                print(f"  update {relative_path.as_posix()}")
            print(
                "  integrations: include Gradle modules, register Koin module, "
                "add feature API dependency"
            )
            print("  navigation graph: register the section manually:")
            print(snippet)
        else:
            print(
                f"Generated feature {request.identity.slug!r} "
                "with feature and API modules. Register its destination in "
                "the app navigation graph manually:"
            )
            print(snippet)
            if arguments.verify:
                print("Gradle verification passed.")
    return 0


def _feature_section_snippet(request: FeatureRequest) -> str:
    identity = request.identity
    package = request.metadata.package_name
    section = (
        f"{identity.type_name[0].lower()}{identity.type_name[1:]}Section"
    )
    return "\n".join(
        (
            "  1. add the import to the file declaring AppNavDisplay:",
            f"       import {package}.feature.{identity.package_segment}"
            f".presentation.{section}",
"  2. add the section to the remembered installer list:",
            "       val installers = remember {",
            "           buildList<EntryProviderInstaller> {",
            f"               add({package}.feature."
            f"{identity.package_segment}.presentation.{section})",
            "           }",
            "       }",
            "     The installer is a value of the installer type, not a call of it:",
            "     `add(section)` registers it, `add(section())` would pass a Unit.",
        )
    )


def _initialize_git(project_directory: Path) -> None:
    try:
        result = subprocess.run(
            ["git", "init", "--quiet"],
            cwd=project_directory,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise ProjectCreationError(f"Git initialization failed: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip()
        suffix = f": {detail}" if detail else ""
        raise ProjectCreationError(
            f"Git initialization failed with exit code {result.returncode}{suffix}"
        )


def _require_buildable_sdk(project_directory: Path) -> None:
    """Fail with the reason before Gradle, which reports a missing SDK only as a build failure."""
    resolution = resolve_sdk(project_directory)
    if resolution.location is None:
        if resolution.invalid_sources:
            raise ProjectCreationError(build_invalid_sdk_message(resolution))
        raise ProjectCreationError(
            build_unconfigured_sdk_message(
                project_directory, resolution, context="the build"
            )
        )
    sdk_directory = resolution.location.path
    missing = missing_api_levels(sdk_directory, project_directory)
    if missing:
        raise ProjectCreationError(
            build_missing_platform_message(
                sdk_directory, missing, installed_api_levels(sdk_directory)
            )
        )


def _warn_about_unconfigured_sdk(project_directory: Path) -> None:
    """Mention the missing SDK right after generation instead of at the first build."""
    resolution = resolve_sdk(project_directory)
    if resolution.location is not None:
        return
    reason = (
        "the configured location is not an Android SDK"
        if resolution.invalid_sources
        else "no SDK location is configured"
    )
    print(
        f"Warning: {reason}, so `./gradlew build` will fail.\n"
        "         Pass --sdk-dir <path> on the next run, or set ANDROID_HOME; "
        "see README.md for the details.",
        file=sys.stderr,
    )


def _verify_gradle(project_directory: Path) -> None:
    _require_buildable_sdk(project_directory)
    command = (
        ["cmd.exe", "/c", "gradlew.bat", "build", "--no-daemon"]
        if os.name == "nt"
        else ["./gradlew", "build", "--no-daemon"]
    )
    try:
        result = subprocess.run(command, cwd=project_directory, check=False)
    except OSError as error:
        raise ProjectCreationError(
            f"Gradle verification could not start: {error}; generated files were kept"
        ) from error
    if result.returncode != 0:
        raise ProjectCreationError(
            f"Gradle verification failed with exit code {result.returncode}; "
            "generated files were kept"
        )
