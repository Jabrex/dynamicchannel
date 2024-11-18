import asyncio

DEVICE_IP = "192.168.1.105"
DEVICE_PORT = 12345

async def listen_and_respond():
    try:
        server = await asyncio.start_server(handle_connection, DEVICE_IP, DEVICE_PORT)
        print("Cihaz E veri alıyor ve yanıtlıyor...")
        async with server:
            await server.serve_forever()
    except Exception as e:
        print(f"Sunucu başlatılırken hata oluştu: {e}")

async def handle_connection(reader, writer):
    try:
        data = await reader.read(1024)
        addr = writer.get_extra_info('peername')
        print(f"Gelen veri: {data} - Gönderen: {addr}")

        # Gelen veri "ping" ise gelen adrese "pong" yanıtı gönder
        if data == b"ping":
            try:
                response_reader, response_writer = await asyncio.open_connection(addr[0], addr[1])
                response_writer.write(b"pong")
                await response_writer.drain()
                print(f"{addr} adresine 'pong' yanıtı gönderildi.")
                response_writer.close()
                await response_writer.wait_closed()
            except Exception as e:
                print(f"Yanıt gönderilirken hata oluştu: {e}")

        writer.close()
        await writer.wait_closed()
    except Exception as e:
        print(f"Bağlantı işlenirken hata oluştu: {e}")
        writer.close()
        await writer.wait_closed()

asyncio.run(listen_and_respond())
