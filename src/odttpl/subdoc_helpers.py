from ast import parse
from copy import deepcopy
from dataclasses import dataclass
from re import sub
from typing import Literal
from xml.dom.minidom import Document, Node, Element, parseString


@dataclass
class ContentCopy:
    content: list[Element]
    automatic_styles: list[Element]
    main_styles: list[Element]


def rename_styles(element: Element, prefix: str) -> list[str]:
    ret: list[str] = []
    for attr in element.attributes.keys():
        if attr.endswith('style-name'):
            style_name = element.getAttribute(attr)
            new_name = f"{prefix}.{style_name}"
            element.setAttribute(attr, new_name)
            ret.append(new_name)
    for child in element.childNodes:
        if child.nodeType == Node.ELEMENT_NODE:
            ret += rename_styles(child, prefix)
    return ret

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
        nodes = self.content.documentElement.getElementsByTagName('office:automatic-styles')[0].childNodes
        for node in nodes:
            if node.nodeType != Node.ELEMENT_NODE:
                continue
            style_name = node.getAttribute("style:name")
            self.automatic_existing_styles[style_name] = node

    def extract_default_estyles(self) -> None:
        nodes = self.styles.documentElement.getElementsByTagName('office:styles')[0].childNodes
        for node in nodes:
            if node.nodeType != Node.ELEMENT_NODE:
                continue
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
    office_text = sub_doc_styles.content.documentElement.getElementsByTagName('office:text')[0]
    elements = [node for node in office_text.childNodes if node.nodeType == Node.ELEMENT_NODE and node.tagName != "text:sequence-decls"]
    for el in elements:
        sub_doc_styles.rename_styles(el, prefix, main_doc_styles)
    sub_doc_styles.content_for_addition = elements




@dataclass
class TableCopy:
    content: Element
    styles: list[Element]
    

def find_and_copy_table(content: Document, table_name: str) -> TableCopy | None:
    office_text = content.documentElement.getElementsByTagName('office:text')[0]
    tables = office_text.getElementsByTagName('table:table')
    for table in tables:
        if table.getAttribute("table:name") == table_name:
            styles: list[Element] = []
            nodes = content.documentElement.getElementsByTagName('office:automatic-styles')[0].childNodes
            for node in nodes:
                if node.nodeType == Node.ELEMENT_NODE and node.tagName == "style:style":
                    style_name = node.getAttribute("style:name")
                    if style_name == table_name or style_name.startswith(f"{table_name}."):
                        print(style_name)
                        styles.append(deepcopy(node))
            return TableCopy(content=deepcopy(table), styles=styles)
    return None