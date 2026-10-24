"""Each target receives only options compatible with its selected patch bundle."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class OptionsContracts(unittest.TestCase):
    def test_rushiranpise_options_are_scoped_to_the_target_app(self):
        targets = {target["id"]: target for target in json.loads((ROOT / "src/targets.json").read_text())}

        def options_for(target_id):
            target = targets[target_id]
            candidate = next(candidate for candidate in target["candidates"] if candidate["name"] == "rushiranpise")
            return json.loads((ROOT / "src/options" / (candidate["options"] + ".json")).read_text())

        photos = options_for("photos")
        self.assertEqual(photos, [{"patches": {"Change package name": {
            "enabled": True,
            "options": {
                "googlePhotosPackageName": "app.morphe.android.apps.photos",
                "googlePhotosAppName": "Photos",
            },
        }}}])
        for target_id in ("adguard", "telegram"):
            with self.subTest(target=target_id):
                options = options_for(target_id)
                self.assertTrue(all("Change package name" not in item.get("patches", {})
                                    for item in options))
