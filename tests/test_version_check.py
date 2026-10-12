from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from android_skeleton import TEMPLATE_VERSION, __version__, version_check as vc


class VersionComparisonTest(unittest.TestCase):
    def test_versions_compare_numerically_not_as_text(self) -> None:
        # Compared as text, "0.10.0" would sort below "0.9.0".
        self.assertTrue(vc.is_newer("0.10.0", "0.9.0"))
        self.assertTrue(vc.is_newer("1.0.0", "0.99.99"))
        self.assertTrue(vc.is_newer("0.3.1", "0.3.0"))

    def test_an_equal_version_is_not_newer(self) -> None:
        self.assertFalse(vc.is_newer("0.3.0", "0.3.0"))
        self.assertFalse(vc.is_newer("0.3.0", "0.4.0"))

    def test_an_unparsable_version_is_never_treated_as_newer(self) -> None:
        for value in ("nightly", "v1.2", "", "1.2.3.4"):
            with self.subTest(value=value):
                self.assertFalse(vc.is_newer(value, "0.3.0"))

    def test_release_tags_lose_their_prefix(self) -> None:
        for tag in ("v0.4.0", "V0.4.0", " 0.4.0 "):
            with self.subTest(tag=tag):
                self.assertEqual("0.4.0", vc._normalize_tag(tag))


class RepositorySlugTest(unittest.TestCase):
    def test_supported_addresses_yield_a_slug(self) -> None:
        expected = "owner/name"
        for url in (
            "https://github.com/owner/name",
            "https://github.com/owner/name/",
            "https://github.com/owner/name.git",
            "git@github.com:owner/name.git",
            "http://github.com/owner/name",
        ):
            with self.subTest(url=url):
                self.assertEqual(expected, vc._repository_slug(url))

    def test_an_unrelated_address_yields_nothing(self) -> None:
        for url in (
            "https://example.com/owner/name",
            "https://github.com/owner",
            "",
            "https://github.com/",
        ):
            with self.subTest(url=url):
                self.assertIsNone(vc._repository_slug(url))


class InternalConsistencyTest(unittest.TestCase):
    def test_the_installed_package_is_consistent(self) -> None:
        check = vc.check_internal_consistency()

        self.assertEqual(vc._UP_TO_DATE, check.status)
        self.assertIsNone(check.warning)

    def test_a_template_version_that_disagrees_with_the_manifest_is_reported(self) -> None:
        with patch.object(vc, "_read_manifest", return_value={"template_version": "9.9.9"}):
            check = vc.check_internal_consistency()

        self.assertEqual(vc._NEWER_AVAILABLE, check.status)
        assert check.warning is not None
        self.assertIn("9.9.9", check.warning)
        self.assertIn(TEMPLATE_VERSION, check.warning)

    def test_a_template_absent_from_the_supported_versions_is_reported(self) -> None:
        with patch.dict(vc.SUPPORTED_TEMPLATE_VERSIONS, {}, clear=True):
            check = vc.check_internal_consistency()

        self.assertEqual(vc._NEWER_AVAILABLE, check.status)
        assert check.warning is not None
        self.assertIn("supported template versions", check.warning)

    def test_a_required_cli_version_other_than_this_one_is_reported(self) -> None:
        with patch.dict(
            vc.SUPPORTED_TEMPLATE_VERSIONS, {TEMPLATE_VERSION: "9.9.9"}
        ):
            check = vc.check_internal_consistency()

        assert check.warning is not None
        self.assertIn("9.9.9", check.warning)

    def test_a_cli_older_than_its_template_requires_is_reported(self) -> None:
        with patch.object(
            vc, "_read_manifest", return_value={"minimum_cli_version": "9.9.9"}
        ):
            check = vc.check_minimum_cli_version()

        self.assertEqual(vc._NEWER_AVAILABLE, check.status)
        assert check.warning is not None
        self.assertIn("9.9.9", check.warning)
        self.assertIn(__version__, check.warning)

    def test_a_satisfied_minimum_cli_version_is_silent(self) -> None:
        with patch.object(
            vc, "_read_manifest", return_value={"minimum_cli_version": "0.0.1"}
        ):
            check = vc.check_minimum_cli_version()

        self.assertEqual(vc._UP_TO_DATE, check.status)
        self.assertIsNone(check.warning)


