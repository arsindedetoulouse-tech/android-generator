from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from android_skeleton.cli import main


def _android_sdk_available() -> bool:
    if os.environ.get("ANDROID_SKELETON_INTEGRATION") != "1":
        return False
    return bool(os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT"))


@unittest.skipUnless(
    _android_sdk_available(),
    "set ANDROID_SKELETON_INTEGRATION=1 with ANDROID_HOME to run real Gradle builds",
)
class GeneratorIntegrationTest(unittest.TestCase):
    """End-to-end checks that run a real Gradle build.

    Opt-in because each case downloads plugins, builds every module and runs its unit tests, which
    takes minutes and needs a configured Android SDK. Run with:

        ANDROID_SKELETON_INTEGRATION=1 ANDROID_HOME=... python -m unittest test_integration
    """

    def test_created_project_builds_and_runs_its_tests(self) -> None:
        with tempfile.TemporaryDirectory(prefix="integration-create-") as temp:
            project = Path(temp)

            with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
                result = main(
                    [
                        "create",
                        "--package",
                        "com.example.integration",
                        "--application-id",
                        "com.example.integration.app",
                        "--verify",
                    ]
                )

            self.assertEqual(0, result)
            self._assert_tests_ran(project, "com.example.integration.core.navigation.NavigatorTest")

    def test_added_feature_builds_and_runs_its_tests(self) -> None:
        with tempfile.TemporaryDirectory(prefix="integration-feature-") as temp:
            project = Path(temp)

            with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
                main(
                    [
                        "create",
                        "--package",
                        "com.example.integration",
                        "--application-id",
                        "com.example.integration.app",
                    ]
                )
            with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
                result = main(["add-feature", "user-profile", "--verify"])

            self.assertEqual(0, result)
            self._assert_tests_ran(
                project,
                "com.example.integration.feature.userprofile."
                "presentation.UserProfileViewModelTest",
            )
            # The repository implementation and its test moved into the shared data module.
            self._assert_tests_ran(
                project,
                "com.example.integration.data.userprofile."
                "UserProfileRepositoryTest",
            )

    def _assert_tests_ran(self, project: Path, expected_test_class: str) -> None:
        reports = list(
            project.glob("**/build/test-results/*/TEST-*.xml")
        )
        self.assertTrue(reports, "no unit test reports were produced")
        executed = set()
        for report in reports:
            executed.add(report.stem.removeprefix("TEST-"))
        self.assertIn(
            expected_test_class,
            executed,
            f"expected {expected_test_class} among {sorted(executed)}",
        )


if __name__ == "__main__":
    unittest.main()