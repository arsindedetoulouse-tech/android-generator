from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from android_sdk_fixture import create_fake_sdk
from android_skeleton.cli import main
from android_skeleton.validation import (
    InputValidationError,
    validate_android_application_id,
    validate_android_package,
)


class CliValidationTest(unittest.TestCase):
    def test_create_requires_package_and_application_id(self) -> None:
        for arguments in (
            ["create"],
            ["create", "--package", "com.example.app"],
            ["create", "--application-id", "com.example.app"],
        ):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(arguments)
                self.assertEqual(2, error.exception.code)

    def test_create_accepts_valid_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with contextlib.chdir(temp), contextlib.redirect_stdout(io.StringIO()):
                result = main(
                    [
                        "create",
                        "--package",
                        "com.example.app",
                        "--application-id",
                        "com.example.app.id",
                    ]
                )

        self.assertEqual(0, result)

    def test_create_reports_invalid_package(self) -> None:
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
            main(
                [
                    "create",
                    "--package",
                    "com.3example.app",
                    "--application-id",
                    "com.example.app",
                ]
            )

        self.assertIn("--package", stderr.getvalue())

    def test_create_reports_invalid_application_id(self) -> None:
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
            main(
                [
                    "create",
                    "--package",
                    "com.example.app",
                    "--application-id",
                    "com.3app.id",
                ]
            )

        self.assertIn("--application-id", stderr.getvalue())

    def test_package_validator_rejects_keywords_and_invalid_segments(self) -> None:
        for package_name in ("com.class.app", "com.3example.app", "com..app"):
            with self.subTest(package_name=package_name):
                with self.assertRaises(InputValidationError):
                    validate_android_package(package_name, "--package")

    def test_application_id_validator_accepts_keyword_segments(self) -> None:
        self.assertEqual("com.class.app", validate_android_application_id("com.class.app"))

    def test_application_id_validator_requires_valid_segments(self) -> None:
        for application_id in ("com.3example.app", "com..app", "com"):
            with self.subTest(application_id=application_id):
                with self.assertRaises(InputValidationError):
                    validate_android_application_id(application_id)


