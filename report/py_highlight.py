# report/py_highlight.py
import html, re
KW = set("""False await else import pass None break except in raise True class finally is return
and continue for lambda try as def from nonlocal while assert del global not with async elif if or yield""".split())
STR_RE = re.compile(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"])*"|\'(?:\\.|[^\'])*\')', re.S)
NUM_RE = re.compile(r"\b(0x[0-9a-fA-F]+|\d+(?:\.\d+)?)\b")
ID_RE  = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")

def highlight_python(code: str, mark_lines=None) -> str:
    mark = set(mark_lines or [])
    lines = code.splitlines()
    out = ["<pre class='code hl'>"]
    for i, line in enumerate(lines, 1):
        safe = html.escape(line)
        # strings
        safe = STR_RE.sub(lambda m: f"<span class='s'>{html.escape(m.group(0))}</span>", safe)
        # comments (only one # per line simple rule)
        if '#' in safe:
            pos = safe.find('#')
            safe = safe[:pos] + f"<span class='c'>{safe[pos:]}</span>"
        # numbers
        safe = NUM_RE.sub(lambda m: f"<span class='n'>{m.group(0)}</span>", safe)
        # keywords
        safe = ID_RE.sub(lambda m: f"<span class='k'>{m.group(1)}</span>" if m.group(1) in KW else m.group(1), safe)
        cls = "mark" if i in mark else ""
        out.append(f"<div class='ln {cls}'><span class='no'>{i:>4}</span> {safe}</div>")
    out.append("</pre>")
    return "\n".join(out)
