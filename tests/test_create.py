from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from android_sdk_fixture import create_fake_sdk

_REGISTERISTERED_TEMP_DIRS: list[tempfile.TemporaryDirectory] = []
from android_skeleton.cli import main


class CreateProjectTest(unittest.TestCase):
    def test_create_generates_the_start_screen_as_a_feature(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sample-home-") as temp:
            project = Path(temp)

            with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
                result = main(
                    [
                        "create",
                        "--package",
                        "com.example.sample",
                        "--application-id",
                        "com.example.sample.app",
                    ]
                )

            self.assertEqual(0, result)
            package_path = Path("src/main/kotlin/com/example/sample")
            feature = project / "feature/home" / package_path / "feature/home"
            for expected in (
                "di/HomeModule.kt",
                "presentation/HomeScreen.kt",
                "presentation/HomeNavigation.kt",
                "presentation/HomeViewModel.kt",
            ):
                with self.subTest(path=expected):
                    self.assertTrue((feature / expected).is_file(), expected)
            # The data and domain layers are shared, so each feature only owns its package inside
            # them and the feature module keeps no layer directories of its own.
            for expected in (
                "data/home/HomeDataSourceImpl.kt",
                "data/home/HomeRepositoryImpl.kt",
                "domain/home/HomeModel.kt",
                "domain/home/HomeRepository.kt",
                "domain/home/HomeUseCase.kt",
            ):
                with self.subTest(path=expected):
                    layer = "common/data" if expected.startswith("data/") else "common/domain"
                    self.assertTrue(
                        (project / layer / package_path / expected).is_file(),
                        expected,
                    )

            test_path = Path("src/test/kotlin/com/example/sample")
            self.assertTrue(
                (
                    project
                    / "common/data"
                    / test_path
                    / "data/home/HomeRepositoryTest.kt"
                ).is_file()
            )
            self.assertTrue(
                (
                    project
                    / "feature/home"
                    / test_path
                    / "feature/home/presentation/HomeViewModelTest.kt"
                ).is_file()
            )
            self.assertTrue(
                (project / "feature/home/src/main/assets/home_stub.json").is_file()
            )
            self.assertTrue(
                (project / "feature/home-api/src/main/kotlin/com/example/sample"
                 "/feature/home/api/HomeRoute.kt").is_file()
            )

            metadata = json.loads(
                (project / ".android-skeleton.json").read_text(encoding="utf-8")
            )
            self.assertEqual(["home"], metadata["features"])

            # The start screen's section is registered like any other feature's, and the navigation
            # module only assembles the graph.
            activity = (
                project / "app/src/main/kotlin/com/example/sample/MainActivity.kt"
            ).read_text()
            self.assertIn("add(homeSection)", activity)
            self.assertIn(
                "import com.example.sample.feature.home.presentation.homeSection",
                activity,
            )
            app_module = (
                project / "app/src/main/kotlin/com/example/sample/App.kt"
            ).read_text()
            self.assertIn("import com.example.sample.feature.home.di.homeModule", app_module)
            self.assertIn("homeModule", app_module)

    def test_create_renders_project_using_the_current_directory_name(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sample-project-") as temp:
            project = Path(temp)
            stdout = io.StringIO()

            with contextlib.chdir(project), contextlib.redirect_stdout(stdout):
                result = main(
                    [
                        "create",
                        "--package",
                        "com.example.sample",
                        "--application-id",
                        "com.example.sample.app",
                    ]
                )

            self.assertEqual(0, result)
            self.assertTrue((project / "gradlew").is_file())
            self.assertTrue((project / "gradlew").stat().st_mode & 0o111)
            self.assertTrue(
                (
                    project
                    / "app/src/main/kotlin/com/example/sample/MainActivity.kt"
                ).is_file()
            )
            self.assertIn(
                f"rootProject.name = {json.dumps(project.name)}",
                (project / "settings.gradle.kts").read_text(),
            )
            self.assertIn(
                "package com.example.sample",
                (
                    project
                    / "app/src/main/kotlin/com/example/sample/MainActivity.kt"
                ).read_text(),
            )
            self.assertIn(
                project.name,
                (project / "app/src/main/res/values/strings.xml").read_text(),
            )
            self.assertNotIn(
                "localeConfig",
                (project / "app/src/main/AndroidManifest.xml").read_text(),
            )
            self.assertIn(
                'applicationId = "com.example.sample.app"',
                (
                    project
                    / "build-logic/src/main/kotlin/android.application.gradle.kts"
                ).read_text(),
            )
            metadata = json.loads((project / ".android-skeleton.json").read_text())
            self.assertEqual(project.name, metadata["project_name"])
            self.assertEqual("com.example.sample", metadata["package_name"])
            self.assertEqual("com.example.sample.app", metadata["application_id"])
            self.assertIn("Created", stdout.getvalue())

    def test_create_supports_a_display_name_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="directory-name-") as temp:
            project = Path(temp)

            with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
                main(
                    [
                        "create",
                        "--package",
                        "com.example.sample",
                        "--application-id",
                        "com.example.sample.app",
                        "--name",
                        'Field "$ Notes & More',
                    ]
                )

            self.assertIn(
                'rootProject.name = "Field \\"\\$ Notes & More"',
                (project / "settings.gradle.kts").read_text(),
            )
            strings = ET.parse(project / "app/src/main/res/values/strings.xml")
            self.assertEqual(
                'Field "$ Notes & More',
                strings.findtext("./string[@name='app_name']"),
            )

    def test_create_refuses_a_nonempty_directory_without_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="occupied-project-") as temp:
            project = Path(temp)
            sentinel = project / "keep.txt"
            sentinel.write_text("user data", encoding="utf-8")
            stderr = io.StringIO()

            with (
                contextlib.chdir(project),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(stderr),
            ):
                with self.assertRaises(SystemExit) as error:
                    main(
                        [
                            "create",
                            "--package",
                            "com.example.sample",
                            "--application-id",
                            "com.example.sample.app",
                        ]
                    )

            self.assertEqual(2, error.exception.code)
            self.assertEqual(
                ["keep.txt"],
                sorted(path.name for path in project.iterdir()),
            )
            self.assertEqual("user data", sentinel.read_text(encoding="utf-8"))
            self.assertIn("empty", stderr.getvalue())

    def test_create_generates_android_resources_for_selected_locales(self) -> None:
        with tempfile.TemporaryDirectory(prefix="localized-project-") as temp:
            project = Path(temp)

            with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
                main(
                    [
                        "create",
                        "--package",
                        "com.example.sample",
                        "--application-id",
                        "com.example.sample.app",
                        "--locale",
                        "ru-ru",
                        "--locale",
                        "uz-latn-uz",
                        "--locale",
                        "RU-RU",
                    ]
                )

            locale_config = ET.parse(
                project / "app/src/main/res/xml/locale_config.xml"
            )
            locale_names = [
                locale.attrib["{http://schemas.android.com/apk/res/android}name"]
                for locale in locale_config.findall("locale")
            ]
            self.assertEqual(["ru-RU", "uz-Latn-UZ"], locale_names)
            self.assertIn(
                'android:localeConfig="@xml/locale_config"',
                (project / "app/src/main/AndroidManifest.xml").read_text(),
            )
            for qualifier in ("values-b+ru+RU", "values-b+uz+Latn+UZ"):
                localized_strings = ET.parse(
                    project / f"app/src/main/res/{qualifier}/strings.xml"
                )
                self.assertEqual(
                    project.name,
                    localized_strings.findtext("./string[@name='app_name']"),
                )
            metadata = json.loads((project / ".android-skeleton.json").read_text())
            self.assertEqual(
                ["ru-RU", "uz-Latn-UZ"],
                metadata["options"]["locales"],
            )

    def test_create_rejects_invalid_locale_without_writing_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="invalid-locale-project-") as temp:
            project = Path(temp)
            stderr = io.StringIO()

            with (
                contextlib.chdir(project),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(stderr),
            ):
                with self.assertRaises(SystemExit) as error:
                    main(
                        [
                            "create",
                            "--package",
                            "com.example.sample",
                            "--application-id",
                            "com.example.sample.app",
                            "--locale",
                            "ru_RU",
                        ]
                    )

            self.assertEqual(2, error.exception.code)
            self.assertEqual([], list(project.iterdir()))
            self.assertIn("--locale", stderr.getvalue())

    def test_git_init_initializes_the_generated_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="git-project-") as temp:
            project = Path(temp)

            with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
                result = main(
                    [
                        "create",
                        "--package",
                        "com.example.sample",
                        "--application-id",
                        "com.example.sample.app",
                        "--git-init",
                    ]
                )

            self.assertEqual(0, result)
            self.assertTrue((project / ".git").is_dir())
            git_root = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=project,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(str(project), git_root.stdout.strip())

    def _fake_sdk(self) -> Path:
        """A fake SDK in its own temporary directory, kept out of the generated project."""
        host = tempfile.TemporaryDirectory(prefix="fake-android-sdk-")
        self.addCleanup(host.cleanup)
        return create_fake_sdk(Path(host.name))

    def test_verify_runs_gradle_build_after_git_init(self) -> None:
        with tempfile.TemporaryDirectory(prefix="verified-project-") as temp:
            project = Path(temp)
            # Verification now checks the SDK before starting Gradle, so the test supplies one.
            sdk_dir = self._fake_sdk()
            process_results = (
                subprocess.CompletedProcess(["git"], 0),
                subprocess.CompletedProcess(["./gradlew"], 0),
            )

            with (
                contextlib.chdir(project),
                contextlib.redirect_stdout(io.StringIO()),
                patch(
                    "android_skeleton.cli.subprocess.run",
                    side_effect=process_results,
                ) as run,
            ):
                result = main(
                    [
                        "create",
                        "--package",
                        "com.example.sample",
                        "--application-id",
                        "com.example.sample.app",
                        "--git-init",
                        "--verify",
                        "--sdk-dir",
                        str(sdk_dir),
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual(2, run.call_count)
            self.assertEqual(
                ["git", "init", "--quiet"],
                run.call_args_list[0].args[0],
            )
            self.assertEqual(
                ["./gradlew", "build", "--no-daemon"],
                run.call_args_list[1].args[0],
            )

    def test_gradle_verification_failure_is_reported_and_keeps_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="failed-verification-") as temp:
            project = Path(temp)
            sdk_dir = self._fake_sdk()
            stderr = io.StringIO()

            with (
                contextlib.chdir(project),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(stderr),
                patch(
                    "android_skeleton.cli.subprocess.run",
                    return_value=subprocess.CompletedProcess(["./gradlew"], 1),
                ),
                self.assertRaises(SystemExit) as error,
            ):
                main(
                    [
                        "create",
                        "--package",
                        "com.example.sample",
                        "--application-id",
                        "com.example.sample.app",
                        "--verify",
                        "--sdk-dir",
                        str(sdk_dir),
                    ]
                )

            self.assertEqual(2, error.exception.code)
            self.assertTrue((project / "gradlew").is_file())
            self.assertIn("Gradle verification failed", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
