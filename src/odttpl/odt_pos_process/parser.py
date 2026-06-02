from __future__ import annotations

from collections.abc import Generator

from lxml import etree
from lxml.etree import _Element, _ElementTree

from odttpl.odt_pos_process.markers import Marker, find_markers
from odttpl.odt_pos_process.xml_builder import make_cross_reference, make_sequence

TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
OFFICE_NS = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"

Part = str | _Element


class SequenceTracker:
    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._refs: dict[str, tuple[str, int]] = {}

    def next_number(self, seq_type: str, ref_name: str) -> int:
        self._counters.setdefault(seq_type, 0)
        self._counters[seq_type] += 1
        number = self._counters[seq_type]
        self._refs[ref_name] = (seq_type, number)
        return number

    def get_ref(self, ref_name: str) -> tuple[str, int] | None:
        return self._refs.get(ref_name)


def _ensure_sequence_decl(office_text: _Element, seq_type: str) -> None:
    decls = office_text.find(f"{{{TEXT_NS}}}sequence-decls")
    if decls is None:
        return
    xpath = f"{{{TEXT_NS}}}sequence-decl[@{{{TEXT_NS}}}name='{seq_type}']"
    existing = decls.find(xpath)
    if existing is not None:
        return
    decl = etree.SubElement(decls, f"{{{TEXT_NS}}}sequence-decl")
    decl.set(f"{{{TEXT_NS}}}display-outline-level", "0")
    decl.set(f"{{{TEXT_NS}}}name", seq_type)


def _replace_parts(text_content: str, tracker: SequenceTracker) -> list[Part] | None:
    if not text_content:
        return None

    markers = find_markers(text_content)
    if not markers:
        return None

    parts: list[Part] = []
    pos = 0

    for marker in markers:
        if marker.start > pos:
            parts.append(text_content[pos : marker.start])

        if marker.kind == "seq":
            number = tracker.next_number(marker.ref_or_type, marker.ref_name)  # type: ignore[arg-type]
            parts.append(make_sequence(marker.ref_or_type, marker.ref_name, number))  # type: ignore[arg-type]
        else:
            ref_info = tracker.get_ref(marker.ref_or_type)
            number = ref_info[1] if ref_info else 0
            parts.append(make_cross_reference(marker.ref_or_type, number))

        pos = marker.end

    if pos < len(text_content):
        parts.append(text_content[pos:])

    return parts


def _iter_text_locations(
    element: _Element,
) -> Generator[tuple[_Element, str], None, None]:
    if element.text:
        yield (element, "text")
    for child in element:
        yield from _iter_text_locations(child)
        if child.tail:
            yield (child, "tail")


def _normalize_paragraph(p_element: _Element) -> None:
    locations = list(_iter_text_locations(p_element))
    if not locations:
        return

    full_text = "".join(getattr(elem, attr) for elem, attr in locations)

    markers = find_markers(full_text)
    if not markers:
        return

    pos_before: list[int] = []
    p = 0
    for elem, attr in locations:
        pos_before.append(p)
        p += len(getattr(elem, attr))

    for marker in markers:
        start_idx: int | None = None
        end_idx: int | None = None
        for i in range(len(locations)):
            loc_start = pos_before[i]
            loc_len = len(getattr(locations[i][0], locations[i][1]))
            loc_end = loc_start + loc_len
            if start_idx is None and marker.start >= loc_start and marker.start < loc_end:
                start_idx = i
            if end_idx is None and marker.end > loc_start and marker.end <= loc_end:
                end_idx = i

        if start_idx is None or end_idx is None or start_idx == end_idx:
            continue

        first_elem, first_attr = locations[start_idx]
        offset = marker.start - pos_before[start_idx]
        first_text = getattr(first_elem, first_attr)
        prefix = first_text[:offset]
        merged = full_text[marker.start : marker.end]
        setattr(first_elem, first_attr, prefix + merged)

        for j in range(start_idx + 1, end_idx):
            elem, attr = locations[j]
            setattr(elem, attr, None)

        last_elem, last_attr = locations[end_idx]
        end_offset = marker.end - pos_before[end_idx]
        last_text = getattr(last_elem, last_attr)
        suffix = last_text[end_offset:]
        setattr(last_elem, last_attr, suffix or None)

    _collapse_empty_spans(p_element)


def _collapse_empty_spans(p_element: _Element) -> None:
    changed = True
    while changed:
        changed = False
        for elem in list(p_element.iter(f"{{{TEXT_NS}}}span")):
            if elem.text is not None or len(elem) > 0:
                continue
            parent = elem.getparent()
            if parent is None:
                continue
            tail = elem.tail or ""
            prev = elem.getprevious()
            if prev is not None:
                prev.tail = (prev.tail or "") + tail
            else:
                parent.text = (parent.text or "") + tail
            parent.remove(elem)
            changed = True


def _apply_parts_text(elem: _Element, parts: list[Part]) -> None:
    elem.text = None
    if not parts:
        return

    if isinstance(parts[0], str):
        elem.text = parts[0]
        parts = parts[1:]
    elif isinstance(parts[0], _Element):
        elem.insert(0, parts[0])
        parts = parts[1:]

    prev_elem: _Element | None = None
    for part in parts:
        if isinstance(part, str):
            if prev_elem is not None:
                prev_elem.tail = (prev_elem.tail or "") + part
            elif elem.text is not None:
                elem.text = elem.text + part
            else:
                elem.text = part
        else:
            elem.append(part)
            prev_elem = part


def _apply_parts_tail(elem: _Element, parts: list[Part]) -> None:
    parent = elem.getparent()
    assert parent is not None
    elem.tail = None
    if not parts:
        return

    if isinstance(parts[0], str):
        elem.tail = parts[0]
        parts = parts[1:]

    idx = list(parent).index(elem)
    prev_elem: _Element | None = None
    for part in parts:
        if isinstance(part, str):
            if prev_elem is not None:
                prev_elem.tail = (prev_elem.tail or "") + part
            else:
                elem.tail = (elem.tail or "") + part
        else:
            parent.insert(idx + 1, part)
            prev_elem = part
            idx += 1


def _process_paragraph(p_element: _Element, tracker: SequenceTracker) -> None:
    locations = list(_iter_text_locations(p_element))

    ops: list[tuple[str, _Element, list[Part]]] = []
    for elem, attr in locations:
        text = getattr(elem, attr)
        parts = _replace_parts(text, tracker)
        if parts is not None:
            ops.append((attr, elem, parts))

    if not ops:
        return

    for attr, elem, parts in reversed(ops):
        if attr == "text":
            _apply_parts_text(elem, parts)
        else:
            _apply_parts_tail(elem, parts)

    _collapse_empty_spans(p_element)


def process_content(tree: _ElementTree) -> None:
    tracker = SequenceTracker()
    root = tree.getroot()

    body = root.find(f"{{{OFFICE_NS}}}body")
    if body is None:
        return
    office_text = body.find(f"{{{OFFICE_NS}}}text")
    if office_text is None:
        return

    paragraphs = list(office_text.iter(f"{{{TEXT_NS}}}p"))

    for p in paragraphs:
        _normalize_paragraph(p)
        _process_paragraph(p, tracker)

    for seq_type in tracker._counters:
        _ensure_sequence_decl(office_text, seq_type)