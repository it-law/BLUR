from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from lxml import etree


WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CP_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"
DCTERMS_NAMESPACE = "http://purl.org/dc/terms/"

NSMAP = {
    "w": WORD_NAMESPACE,
    "cp": CP_NAMESPACE,
    "dc": DC_NAMESPACE,
    "dcterms": DCTERMS_NAMESPACE,
}


def clean_docx_parts(parts: dict[str, bytes]) -> dict[str, bytes]:
    cleaned = dict(parts)
    for name, data in parts.items():
        if not name.endswith(".xml"):
            continue
        try:
            tree = etree.fromstring(data)
        except etree.XMLSyntaxError:
            continue
        if name.startswith("word/"):
            _accept_revisions(tree)
            _remove_comments(tree)
        if name == "docProps/core.xml":
            _wipe_core_properties(tree)
        if name == "docProps/custom.xml":
            _wipe_custom_properties(tree)
        cleaned[name] = etree.tostring(tree, xml_declaration=True, encoding="UTF-8")

    cleaned = _remove_comments_part(cleaned)
    return cleaned


def _accept_revisions(tree: etree._Element) -> None:
    for tag in ("w:del", "w:moveFrom"):
        for node in tree.xpath(f".//{tag}", namespaces=NSMAP):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
    for tag in ("w:ins", "w:moveTo"):
        for node in tree.xpath(f".//{tag}", namespaces=NSMAP):
            _unwrap(node)


def _unwrap(node: etree._Element) -> None:
    parent = node.getparent()
    if parent is None:
        return
    index = parent.index(node)
    for child in list(node):
        parent.insert(index, child)
        index += 1
    parent.remove(node)


def _remove_comments(tree: etree._Element) -> None:
    for tag in ("w:commentRangeStart", "w:commentRangeEnd", "w:commentReference"):
        for node in tree.xpath(f".//{tag}", namespaces=NSMAP):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)


def _remove_comments_part(parts: dict[str, bytes]) -> dict[str, bytes]:
    cleaned = dict(parts)
    if "word/comments.xml" in cleaned:
        cleaned.pop("word/comments.xml", None)
    return cleaned


def _wipe_core_properties(tree: etree._Element) -> None:
    for element in tree.xpath("//*", namespaces=NSMAP):
        if element.text:
            element.text = ""
    for tag in ("dc:creator", "cp:lastModifiedBy", "dcterms:created", "dcterms:modified"):
        for node in tree.xpath(f".//{tag}", namespaces=NSMAP):
            node.text = ""


def _wipe_custom_properties(tree: etree._Element) -> None:
    for element in tree.xpath("//*", namespaces=NSMAP):
        if element.text:
            element.text = ""
