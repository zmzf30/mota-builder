from __future__ import annotations

from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import build_mota_tower as mota


class CopilotBackendTest(unittest.TestCase):
    def setUp(self) -> None:
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.output_path = Path(workspace.name) / "output" / "floor.json"
        self.args = mota.parse_args(["--self-test", "--agent-backend", "copilot"])
        self.schema = {"type": "object", "properties": {"floor_id": {"type": "string"}}}

    def test_defaults_preserve_cli_model_and_reasoning_settings(self) -> None:
        command = mota.build_copilot_command(self.args)

        self.assertEqual(command[:3], ["copilot", "-C", str(self.args.repo_root)])
        self.assertIn("--silent", command)
        self.assertIn("--no-ask-user", command)
        self.assertIn("--available-tools=", command)
        self.assertIn("--deny-tool=shell", command)
        self.assertIn("--deny-tool=write", command)
        self.assertNotIn("--model", command)
        self.assertNotIn("--reasoning-effort", command)
        self.assertNotIn("--config", command)
        self.assertEqual(self.args.config, [])
        self.assertEqual(self.args.max_attempts, mota.DEFAULT_MAX_ATTEMPTS)

    def test_custom_binary_model_and_repeatable_arguments(self) -> None:
        args = mota.parse_args([
            "--self-test", "--agent-backend", "copilot",
            "--copilot-bin", "/opt/bin/copilot", "--model", "custom-model",
            "--copilot-arg=--reasoning-effort=high", "--copilot-arg=--no-custom-instructions",
            "--max-attempts", "2",
        ])
        command = mota.build_copilot_command(args)

        self.assertEqual(command[0], "/opt/bin/copilot")
        self.assertEqual(command[-4:], [
            "--model", "custom-model", "--reasoning-effort=high", "--no-custom-instructions",
        ])
        self.assertEqual(args.max_attempts, 2)

    def test_backend_specific_arguments_are_rejected_for_other_backends(self) -> None:
        for backend, argument in (
            ("copilot", "--profile=custom"),
            ("copilot", "--config=key=value"),
            ("copilot", "--codex-arg=--custom"),
            ("copilot", "--opencode-arg=--custom"),
            ("codex", "--copilot-arg=--custom"),
            ("opencode", "--copilot-arg=--custom"),
        ):
            with self.subTest(backend=backend, argument=argument):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    mota.parse_args(["--self-test", "--agent-backend", backend, argument])

    def test_dispatch_sends_schema_on_stdin_and_persists_response(self) -> None:
        response = {"floor_id": "MT0"}
        with patch.object(mota.subprocess, "run", return_value=subprocess.CompletedProcess(
            [], 0, json.dumps(response), "",
        )) as run:
            result = mota.agent_exec(self.args, "Build a floor.", self.schema, self.output_path)

        self.assertEqual(result, response)
        self.assertEqual(json.loads(self.output_path.read_text()), response)
        self.assertEqual(run.call_args.args[0], mota.agent_command_for_subprocess(
            mota.build_copilot_command(self.args)
            + ["--log-dir", str(self.output_path.parent / ".copilot-logs")],
        ))
        self.assertEqual(run.call_args.kwargs["input"], mota.prompt_with_inline_schema(
            "Build a floor.", self.schema,
        ))
        self.assertEqual(run.call_args.kwargs["timeout"], self.args.timeout)
        self.assertTrue(run.call_args.kwargs["capture_output"])
        self.assertEqual(list(self.output_path.parent.iterdir()), [self.output_path])

    def test_keep_prompts_saves_schema_with_prompt(self) -> None:
        self.args.keep_prompts = True
        with patch.object(mota.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "{}", "")):
            mota.copilot_exec(self.args, "Build a floor.", self.schema, self.output_path)

        prompt_path = self.output_path.with_name(self.output_path.name + ".prompt.md")
        self.assertEqual(prompt_path.read_text(), mota.prompt_with_inline_schema(
            "Build a floor.", self.schema,
        ) + "\n")

    def test_process_failure_reports_output_without_persisting_it(self) -> None:
        with patch.object(mota.subprocess, "run", return_value=subprocess.CompletedProcess(
            [], 1, "partial output", "authentication failed",
        )):
            with self.assertRaises(mota.PipelineError) as caught:
                mota.copilot_exec(self.args, "Build a floor.", self.schema, self.output_path)

        self.assertIn("copilot failed", str(caught.exception))
        self.assertIn("authentication failed", str(caught.exception))
        self.assertIn("partial output", str(caught.exception))
        self.assertFalse(self.output_path.exists())

    def test_invalid_output_does_not_reuse_stale_file(self) -> None:
        self.output_path.parent.mkdir()
        self.output_path.write_text('{"floor_id": "stale"}')
        with patch.object(mota.subprocess, "run", return_value=subprocess.CompletedProcess(
            [], 0, "not json", "diagnostic details",
        )):
            with self.assertRaisesRegex(mota.PipelineError, "copilot output must contain a JSON object"):
                mota.copilot_exec(self.args, "Build a floor.", self.schema, self.output_path)

        self.assertEqual(json.loads(self.output_path.read_text()), {"floor_id": "stale"})

    def test_timeout_is_propagated_without_persisting_output(self) -> None:
        with patch.object(mota.subprocess, "run", side_effect=subprocess.TimeoutExpired("copilot", 1)):
            with self.assertRaises(subprocess.TimeoutExpired):
                mota.copilot_exec(self.args, "Build a floor.", self.schema, self.output_path)

        self.assertFalse(self.output_path.exists())


if __name__ == "__main__":
    unittest.main()