class SourceTreeTest(unittest.TestCase):
    def test_a_plain_copy_has_no_tree_to_compare_and_stays_silent(self) -> None:
        with patch.object(vc, "_find_repository_root", return_value=None):
            check = vc.check_source_tree()

        self.assertEqual(vc._UP_TO_DATE, check.status)
        self.assertIsNone(check.warning)

    def test_a_tree_ahead_of_the_installed_copy_is_reported(self) -> None:
        with patch.object(vc, "_find_repository_root", return_value=Path("/repo")):
            with patch.object(vc, "_read_project_version", return_value="9.9.9"):
                with patch.object(vc, "package_version", return_value="0.3.0"):
                    check = vc.check_source_tree()

        self.assertEqual(vc._NEWER_AVAILABLE, check.status)
        assert check.warning is not None
        self.assertIn("9.9.9", check.warning)
        self.assertIn("0.3.0", check.warning)
        self.assertIn("/repo", check.warning)

    def test_a_tree_behind_the_installed_copy_is_not_reported(self) -> None:
        with patch.object(vc, "_find_repository_root", return_value=Path("/repo")):
            with patch.object(vc, "_read_project_version", return_value="0.1.0"):
                with patch.object(vc, "package_version", return_value="0.3.0"):
                    check = vc.check_source_tree()

        self.assertEqual(vc._UP_TO_DATE, check.status)
        self.assertIsNone(check.warning)

    def test_the_repository_root_is_found_next_to_the_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="version-tree-") as temp:
            repository = Path(temp)
            (repository / ".git").mkdir()
            nested = repository / "src" / "android_skeleton"
            nested.mkdir(parents=True)

            self.assertEqual(repository, vc._find_repository_root(nested))

    def test_a_directory_without_a_repository_is_not_found(self) -> None:
        with tempfile.TemporaryDirectory(prefix="version-no-tree-") as temp:
            self.assertIsNone(vc._find_repository_root(Path(temp)))


class RemoteReferenceTest(unittest.TestCase):
    def test_a_newer_release_is_reported_with_an_update_command(self) -> None:
        with patch.object(vc, "package_url", return_value="https://github.com/o/n"):
            with patch.object(vc, "_fetch_json", return_value=(200, {"tag_name": "v0.4.0"})):
                check = vc.check_github_release()

        self.assertEqual(vc._NEWER_AVAILABLE, check.status)
        assert check.warning is not None
        self.assertIn("0.4.0", check.warning)
        self.assertIn(__version__, check.warning)
        self.assertIn("pipx install", check.warning)

    def test_the_same_release_is_not_a_mismatch(self) -> None:
        with patch.object(vc, "package_url", return_value="https://github.com/o/n"):
            with patch.object(vc, "_fetch_json", return_value=(200, {"tag_name": f"v{__version__}"})):
                check = vc.check_github_release()

        self.assertEqual(vc._UP_TO_DATE, check.status)
        self.assertIsNone(check.warning)

    def test_no_releases_is_a_fact_rather_than_a_mismatch(self) -> None:
        with patch.object(vc, "package_url", return_value="https://github.com/o/n"):
            with patch.object(vc, "_fetch_json", return_value=(404, None)):
                check = vc.check_github_release()

        self.assertEqual(vc._NOT_PUBLISHED, check.status)
        self.assertIsNone(check.warning)

    def test_an_unreachable_network_is_unverified(self) -> None:
        with patch.object(vc, "package_url", return_value="https://github.com/o/n"):
            with patch.object(vc, "_fetch_json", return_value=None):
                check = vc.check_github_release()

        self.assertEqual(vc._UNVERIFIED, check.status)
        self.assertIsNone(check.warning)

    def test_a_malformed_release_payload_is_unverified(self) -> None:
        for payload in ({}, {"tag_name": ""}, {"tag_name": 7}, []):
            with self.subTest(payload=payload):
                with patch.object(vc, "package_url", return_value="https://github.com/o/n"):
                    with patch.object(vc, "_fetch_json", return_value=(200, payload)):
                        check = vc.check_github_release()

                self.assertEqual(vc._UNVERIFIED, check.status)

    def test_an_unknown_repository_address_skips_the_check(self) -> None:
        with patch.object(vc, "package_url", return_value="https://example.com/x"):
            check = vc.check_github_release()

        self.assertEqual(vc._UNVERIFIED, check.status)

    def test_a_newer_published_version_is_reported(self) -> None:
        with patch.object(vc, "_fetch_json", return_value=(200, {"info": {"version": "0.9.1"}})):
            check = vc.check_published_package()

        self.assertEqual(vc._NEWER_AVAILABLE, check.status)
        assert check.warning is not None
        self.assertIn("0.9.1", check.warning)

    def test_an_unpublished_package_is_a_fact_rather_than_a_mismatch(self) -> None:
        with patch.object(vc, "_fetch_json", return_value=(404, None)):
            check = vc.check_published_package()

        self.assertEqual(vc._NOT_PUBLISHED, check.status)
        self.assertIsNone(check.warning)

    def test_an_unreachable_index_is_unverified(self) -> None:
        with patch.object(vc, "_fetch_json", return_value=None):
            check = vc.check_published_package()

        self.assertEqual(vc._UNVERIFIED, check.status)

    def test_a_malformed_index_payload_is_unverified(self) -> None:
        for payload in ({}, {"info": {}}, {"info": {"version": 3}}):
            with self.subTest(payload=payload):
                with patch.object(vc, "_fetch_json", return_value=(200, payload)):
                    check = vc.check_published_package()

                self.assertEqual(vc._UNVERIFIED, check.status)


