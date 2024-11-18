import asyncio
import random
import time
from asyncio.exceptions import TimeoutError

# Configuration
DEVICE_IP = "192.168.1.101"
DEVICE_PORT = 12345
NEIGHBORS = {
    "B": ("192.168.1.102", 12345),
    "C": ("192.168.1.103", 12345),
}

# Reinforcement Learning Parameters
alpha = 0.1
gamma = 0.9
epsilon = 0.1
Q = {
    "A": {"B": 0.0, "C": 0.0},
}

base_delays = {}


async def measure_average_delay(target_ip, target_port, num_samples=5):
    """Measures average delay to a target device."""
    delays = []
    for _ in range(num_samples):
        start_time = time.time()
        try:
            reader, writer = await asyncio.open_connection(
                target_ip, target_port
            )
            writer.write(b"ping")
            await writer.drain()
            await asyncio.wait_for(reader.read(100), timeout=2)
            end_time = time.time()
            delays.append((end_time - start_time) * 1000)
        except (TimeoutError, ConnectionRefusedError):
            delays.append(1000)  # Default high delay
        finally:
            if "writer" in locals() and writer:
                writer.close()
                await writer.wait_closed()
    return sum(delays) / len(delays)


async def calculate_base_delays():
    """Calculates and caches base delays to neighbors."""
    for neighbor, (ip, port) in NEIGHBORS.items():
        try:
            base_delays[("A", neighbor)] = await measure_average_delay(ip, port)
        except Exception as e:
            base_delays[("A", neighbor)] = 1000  # High default delay
            print(f"Failed to measure delay for {neighbor}: {e}")


def dynamic_delay(state, action):
    """Adds random noise to base delays for SARSA learning."""
    return base_delays.get((state, action), 1000) + random.uniform(-20, 20)


def update_q_table(state, action, reward, next_state, next_action):
    """Updates the Q-value table using the SARSA algorithm."""
    current_q = Q[state][action]
    next_q = Q[next_state][next_action] if next_state in Q and next_action in Q[next_state] else 0
    Q[state][action] = current_q + alpha * (reward + gamma * next_q - current_q)


def choose_best_route(current_state):
    """Selects the best route based on Q-table values or exploration."""
    if random.uniform(0, 1) < epsilon:
        return random.choice(list(NEIGHBORS.keys()))
    return min(Q[current_state], key=Q[current_state].get)


async def forward_packet(data, next_device):
    """Forwards a packet to the specified neighbor device."""
    try:
        next_ip, next_port = NEIGHBORS[next_device]
        reader, writer = await asyncio.open_connection(next_ip, next_port)
        writer.write(data)
        await writer.drain()
        print(f"Packet forwarded to {next_device}.")
        writer.close()
        await writer.wait_closed()
    except Exception as e:
        print(f"Failed to forward packet to {next_device}: {e}")


async def handle_connection(reader, writer):
    """Handles incoming connections and processes packets."""
    try:
        data = await reader.read(1024)
        addr = writer.get_extra_info("peername")
        print(f"Received data: {data} from {addr}")

        if data == b"ping":
            writer.write(b"pong")
            await writer.drain()
            print(f"Pong sent to {addr}")
        else:
            state = "A"
            action = choose_best_route(state)
            reward = -dynamic_delay(state, action)

            next_state = action
            next_action = choose_best_route(next_state) if next_state in Q else None

            if next_action:
                update_q_table(state, action, reward, next_state, next_action)

            await forward_packet(data, action)
    except Exception as e:
        print(f"Error handling connection: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def listen_and_process():
    """Starts the server to listen for packets."""
    server = await asyncio.start_server(handle_connection, DEVICE_IP, DEVICE_PORT)
    print("Listening for packets...")
    async with server:
        await server.serve_forever()


async def main():
    """Main entry point for the application."""
    await calculate_base_delays()
    await listen_and_process()


if __name__ == "__main__":
    asyncio.run(main())
