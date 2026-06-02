from copy import deepcopy
from dataclasses import dataclass
from typing import Literal, cast
from xml.dom.minidom import Document, Node, Element

@dataclass
class FoundStyle:
    name: str
    element: Element
    where: Literal["default", "automatic"]


class StylesManager:
    def __init__(self, content: Document, styles: Document) -> None:
        self.content = content
        self.styles = styles
        self.automatic_existing_styles: dict[str, Element] = {}
        self.default_existing_styles: dict[str, Element] = {}
        self.default_styles_for_addition: list[Element] = []
        self.automatic_styles_for_addition: list[Element] = []
        self.content_for_addition: list[Element] = []
        self.extract_automatic_estyles()
        self.extract_default_estyles()

    def extract_automatic_estyles(self) -> None:
        doc_elem = self.content.documentElement
        assert doc_elem is not None
        auto_styles = doc_elem.getElementsByTagName('office:automatic-styles')[0]
        assert auto_styles is not None
        nodes = auto_styles.childNodes
        for node in nodes:
            if node.nodeType != Node.ELEMENT_NODE:
                continue
            node = cast(Element, node)
            style_name = node.getAttribute("style:name")
            self.automatic_existing_styles[style_name] = node

    def extract_default_estyles(self) -> None:
        doc_elem = self.styles.documentElement
        assert doc_elem is not None
        styles_elem = doc_elem.getElementsByTagName('office:styles')[0]
        assert styles_elem is not None
        nodes = styles_elem.childNodes
        for node in nodes:
            if node.nodeType != Node.ELEMENT_NODE:
                continue
            node = cast(Element, node)
            style_name = node.getAttribute("style:name")
            self.default_existing_styles[style_name] = node


    def find_style(self, style_name: str) -> FoundStyle | None:
        if style_name in self.automatic_existing_styles:
            return FoundStyle(name=style_name, element=self.automatic_existing_styles[style_name], where="automatic")
        if style_name in self.default_existing_styles:
            return FoundStyle(name=style_name, element=self.default_existing_styles[style_name], where="default")
        return None
    
    def rename_styles(self, element: Element, prefix: str, other: 'StylesManager') -> None:
        for attr in element.attributes.keys():
            if attr.endswith('style-name'):
                style_name = element.getAttribute(attr)
                found = self.find_style(style_name)
                if found is None:
                    raise ValueError(f"Style {style_name} not found in either automatic or default styles")
                if found.where == "automatic":
                    new_name = f"{prefix}.{style_name}"
                    element.setAttribute(attr, new_name)
                    new_element = deepcopy(found.element)
                    new_element.setAttribute("style:name", new_name)
                    other.automatic_styles_for_addition.append(new_element)
                elif found.where == "default" and not other.find_style(style_name):
                   other.default_styles_for_addition.append(deepcopy(found.element))

        for child in element.childNodes:
            if child.nodeType == Node.ELEMENT_NODE:
                self.rename_styles(child, prefix, other)


def get_copy_content(main_doc_styles: StylesManager, sub_doc_styles: StylesManager, prefix: str) -> None:
    doc_elem = sub_doc_styles.content.documentElement
    assert doc_elem is not None
    office_text = doc_elem.getElementsByTagName('office:text')[0]
    assert office_text is not None
    elements: list[Element] = []
    for node in office_text.childNodes:
        if node.nodeType == Node.ELEMENT_NODE:
            node = cast(Element, node)
            if node.tagName != "text:sequence-decls":
                elements.append(node)
    for el in elements:
        sub_doc_styles.rename_styles(el, prefix, main_doc_styles)
    sub_doc_styles.content_for_addition = elements