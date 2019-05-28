from __future__ import annotations

import unittest
from pathlib import Path

from yarl import URL

from ..src import Request


class TestRequest(unittest.TestCase):

    def test_request(self):
        url = 'http://www.baidu.com/'
        method = 'post'
        file = './test'
        request = Request(url, method=method, file=file)
        self.assertEqual(request.url, URL(url))
        self.assertEqual(request.method, method.upper())
        self.assertEqual(request.file, Path(file))
        self.assertEqual(str(request), f'<Request {method.upper()} {url}>')
        self.assertEqual(hash(request), id(request))
