"""
Detect Serverless-style and other macro placeholders that MiniStack does not expand.

After JSON/YAML parse, only standard CloudFormation intrinsic functions are resolved.
Placeholders such as ``${file(...)}`` or ``${self:...}`` remain literal strings unless
the template is pre-compiled (for example ``serverless package``, ``sam package``, or
``cdk synth`` output).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("cloudformation")

_PATTERN_LABELS: tuple[tuple[str, str], ...] = (
    ("${file(", "${file(...)} (Serverless Framework — compile template first)"),
    ("${self:", "${self:...} (Serverless Framework — compile template first)"),
    ("MasonFn::", "MasonFn:: (custom macro / pseudo-type — not evaluated)"),
)


def _iter_template_strings(obj: Any) -> list[str]:
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(_iter_template_strings(k))
            out.extend(_iter_template_strings(v))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_iter_template_strings(item))
    return out


def scan_template_for_custom_placeholders(template: dict) -> list[str]:
    """Return sorted unique human-readable hits for known non-CFN substrings."""
    hits: set[str] = set()
    for chunk in _iter_template_strings(template):
        for needle, label in _PATTERN_LABELS:
            if needle in chunk:
                hits.add(label)
    return sorted(hits)


def warn_or_reject_custom_syntax(template: dict) -> str | None:
    """
    Log a warning when known macro syntax is present.

    If ``MINISTACK_CFN_FAIL_ON_CUSTOM_SYNTAX`` is set to a truthy value (``1``,
    ``true``, ``yes``, ``on``), return a validation error message instead of None.
    """
    messages = scan_template_for_custom_placeholders(template)
    if not messages:
        return None
    detail = "; ".join(messages)
    logger.warning(
        "Template contains syntax MiniStack does not evaluate: %s", detail
    )
    flag = os.environ.get("MINISTACK_CFN_FAIL_ON_CUSTOM_SYNTAX", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return (
            "Template contains syntax MiniStack does not evaluate ("
            f"{detail}). Pre-compile with Serverless/SAM/CDK, or disable "
            "MINISTACK_CFN_FAIL_ON_CUSTOM_SYNTAX."
        )
    return None
