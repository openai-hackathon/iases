import json
import os
from pathlib import Path


def render(template, models):
    for name in ("FAST_MODEL", "ANALYSIS_MODEL"):
        value = models.get(name, "").strip()
        if not value:
            raise ValueError(f"Set {name} before starting live routing")
        template = template.replace("${" + name + "}", json.dumps(value))
    template = template.replace(
        "    model: incident-analysis\n", "    default_model: incident-analysis\n"
    )
    template = template.replace(
        "routing:\n",
        "routing:\n  modelCards:\n    - name: incident-fast\n    - name: incident-analysis\n",
    )
    return template.replace("  stores:\n    response_cache: {enabled: false}\n", "")


if __name__ == "__main__":
    template = Path("/app/tools/semantic-router/config.yaml").read_text()
    Path("/data/router.yaml").write_text(render(template, os.environ))
