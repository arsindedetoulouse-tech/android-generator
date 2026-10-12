from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from android_skeleton.validation import InputValidationError, validate_locale_tag


class LocaleTagValidationTest(unittest.TestCase):
    def test_valid_bcp47_tags_are_canonicalized(self) -> None:
        cases = {
            "ru-ru": "ru-RU",
            "uz-latn-uz": "uz-Latn-UZ",
            "zh-hant-tw": "zh-Hant-TW",
            "en-us-u-ca-gregory": "en-US-u-ca-gregory",
            "zh-cmn-hans-cn": "zh-cmn-Hans-CN",
            "en-gb-oed": "en-GB-oed",
            "und": "und",
            "x-private": "x-private",
        }

        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(expected, validate_locale_tag(value))

    def test_invalid_bcp47_tags_are_rejected(self) -> None:
        for value in ("", "ru_RU", "en--US", "a-US", "en-u", "en-u-ca-u-nu"):
            with self.subTest(value=value):
                with self.assertRaises(InputValidationError):
                    validate_locale_tag(value)


if __name__ == "__main__":
    unittest.main()
