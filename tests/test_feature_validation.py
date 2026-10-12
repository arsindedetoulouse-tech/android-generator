from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from android_skeleton.cli import main
from android_skeleton.feature import (
    FeatureValidationError,
    parse_feature_slug,
    validate_feature_request,
)


class FeatureValidationTest(unittest.TestCase):
    def test_feature_slug_maps_to_package_and_type_names(self) -> None:
        identity = parse_feature_slug("user-profile")

        self.assertEqual("user-profile", identity.slug)
        self.assertEqual("userprofile", identity.package_segment)
        self.assertEqual("UserProfile", identity.type_name)

    def test_feature_slug_must_be_lowercase_kebab_case(self) -> None:
        for slug in ("", "User-profile", "user_profile", "-profile", "user-", "2fa"):
            with self.subTest(slug=slug), self.assertRaises(FeatureValidationError):
                parse_feature_slug(slug)

    def test_add_feature_requires_supported_project_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="missing-metadata-") as temp:
            project = Path(temp)
            before = sorted(path.name for path in project.iterdir())
            stderr = io.StringIO()

            with contextlib.chdir(project), contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as error:
                    main(["add-feature", "user-profile"])

            self.assertEqual(2, error.exception.code)
            self.assertEqual(before, sorted(path.name for path in project.iterdir()))
            self.assertIn(".android-skeleton.json", stderr.getvalue())

    def test_add_feature_rejects_unsupported_metadata_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="unsupported-metadata-") as temp:
            project = self._create_project(Path(temp))
            metadata_path = project / ".android-skeleton.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["template_version"] = "9.0.0"
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            before = self._snapshot(project)
            stderr = io.StringIO()

            with contextlib.chdir(project), contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as error:
                    main(["add-feature", "user-profile"])

            self.assertEqual(2, error.exception.code)
            self.assertEqual(before, self._snapshot(project))
            self.assertIn("Unsupported template version", stderr.getvalue())

    def test_add_feature_rejects_invalid_slug_before_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="invalid-feature-") as temp:
            project = self._create_project(Path(temp))
            before = self._snapshot(project)
            stderr = io.StringIO()

            with contextlib.chdir(project), contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as error:
                    main(["add-feature", "User_Profile"])

            self.assertEqual(2, error.exception.code)
            self.assertEqual(before, self._snapshot(project))
            self.assertIn("kebab-case", stderr.getvalue())

    def test_existing_feature_path_conflicts_before_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="feature-conflict-") as temp:
            project = self._create_project(Path(temp))
            existing_feature = project / "feature" / "user-profile"
            existing_feature.mkdir(parents=True)
            sentinel = existing_feature / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")
            before = self._snapshot(project)

            with self.assertRaisesRegex(FeatureValidationError, "already exists"):
                validate_feature_request(project, "user-profile")

            self.assertEqual(before, self._snapshot(project))

    def test_metadata_feature_registration_conflicts_before_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="registered-feature-") as temp:
            project = self._create_project(Path(temp))
            metadata_path = project / ".android-skeleton.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["features"] = ["user-profile"]
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            before = self._snapshot(project)

            with self.assertRaisesRegex(FeatureValidationError, "already registered"):
                validate_feature_request(project, "user-profile")

            self.assertEqual(before, self._snapshot(project))

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

    @staticmethod
    def _snapshot(project: Path) -> dict[str, bytes]:
        return {
            path.relative_to(project).as_posix(): path.read_bytes()
            for path in project.rglob("*")
            if path.is_file()
        }


if __name__ == "__main__":
    unittest.main()
