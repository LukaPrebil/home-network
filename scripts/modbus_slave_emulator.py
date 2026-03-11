#!/usr/bin/env python3
"""Emulate a th-Tune Modbus slave on the Elfin EW11 to capture what the Carel board sends.

Connects to the Elfin in transparent mode, listens for Modbus RTU requests
addressed to our slave ID, and responds. Logs all requests and any write data
the board sends.
"""

import socket
import struct
import time
import sys

ELFIN_HOST = "192.168.1.160"
ELFIN_PORT = 502
SLAVE_ID = 11  # Emulate th-Tune at address 11

# Pre-allocate registers/coils the board might read or write
coils = [False] * 256
holding_registers = [0] * 256
input_registers = [0] * 256


def crc16(data):
    """Calculate Modbus RTU CRC16."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc


def build_response(slave_id, func, payload):
    """Build a Modbus RTU response frame."""
    frame = bytes([slave_id, func]) + payload
    crc = crc16(frame)
    return frame + struct.pack('<H', crc)


def handle_request(data):
    """Parse a Modbus RTU request and build a response."""
    if len(data) < 4:
        return None

    slave_id = data[0]
    if slave_id != SLAVE_ID:
        return None  # Not for us

    func = data[1]
    
    if func == 0x01:  # Read Coils
        addr = struct.unpack('>H', data[2:4])[0]
        count = struct.unpack('>H', data[4:6])[0]
        print(f"  >> READ COILS addr={addr} count={count}")
        byte_count = (count + 7) // 8
        coil_bytes = bytearray(byte_count)
        for i in range(count):
            if coils[addr + i]:
                coil_bytes[i // 8] |= (1 << (i % 8))
        return build_response(slave_id, func, bytes([byte_count]) + bytes(coil_bytes))

    elif func == 0x02:  # Read Discrete Inputs
        addr = struct.unpack('>H', data[2:4])[0]
        count = struct.unpack('>H', data[4:6])[0]
        print(f"  >> READ DISCRETE INPUTS addr={addr} count={count}")
        byte_count = (count + 7) // 8
        return build_response(slave_id, func, bytes([byte_count]) + bytes(byte_count))

    elif func == 0x03:  # Read Holding Registers
        addr = struct.unpack('>H', data[2:4])[0]
        count = struct.unpack('>H', data[4:6])[0]
        print(f"  >> READ HOLDING REGISTERS addr={addr} count={count}")
        payload = bytes([count * 2])
        for i in range(count):
            payload += struct.pack('>H', holding_registers[addr + i])
        return build_response(slave_id, func, payload)

    elif func == 0x04:  # Read Input Registers
        addr = struct.unpack('>H', data[2:4])[0]
        count = struct.unpack('>H', data[4:6])[0]
        print(f"  >> READ INPUT REGISTERS addr={addr} count={count}")
        payload = bytes([count * 2])
        for i in range(count):
            payload += struct.pack('>H', input_registers[addr + i])
        return build_response(slave_id, func, payload)

    elif func == 0x05:  # Write Single Coil
        addr = struct.unpack('>H', data[2:4])[0]
        value = struct.unpack('>H', data[4:6])[0]
        coils[addr] = value == 0xFF00
        print(f"  ** WRITE COIL addr={addr} value={coils[addr]}")
        return build_response(slave_id, func, data[2:6])

    elif func == 0x06:  # Write Single Register
        addr = struct.unpack('>H', data[2:4])[0]
        value = struct.unpack('>H', data[4:6])[0]
        holding_registers[addr] = value
        print(f"  ** WRITE REGISTER addr={addr} value={value} (÷10={value/10:.1f})")
        return build_response(slave_id, func, data[2:6])

    elif func == 0x0F:  # Write Multiple Coils
        addr = struct.unpack('>H', data[2:4])[0]
        count = struct.unpack('>H', data[4:6])[0]
        byte_count = data[6]
        print(f"  ** WRITE MULTIPLE COILS addr={addr} count={count} data={data[7:7+byte_count].hex()}")
        for i in range(count):
            coils[addr + i] = bool(data[7 + i // 8] & (1 << (i % 8)))
        return build_response(slave_id, func, data[2:6])

    elif func == 0x10:  # Write Multiple Registers
        addr = struct.unpack('>H', data[2:4])[0]
        count = struct.unpack('>H', data[4:6])[0]
        byte_count = data[6]
        values = []
        for i in range(count):
            val = struct.unpack('>H', data[7 + i*2:9 + i*2])[0]
            holding_registers[addr + i] = val
            values.append(val)
        print(f"  ** WRITE MULTIPLE REGISTERS addr={addr} count={count} values={values}")
        return build_response(slave_id, func, data[2:6])

    else:
        print(f"  ?? UNKNOWN FUNCTION {func:#x}")
        # Return exception: illegal function
        return build_response(slave_id, func | 0x80, bytes([0x01]))


def main():
    global SLAVE_ID
    SLAVE_ID = int(sys.argv[1]) if len(sys.argv) > 1 else SLAVE_ID

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    sock.connect((ELFIN_HOST, ELFIN_PORT))

    print(f"Connected to Elfin at {ELFIN_HOST}:{ELFIN_PORT}")
    print(f"Emulating th-Tune slave at address {SLAVE_ID}")
    print(f"Listening for requests... (Ctrl+C to stop)")
    print()

    request_count = 0
    start = time.time()

    try:
        while True:
            try:
                data = sock.recv(1024)
                if not data:
                    continue

                elapsed = time.time() - start
                slave = data[0]
                
                if slave == SLAVE_ID:
                    request_count += 1
                    print(f"[{elapsed:6.1f}s] #{request_count} Request for us: {data.hex()}")
                    
                    resp = handle_request(data)
                    if resp:
                        sock.sendall(resp)
                        print(f"          Responded: {resp.hex()}")
                    print()

            except socket.timeout:
                pass

    except KeyboardInterrupt:
        print(f"\nStopped. Handled {request_count} requests in {time.time()-start:.0f}s")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
