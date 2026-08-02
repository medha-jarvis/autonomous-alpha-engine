"""Helper for safe template interpolation — avoids .format() eating JSON braces."""

from __future__ import annotations

import re
from typing import Any


def fill_template(template: str, context: dict[str, Any]) -> str:
    """Replace {var_name} placeholders with values from context.

    Uses regex replacement instead of str.format() so that literal
    ``{`` and ``}`` characters (e.g. inside JSON examples) are left
    untouched.
    """
    def _replacer(m: re.Match) -> str:
        name = m.group(1)
        if name in context:
            val = context[name]
            if isinstance(val, (dict, list)):
                import json
                return json.dumps(val)
            return str(val)
        raise KeyError(f"Missing context variable: '{name}'")

    return re.sub(r"\{(\w+)\}", _replacer, template)