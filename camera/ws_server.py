import asyncio
import websockets

async def handler(websocket, path):
    # 解析URL查询参数以获取客户端ID
    query_params = dict(param.split('=') for param in path.split('?')[1].split('&'))
    client_id = query_params.get('client_id')
    print(f"Connected client ID: {client_id}")
    # 处理WebSocket通信...

async def main():
    async with websockets.serve(handler, "localhost", 61789):
        await asyncio.Future()  # 运行直到被手动停止

asyncio.run(main())
