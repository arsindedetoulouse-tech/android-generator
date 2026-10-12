from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from android_skeleton import sdk
from android_skeleton.validation import InputValidationError


def _make_sdk(root: Path, name: str = "sdk") -> Path:
    directory = root / name
    (directory / "platform-tools").mkdir(parents=True)
    (directory / "platforms").mkdir(parents=True)
    return directory


def _make_platform(sdk_directory: Path, api_level: str) -> None:
    (sdk_directory / "platforms" / f"android-{api_level}").mkdir(parents=True)


def _make_project(root: Path, *, compile_sdks: tuple[int, ...] = (37,)) -> Path:
    project = root / "project"
    plugins = project / "build-logic/src/main/kotlin"
    plugins.mkdir(parents=True)
    (plugins / "android.application.gradle.kts").write_text(
        "compileSdk = " + "\ncompileSdk = ".join(str(level) for level in compile_sdks) + "\n",
        encoding="utf-8",
    )
    (plugins / "android.library.gradle.kts").write_text(
        "compileSdk = 37\n", encoding="utf-8"
    )
    (plugins / "android.serialization.gradle.kts").write_text(
        "plugins { id(\"org.jetbrains.kotlin.plugin.serialization\") }\n",
        encoding="utf-8",
    )
    return project


class AndroidEnvironmentTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="android-sdk-")
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        # The host machine may have a real SDK configured; none of these tests may see it.
        patcher = patch.dict(
            os.environ,
            {"ANDROID_HOME": "", "ANDROID_SDK_ROOT": "", "LOCALAPPDATA": ""},
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_directory_is_accepted_as_sdk_only_by_its_content(self) -> None:
        sdk_directory = _make_sdk(self.root)
        unrelated = self.root / "empty"
        unrelated.mkdir()
        markerless = self.root / "markerless"
        markerless.mkdir()
        (markerless / "src").mkdir()

        self.assertTrue(sdk.looks_like_sdk(sdk_directory))
        self.assertFalse(sdk.looks_like_sdk(unrelated))
        self.assertFalse(sdk.looks_like_sdk(markerless))
        self.assertFalse(sdk.looks_like_sdk(self.root / "absent"))

    def test_platform_tools_alone_are_enough(self) -> None:
        minimal = self.root / "minimal"
        (minimal / "platform-tools").mkdir(parents=True)

        self.assertTrue(sdk.looks_like_sdk(minimal))

    def test_resolve_reports_no_location_when_nothing_is_configured(self) -> None:
        project = _make_project(self.root)

        resolution = sdk.resolve_sdk(project)

        self.assertFalse(resolution.is_configured)
        self.assertEqual((), resolution.invalid_sources)

    def test_resolve_uses_environment_before_local_properties(self) -> None:
        from_environment = _make_sdk(self.root, "from-env")
        from_properties = _make_sdk(self.root, "from-properties")
        project = _make_project(self.root)
        (project / "local.properties").write_text(
            f"sdk.dir={from_properties}\n", encoding="utf-8"
        )
        os.environ["ANDROID_HOME"] = str(from_environment)

        location = sdk.resolve_sdk(project).location

        assert location is not None
        self.assertEqual(from_environment, location.path)
        self.assertEqual("ANDROID_HOME", location.source)

    def test_resolve_falls_back_to_sdk_dir_of_local_properties(self) -> None:
        sdk_directory = _make_sdk(self.root)
        project = _make_project(self.root)
        (project / "local.properties").write_text(
            f"other=value\nsdk.dir={sdk_directory}\n", encoding="utf-8"
        )

        location = sdk.resolve_sdk(project).location

        assert location is not None
        self.assertEqual(sdk_directory, location.path)
        self.assertEqual("local.properties", location.source)

    def test_resolve_reports_a_configured_location_that_is_not_an_sdk(self) -> None:
        project = _make_project(self.root)
        unrelated = self.root / "not-an-sdk"
        unrelated.mkdir()
        os.environ["ANDROID_HOME"] = str(unrelated)

        resolution = sdk.resolve_sdk(project)

        self.assertFalse(resolution.is_configured)
        self.assertEqual(1, len(resolution.invalid_sources))
        self.assertEqual("ANDROID_HOME", resolution.invalid_sources[0].source)
        self.assertEqual(str(unrelated), resolution.invalid_sources[0].value)

    def test_resolve_prefers_a_usable_source_over_an_invalid_earlier_one(self) -> None:
        sdk_directory = _make_sdk(self.root)
        project = _make_project(self.root)
        os.environ["ANDROID_HOME"] = str(self.root / "absent")
        os.environ["ANDROID_SDK_ROOT"] = str(sdk_directory)

        resolution = sdk.resolve_sdk(project)

        assert resolution.location is not None
        self.assertEqual("ANDROID_SDK_ROOT", resolution.location.source)
        self.assertEqual(1, len(resolution.invalid_sources))

    def test_local_properties_escapes_are_undone(self) -> None:
        # A properties file escapes the separators of its own format, so a directory whose name
        # contains a backslash is recorded doubled. The value must reach Gradle unescaped.
        unusual = self.root / ("odd" + chr(92) + "name")
        (unusual / "platforms").mkdir(parents=True)
        project = _make_project(self.root)
        escaped = str(unusual).replace(chr(92), chr(92) * 2)
        (project / "local.properties").write_text(
            f"sdk.dir={escaped}\n", encoding="utf-8"
        )

        location = sdk.resolve_sdk(project).location

        assert location is not None
        self.assertEqual(unusual, location.path)

    def test_unescaping_handles_separators_and_unicode_escapes(self) -> None:
        separator = chr(92)
        self.assertEqual(
            "C:" + separator + "Android" + separator + "Sdk",
            sdk._unescape_property_value(
                "C" + separator + ":" + separator * 2
                + "Android" + separator * 2 + "Sdk"
            ),
        )
        self.assertEqual(
            "sk",
            sdk._unescape_property_value(separator + "u0073k"),
        )

    def test_required_api_levels_come_from_every_convention_plugin(self) -> None:
        project = _make_project(self.root, compile_sdks=(37, 36))

        self.assertEqual((36, 37), sdk.required_api_levels(project))

    def test_required_api_levels_are_empty_without_build_logic(self) -> None:
        self.assertEqual((), sdk.required_api_levels(self.root / "absent"))

    def test_installed_levels_accept_minor_versions_and_reject_other_ones(self) -> None:
        sdk_directory = _make_sdk(self.root)
        for api_level in ("34", "36.1", "37.0", "37.4"):
            _make_platform(sdk_directory, api_level)
        (sdk_directory / "platforms" / "android-notes").mkdir()

        self.assertEqual((34, 36, 37), sdk.installed_api_levels(sdk_directory))

    def test_minor_version_suffix_satisfies_only_its_own_api_level(self) -> None:
        sdk_directory = _make_sdk(self.root)
        _make_platform(sdk_directory, "36.1")

        project = _make_project(self.root, compile_sdks=(37,))
        # The library plugin of `_make_project` also declares 37, so both resolve to the same level.
        self.assertEqual((37,), sdk.missing_api_levels(sdk_directory, project))

    def test_missing_levels_are_reported_against_the_installed_ones(self) -> None:
        sdk_directory = _make_sdk(self.root)
        _make_platform(sdk_directory, "34")
        _make_platform(sdk_directory, "36.1")
        project = _make_project(self.root)

        self.assertEqual((37,), sdk.missing_api_levels(sdk_directory, project))

    def test_nothing_is_missing_when_the_platform_is_installed(self) -> None:
        sdk_directory = _make_sdk(self.root)
        _make_platform(sdk_directory, "37.0")
        project = _make_project(self.root)

        self.assertEqual((), sdk.missing_api_levels(sdk_directory, project))

    def test_candidate_is_recovered_from_the_location_of_adb(self) -> None:
        sdk_directory = _make_sdk(self.root)
        tools = shutil_which = str(sdk_directory / "platform-tools" / "adb")
        Path(tools).write_text("", encoding="utf-8")

        with patch("shutil.which", return_value=shutil_which):
            candidates = sdk.discover_candidates()

        self.assertIn(sdk_directory.resolve(), candidates)

    def test_candidate_is_not_recovered_from_an_unrelated_adb_on_path(self) -> None:
        elsewhere = self.root / "bin"
        elsewhere.mkdir()
        adb = elsewhere / "adb"
        adb.write_text("", encoding="utf-8")

        with patch("shutil.which", return_value=str(adb)):
            self.assertNotIn(adb.parent.parent.resolve(), sdk.discover_candidates())

    def test_candidates_exclude_directories_that_are_not_sdks(self) -> None:
        sdk_directory = _make_sdk(self.root)
        unrelated = self.root / "not-an-sdk"
        unrelated.mkdir()
        adb = sdk_directory / "platform-tools" / "adb"
        adb.write_text("", encoding="utf-8")

        with (
            patch("shutil.which", return_value=str(adb)),
            patch.object(sdk, "_well_known_locations", return_value=[unrelated]),
        ):
            candidates = sdk.discover_candidates()

        self.assertEqual((sdk_directory.resolve(),), candidates)

    def test_candidates_never_repeat_a_path_reachable_twice(self) -> None:
        sdk_directory = _make_sdk(self.root)
        adb = sdk_directory / "platform-tools" / "adb"
        adb.write_text("", encoding="utf-8")

        with (
            patch("shutil.which", return_value=str(adb)),
            patch.object(
                sdk, "_well_known_locations", return_value=[sdk_directory]
            ),
        ):
            candidates = sdk.discover_candidates()

        self.assertEqual((sdk_directory.resolve(),), candidates)

    def test_setup_message_covers_every_shell_without_reading_shell(self) -> None:
        project = _make_project(self.root)
        resolution = sdk.resolve_sdk(project)

        # The host machine may hold a real SDK; the "nothing installed" branch needs isolation.
        with patch.object(sdk, "discover_candidates", return_value=()):
            message = sdk.build_unconfigured_sdk_message(
                project, resolution, context="build verification"
            )

        for shell_hint in ("~/.zshrc", "~/.bashrc", "~/.config/fish/config.fish"):
            with self.subTest(shell=shell_hint):
                self.assertIn(shell_hint, message)
        self.assertIn("PowerShell", message)
        self.assertIn("command-line tools", message)
        self.assertIn("Android Studio is not required", message)
        self.assertIn("ANDROID_HOME", message)
        self.assertIn("sdk.dir", message)

    def test_setup_message_offers_a_found_candidate_without_choosing_it(self) -> None:
        project = _make_project(self.root)
        sdk_directory = _make_sdk(self.root)

        with patch.object(sdk, "discover_candidates", return_value=(sdk_directory,)):
            message = sdk.build_unconfigured_sdk_message(
                project, sdk.resolve_sdk(project), context="the build"
            )

        self.assertIn(str(sdk_directory), message)
        self.assertIn("does not choose for you", message)
        self.assertNotIn("Android Studio is not required", message)

    def test_setup_message_lists_the_checked_sources(self) -> None:
        project = _make_project(self.root)

        message = sdk.build_unconfigured_sdk_message(
            project, sdk.resolve_sdk(project), context="the build"
        )

        self.assertIn("ANDROID_HOME: not set", message)
        self.assertIn("ANDROID_SDK_ROOT: not set", message)
        self.assertIn("no local.properties in the project", message)

    def test_setup_message_reports_a_rejected_location_separately(self) -> None:
        project = _make_project(self.root)
        unrelated = self.root / "not-an-sdk"
        unrelated.mkdir()
        os.environ["ANDROID_HOME"] = str(unrelated)

        message = sdk.build_unconfigured_sdk_message(
            project, sdk.resolve_sdk(project), context="the build"
        )

        self.assertIn("Rejected as SDK locations:", message)
        self.assertIn(str(unrelated), message)

    def test_invalid_sdk_message_names_the_source_and_how_to_fix_it(self) -> None:
        resolution = sdk.SdkResolution(
            location=None,
            invalid_sources=(
                sdk.InvalidSdkSource(source="ANDROID_SDK_ROOT", value="/nope"),
            ),
        )

        message = sdk.build_invalid_sdk_message(resolution)

        self.assertIn("ANDROID_SDK_ROOT = /nope", message)
        self.assertIn("--sdk-dir", message)

    def test_missing_platform_message_lists_required_and_installed(self) -> None:
        sdk_directory = _make_sdk(self.root)
        _make_platform(sdk_directory, "34")

        message = sdk.build_missing_platform_message(
            sdk_directory, (37,), (34,)
        )

        self.assertIn(str(sdk_directory), message)
        self.assertIn("API: 37", message)
        self.assertIn("Installed platforms: 34", message)
        self.assertIn('sdkmanager "platforms;android-37"', message)

    def test_write_local_properties_records_the_chosen_directory(self) -> None:
        sdk_directory = _make_sdk(self.root)
        project = _make_project(self.root)

        written = sdk.write_local_properties(project, sdk_directory)

        self.assertEqual(project / "local.properties", written)
        self.assertEqual(
            f"sdk.dir={sdk_directory}\n",
            written.read_text(encoding="utf-8").splitlines()[-1] + "\n",
        )
        self.assertEqual(
            sdk_directory, sdk.resolve_sdk(project).location.path
        )

    def test_validate_sdk_directory_rejects_unusable_values(self) -> None:
        sdk_directory = _make_sdk(self.root)
        unrelated = self.root / "not-an-sdk"
        unrelated.mkdir()

        self.assertEqual(sdk_directory, sdk.validate_sdk_directory(str(sdk_directory)))

        for value in ("", "   ", str(self.root / "absent"), str(unrelated)):
            with self.subTest(value=value):
                with self.assertRaises(InputValidationError):
                    sdk.validate_sdk_directory(value)

    def test_validate_sdk_directory_rejects_a_file(self) -> None:
        a_file = self.root / "file"
        a_file.write_text("", encoding="utf-8")

        with self.assertRaisesRegex(InputValidationError, "not a directory"):
            sdk.validate_sdk_directory(str(a_file))


if __name__ == "__main__":
    unittest.main()