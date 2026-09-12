from pathlib import Path

from jinja2 import StrictUndefined, Template
import yaml

from swebench.inference.mini_swe_agent import build_command


def test_tsmc_prompt_uses_only_variables_supplied_by_mini(tmp_path):
    config = Path(__file__).resolve().parents[1] / "benchmarks/tsmc/configs/agent.yaml"
    data = yaml.safe_load(config.read_text())
    rendered = Template(
        data["agent"]["instance_template"], undefined=StrictUndefined
    ).render(task="Fix this issue")
    assert "Fix this issue" in rendered and "automatically collects" in rendered
    command = build_command(
        str(tmp_path / "public"),
        output=tmp_path / "preds",
        split="demo_dev",
        configs=(str(config),),
    )
    assert command[command.index("--subset") + 1] == str(tmp_path / "public")
    assert command.count("-c") == 2
    assert "swebench.inference.workspace_agent" in command
    assert data["environment"]["forward_env"] == []
