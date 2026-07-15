import json
from pathlib import Path
import tempfile
import unittest
from typing import Optional
from unittest.mock import patch

from scripts import mota_builder_app


class UiInstanceIsolationTest(unittest.TestCase):
    def write_run(self, root: Path, run_id: str, instance_id: Optional[str]) -> None:
        run_dir = root / run_id
        run_dir.mkdir()
        status = {"run_id": run_id, "state": "complete"}
        if instance_id is not None:
            status["ui_instance_id"] = instance_id
        (run_dir / mota_builder_app.STATUS_FILENAME).write_text(
            json.dumps(status), encoding="utf-8"
        )

    def test_run_is_only_accessible_from_its_own_port(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir)
            self.write_run(runs_dir, "run-8766", "127.0.0.1:8766")
            with patch.object(mota_builder_app, "RUNS_DIR", runs_dir):
                resolved = mota_builder_app.require_run_for_ui_instance(
                    "run-8766", "127.0.0.1:8766"
                )
                self.assertEqual(resolved, runs_dir / "run-8766")
                with self.assertRaises(FileNotFoundError):
                    mota_builder_app.require_run_for_ui_instance(
                        "run-8766", "127.0.0.1:8765"
                    )

    def test_legacy_run_is_only_visible_on_default_port(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir)
            self.write_run(runs_dir, "legacy-run", None)
            with patch.object(mota_builder_app, "RUNS_DIR", runs_dir):
                mota_builder_app.require_run_for_ui_instance(
                    "legacy-run", f"127.0.0.1:{mota_builder_app.DEFAULT_UI_PORT}"
                )
                with self.assertRaises(FileNotFoundError):
                    mota_builder_app.require_run_for_ui_instance(
                        "legacy-run", "127.0.0.1:8766"
                    )


class WebBuildCommandTest(unittest.TestCase):
    def test_new_run_does_not_reuse_generation_cache(self) -> None:
        command = mota_builder_app.build_command(
            Path("/tmp/output"), Path("/tmp/idea.txt"), {}, "idea"
        )
        self.assertIn("--no-generation-cache", command)

    def test_resume_keeps_its_existing_output_without_cache_flag(self) -> None:
        command = mota_builder_app.build_command(
            Path("/tmp/output"),
            Path("/tmp/tower_brief.json"),
            {"resumeExisting": True},
            "brief",
        )
        self.assertIn("--resume-existing", command)
        self.assertNotIn("--no-generation-cache", command)


class TowerStyleDefaultsTest(unittest.TestCase):
    def test_traditional_defaults_are_unchanged(self) -> None:
        defaults = mota_builder_app.default_resources(4, "traditional")
        self.assertEqual(defaults["redGems"], 24)
        self.assertEqual(defaults["blueGems"], 24)
        self.assertEqual(defaults["redPotions"], 24)
        self.assertEqual(defaults["bluePotions"], 4)
        self.assertEqual(defaults["pickaxes"], 2)
        self.assertEqual(defaults["bombs"], 2)
        self.assertEqual(defaults["centerFly"], 2)

        normalized = mota_builder_app.normalize_form({"towerStyle": "traditional"})
        self.assertEqual((normalized["wallRatioMin"], normalized["wallRatioMax"]), (0.35, 0.45))
        self.assertEqual((normalized["enemyMin"], normalized["enemyMax"]), (18, 28))

    def test_red_sea_defaults_are_style_specific(self) -> None:
        defaults = mota_builder_app.default_resources(4, "red_sea")
        self.assertEqual(defaults["redGems"], 28)
        self.assertEqual(defaults["blueGems"], 28)
        self.assertEqual(defaults["redPotions"], 28)
        self.assertEqual(defaults["bluePotions"], 12)
        self.assertEqual(defaults["yellowKeys"], 8)
        self.assertEqual(defaults["blueKeys"], 4)
        self.assertEqual(defaults["pickaxes"], 4)
        self.assertEqual(defaults["bombs"], 4)
        self.assertEqual(defaults["centerFly"], 4)

        normalized = mota_builder_app.normalize_form({"towerStyle": "red_sea"})
        self.assertEqual((normalized["wallRatioMin"], normalized["wallRatioMax"]), (0.40, 0.52))
        self.assertEqual((normalized["enemyMin"], normalized["enemyMax"]), (24, 32))

    def test_red_sea_floor_plan_is_progressive_and_exact(self) -> None:
        limits = {
            key: 0
            for key in mota_builder_app.TRACKED_RESOURCE_KEYS
        }
        limits.update(
            {
                "redGems": 42,
                "blueGems": 42,
                "redPotions": 42,
                "bluePotions": 18,
                "yellow_keys": 12,
                "blue_keys": 6,
                "pickaxes": 6,
                "bombs": 6,
                "centerFly": 6,
            }
        )
        plan = mota_builder_app.red_sea_floor_progression_plan(limits, 6)
        for key in mota_builder_app.TRACKED_RESOURCE_KEYS:
            self.assertEqual(sum(item["resource_budget"][key] for item in plan), limits[key])
        self.assertEqual([item["resource_budget"]["redGems"] for item in plan], [6, 6, 7, 7, 8, 8])
        self.assertEqual([item["resource_budget"]["bluePotions"] for item in plan], [3] * 6)

    def test_red_sea_brief_does_not_receive_traditional_fixed_rule(self) -> None:
        brief = mota_builder_app.build_brief({"towerStyle": "red_sea"})
        self.assertNotIn("traditional key-door route pressure", brief["fixed_rules"])
        self.assertIn("red-sea fragmented local-route and distributed-resource pressure", brief["fixed_rules"])


if __name__ == "__main__":
    unittest.main()
