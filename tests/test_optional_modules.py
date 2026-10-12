from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from android_skeleton.cli import main


class OptionalModulesTest(unittest.TestCase):
    def create_project(self, flags: tuple[str, ...] = ()) -> Path:
        temp = tempfile.TemporaryDirectory(prefix="optional-modules-")
        self.addCleanup(temp.cleanup)
        project = Path(temp.name)

        with contextlib.chdir(project), contextlib.redirect_stdout(io.StringIO()):
            result = main(
                [
                    "create",
                    "--package",
                    "com.example.sample",
                    "--application-id",
                    "com.example.sample.app",
                    *flags,
                ]
            )

        self.assertEqual(0, result)
        return project

    def test_storage_module_is_present_without_flags(self) -> None:
        project = self.create_project()
        settings = (project / "settings.gradle.kts").read_text()
        app_dependencies = (project / "app/build.gradle.kts").read_text()
        app_module = (
            project / "app/src/main/kotlin/com/example/sample/App.kt"
        ).read_text()
        datastore_build = (project / "core/datastore/build.gradle.kts").read_text()
        datastore_source = (
            project
            / "core/datastore/src/main/kotlin/com/example/sample/core/datastore/DataStoreModule.kt"
        ).read_text()
        catalog = (project / "gradle/libs.versions.toml").read_text()
        manifest = (project / "app/src/main/AndroidManifest.xml").read_text()
        metadata = json.loads((project / ".android-skeleton.json").read_text())
        catalog_data = tomllib.loads(catalog)

        self.assertIn('":core:datastore"', settings)
        self.assertIn('project(":core:datastore")', app_dependencies)
        self.assertIn("coreDataStoreModule", app_module)
        self.assertTrue((project / "core/datastore").is_dir())
        self.assertIn("libs.androidx.datastore.preferences", datastore_build)
        self.assertIn("preferencesDataStore", datastore_source)
        self.assertIn("androidx-datastore", catalog)
        self.assertIn("androidx-datastore-preferences", catalog_data["libraries"])
        # Storage is not network: no permission and no HTTP client may appear without the flag.
        self.assertNotIn("INTERNET", manifest)
        self.assertNotIn("io.ktor", catalog)
        self.assertFalse((project / "core/network").exists())
        self.assertNotIn("datastore", metadata["options"])
        # The start screen is not optional infrastructure: it stays registered whatever the flags say.
        self.assertIn("homeModule", app_module)

    def test_datastore_flag_is_rejected(self) -> None:
        project = self.create_project()

        with contextlib.chdir(project), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(
                    [
                        "create",
                        "--package",
                        "com.example.sample",
                        "--application-id",
                        "com.example.sample.app",
                        "--datastore",
                    ]
                )

    def test_network_flag_adds_only_network_module_and_wiring(self) -> None:
        project = self.create_project(("--network",))
        settings = (project / "settings.gradle.kts").read_text()
        app_dependencies = (project / "app/build.gradle.kts").read_text()
        app_module = (
            project / "app/src/main/kotlin/com/example/sample/App.kt"
        ).read_text()
        network_build = (project / "core/network/build.gradle.kts").read_text()
        network_source = (
            project
            / "core/network/src/main/kotlin/com/example/sample/core/network/NetworkModule.kt"
        ).read_text()
        catalog = (project / "gradle/libs.versions.toml").read_text()
        manifest = (project / "app/src/main/AndroidManifest.xml").read_text()
        metadata = json.loads((project / ".android-skeleton.json").read_text())
        catalog_data = tomllib.loads(catalog)

        self.assertIn('":core:network"', settings)
        self.assertIn('project(":core:network")', app_dependencies)
        self.assertIn("coreNetworkModule", app_module)
        self.assertIn('android:name="android.permission.INTERNET"', manifest)
        self.assertIn("libs.ktor.client.okhttp", network_build)
        self.assertIn("HttpClient(OkHttp)", network_source)
        self.assertIn("ContentNegotiation", network_source)
        self.assertIn("expectSuccess = false", network_source)
        self.assertIn("HttpTimeout", network_source)
        self.assertNotIn("baseUrl", network_source)
        self.assertNotIn("Logging", network_source)
        self.assertIn("io.ktor", catalog)
        self.assertIn("ktor-client-okhttp", catalog_data["libraries"])
        self.assertTrue((project / "core/network").is_dir())
        self.assertEqual(True, metadata["options"]["network"])

    def test_data_chain_dependencies_are_available_without_flags(self) -> None:
        project = self.create_project()
        catalog = (project / "gradle/libs.versions.toml").read_text()
        common_data = (project / "common/data/build.gradle.kts").read_text()
        catalog_data = tomllib.loads(catalog)

        # The offline chain parses its stub with kotlinx.serialization, which therefore cannot be
        # gated behind the network flag.
        self.assertIn("kotlinx-serialization-json", catalog_data["libraries"])
        self.assertIn("libs.kotlinx.serialization.json", common_data)
        self.assertIn('project(":core:datastore")', common_data)

    def test_catalog_has_no_empty_lines(self) -> None:
        for flags in ((), ("--network",)):
            with self.subTest(flags=flags):
                project = self.create_project(flags)
                catalog = (project / "gradle/libs.versions.toml").read_text()

                # A placeholder that collapses to nothing must not leave a blank line inside a
                # section; the blank line between sections is part of the template's formatting.
                for section in ("[versions]", "[libraries]", "[plugins]"):
                    body = catalog.split(section, 1)[1].split("\n[", 1)[0]
                    for number, line in enumerate(body.strip().splitlines(), start=1):
                        with self.subTest(section=section, line=number):
                            self.assertNotEqual("", line.strip())
                # The catalog has to stay parseable after the placeholder replacements.
                tomllib.loads(catalog)

    def test_optional_includes_collapse_without_a_blank_line(self) -> None:
        project = self.create_project()
        settings = (project / "settings.gradle.kts").read_text()

        include_block = settings.split("include(", 1)[1]
        self.assertNotIn("\n\n", include_block)


if __name__ == "__main__":
    unittest.main()