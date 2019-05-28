# requestkit

`requestkit` is a simple library providing a synchronous wrapper over [AIOHTTP](https://docs.aiohttp.org/). Currently `requestkit` supports HTTP client, WebSocket client/server.

---

## HTTP Client

```python
    from requestkit import Client

    with Client() as client:
        future = client.request('http://www.httpbin.org/get')
        response = future.result()
```

### Build a Client

```python
Client(self, setting: Optional[dict] = None)
```

`setting` applies to all requests, but will be overridden by parameters set in a specific request (or merged, for `headers` and `cookies`). The default setting is:

```python
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
```

- `timeout`  
    Timeout for one request attempt in seconds.

- `retry`  
    Retry times. Notice `retry + 1` is the number of total attempts.

- `concurrency`  
    Maximum concurrent requests.

- `concurrency_per_host`  
    Maximum concurrent requests towards one host. Host is obtained by `yarl.URL.host`.

### Send a request

`request(self, url, **kwargs) -> Future`

Besides `url`, `request()` takes many other parameters listed below, and returns a [Future](https://docs.python.org/3/library/concurrent.futures.html#future-objects).

- `url: Union[str, URL]`  
    Target url.

- `method: str = 'GET'`    
    HTTP verb. Now support `GET` and `POST`.

- `headers: Optional[dict] = None`  
    HTTP headers, which will be merged with `Client` headers.

- `cookies: Optional[dict] = None`  
    HTTP cookies, which will be merged with `Client` cookies.

- `params: Optional[dict] = None`  
    HTTP query string.

- `body: Optional[bytes] = None`  
    HTTP body in raw bytes.

- `json: Optional[dict] = None`  
    HTTP body in json.

- `text: Optional[str] = None`  
    HTTP body in text.

- `form: Optional[dict] = None`  
    HTTP body in form.

- `file: Optional[Union[str, Path]] = None`  
    Send a file in HTTP body. `Path` is the Python `pathlib.Path`.
    
- `timeout: Optional[SupportsFloat] = None`  
    Timeout for one request attempt in seconds, which will override `timeout` in `Client`.

- `retry: Optional[int] = None`  
    Retry times, which will override `retry` in `Client`. Notice `retry + 1` is the number of total attempts.

- `meta: Optional[dict] = None`  
    User-defined meta data, which can be accessed later.

Under the hood, all parameters are passed into the constructor of a special class called `Request`, which can later be assessed in `Response`. Also be aware of that two `Request`s are equal if all their parameters are the same, but hash values of any two `Request`s are different.

### Process the Response

`Response` has following properties and methods:

- `url: URL`  
    Response url. Note that this url does not necessarily equal to the url of its corresponding `Request`.

- `status: int`  
    Response status code.

- `reason: str`  
    Response reason.

- `headers: CIMultiDictProxy`  
    Response headers.

- `body: bytes`  
    Response body in raw bytes.

- `request: Request`  
    Corresponding `Request`.

- `meta: dict`  
    `meta` data in the corresponding `Request`.

- `text(self, encoding: Optional[str] = None) -> str`  
    Response body in text. If `encoding` is not set, `Response` will use [cchardet](https://github.com/PyYoshi/cChardet) to detect encoding. If cchardet fails, `'utf-8'` will be assumed. 

- `json(self) -> Jsonable`  
    Response body as json. `Jsonable` is defined as `NewType('Jsonable', Any)`.

- `etree(self, html: bool = True) -> etree._ElementTree`  
    Response body as [lxml](https://lxml.de/) etree. If `html` is `True`, body will be first processed by [html5lib](https://github.com/html5lib/html5lib-python).
    
`text()`, `json()`, or `etree()` may sometimes be a expensive operation and they are not likely to be all valid for a single `Response`, so `Response` will compute them lazily.

If an exception occurs during processing (including timeout), `Response` will be constructed like:

```python
    resp = Response(
        url=URL(''),
        status=-1,
        reason=repr(result),
        headers={},
        body=b'',
        request=req,
        meta=req.meta,
    )
```

Same as `Request`, two `Response`s are equal if all their parameters are the same, but hash values of any two `Response`s are different.

### Close the Client
`Client` supports the context manager protocol, or you may close it directly by calling `close()`.  

```python
    close(self) -> None
```

---

## WebSocket

`WebSocketServer` and `WebSocketClient` have exactly the same interface, so we will only take `WebSocketClient` as an example.

```python
    from requestkit import WebSocketClient

    def callback(msg: str):
        print(msg)

    with WebSocketClient(callbacks=[callback]) as client:
        client.send('Hello, world!')
        client.join()
```

First, we need to build a client, which takes a few parameters as shown below:

- `host: Optional[str] = None`  
    TCP/IP host. If it is not set, the default value from `AIOHTTP` will be used, which currently is `'0.0.0.0'`.

- `port: Optional[int] = None`  
    TCP/IP port. If it is not set, the default value from `AIOHTTP` will be used, which currently is `8080`.

- `route: str = '/ws'`  
    The route definition.

- `maxsize: int = 0`  
    The maximum size of the underlying queue. If the queue is full, the first arrived item will be discarded. Set it to `0` if you want an infinite size.

- `callbacks: Optional[List[Callable]] = None`  

    Callback funtions when a message arrives. Every function should have a `msg` parameter with an annotation type `str`, `bytes`, or `Jsonable` (`from requestkit import Jsonable`), and then only messages of the specific type will be passed to this function.  

    Also notice, since WebSocket does not natively support JSON, we will try to load every text message as JSON and only use `str` callbacks as a fallback.

After construct a `WebSocketClient`, we can send messages. `send(item)` method does not block. If you want to make sure all messages are actually sent, use `join()`.

```python
    send(self, item: Union[str, bytes, Jsonable]) -> None

    join(self) -> None
```

Finally, you should close the `WebSocketClient` if you are not using the context manager.

```python
    close(self) -> None
```

---

## Logging, Testing, and Dependencies

`requestkit` uses the standard logging module with the logger named `Client`, `WebSocketServer`, and `WebSocketClient`.

`requestkit` is tested under CPython 3.7.3 in Windows. All test files are properly constructed so that you can use [Test Discovery](https://docs.python.org/3.7/library/unittest.html#test-discovery) to run all tests.

Dependencies with their versions being tested against are listed as below:

```
    yarl       1.3.0
    aiofiles   0.4.0
    aiohttp    3.5.4
    multidict  4.5.2
    cchardet   2.1.4
    html5lib   1.0.1
    lxml       4.3.3
```