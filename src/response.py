from __future__ import annotations

__all__ = ['Response']

import json
from dataclasses import dataclass
from typing import Optional

import cchardet
import html5lib
from lxml import etree
from multidict import CIMultiDictProxy
from yarl import URL

from .request import Jsonable, Request


@dataclass
class Response:

    url: URL
    status: int
    reason: str
    headers: CIMultiDictProxy
    body: bytes

    request: Request
    meta: dict

    def __repr__(self):
        return f'<Response {self.status} {self.url}>'

    def __hash__(self):
        return id(self)

    def text(self, encoding: Optional[str] = None) -> str:
        encoding = encoding or cchardet.detect(self.body)['encoding'] or 'utf-8'
        return self.body.decode(encoding)

    def json(self) -> Jsonable:
        return json.loads(self.body)

    def etree(self, html: bool = True) -> etree._ElementTree:
        if html:
            return html5lib.parse(self.body, treebuilder='lxml', namespaceHTMLElements=False)
        else:
            return etree.fromstring(self.body).getroottree()
