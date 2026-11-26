"""Ordering assertions for deployment's Nginx reconciliation gate."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]


class DeployNginxContract(unittest.TestCase):
    def test_gate_precedes_checkout_cutover_and_deploy_refresh(self):
        source = (ROOT / "src/scripts/operacion/deploy_verified.sh").read_text(
            encoding="utf-8"
        )
        gate = 'bash "$nginx_gate" "$DEPLOY_ENVIRONMENT" "$EXPECTED_REVISION"'
        self.assertIn(gate, source)
        self.assertLess(source.index(gate), source.index("deployment_started=1"))
        self.assertLess(
            source.index(gate),
            source.index('bash "$ROOT_DIR/src/scripts/operacion/deploy_refresh.sh"'),
        )

    def test_qa_gate_runs_before_checkout_fast_forward(self):
        source = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
        qa = source.split("    deploy-qa:", 1)[1].split("    deploy-homologacion:", 1)[
            0
        ]
        self.assertLess(
            qa.index('bash "$nginx_gate" qa "$EXPECTED_SHA"'),
            qa.index('git -C "$APP_ROOT" merge --ff-only'),
        )


if __name__ == "__main__":
    unittest.main()
