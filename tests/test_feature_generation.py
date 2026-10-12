from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from android_sdk_fixture import create_fake_sdk

_REGISTERISTERED_TEMP_DIRS: list[tempfile.TemporaryDirectory] = []
from android_skeleton.cli import main


class FeatureGenerationTest(unittest.TestCase):
    def test_add_feature_generates_layers_and_navigation_only_api(self) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-generation-") as temp:
            project = self._create_project(Path(temp))
            app_navigation = (
                project
                / "app/src/main/kotlin/com/example/sample/MainActivity.kt"
            ).read_text()

            with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
                result = main(["add-feature", "user-profile"])

            self.assertEqual(0, result)
            feature_root = project / "feature/user-profile"
            api_root = project / "feature/user-profile-api"
            feature_sources = (
                feature_root / "src/main/kotlin/com/example/sample/feature/userprofile"
            )
            for layer in ("presentation", "di"):
                with self.subTest(layer=layer):
                    self.assertTrue((feature_sources / layer).is_dir())
            # The data and domain layers are shared by every feature and live in the common modules,
            # one package per feature, so the feature module keeps no layer directories of its own.
            for module, layer in (
                ("common/domain", "domain"),
                ("common/data", "data"),
            ):
                with self.subTest(module=module, layer=layer):
                    self.assertTrue(
                        (
                            project
                            / module
                            / f"src/main/kotlin/com/example/sample/{layer}/userprofile"
                        ).is_dir()
                    )
            self.assertTrue((feature_root / "build.gradle.kts").is_file())
            self.assertTrue((api_root / "build.gradle.kts").is_file())
            self.assertTrue(
                (
                    feature_root
                    / "src/main/kotlin/com/example/sample/feature/userprofile/presentation/UserProfileViewModel.kt"
                ).is_file()
            )
            self.assertTrue(
                (
                    project
                    / "common/domain/src/main/kotlin/com/example/sample/domain/userprofile/UserProfileRepository.kt"
                ).is_file()
            )
            self.assertTrue(
                (
                    project
                    / "common/data/src/main/kotlin/com/example/sample/data/userprofile/UserProfileDataSource.kt"
                ).is_file()
            )
            self.assertTrue(
                (feature_root / "src/main/assets/user-profile_stub.json").is_file()
            )
            self.assertTrue(
                (
                    feature_root
                    / "src/main/kotlin/com/example/sample/feature/userprofile/di/UserProfileModule.kt"
                ).is_file()
            )
            self.assertTrue(
                (
                    api_root
                    / "src/main/kotlin/com/example/sample/feature/userprofile/api/UserProfileRoute.kt"
                ).is_file()
            )
            self.assertEqual(
                app_navigation,
                (
                    project
                    / "app/src/main/kotlin/com/example/sample/MainActivity.kt"
                ).read_text(),
            )
            self.assertIn(
                '":feature:user-profile"',
                (project / "settings.gradle.kts").read_text(),
            )
            self.assertIn(
                '":feature:user-profile-api"',
                (project / "settings.gradle.kts").read_text(),
            )
            self.assertIn(
                'implementation(project(":feature:user-profile"))',
                (project / "app/build.gradle.kts").read_text(),
            )
            self.assertIn(
                'api(project(":feature:user-profile-api"))',
                (project / "app/navigation/build.gradle.kts").read_text(),
            )
            self.assertIn(
                "import com.example.sample.feature.userprofile.di.userProfileModule",
                (
                    project
                    / "app/src/main/kotlin/com/example/sample/App.kt"
                ).read_text(),
            )
            self.assertIn(
                '"user-profile"',
                (project / ".android-skeleton.json").read_text(),
            )

    def test_add_feature_preserves_optional_koin_modules_and_prompts_manual_navigation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-wiring-") as temp:
            project = Path(temp)
            with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
                main(
                    [
                        "create",
                        "--package",
                        "com.example.sample",
                        "--application-id",
                        "com.example.sample.app",
                        "--network",
                    ]
                )
            output = io.StringIO()
            with contextlib.chdir(project), contextlib.redirect_stdout(output):
                main(["add-feature", "user-profile"])

            app_source = (
                project / "app/src/main/kotlin/com/example/sample/App.kt"
            ).read_text()
            self.assertIn("coreNetworkModule", app_source)
            self.assertIn("coreDataStoreModule", app_source)
            self.assertIn("userProfileModule", app_source)
            self.assertIn("navigation graph", output.getvalue().lower())
            self.assertIn("manually", output.getvalue().lower())
            self.assertIn(
                "import com.example.sample.feature.userprofile.presentation"
                ".userProfileSection",
                output.getvalue(),
            )
            self.assertIn("add(com.example.sample.feature.userprofile"
                          ".presentation.userProfileSection)",
                          output.getvalue())
            self.assertNotIn(
                "add(com.example.sample.feature.userprofile"
                ".presentation.userProfileSection())",
                output.getvalue(),
            )

    def test_add_feature_dry_run_prints_plan_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-dry-run-") as temp:
            project = self._create_project(Path(temp))
            before = self._snapshot(project)
            output = io.StringIO()

            with contextlib.chdir(project), contextlib.redirect_stdout(output):
                result = main(["add-feature", "user-profile", "--dry-run"])

            self.assertEqual(0, result)
            self.assertEqual(before, self._snapshot(project))
            self.assertIn("feature/user-profile/", output.getvalue())
            self.assertIn("settings.gradle.kts", output.getvalue())
            self.assertIn("Koin", output.getvalue())
            self.assertIn("navigation graph", output.getvalue().lower())
            self.assertIn("userProfileSection", output.getvalue())

    def test_add_feature_rolls_back_on_replacement_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-rollback-") as temp:
            project = self._create_project(Path(temp))
            before = self._snapshot(project)
            original_replace = __import__("os").replace
            injected = False

            def fail_app_dependency_update(source: object, destination: object) -> None:
                nonlocal injected
                if (
                    not injected
                    and Path(destination).name == "build.gradle.kts"
                    and Path(destination).parent.name == "app"
                    and Path(source).name.startswith(".android-skeleton-stage-")
                ):
                    injected = True
                    raise OSError("injected replacement failure")
                original_replace(source, destination)

            stderr = io.StringIO()
            with (
                contextlib.chdir(project),
                contextlib.redirect_stderr(stderr),
                patch("os.replace", side_effect=fail_app_dependency_update),
            ):
                with self.assertRaises(SystemExit) as error:
                    main(["add-feature", "user-profile"])

            self.assertEqual(2, error.exception.code)
            self.assertTrue(injected)
            self.assertEqual(before, self._snapshot(project))
            self.assertTrue((project / "feature" / "home").is_dir())
            self.assertFalse((project / "feature" / "user-profile").exists())
            self.assertFalse((project / "feature" / "user-profile-api").exists())
            self.assertIn("injected replacement failure", stderr.getvalue())

    def test_add_feature_rejects_symlinked_project_paths_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-symlink-") as temp:
            parent = Path(temp)
            project = parent / "project"
            project.mkdir()
            self._create_project(project)
            outside = parent / "outside"
            outside.mkdir()
            outside_app = outside / "App.kt"
            outside_app.write_text("package outside\n", encoding="utf-8")
            kotlin_directory = (
                project / "app/src/main/kotlin/com/example/sample"
            )
            kotlin_directory.rename(kotlin_directory.with_name("sample-original"))
            kotlin_directory.symlink_to(outside, target_is_directory=True)
            before = self._snapshot(project)
            outside_before = outside_app.read_bytes()
            stderr = io.StringIO()

            with contextlib.chdir(project), contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as error:
                    main(["add-feature", "user-profile"])

            self.assertEqual(2, error.exception.code)
            self.assertEqual(before, self._snapshot(project))
            self.assertEqual(outside_before, outside_app.read_bytes())
            self.assertIn("escapes project directory", stderr.getvalue())

    def test_add_feature_rejects_existing_gradle_registration_before_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-registration-") as temp:
            project = self._create_project(Path(temp))
            metadata_path = project / ".android-skeleton.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["features"] = []
            metadata_path.write_text(
                json.dumps(metadata, indent=2) + "\n",
                encoding="utf-8",
            )
            settings_path = project / "settings.gradle.kts"
            settings_path.write_text(
                settings_path.read_text(encoding="utf-8")
                .replace(
                    '    ":feature:home-api",',
                    '    ":feature:home-api",\n    ":feature:user-profile",',
                ),
                encoding="utf-8",
            )
            before = self._snapshot(project)
            stderr = io.StringIO()

            with contextlib.chdir(project), contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit):
                    main(["add-feature", "user-profile"])

            self.assertEqual(before, self._snapshot(project))
            self.assertFalse((project / "feature/user-profile").exists())
            self.assertIn("already registered", stderr.getvalue())

    @staticmethod
    def _snapshot(project: Path) -> dict[str, bytes]:
        return {
            path.relative_to(project).as_posix(): path.read_bytes()
            for path in project.rglob("*")
            if path.is_file()
        }

    def test_feature_api_exposes_only_its_route_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-api-") as temp:
            project = self._create_project(Path(temp))

            with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
                main(["add-feature", "user-profile"])

            route_source = (
                project
                / "feature/user-profile-api/src/main/kotlin/com/example/sample/feature/userprofile/api/UserProfileRoute.kt"
            ).read_text()
            self.assertIn(
                "package com.example.sample.feature.userprofile.api",
                route_source,
            )
            self.assertIn("@Serializable", route_source)
            self.assertIn("data object UserProfile : AppRoute", route_source)
            for presentation_detail in (
                "UserProfileState",
                "UserProfileAction",
                "UserProfileSideEffect",
                "Compose",
                "ViewModel",
            ):
                with self.subTest(detail=presentation_detail):
                    self.assertNotIn(presentation_detail, route_source)

    def test_add_feature_creates_the_full_domain_chain_and_its_tests(self) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-chain-") as temp:
            project = self._create_project(Path(temp))

            with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
                main(["add-feature", "user-profile"])

            sources = project / "feature/user-profile/src/main/kotlin/com/example/sample/feature/userprofile"
            tests = project / "feature/user-profile/src/test/kotlin/com/example/sample/feature/userprofile"
            data = (
                project
                / "common/data/src/main/kotlin/com/example/sample/data/userprofile"
            )
            domain = (
                project
                / "common/domain/src/main/kotlin/com/example/sample/domain/userprofile"
            )
            data_tests = (
                project
                / "common/data/src/test/kotlin/com/example/sample/data/userprofile"
            )
            for expected in (
                data / "UserProfileDataSourceImpl.kt",
                data / "UserProfileRepositoryImpl.kt",
                domain / "UserProfileRepository.kt",
                domain / "UserProfileUseCase.kt",
                sources / "presentation/UserProfileNavigation.kt",
                sources / "di/UserProfileModule.kt",
                # The repository test follows the implementation it covers into the shared module.
                data_tests / "UserProfileRepositoryTest.kt",
                tests / "presentation/UserProfileViewModelTest.kt",
            ):
                with self.subTest(path=expected.name):
                    self.assertTrue(expected.is_file(), expected)

            koin_module = (sources / "di/UserProfileModule.kt").read_text()
            for registration in (
                "single<UserProfileDataSource> { UserProfileDataSourceImpl(get(), androidContext()) }",
                "single<UserProfileRepository>",
                "single { UserProfileUseCase(get()) }",
                "viewModel { UserProfileViewModel(get()) }",
            ):
                with self.subTest(registration=registration):
                    self.assertIn(registration, koin_module)

            view_model = (sources / "presentation/UserProfileViewModel.kt").read_text()
            self.assertIn("intent {", view_model)
            self.assertIn("reduce {", view_model)

            state = (sources / "presentation/UserProfileState.kt").read_text()
            self.assertIn("enum class UserProfileError", state)
            self.assertIn("Network", state)
            self.assertIn("UserProfileError.Network", view_model)
            self.assertNotIn("errorMessage", state)

            feature_build = (project / "feature/user-profile/build.gradle.kts").read_text()
            for dependency in (
                'api(project(":feature:user-profile-api"))',
                'api(project(":core:navigation"))',
                'api(project(":common:presentation"))',
                'api(project(":common:domain"))',
                'api(project(":common:data"))',
            ):
                with self.subTest(dependency=dependency):
                    self.assertIn(dependency, feature_build)

            api_build = (project / "feature/user-profile-api/build.gradle.kts").read_text()
            self.assertIn('id("android.library")', api_build)
            self.assertIn('id("android.serialization")', api_build)
            self.assertIn('api(project(":core:navigation"))', api_build)

    def test_add_feature_verify_runs_gradle_build(self) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-verify-") as temp:
            project = self._create_project(Path(temp))
            sdk_dir = self._fake_sdk()
            output = io.StringIO()

            with (
                contextlib.chdir(project),
                contextlib.redirect_stdout(output),
                patch(
                    "android_skeleton.cli.subprocess.run",
                    return_value=subprocess.CompletedProcess(["./gradlew"], 0),
                ) as run,
            ):
                result = main(
                    [
                        "add-feature",
                        "user-profile",
                        "--verify",
                        "--sdk-dir",
                        str(sdk_dir),
                    ]
                )

            self.assertEqual(0, result)
            self.assertEqual(["./gradlew", "build", "--no-daemon"], run.call_args.args[0])
            self.assertIn("Gradle verification passed.", output.getvalue())

    def test_add_feature_verify_failure_keeps_generated_feature(self) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-verify-fail-") as temp:
            project = self._create_project(Path(temp))
            sdk_dir = self._fake_sdk()
            stderr = io.StringIO()

            with (
                contextlib.chdir(project),
                contextlib.redirect_stderr(stderr),
                patch(
                    "android_skeleton.cli.subprocess.run",
                    return_value=subprocess.CompletedProcess(["./gradlew"], 1),
                ),
                self.assertRaises(SystemExit),
            ):
                main(
                    [
                        "add-feature",
                        "user-profile",
                        "--verify",
                        "--sdk-dir",
                        str(sdk_dir),
                    ]
                )

            self.assertIn("verification failed", stderr.getvalue())
            self.assertTrue(
                (
                    project
                    / "feature/user-profile/build.gradle.kts"
                ).is_file()
            )

    def test_add_feature_without_verify_does_not_run_gradle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-no-verify-") as temp:
            project = self._create_project(Path(temp))

            with (
                contextlib.chdir(project),
                contextlib.redirect_stdout(io.StringIO()),
                patch("android_skeleton.cli.subprocess.run") as run,
            ):
                result = main(["add-feature", "user-profile"])

            self.assertEqual(0, result)
            run.assert_not_called()

    def test_feature_strings_are_namespaced_by_slug(self) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-strings-") as temp:
            project = self._create_project(Path(temp))

            with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
                main(["add-feature", "user-profile"])

            strings = (
                project
                / "feature/user-profile/src/main/res/values/strings.xml"
            ).read_text()
            home_strings = (
                project / "feature/home/src/main/res/values/strings.xml"
            ).read_text()
            # Resource names of every feature library are merged into the application, so two
            # features declaring `feature_title` would silently resolve to whichever is merged last.
            self.assertIn('name="feature_user_profile_title"', strings)
            self.assertIn('name="feature_home_title"', home_strings)
            self.assertNotIn('name="feature_title"', strings)
            self.assertNotIn('name="feature_title"', home_strings)

    def test_add_feature_rejects_the_reserved_slug_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-reserved-") as temp:
            project = self._create_project(Path(temp))
            before = self._snapshot(project)
            stderr = io.StringIO()

            with (
                contextlib.chdir(project),
                contextlib.redirect_stderr(stderr),
                self.assertRaises(SystemExit),
            ):
                main(["add-feature", "home"])

            self.assertIn("reserved", stderr.getvalue())
            self.assertEqual(before, self._snapshot(project))

    def _fake_sdk(self) -> Path:
        """A fake SDK in its own temporary directory, kept out of the generated project."""
        host = tempfile.TemporaryDirectory(prefix="fake-android-sdk-")
        self.addCleanup(host.cleanup)
        return create_fake_sdk(Path(host.name))

    @staticmethod
    def _create_project(project: Path) -> Path:
        with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
            main(
                [
                    "create",
                    "--package",
                    "com.example.sample",
                    "--application-id",
                    "com.example.sample.app",
                ]
            )
        return project


if __name__ == "__main__":
    unittest.main()
