import asyncio
import random
import time

DEVICE_IP = "192.168.1.101"
DEVICE_PORT = 12345
NEIGHBORS = {
    "B": ("192.168.1.102", 12345),
    "C": ("192.168.1.103", 12345),
}

alpha = 0.1
gamma = 0.9
epsilon = 0.1

Q = {
    "A": {"B": 0.0, "C": 0.0},
}

base_delays = {}


async def measure_average_delay(target_ip, target_port, num_samples=5):
    delays = []
    for _ in range(num_samples):
        start_time = time.time()
        try:
            reader, writer = await asyncio.open_connection(target_ip, target_port)
            writer.write(b"ping")
            await writer.drain()
            await asyncio.wait_for(reader.read(100), timeout=2)
            end_time = time.time()
            delays.append((end_time - start_time) * 1000)
        except (asyncio.TimeoutError, ConnectionRefusedError):
            delays.append(1000)
        finally:
            if "writer" in locals() and writer:
                writer.close()
                await writer.wait_closed()
    return sum(delays) / len(delays)


async def calculate_base_delays():
    for neighbor, (ip, port) in NEIGHBORS.items():
        try:
            base_delays[("A", neighbor)] = await measure_average_delay(ip, port)
        except Exception as e:
            base_delays[("A", neighbor)] = 1000


def dynamic_delay(state, action):
    return base_delays.get((state, action), 1000) + random.uniform(-20, 20)


def update_q_table(state, action, reward, next_state, next_action):
    current_q = Q[state][action]
    next_q = Q[next_state][next_action] if next_state in Q and next_action in Q[next_state] else 0
    Q[state][action] = current_q + alpha * (reward + gamma * next_q - current_q)


def choose_best_route(current_state):
    if random.uniform(0, 1) < epsilon:
        return random.choice(list(NEIGHBORS.keys()))
    return min(Q[current_state], key=Q[current_state].get)


async def forward_packet(data, next_device):
    next_ip, next_port = NEIGHBORS[next_device]
    reader, writer = await asyncio.open_connection(next_ip, next_port)
    writer.write(data)
    await writer.drain()
    print(f"Packet forwarded to {next_device}.")
    writer.close()
    await writer.wait_closed()


async def handle_connection(reader, writer):
    data = await reader.read(1024)
    addr = writer.get_extra_info("peername")
    print(f"Received data: {data} from {addr}")

    state = "A"
    action = choose_best_route(state)
    reward = -dynamic_delay(state, action)

    next_state = action
    next_action = choose_best_route(next_state) if next_state in Q else None

    if next_action:
        update_q_table(state, action, reward, next_state, next_action)

    await forward_packet(data, action)
    writer.close()
    await writer.wait_closed()


async def listen_and_process():
    server = await asyncio.start_server(handle_connection, DEVICE_IP, DEVICE_PORT)
    print("Listening for packets...")
    async with server:
        await server.serve_forever()


async def main():
    await calculate_base_delays()
    await listen_and_process()


if __name__ == "__main__":
    asyncio.run(main())