class SdkPreflightTest(unittest.TestCase):
    """The CLI must explain a missing SDK instead of letting Gradle report it."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory(prefix="sdk-preflight-")
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        # Never let a real SDK configured on the host satisfy these tests.
        patcher = patch.dict(
            os.environ, {"ANDROID_HOME": "", "ANDROID_SDK_ROOT": ""}
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _create_direct(self, project: Path, *extra: str) -> int:
        return main(
            [
                "create",
                "--package",
                "com.example.sample",
                "--application-id",
                "com.example.sample.app",
                *extra,
            ]
        )

    def _fake_sdk(self, *api_levels: str) -> Path:
        host = tempfile.TemporaryDirectory(prefix="fake-android-sdk-")
        self.addCleanup(host.cleanup)
        return create_fake_sdk(Path(host.name), api_levels=api_levels or ("37",))

    def _create(self, project: Path, *extra: str) -> int:
        # stderr is swallowed here so the SDK warning of a successful run does not pollute the
        # test output; tests that assert on a message drive `main` themselves.
        with (
            contextlib.chdir(project),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            return main(
                [
                    "create",
                    "--package",
                    "com.example.sample",
                    "--application-id",
                    "com.example.sample.app",
                    *extra,
                ]
            )

    def test_verify_does_not_start_gradle_when_the_sdk_is_unconfigured(self) -> None:
        project = self.root / "unconfigured"
        project.mkdir()
        stderr = io.StringIO()

        with (
            contextlib.chdir(project),
            contextlib.redirect_stderr(stderr),
            patch("android_skeleton.cli.subprocess.run") as run,
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
                ]
            )

        self.assertEqual(2, error.exception.code)
        run.assert_not_called()
        message = stderr.getvalue()
        self.assertIn("Android SDK location is not configured", message)
        self.assertIn("ANDROID_HOME: not set", message)
        self.assertIn("--sdk-dir", message)

    def test_verify_reports_a_configured_location_that_is_not_an_sdk(self) -> None:
        project = self.root / "wrong-location"
        project.mkdir()
        unrelated = self.root / "not-an-sdk"
        unrelated.mkdir()
        os.environ["ANDROID_HOME"] = str(unrelated)
        stderr = io.StringIO()

        with (
            contextlib.chdir(project),
            contextlib.redirect_stderr(stderr),
            patch("android_skeleton.cli.subprocess.run") as run,
            self.assertRaises(SystemExit),
        ):
            main(
                [
                    "create",
                    "--package",
                    "com.example.sample",
                    "--application-id",
                    "com.example.sample.app",
                    "--verify",
                ]
            )

        run.assert_not_called()
        message = stderr.getvalue()
        self.assertIn("is not an SDK", message)
        self.assertIn(str(unrelated), message)

    def test_verify_reports_a_missing_platform_before_starting_gradle(self) -> None:
        project = self.root / "missing-platform"
        project.mkdir()
        sdk_dir = self._fake_sdk("34", "36.1")
        stderr = io.StringIO()

        with (
            contextlib.chdir(project),
            contextlib.redirect_stderr(stderr),
            patch("android_skeleton.cli.subprocess.run") as run,
            self.assertRaises(SystemExit),
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

        run.assert_not_called()
        message = stderr.getvalue()
        self.assertIn("missing a required platform", message)
        self.assertIn("API: 37", message)
        self.assertIn("Installed platforms: 34, 36", message)

    def test_sdk_dir_records_the_location_and_lets_verification_run(self) -> None:
        project = self.root / "with-sdk"
        project.mkdir()
        sdk_dir = self._fake_sdk()

        with (
            contextlib.chdir(project),
            contextlib.redirect_stderr(io.StringIO()),
            patch(
                "android_skeleton.cli.subprocess.run",
                return_value=subprocess.CompletedProcess(["./gradlew"], 0),
            ) as run,
        ):
            result = self._create(
                project, "--verify", "--sdk-dir", str(sdk_dir)
            )

        self.assertEqual(0, result)
        self.assertEqual(
            f"sdk.dir={sdk_dir}",
            (project / "local.properties")
            .read_text(encoding="utf-8")
            .splitlines()[-1],
        )
        run.assert_called_once()

    def test_sdk_dir_is_rejected_before_the_project_is_created(self) -> None:
        project = self.root / "rejected"
        project.mkdir()
        unrelated = self.root / "not-an-sdk"
        unrelated.mkdir()

        with contextlib.chdir(project), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                self._create(project, "--sdk-dir", str(unrelated))

        self.assertEqual(2, error.exception.code)
        self.assertFalse((project / "local.properties").exists())
        self.assertFalse((project / "settings.gradle.kts").exists())

    def test_add_feature_verify_uses_the_same_preflight(self) -> None:
        project = self.root / "feature-project"
        project.mkdir()
        self.assertEqual(0, self._create(project))
        stderr = io.StringIO()

        with (
            contextlib.chdir(project),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(stderr),
            patch("android_skeleton.cli.subprocess.run") as run,
            self.assertRaises(SystemExit),
        ):
            main(["add-feature", "user-profile", "--verify"])

        run.assert_not_called()
        self.assertIn("Android SDK location is not configured", stderr.getvalue())
        # The feature itself is written before verification, so it is kept.
        self.assertTrue((project / "feature/user-profile").is_dir())

    def test_add_feature_records_an_explicit_sdk_location(self) -> None:
        project = self.root / "feature-sdk"
        project.mkdir()
        self.assertEqual(0, self._create(project))
        sdk_dir = self._fake_sdk()

        with (
            contextlib.chdir(project),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            result = main(
                ["add-feature", "user-profile", "--sdk-dir", str(sdk_dir)]
            )

        self.assertEqual(0, result)
        self.assertIn(
            f"sdk.dir={sdk_dir}",
            (project / "local.properties").read_text(encoding="utf-8"),
        )

    def test_generation_warns_about_the_sdk_when_verification_is_not_requested(self) -> None:
        project = self.root / "warned"
        project.mkdir()
        stderr = io.StringIO()

        with (
            contextlib.chdir(project),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(stderr),
        ):
            result = self._create_direct(project)

        self.assertEqual(0, result)
        warning = stderr.getvalue()
        self.assertIn("Warning:", warning)
        self.assertIn("--sdk-dir", warning)
        self.assertTrue((project / "settings.gradle.kts").is_file())

    def test_generation_stays_quiet_when_the_sdk_is_configured(self) -> None:
        project = self.root / "quiet"
        project.mkdir()
        os.environ["ANDROID_HOME"] = str(self._fake_sdk())
        stderr = io.StringIO()

        with contextlib.chdir(project), contextlib.redirect_stderr(stderr):
            result = self._create(project)

        self.assertEqual(0, result)
        self.assertEqual("", stderr.getvalue())

    def test_generation_stays_quiet_when_a_location_is_recorded(self) -> None:
        project = self.root / "quiet-recorded"
        project.mkdir()
        stderr = io.StringIO()

        with contextlib.chdir(project), contextlib.redirect_stderr(stderr):
            result = self._create(project, "--sdk-dir", str(self._fake_sdk()))

        self.assertEqual(0, result)
        self.assertEqual("", stderr.getvalue())

    def test_warning_names_a_configured_location_that_is_not_an_sdk(self) -> None:
        project = self.root / "wrong-warned"
        project.mkdir()
        unrelated = self.root / "not-an-sdk"
        unrelated.mkdir()
        os.environ["ANDROID_HOME"] = str(unrelated)
        stderr = io.StringIO()

        with (
            contextlib.chdir(project),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(stderr),
        ):
            result = self._create_direct(project)

        self.assertEqual(0, result)
        self.assertIn("not an Android SDK", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
