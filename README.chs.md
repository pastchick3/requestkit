# requestkit

`requestkit`是一个对[AIOHTTP](https://docs.aiohttp.org/)的封装，提供了简洁的同步形式接口。目前`requestkit`提供了对HTTP协议客户端、WebSocket协议客户端及服务端的封装。

---

## HTTP客户端

```python
    from requestkit import Client

    with Client() as client:
        future = client.request('http://www.httpbin.org/get')
        response = future.result()
```

### 初始化客户端

```python
Client(self, setting: Optional[dict] = None)
```

`setting`适用于所有该客户端发送的全部请求，但会被各请求设置的对应参数覆盖（对`headers`和`cookies`来说是合并）。默认设置是：

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
    单次尝试连接的超时时间（秒）。

- `retry`  
    重试次数，注意`retry + 1`等于总尝试连接数。

- `concurrency`  
    最大并发请求数。

- `concurrency_per_host`
    对单个域名的最大并发请求数，域名由`yarl.URL.host`获得。

### 发送请求

`request(self, url, **kwargs) -> Future`

除了`url`，`request()`方法还接受下列的参数，并将返回一个[Future](https://docs.python.org/3/library/concurrent.futures.html#future-objects)。

- `url: Union[str, URL]`  
    目标url。

- `method: str = 'GET'`    
    HTTP方法，目前支持`'GET'`与`'POST'`。

- `headers: Optional[dict] = None`  
    HTTP请求头，将与`Client`的请求头合并。

- `cookies: Optional[dict] = None`  
    HTTP cookies，将与`Client`的cookies合并。

- `params: Optional[dict] = None`  
    查询字符串。

- `body: Optional[bytes] = None`  
    bytes形式的请求体。

- `json: Optional[dict] = None`  
    json形式的请求体。

- `text: Optional[str] = None`  
    text形式的请求体。

- `form: Optional[dict] = None`  
    form形式的请求体。

- `file: Optional[Union[str, Path]] = None`  
    在请求体中发送一个文件，`Path`参数是Python内置的`pathlib.Path`。
    
- `timeout: Optional[SupportsFloat] = None`  
    单次尝试连接的超时时间（秒），会覆盖`Client`中的`timeout`。

- `retry: Optional[int] = None`  
    重试次数，会覆盖`Client`中的`retry`。注意`retry + 1`等于总尝试连接数。

- `meta: Optional[dict] = None`  
    自定义元数据，可以在响应中获取。

实现上，所有参数都会被进一步传进`Request`类的构造函数中，用户可以在获得的`Response`中获取生成的`request`。同时注意，两个`Request`被认为相等如果它们的参数完全相同，但任意两个`Request`的哈希值均不相等。

### 处理响应

`Response`定义了以下的属性与方法：

- `url: URL`  
    响应的url。注意这个url不一定与`Request`的url相同。

- `status: int`  
    响应状态码。

- `reason: str`  
    响应原因。

- `headers: CIMultiDictProxy`  
    响应头。

- `body: bytes`  
    bytes形式的响应体。

- `request: Request`  
    对应的`Request`。

- `meta: dict`  
    对应的`Request`的`meta`属性。

- `text(self, encoding: Optional[str] = None) -> str`  
    返回text形式的响应体。如果不指定`encoding`参数，`Response`将使用[cchardet](https://github.com/PyYoshi/cChardet)推断编码，如果推断失败，程序将使用`'utf-8'`编码。

- `json(self) -> Jsonable`  
    返回json形式的响应体。`Jsonable`的定义为`NewType('Jsonable', Any)`。

- `etree(self, html: bool = True) -> etree._ElementTree`  
    返回[lxml](https://lxml.de/) etree形式的响应体。如果`html`被指定为`True`，响应体将先经过[html5lib](https://github.com/html5lib/html5lib-python)的处理。
    
`text()`，`json()`和`etree()`有时会是一个相对昂贵的操作，而且它们同时对一个`Response`有效的机率很小，所以`Response`将由`body`属性动态计算这几个函数。

如果在请求过程中程序抛出异常（包括超时异常），`Response`将使用如下参数初始化，其中`result`为抛出的异常:

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

与`Request`一样，两个`Response`被认为相等如果他们的参数完全一致，但任意两个`Response`的哈希值都不同。

### 关闭客户端

`Client`支持上下文管理器，或者你可以调用`close()`来手动关闭它。

```python
    close(self) -> None
```

---

## WebSocket

`WebSocketServer`与`WebSocketClient`的接口完全一致，所以我们将只介绍`WebSocketClient`。

```python
    from requestkit import WebSocketClient

    def callback(msg: str):
        print(msg)

    with WebSocketClient(callbacks=[callback]) as client:
        client.send('Hello, world!')
        client.join()
```

首先，我们需要建立一个客户端，它的构造函数接受如下参数：

- `host: Optional[str] = None`  
    TCP/IP主机名。如果未设置，程序将使用`AIOHTTP`的默认值，当前版本下是`'0.0.0.0'`。

- `port: Optional[int] = None`  
    TCP/IP端口。如果未设置，程序将使用`AIOHTTP`的默认值，当前版本下是`8080`。

- `route: str = '/ws'`  
    目标服务器路由路径。

- `maxsize: int = 0`  
    底层队列的最大容量。如果队列达到最大容量，最先入队的请求将被抛弃。如果该参数被设置为0，队列将拥有无限的容量。

- `callbacks: Optional[List[Callable]] = None`  

    当接收到一条消息时的回调函数。每一个函数都必须有一个`msg`参数并带有合适的类型标记，合法的标记包括`str`，`bytes`及`Jsonable`(`from requestkit import Jsonable`)。只有与标记类型一致的消息才会被传入该函数。

    同时注意，由于WebSocket没有对JSON的原生支持，程序将尝试将每一条文本消息都解释为JSON，若解释失败才会调用`str`类型的回调函数。

在初始化`WebSocketClient`后，我们调用`send(item)`来发送消息。`send(item)`不会阻塞，如果你想确认所有消息都已经被确实地发送，请再调用阻塞的`join()`。

```python
    send(self, item: Union[str, bytes, Jsonable]) -> None

    join(self) -> None
```

最后，你必须手动关闭`WebSocketClient`如果你不使用上下文管理器。

```python
    close(self) -> None
```

---

## 日志，测试以及依赖

`requestkit`使用标准logging模块，定义了名为`Client`，`WebSocketServer`以及`WebSocketClient`的logger。

`requestkit`使用Windows版本的CPython 3.7.3开发测试。所有测试均支持[Test Discovery](https://docs.python.org/3.7/library/unittest.html#test-discovery)。

依赖库及测试时的版本如下所示：

```
    yarl       1.3.0
    aiofiles   0.4.0
    aiohttp    3.5.4
    multidict  4.5.2
    cchardet   2.1.4
    html5lib   1.0.1
    lxml       4.3.3
```