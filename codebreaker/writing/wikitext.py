"""Minimal wikitext cleaning for the recorded sign tables in data/sources/scripts (raw Wikipedia pages)."""
import re

DROP = {"sfn", "efn", "r", "cn", "citation needed", "refn", "ref", "anchor", "nbsp", "-", "clarify", "dubious", "sfnp", "harvcoltxt", "lit"}


def _template(body: str) -> str:
    parts = body.split("|")
    name = parts[0].strip().lower()
    if name in DROP:
        return ""
    for p in parts[1:]:
        if p.strip().startswith("text="):
            return p.split("=", 1)[1]
    pos = [p for p in parts[1:] if "=" not in p or p.strip().startswith("[[")]
    return pos[-1] if pos else ""


def clean(cell: str) -> str:
    """Templates reduced to their text, links to their label, markup and references removed."""
    t = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", "", cell, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"\[\[(?:File|Image):[^\]]*\]\]", "", t)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)
    for _ in range(8):
        t2 = re.sub(r"\{\{([^{}]*)\}\}", lambda m: _template(m.group(1)), t)
        if t2 == t:
            break
        t = t2
    t = re.sub(r"\[\[(?:File|Image):[^\]]*\]\]", "", t)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"^\s*(?:style|lang|rowspan|colspan|align|valign)=[^|]*\|", "", t)
    t = t.replace("'''", "").replace("''", "").replace("&nbsp;", " ").replace("⟨", "").replace("⟩", "")
    return re.sub(r"\s+", " ", t).strip()


def rows(text: str) -> list[list[str]]:
    """Every table row as a list of raw cells (cells split on '||' or on new lines starting with '|' or '!')."""
    out = []
    for block in re.findall(r"\{\|(.*?)\n\|\}", text, flags=re.S):
        for row in re.split(r"\n\|-[^\n]*", block):
            cells = []
            for line in row.split("\n"):
                line = line.strip()
                if not line or line[0] not in "|!" or line.startswith("|+"):
                    continue
                cells += [c for c in re.split(r"\|\||!!", line[1:])]
            if cells:
                out.append(cells)
    return out
