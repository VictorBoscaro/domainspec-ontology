"""Write spec.yaml from CodeAnchor list."""

from pathlib import Path

import yaml

from semantic_index.models import CodeAnchor


def write_spec_yaml(anchors: list[CodeAnchor], output_path: Path) -> None:
    """Write enriched CodeAnchors to a spec.yaml file.

    Args:
        anchors: List of CodeAnchor objects (with domain/term/term_registered populated)
        output_path: Where to write the YAML file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "concepts": [a.model_dump() for a in anchors]
    }

    yaml_text = yaml.dump(
        output,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )

    output_path.write_text(yaml_text, encoding="utf-8")
