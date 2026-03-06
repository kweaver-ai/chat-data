# -*- coding: utf-8 -*-
# @Time : 2023/12/21 14:57
# @Author : Jack.li
# @Email : jack.li@xxx.cn
# @File : chat_handler_v2.py
# @Project : copilot
import asyncio
from pydantic import BaseModel, Field
from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse
# from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from sse_starlette import EventSourceResponse, ServerSentEvent
from app.routers import SSERouter, SSETestHtmlRouter
chat_router_v2 = APIRouter()


@chat_router_v2.get(SSERouter)
async def root(request: Request):
    async def event_generator(request: Request):
        res_str = "七夕情人节即将来临，我们为您准备了精美的鲜花和美味的蛋糕"
        for i in res_str:
            if await request.is_disconnected():
                print("连接已中断")
                break
            yield {
                "event": "message",
                "retry": 15000,
                "data": i
            }

            await asyncio.sleep(0.1)
    g = event_generator(request)
    return EventSourceResponse(g)


class Message(BaseModel):
    message: str


@chat_router_v2.post("/sse")
async def indexpost(msg: Message, req: Request):
    async def event_generator(request: Request):
        res_str = msg.message
        for i in res_str:
            if await request.is_disconnected():
                print("连接已中断")
                break
            yield {
                "event": "message",
                "retry": 15000,  # milisecond
                "data": i
            }

            await asyncio.sleep(0.1)

    return EventSourceResponse(event_generator(req))


from datetime import datetime
async def echo_stream(message: str):
    t = 0
    while True:
        await asyncio.sleep(1)
        yield ServerSentEvent(
            event="echo",
            id=t,
            # data={
            #     "message": message,
            #     "created_at": datetime.now().timestamp(),
            # },
            data=message
        )
        t += 1


@chat_router_v2.get("/sse_v2")
async def sse(message: str):
    return EventSourceResponse(content=echo_stream(message))


client_html = """
<!DOCTYPE html>
<html>
<head>
  <style>
  #logs {
    background-color: black;
    color:white;
    height:600px;
    overflow-x: hidden;
    overflow-y: auto;
    text-align: left;
    padding-left:10px;
  }
  </style>
</head>

<body>

<h1>Server Messages:</h1>
<div id="messages">
</div>

<script>
  var source = new EventSource("http://10.4.117.180:9090/sse_v2?message=hello");
  source.onmessage = function(event) {
    document.getElementById("messages").innerHTML += event.data + "<br>";
  };
</script>

</body>
</html>
"""

@chat_router_v2.get(SSETestHtmlRouter)
async def get():
    return HTMLResponse(client_html)

# import typing
# from camel_converter import to_snake
# T = typing.TypeVar("T", bound=BaseModel)
#
#
# class BaseEvent(BaseModel, typing.Generic[T]):
#     data: T
#
#     @classmethod
#     @property
#     def event_name(cls):
#         return to_snake(cls.__name__)
#
#     @classmethod
#     def create(cls, data: T):
#         return cls(data=data)
#
#
# P = typing.ParamSpec("P")
#
#
# def event_source():
#     def decorator(
#         func: typing.Callable[
#             P,
#             typing.AsyncGenerator[BaseEvent[T], BaseEvent[T]],
#         ],
#     ):
#         async def wrapper(
#             *args: typing.Any,
#             **kwargs: typing.Any,
#         ) -> typing.AsyncGenerator[ServerSentEvent, ServerSentEvent]:
#             t = 0
#             async for e in func(*args, **kwargs):
#                 yield ServerSentEvent(
#                     event=e.__class__.event_name,
#                     id=t,
#                     data=e.data.model_dump_json(),
#                 )
#                 t += 1
#
#         return wrapper
#
#     return decorator
#
#
# class EchoPayload(BaseModel):
#     message: str
#     created_at: datetime = Field(default_factory=datetime.now)
#
#
# class Echo(BaseEvent[EchoPayload]):
#     pass
#
#
# @event_source()
# async def echo_stream2(message: str):
#     t = 0
#     while True:
#         await asyncio.sleep(1)
#         yield Echo.create(
#             EchoPayload(
#                 message=message,
#             )
#         )
#         t += 1
#
#
# @chat_router_v2.get("/sse2")
# async def sse2(message: str):
#     return EventSourceResponse(content=echo_stream2(message))
#
#
# class ReverseEcho(BaseEvent[EchoPayload]):
#     pass
#
#
# @event_source()
# async def echo_stream3(message: str):
#     await asyncio.sleep(1)
#     t = 0
#     while True:
#         await asyncio.sleep(1)
#         yield Echo.create(
#             EchoPayload(
#                 message=message[::-1],
#             )
#         )
#         t += 1


# @app.get("/sse3")
# async def sse3(message: str):
#     return EventSourceResponse(
#         content=aiostream.stream.merge(
#             echo_stream2(message),
#             echo_stream3(message),
#         )
#     )
