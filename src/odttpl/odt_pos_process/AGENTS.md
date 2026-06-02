# `odt_pos_process` module

Processes ODT `content.xml` and replaces text markers with proper ODF XML for number sequences and cross-references.

## Markers

Plain-text placeholders typed in LibreOffice Writer (with automatic field codes disabled):

- **Number sequence:** `@seq(SequenceType, ReferenceName)`
  - Example: `@seq(Foto, ref1)` → inserts `text:sequence` with `text:ref-name="ref1"`, `text:name="Foto"` and `text:formula="ooow:Foto+1"` (incrementing per type)
  - Example: `@seq(Figura, ref2)` → same pattern for type `Figura`

- **Cross-reference (number only):** `@cross(ReferenceName)`
  - Example: `@cross(ref1)` → inserts `text:sequence-ref` with `text:ref-name="ref1"` and `text:reference-format="value"`, showing the sequence number
  - Shorthand: `${ref1}` is equivalent to `@cross(ref1)`

## ODF XML structure

### Number sequence (`text:sequence`)

```xml
<text:sequence text:ref-name="ref1" text:name="Foto" text:formula="ooow:Foto+1" style:num-format="1">1</text:sequence>
```

- `text:name` is the sequence type (e.g., `Foto`).
- `text:formula` uses the OOo-Wiki formula syntax: `ooow:<SequenceType>+1`.
- `style:num-format` controls numbering style (`1`, `01`, `A`, `a`, `I`, `i`). Default is `1`.
- The element text content is the rendered number.

### Cross-reference (`text:sequence-ref`)

```xml
<text:sequence-ref text:ref-name="ref1" text:reference-format="value">1</text:sequence-ref>
```

- `text:ref-name` must match the `text:ref-name` of the target `text:sequence`.
- The element text content is the fallback display number.

## File structure

```
__init__.py         ← process_odt() orchestration
archive.py          ← zip/unzip helpers (unpack, repack)
markers.py          ← Marker NamedTuple, regex patterns, find_markers()
parser.py           ← SequenceTracker, normalization, _replace_parts, _process_paragraph
xml_builder.py      ← make_sequence(), make_cross_reference()
```

## File details

**`__init__.py`** — Exports `process_odt(input_path, output_path)` which:
1. Unzips the ODT via `archive.unpack()`
2. Parses `content.xml` with lxml
3. Calls `parser.process_content()` to replace markers
4. Writes back `content.xml`
5. Re-zips via `archive.repack()`

**`archive.py`** — Two functions:
- `unpack(odt_path)` — Extracts ODT to a temp dir, returns `(temp_dir, _ElementTree)`
- `repack(temp_dir, output_path)` — Zips temp dir back into an ODT, ensuring `mimetype` is first and uncompressed

**`markers.py`** — Defines a `Marker` NamedTuple with fields `kind`, `start`, `end`, `ref_or_type`, `ref_name`. Three regex patterns (`SEQ_RE`, `CROSS_RE`, `SHORT_CROSS_RE`). `find_markers(text)` scans for all three and returns a sorted list.

**`parser.py`** — Core logic. Entry point is `process_content(tree)`.

- `SequenceTracker` — Maintains per-type counters (`_counters: dict[str, int]`) and a ref-name → (type, number) mapping (`_refs: dict[str, tuple[str, int]]`).
  - `next_number(seq_type, ref_name)` — Increments counter for type, registers ref_name, returns number
  - `get_ref(ref_name)` — Returns `(type, number)` or `None`

- `_replace_parts(text_content, tracker)` — Finds markers in text and returns `list[str | _Element]` of alternating text fragments and XML elements. Callers use `.text`/`.tail` directly rather than wrapping text in spans.

- `_iter_text_locations(element)` — Generator that yields `(element, attr_name)` tuples in strict document order:
  1. `element.text` of the current element
  2. Recursively, `.text` and child `.tail` of each child
  3. `.tail` of the current child element

- `_normalize_paragraph(p_element)` — Builds full paragraph text from all text locations, finds split markers, and merges them into a single location.

- `_apply_parts_text(elem, parts)` — Inserts replacement parts into `elem.text` using `.text`/`.tail` model (no span wrappers).
- `_apply_parts_tail(elem, parts)` — Inserts replacement parts after `elem` in parent, using `.text`/`.tail` model.
- `_process_paragraph(p_element, tracker)` — Collects all text locations, calls `_replace_parts()` on each, and applies changes in reverse order to preserve positions.
- `_collapse_empty_spans(p_element)` — Repeatedly removes empty `<text:span>` elements (no text, no children) and merges their tail text into the previous sibling or parent.

- `_ensure_sequence_decl(office_text, seq_type)` — Adds a `<text:sequence-decl>` for a new sequence type if not already present.

- `process_content(tree)` — Main entry point. Finds `office:body/office:text`, iterates all `<text:p>` elements, normalizes and processes each, then ensures sequence declarations for new types.

**`xml_builder.py`** — Factory functions:
- `make_sequence(seq_type, ref_name, number)` — Creates `<text:sequence>` with attributes: `text:ref-name`, `text:name`, `text:formula`, `style:num-format`
- `make_cross_reference(ref_name, number)` — Creates `<text:sequence-ref>` with `text:ref-name` and `text:reference-format="value"`

## Normalization of split markers

When a user styles part of a marker (e.g., `@seq(Foto, ref2)` with "Foto" having a different style), LibreOffice's XML represents this as separate `<text:span>` elements:

```xml
<text:p>...
  <text:span tail="@seq(" />
  <text:span style="T2">Foto</text:span>
  <text:span tail=", ref2), é " />
...</text:p>
```

The normalizer assembles the full paragraph text in document order, detects that `@seq(Foto, ref2)` spans three locations, merges the complete marker text into the first location, and clears the intermediate ones:

```xml
<text:p>...
  <text:span tail="@seq(Foto, ref2)" />
  <text:span tail=", é " />
...</text:p>
```

Then `_process_paragraph` replaces the now-contiguous marker. Empty spans left behind are cleaned up by `_collapse_empty_spans()`.
