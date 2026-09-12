"""Incident recovery replay, separate from per-instance SWE-bench resolution."""

from pathlib import Path
from typing import Optional

import typer

scenario_app = typer.Typer(
    help="Run and report TSMC incident replays.", no_args_is_help=True
)


@scenario_app.command("run")
def run_command(
    scenario: str = typer.Argument(..., help="DC01, DC02, DC03 or DC04"),
    trial_id: str = typer.Option(
        ..., "--trial-id", help="Fresh trial artifact directory name"
    ),
    predictions: Optional[Path] = typer.Option(
        None, "-p", "--predictions", help="Standard predictions JSON/JSONL"
    ),
    gold: bool = typer.Option(
        False, "--gold", help="Validate with bundled reference patches"
    ),
    source: Path = typer.Option(Path("benchmarks/tsmc"), "--source"),
    task_repo: Path = typer.Option(Path(".generated/tsmc/task-repo"), "--task-repo"),
    availability: Optional[Path] = typer.Option(
        None,
        "--availability",
        help="Host-owned JSON service-to-replay-seconds map; default all at 0",
    ),
    horizon: float = typer.Option(
        240, "--horizon", help="Synthetic observation window in seconds"
    ),
    workers: int = typer.Option(
        2, "-j", "--workers", help="Independent Docker grade slots"
    ),
    output: Path = typer.Option(Path("logs/scenarios"), "-o", "--output"),
):
    """Grade candidate patches, then replay their incident recovery gates.

    Availability times are synthetic inputs, not measured agent repair times.
    """
    from swebench.benchmarks.tsmc.scenario.runner import run
    from swebench.task.publish import CheckFailed

    try:
        directory, report = run(
            scenario,
            trial_id,
            source=source,
            task_repo=task_repo,
            predictions=predictions,
            gold=gold,
            availability=availability,
            horizon=horizon,
            workers=workers,
            output=output,
        )
    except (ValueError, OSError, CheckFailed) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(
        f"{report['scenario_id']}: {report['restored_rate']:.0%} restored; {directory / 'report.json'}"
    )


@scenario_app.command("report")
def report_command(
    trial: Path = typer.Argument(..., help="Trial directory containing events.jsonl"),
):
    """Reconstruct the report from receipts without executing candidate code."""
    from swebench.benchmarks.tsmc.prepare import write_json
    from swebench.benchmarks.tsmc.scenario.events import read_events
    from swebench.benchmarks.tsmc.scenario.reporting import summarize

    try:
        report = summarize(read_events(trial / "events.jsonl"))
        write_json(trial / "report.json", report)
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(
        f"{report['scenario_id']}: {report['restored_rate']:.0%} restored; {trial / 'report.json'}"
    )
