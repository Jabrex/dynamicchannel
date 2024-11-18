import asyncio
import random
import time

DEVICE_IP = "192.168.1.102"
DEVICE_PORT = 12345
NEIGHBORS = {
    "D": ("192.168.1.104", 12345),
    "E": ("192.168.1.105", 12345)
}

alpha = 0.1
gamma = 0.9
epsilon = 0.1

Q = {
    "B": {"D": 0.0, "E": 0.0}
}

async def measure_average_delay(target_ip, target_port, num_samples=5):
    delays = []
    for _ in range(num_samples):
        start_time = time.time()
        try:
            reader, writer = await asyncio.open_connection(target_ip, target_port)
            writer.write(b"ping")
            await writer.drain()
            await reader.read(100)
            end_time = time.time()
            delays.append((end_time - start_time) * 1000)
        except (asyncio.TimeoutError, ConnectionRefusedError):
            delays.append(1000)
        finally:
            if 'writer' in locals():
                writer.close()
                await writer.wait_closed()
    return sum(delays) / len(delays)

base_delays = {}

async def calculate_base_delays():
    base_delays[("B", "D")] = await measure_average_delay(NEIGHBORS["D"][0], NEIGHBORS["D"][1])
    base_delays[("B", "E")] = await measure_average_delay(NEIGHBORS["E"][0], NEIGHBORS["E"][1])

def dynamic_delay(state, action):
    return base_delays[(state, action)] + random.randint(-20, 20)

def update_q_table(state, action, reward, next_state, next_action):
    current_q = Q[state][action]
    next_q = Q[next_state][next_action] if next_state in Q and next_action in Q[next_state] else 0
    Q[state][action] = current_q + alpha * (reward + gamma * next_q - current_q)

def choose_best_route(current_state):
    if random.uniform(0, 1) < epsilon:
        return random.choice(list(NEIGHBORS.keys()))
    else:
        return min(Q[current_state], key=Q[current_state].get)

async def forward_packet(data, next_device):
    next_ip, next_port = NEIGHBORS[next_device]
    reader, writer = await asyncio.open_connection(next_ip, next_port)
    writer.write(data)
    await writer.drain()
    print(f"Paket {next_device} cihazına yönlendirildi.")
    writer.close()
    await writer.wait_closed()

async def listen_and_process():
    server = await asyncio.start_server(handle_connection, DEVICE_IP, DEVICE_PORT)
    print("Paket dinleniyor ve yanıt veriyor...")
    async with server:
        await server.serve_forever()

async def handle_connection(reader, writer):
    data = await reader.read(1024)
    addr = writer.get_extra_info('peername')
    print(f"Gelen veri: {data} - Gönderen: {addr}")

    # Gelen veri "ping" ise gelen adrese "pong" yanıtı gönder
    if data == b"ping":
        response_reader, response_writer = await asyncio.open_connection(addr[0], addr[1])
        response_writer.write(b"pong")
        await response_writer.drain()
        print(f"{addr} adresine 'pong' yanıtı gönderildi.")
        response_writer.close()
        await response_writer.wait_closed()
    else:
        # Normal yönlendirme işlemi için SARSA ile en iyi rotayı seçme
        state = "B"
        action = choose_best_route(state)
        reward = -dynamic_delay(state, action)

        next_state = action
        next_action = choose_best_route(next_state) if next_state in Q else None

        if next_action:
            update_q_table(state, action, reward, next_state, next_action)

        await forward_packet(data, action)
    writer.close()
    await writer.wait_closed()

async def main():
    await calculate_base_delays()
    await listen_and_process()

asyncio.run(main())
