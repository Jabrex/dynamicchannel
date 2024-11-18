import asyncio

DEVICE_IP = "192.168.1.105"
DEVICE_PORT = 12345

async def listen_and_respond():
    """Starts the server to listen for incoming connections."""
    try:
        server = await asyncio.start_server(handle_connection, DEVICE_IP, DEVICE_PORT)
        print("Device E is listening for data and responding...")
        async with server:
            await server.serve_forever()
    except Exception as e:
        print(f"Error occurred while starting the server: {e}")

async def handle_connection(reader, writer):
    """Handles incoming connections and sends responses if needed."""
    try:
        data = await reader.read(1024)
        addr = writer.get_extra_info('peername')
        print(f"Received data: {data} from {addr}")

        # Respond with 'pong' if the message is 'ping'
        if data == b"ping":
            try:
                writer.write(b"pong")
                await writer.drain()
                print(f"'pong' response sent to {addr}")
            except Exception as e:
                print(f"Error occurred while sending response to {addr}: {e}")
        
        writer.close()
        await writer.wait_closed()
    except Exception as e:
        print(f"Error occurred while processing connection: {e}")
        writer.close()
        await writer.wait_closed()

if __name__ == "__main__":
    asyncio.run(listen_and_respond())