class WarningRenderingTest(unittest.TestCase):
    def test_silent_states_produce_no_output(self) -> None:
        checks = [
            vc.VersionCheck("github-release", vc._UP_TO_DATE),
            vc.VersionCheck("published-package", vc._NOT_PUBLISHED),
            vc.VersionCheck("source-tree", vc._UP_TO_DATE),
        ]

        self.assertEqual([], vc.format_warnings(checks))

    def test_unverified_checks_are_summarised_in_one_line(self) -> None:
        checks = [
            vc.VersionCheck("github-release", vc._UNVERIFIED),
            vc.VersionCheck("published-package", vc._UNVERIFIED),
        ]

        lines = vc.format_warnings(checks)

        self.assertEqual(1, len(lines))
        self.assertIn("github-release", lines[0])
        self.assertIn("published-package", lines[0])
        self.assertIn("continues", lines[0])

    def test_warnings_are_rendered_before_the_unverified_line(self) -> None:
        checks = [
            vc.VersionCheck("github-release", vc._NEWER_AVAILABLE, warning="newer"),
            vc.VersionCheck("published-package", vc._UNVERIFIED),
        ]

        lines = vc.format_warnings(checks)

        self.assertEqual(2, len(lines))
        self.assertEqual("newer", lines[0])

    def test_the_header_names_the_generator_and_its_template(self) -> None:
        header = vc.format_version_header()

        self.assertIn(__version__, header)
        self.assertIn(TEMPLATE_VERSION, header)

    def test_collect_checks_can_run_without_the_network(self) -> None:
        checks = vc.collect_checks(include_network=False)

        self.assertEqual(3, len(checks))
        self.assertFalse(
            any(check.name in ("github-release", "published-package") for check in checks)
        )


class ProjectTemplateTest(unittest.TestCase):
    def test_the_recorded_template_version_is_read(self) -> None:
        with tempfile.TemporaryDirectory(prefix="project-template-") as temp:
            project = Path(temp)
            (project / ".android-skeleton.json").write_text(
                json.dumps({"template_version": "1.1.0"}), encoding="utf-8"
            )

            self.assertEqual("1.1.0", vc.project_template_version(project))

    def test_an_absent_or_broken_metadata_file_yields_nothing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="project-template-") as temp:
            project = Path(temp)
            self.assertIsNone(vc.project_template_version(project))

            (project / ".android-skeleton.json").write_text("{", encoding="utf-8")
            self.assertIsNone(vc.project_template_version(project))

            (project / ".android-skeleton.json").write_text(
                json.dumps({"template_version": ""}), encoding="utf-8"
            )
            self.assertIsNone(vc.project_template_version(project))

    def test_the_mismatch_message_names_both_versions_and_the_way_out(self) -> None:
        message = vc.build_template_mismatch_message("1.1.0")

        self.assertIn("1.1.0", message)
        self.assertIn(__version__, message)
        self.assertIn(TEMPLATE_VERSION, message)
        self.assertIn("--force", message)


if __name__ == "__main__":
    unittest.main()