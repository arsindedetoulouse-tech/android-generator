from __future__ import annotations

import glob
import subprocess
import sys
import tomllib
import unittest
from importlib.resources import files
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class PackageContractTest(unittest.TestCase):
    def test_project_declares_console_entry_and_template_package_data(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as project_file:
            project = tomllib.load(project_file)

        self.assertEqual("android-skeleton", project["project"]["name"])
        self.assertEqual(
            "android_skeleton.cli:main",
            project["project"]["scripts"]["android-skeleton"],
        )
        patterns = project["tool"]["setuptools"]["package-data"]["android_skeleton"]

        self.assertIn("templates/**/*", patterns)

    def test_every_template_file_is_covered_by_the_package_data(self) -> None:
        """No template file may be dropped when the package is installed.

        setuptools applies these patterns with glob semantics, which do not match a leading dot.
        A pattern change that stops covering a file fails only for an installed package, so the
        coverage is checked here instead of being discovered by a user.
        """
        with (ROOT / "pyproject.toml").open("rb") as project_file:
            patterns = tomllib.load(project_file)["tool"]["setuptools"]["package-data"][
                "android_skeleton"
            ]

        package_root = ROOT / "src" / "android_skeleton"
        template_root = package_root / "templates"
        expected = {
            path.relative_to(package_root).as_posix()
            for path in template_root.rglob("*")
            if path.is_file()
        }
        packaged = {
            Path(match).relative_to(package_root).as_posix()
            for pattern in patterns
            for match in glob.glob(str(package_root / pattern), recursive=True)
            if Path(match).is_file()
        }

        self.assertEqual(set(), expected - packaged)

    def test_template_manifest_is_available_as_package_resource(self) -> None:
        manifest = files("android_skeleton").joinpath(
            "templates", "v1", "manifest.json"
        )
        gradle_wrapper = files("android_skeleton").joinpath(
            "templates", "v1", "gradle", "wrapper", "gradle-wrapper.jar"
        )
        app_entry_point = files("android_skeleton").joinpath(
            "templates",
            "v1",
            "app",
            "src",
            "main",
            "kotlin",
            "__PACKAGE_PATH__",
            "MainActivity.kt",
        )

        self.assertTrue(manifest.is_file())
        self.assertTrue(gradle_wrapper.is_file())
        self.assertTrue(app_entry_point.is_file())

    def test_module_entry_point_displays_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "android_skeleton", "--help"],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("android-skeleton", result.stdout)
