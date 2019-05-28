from __future__ import annotations

import unittest

from yarl import URL

from ..src import Request, Response


class TestResponse(unittest.TestCase):

    def test_response(self):
        url = URL('http://www.baidu.com/')
        status = 200
        reason = 'OK'
        headers = {}
        json_body = b'[1]'
        etree_body = b'<p>p</p>'
        request = Request(url)

        json_response = Response(
            url=url,
            status=status,
            reason=reason,
            headers=headers,
            body=json_body,
            request=request,
            meta=request.meta,
        )
        etree_response = Response(
            url=url,
            status=status,
            reason=reason,
            headers=headers,
            body=etree_body,
            request=request,
            meta=request.meta,
        )

        self.assertEqual(json_response.text(), json_body.decode())
        self.assertEqual(json_response.json(), [1])
        p = etree_response.etree().xpath('//body/p/text()')[0]
        self.assertEqual(p, 'p')
        p = etree_response.etree(html=False).xpath('/p/text()')[0]
        self.assertEqual(p, 'p')
        self.assertEqual(str(json_response), f'<Response {status} {url}>')
        self.assertEqual(hash(json_response), id(json_response))
