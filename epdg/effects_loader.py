from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
try:
    import yaml  # type: ignore
except Exception:
    yaml = None


@dataclass
class EffectItem:
    fqname: str
    match_type: str
    pattern: str
    reads: List[str]
    writes: List[str]
    flags: Dict[str, bool]


class EffectDB:
    """Lightweight effect summary database backed by YAML or JSON.

    Each entry in the config describes how a particular API or family of APIs
    read / write abstract memory regions (STACK / HEAP / GLOBAL / FILE / NET / DB
    / ENV, etc.) together with boolean flags such as ``io_file`` or ``rng``.

    In addition to explicit matches, the config may contain a single
    ``match.type == 'default'`` (or an entry whose ``fqname`` is
    ``"__UNKNOWN__"``).  This entry is treated as the summary for unknown
    calls and is used by the Python frontend to apply a *conservative but
    down-weighted* effect for unmodelled functions.
    """

    def __init__(self, items: List[EffectItem]):
        self.items = items
        self._regex: List[tuple[re.Pattern[str], EffectItem]] = []
        self._fq: Dict[str, EffectItem] = {}
        self._default: Optional[EffectItem] = None

        for it in items:
            mt = it.match_type
            if mt == "regex":
                self._regex.append((re.compile(it.pattern), it))
            elif mt == "fqname":
                self._fq[it.pattern] = it
            elif mt == "default":
                # There should be at most one, but if there are multiple the
                # last one wins.
                self._default = it
            elif mt == "module":
                # Module-level entries are kept in ``self.items`` and handled
                # in :meth:`match`.
                continue

        # Fallback: treat the sentinel ``fqname == "__UNKNOWN__"`` as the
        # default summary when an explicit ``match.type == 'default'`` entry
        # is not present.
        if self._default is None:
            for it in items:
                if it.fqname == "__UNKNOWN__":
                    self._default = it
                    break

    @staticmethod
    def from_file(path: str) -> "EffectDB":
        if path.endswith(".json"):
            import json
            data = json.loads(open(path, "r", encoding="utf-8").read())
        else:
            if yaml is None:
                raise RuntimeError(
                    "PyYAML not installed. Install with `pip install pyyaml`, "
                    "or provide a .json effects file."
                )
            data = yaml.safe_load(open(path, "r", encoding="utf-8"))
        items: List[EffectItem] = []
        for ent in data:
            eff = ent.get("effects", {}) or {}
            items.append(
                EffectItem(
                    fqname=ent.get("fqname", ""),
                    match_type=ent.get("match", {}).get("type", "fqname"),
                    pattern=ent.get("match", {}).get("pattern", ent.get("fqname", "")),
                    reads=eff.get("reads", []) or [],
                    writes=eff.get("writes", []) or [],
                    flags=eff.get("flags", {}) or {},
                )
            )
        return EffectDB(items)

    def match(self, call_name: str) -> Optional[EffectItem]:
        if call_name in self._fq:
            return self._fq[call_name]
        for rgx, it in self._regex:
            if rgx.match(call_name):
                return it
        for it in self.items:
            if it.match_type == "module" and call_name.startswith(it.pattern + "."):
                return it
        return None

    def default_item(self) -> Optional[EffectItem]:
        """Return the fallback summary for unknown calls, if configured."""
        return self._default
