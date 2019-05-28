from __future__ import annotations

import logging
import os
import unittest
from concurrent.futures import wait

from ..src import Client


class TestClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logger = logging.getLogger('Client')
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s')
        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG)
        sh.setFormatter(formatter)
        logger.addHandler(sh)

    def test_concurrency(self):
        setting = {
            'concurrency': 2,
            'concurrency_per_host': 1,
        }
        with Client(setting) as client:
            print('@@@@ test concurrency')
            wait([
                client.request('http://www.httpbin.org/get'),
                client.request('https://www.microsoftstore.com/'),
                client.request('http://www.httpbin.org/get'),
                client.request('https://www.microsoftstore.com/'),
            ])
            print('@@@@ test concurrency')

    def test_exception(self):
        with Client() as client:
            resp = client.request('').result()
            self.assertEqual(resp.status, -1)

    def test_request(self):
        setting = {
            'headers': {'hk': 'hv'},
            'cookies': {'ck': 'cv'},
        }
        url = 'http://www.httpbin.org'
        file = './test'
        with open(file, 'wb') as f:
            f.write(b'a')

        with Client(setting) as client:
            get_resp = client.request(f'{url}/get').result()
            post_resp = client.request(f'{url}/post', method='POST').result()
            params_resp = client.request(f'{url}/get?pk=pv').result()
            headers_resp = client.request(f'{url}/headers', headers={'a': 'b'}).result()
            cookies_resp = client.request(f'{url}/cookies', cookies={'a': 'b'}).result()
            body_resp = client.request(f'{url}/post', method='POST', body=b'a').result()
            json_resp = client.request(f'{url}/post', method='POST', json={'a': 'b'}).result()
            text_resp = client.request(f'{url}/post', method='POST', text='a').result()
            form_resp = client.request(f'{url}/post', method='POST', form={'a': 'b'}).result()
            file_resp = client.request(f'{url}/post', method='POST', file=file).result()

            self.assertEqual(get_resp.status, 200)
            self.assertEqual(post_resp.status, 200)
            self.assertEqual(params_resp.json()['args'], {'pk': 'pv'})
            self.assertEqual(headers_resp.json()['headers']['Accept'], '*/*')
            self.assertEqual(headers_resp.json()['headers']['Hk'], 'hv')
            self.assertEqual(cookies_resp.json()['cookies']['ck'], 'cv')
            self.assertEqual(body_resp.json()['headers']['Content-Type'], 'application/octet-stream')
            self.assertEqual(body_resp.json()['data'], 'a')
            self.assertEqual(json_resp.json()['headers']['Content-Type'], 'application/json')
            self.assertEqual(json_resp.json()['json'], {'a': 'b'})
            self.assertEqual(text_resp.json()['headers']['Content-Type'], 'text/plain; charset=utf-8')
            self.assertEqual(text_resp.json()['data'], 'a')
            self.assertEqual(form_resp.json()['headers']['Content-Type'], 'application/x-www-form-urlencoded')
            self.assertEqual(form_resp.json()['form'], {'a': 'b'})
            self.assertEqual(file_resp.json()['headers']['Content-Type'], 'application/octet-stream')
            self.assertEqual(file_resp.json()['data'], 'a')

            os.remove(file)
