from __future__ import annotations

__all__ = ['Client']

import asyncio
import logging
from concurrent.futures import Future
from contextlib import asynccontextmanager
from copy import deepcopy
from functools import partial
from queue import Empty, Queue
from threading import Thread
from time import sleep
from typing import Optional
from weakref import WeakValueDictionary

import aiofiles
from aiohttp import ClientSession, ClientTimeout
from multidict import CIMultiDict
from yarl import URL

from .request import Request
from .response import Response


class Throttle:

    def __init__(self, concur, concur_per_host):
        self._concur_sema = asyncio.Semaphore(concur)
        self._host_sema_factory = partial(asyncio.Semaphore, concur_per_host)
        self._hosts = WeakValueDictionary()

    @asynccontextmanager
    async def request(self, host):
        sema = self._host_sema_factory()
        host_sema = self._hosts.setdefault(host, sema)
        async with self._concur_sema, host_sema:
            yield


class Client:

    setting: dict = {
        'timeout': 20,
        'retry': 1,
        'concurrency': 4,
        'concurrency_per_host': 2,

        'headers': CIMultiDict({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/74.0.3729.169 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,'
                               'ja;q=0.6,zh-TW;q=0.5',
        }),
        'cookies': {},
    }

    def __init__(self, setting: Optional[dict] = None) -> None:
        self._name = self.__class__.__name__
        self._logger = logging.getLogger(self._name)
        self._queue = Queue()
        self._running = True
        self.setting = deepcopy(self.setting)
        if setting:
            headers = setting.pop('headers', {})
            self.setting['headers'].update(headers)
            cookies = setting.pop('cookies', {})
            self.setting['cookies'].update(cookies)
            self.setting.update(setting)
        self._thread = Thread(target=self._main)
        self._thread.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def request(self, url, **kwargs) -> Future:
        req = Request(url, **kwargs)
        fut = Future()
        self._queue.put((fut, req))
        return fut

    def close(self) -> None:
        self._running = False
        while self._thread.is_alive():
            sleep(0.1)

    def _main(self):
        asyncio.run(self._async_main())

    async def _async_main(self):
        self._logger.info('start')
        timeout = ClientTimeout(total=self.setting['timeout'])
        throttle = Throttle(self.setting['concurrency'],
                            self.setting['concurrency_per_host'])
        async with ClientSession(timeout=timeout,
                                 headers=self.setting['headers'],
                                 cookies=self.setting['cookies']) as session:
            while self._running:
                try:
                    fut, req = self._queue.get(timeout=0.05)
                except Empty:
                    continue
                else:
                    if fut.set_running_or_notify_cancel():
                        task = asyncio.create_task(self._process(req, session, throttle))
                        task.add_done_callback(lambda task: fut.set_result(task.result()))
                    self._queue.task_done()
                finally:
                    await asyncio.sleep(0.1)
        await asyncio.sleep(1)
        self._logger.info('close')

    async def _process(self, req, session, throttle):
        self._logger.debug(f'{req} pending')
        async with throttle.request(req.url.host):
            self._logger.debug(f'{req} processing')
            timeout, retry, req_params = self._make_aio_req_params(req)
            try:
                for _ in range(retry+1):
                    try:
                        async with session.request(**req_params) as aio_resp:
                            resp = await self._make_response(req, aio_resp)
                            break
                    except asyncio.TimeoutError:
                        continue
                else:
                    raise asyncio.TimeoutError(f'{timeout}s')
            except Exception as exc:
                if not isinstance(exc, (asyncio.TimeoutError, asyncio.CancelledError)):
                    self._logger.exception('unexpected exception')
                resp = await self._make_response(req, exc)
            finally:
                self._logger.debug(f'{req} => {resp}')
                return resp

    async def _file_gen(self, path):
        async with aiofiles.open(path, 'rb') as file:
            chunk = await file.read(64*1024)
            while chunk:
                yield chunk
                chunk = await file.read(64*1024)

    def _make_aio_req_params(self, req):
        url = req.url
        method = req.method
        params = req.params
        timeout = req.timeout or self.setting['timeout']
        retry = req.retry or self.setting['retry']

        headers = deepcopy(self.setting['headers'])
        headers.update(req.headers or {})
        cookies = deepcopy(self.setting['cookies'])
        cookies.update(req.cookies or {})

        body = req.body
        json = req.json
        text = req.text
        form = req.form
        file = req.file and self._file_gen(req.file)

        possible_body = [body, json, text, form, file]
        num = len([v for v in possible_body if v is not None])
        if method == 'GET':
            assert num == 0, 'GET does not have a request body.'
        elif method == 'POST':
            assert num <= 1, 'POST require exactly one request body.'

        return (timeout, retry, {
            'url': url,
            'method': method,
            'timeout': timeout,
            'params': params,
            'headers': headers,
            'cookies': cookies,
            'json': json,
            'data': form or body or text or file,
        })

    async def _make_response(self, req, result):
        if isinstance(result, Exception):
            resp = Response(
                url=URL(''),
                status=-1,
                reason=repr(result),
                headers={},
                body=b'',
                request=req,
                meta=req.meta,
            )
        else:
            resp = Response(
                url=result.url,
                status=result.status,
                reason=result.reason,
                headers=result.headers,
                body=await result.read(),
                request=req,
                meta=req.meta,
            )
        return resp
