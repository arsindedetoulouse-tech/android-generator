from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from android_skeleton.metadata import (
    MetadataError,
    create_project_metadata,
    validate_project_metadata,
)


class ProjectMetadataTest(unittest.TestCase):
    def test_create_metadata_records_project_and_template_versions(self) -> None:
        metadata = create_project_metadata(
            project_name="Weather",
            package_name="com.example.weather",
            application_id="com.example.weather.app",
            options={"network": True, "locales": ["ru"]},
        )

        self.assertEqual(
            {
                "schema_version": 1,
                "cli_version": "0.3.0",
                "template_version": "1.2.0",
                "project_name": "Weather",
                "package_name": "com.example.weather",
                "application_id": "com.example.weather.app",
                "options": {
                    "network": True,
                    "locales": ["ru"],
                },
                "features": [],
            },
            metadata,
        )

    def test_validate_accepts_supported_template_and_cli(self) -> None:
        metadata = create_project_metadata(
            project_name="Weather",
            package_name="com.example.weather",
            application_id="com.example.weather",
        )

        parsed = validate_project_metadata(metadata)

        self.assertEqual("1.2.0", parsed.template_version)
        self.assertEqual((), parsed.features)

    def test_validate_rejects_unknown_metadata_schema(self) -> None:
        metadata = self._metadata()
        metadata["schema_version"] = 2

        with self.assertRaisesRegex(MetadataError, "schema version"):
            validate_project_metadata(metadata)

    def test_validate_rejects_unknown_template_version(self) -> None:
        metadata = self._metadata()
        metadata["template_version"] = "9.0.0"

        with self.assertRaisesRegex(MetadataError, "template version"):
            validate_project_metadata(metadata)

    def test_validate_rejects_cli_below_template_minimum(self) -> None:
        with self.assertRaisesRegex(MetadataError, "requires CLI"):
            validate_project_metadata(self._metadata(), cli_version="0.1.9")

    def test_validate_rejects_project_from_previous_template_version(self) -> None:
        metadata = self._metadata()
        metadata["template_version"] = "1.1.0"

        with self.assertRaisesRegex(MetadataError, "template version"):
            validate_project_metadata(metadata)

    @staticmethod
    def _metadata() -> dict[str, object]:
        return {
            "schema_version": 1,
            "cli_version": "0.3.0",
            "template_version": "1.2.0",
            "project_name": "Weather",
            "package_name": "com.example.weather",
            "application_id": "com.example.weather",
            "options": {},
            "features": [],
        }


if __name__ == "__main__":
    unittest.main()
