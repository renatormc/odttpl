from lxml import etree
from lxml.etree import _Element


TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
STYLE_NS = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"


def make_sequence(seq_type: str, ref_name: str, number: int) -> _Element:
    elem = etree.Element(f"{{{TEXT_NS}}}sequence")
    elem.set(f"{{{TEXT_NS}}}ref-name", ref_name)
    elem.set(f"{{{TEXT_NS}}}name", seq_type)
    elem.set(f"{{{TEXT_NS}}}formula", f"ooow:{seq_type}+1")
    elem.set(f"{{{STYLE_NS}}}num-format", "1")
    elem.text = str(number)
    return elem


def make_cross_reference(ref_name: str, number: int) -> _Element:
    elem = etree.Element(f"{{{TEXT_NS}}}sequence-ref")
    elem.set(f"{{{TEXT_NS}}}ref-name", ref_name)
    elem.set(f"{{{TEXT_NS}}}reference-format", "value")
    elem.text = str(number)
    return elem