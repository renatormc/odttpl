import re
from typing import NamedTuple


class Marker(NamedTuple):
    kind: str
    start: int
    end: int
    ref_or_type: str
    ref_name: str | None


SEQ_RE = re.compile(r"@seq\((\w+),\s*(\w+)\)")
CROSS_RE = re.compile(r"@cross\((\w+)\)")
SHORT_CROSS_RE = re.compile(r"\$\{(\w+)\}")


def find_markers(text: str) -> list[Marker]:
    markers: list[Marker] = []
    for m in SEQ_RE.finditer(text):
        markers.append(Marker("seq", m.start(), m.end(), m.group(1), m.group(2)))
    for m in CROSS_RE.finditer(text):
        markers.append(Marker("cross", m.start(), m.end(), m.group(1), None))
    for m in SHORT_CROSS_RE.finditer(text):
        markers.append(Marker("cross", m.start(), m.end(), m.group(1), None))
    markers.sort(key=lambda x: x.start)
    return markers