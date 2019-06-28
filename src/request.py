'''The Request class used in Clinet.'''

from __future__ import annotations

__all__ = ['Request']

from dataclasses import dataclass
from pathlib import Path
from typing import Any, NewType, Optional, SupportsFloat, Union

from yarl import URL


# A library-defined type used in type annotations.
Jsonable = NewType('Jsonable', Any)


@dataclass
class Request:
    '''The Request class used in Clinet.

    Users should not directly instantiate Request.
    Use Client.request() instead.
    '''

    url: Union[str, URL]
    method: str = 'GET'
    headers: Optional[dict] = None
    cookies: Optional[dict] = None

    params: Optional[dict] = None
    body: Optional[bytes] = None
    json: Optional[Jsonable] = None
    text: Optional[str] = None
    form: Optional[dict] = None
    file: Optional[Union[str, Path]] = None

    timeout: Optional[SupportsFloat] = None
    retry: Optional[int] = None
    meta: Optional[dict] = None

    def __post_init__(self):
        self.url = URL(self.url)
        self.method = self.method.upper()
        self.file = Path(self.file) if self.file is not None else self.file

    def __repr__(self):
        return f'<Request {self.method} {self.url}>'

    def __hash__(self):
        return id(self)
