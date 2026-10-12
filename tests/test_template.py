from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "src" / "android_skeleton" / "templates" / "v1"


class AndroidTemplateTest(unittest.TestCase):
    def test_template_includes_the_agreed_module_structure(self) -> None:
        settings = (TEMPLATE / "settings.gradle.kts").read_text()

        for module in (
            ":app",
            ":app:navigation",
            ":common:data",
            ":common:domain",
            ":common:presentation",
            ":common:testing",
            ":core:designsystem",
            ":core:navigation",
            ":core:datastore",
            ":feature:home",
            ":feature:home-api",
        ):
            with self.subTest(module=module):
                self.assertIn(module, settings)

    def test_template_orders_core_modules_before_features(self) -> None:
        settings = (TEMPLATE / "settings.gradle.kts").read_text()

        self.assertLess(
            settings.index('":core:navigation",'),
            settings.index('":feature:home",'),
        )
        # New features are appended after the reserved one, so this line must stay last.
        self.assertIn('    ":feature:home-api",__OPTIONAL_MODULE_INCLUDES__', settings)

    def test_template_keeps_no_screen_in_the_navigation_module(self) -> None:
        navigation_sources = TEMPLATE / "app" / "navigation" / "src" / "main" / "kotlin"
        declared = {
            path.name
            for path in navigation_sources.rglob("*.kt")
        }

        self.assertEqual({"AppRoutes.kt", "AppEntryProvider.kt"}, declared)
        self.assertFalse(
            (TEMPLATE / "app" / "navigation" / "src" / "main" / "res").exists(),
            "the navigation module must not declare resources",
        )

    def test_template_provides_the_shared_layer_modules(self) -> None:
        settings = (TEMPLATE / "settings.gradle.kts").read_text()

        for module in (":common:domain", ":common:data"):
            with self.subTest(module=module):
                self.assertIn(module, settings)
                self.assertTrue(
                    (TEMPLATE / module[1:].replace(":", "/") / "build.gradle.kts").is_file()
                )

    def test_template_minifies_the_release_variant(self) -> None:
        convention = (
            TEMPLATE
            / "build-logic"
            / "src"
            / "main"
            / "kotlin"
            / "android.application.gradle.kts"
        ).read_text()

        self.assertIn("isMinifyEnabled = true", convention)
        self.assertIn("isShrinkResources = true", convention)
        self.assertTrue((TEMPLATE / "app" / "proguard-rules.pro").is_file())

    def test_template_uses_the_agreed_android_and_jvm_baseline(self) -> None:
        build_logic = TEMPLATE / "build-logic" / "src" / "main" / "kotlin"
        plugin_sources = "\n".join(
            path.read_text() for path in build_logic.glob("*.gradle.kts")
        )

        for setting in (
            "compileSdk = 37",
            "targetSdk = 36",
            "minSdk = 24",
            "JavaVersion.VERSION_21",
            "jvmToolchain(21)",
        ):
            with self.subTest(setting=setting):
                self.assertIn(setting, plugin_sources)

    def test_template_declares_the_agreed_ui_and_application_stack(self) -> None:
        catalog = (TEMPLATE / "gradle" / "libs.versions.toml").read_text()

        for dependency in (
            "compose-bom",
            "compose-material3",
            "androidx-navigation3-runtime",
            "androidx-navigation3-ui",
            "androidx-savedstate-compose",
            "kotlinx-serialization-core",
            "kotlinx-serialization-json",
            "androidx-datastore-preferences",
            "orbit-core",
            "orbit-viewmodel",
            "koin-android",
        ):
            with self.subTest(dependency=dependency):
                self.assertIn(dependency, catalog)

        self.assertNotIn("androidx-navigation-compose", catalog)

        for version in ('agp = "9.4.1"', 'kotlin = "2.4.20"'):
            with self.subTest(version=version):
                self.assertIn(version, catalog)

    def test_template_contains_no_appscanner_specific_behavior(self) -> None:
        source_text = "\n".join(
            path.read_text()
            for path in TEMPLATE.rglob("*")
            if path.is_file() and path.suffix in {".kt", ".kts", ".xml", ".toml"}
        )

        # `feature/home` is deliberately absent from this list: the start screen is a feature of the
        # generated project, so the template names it. What must not survive is AppScanner's own
        # package, product name and permissions.
        for appscanner_detail in (
            "net.arsinde.appscaner",
            "AppScanner",
            "QUERY_ALL_PACKAGES",
        ):
            with self.subTest(detail=appscanner_detail):
                self.assertNotIn(appscanner_detail, source_text)
