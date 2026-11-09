"""Read-only live streams. Each yields one JSON-ready dict per update and stops at its time limit."""
import time

from .analysis import analyse

MAX_SECONDS = 600
KEEP = 16384


def serial_stream(port: str, baud: int = 9600, seconds: float = 120, interval: float = 0.5):
    """Open a serial port without asserting DTR or RTS, read, and never write."""
    if port.startswith("sim://"):
        from .sim import SimPort
        s = SimPort(port)
    else:
        import serial

        s = serial.serial_for_url(port, do_not_open=True, timeout=0.1)
        s.baudrate, s.dtr, s.rts = baud, False, False
        s.open()
    buf, total, start, last = bytearray(), 0, time.time(), 0.0
    try:
        while time.time() - start < min(seconds, MAX_SECONDS):
            chunk = s.read(4096)
            if chunk:
                buf += chunk
                total += len(chunk)
                del buf[:-KEEP]
            if time.time() - last >= interval:
                last = time.time()
                recent = bytes(buf[-512:])
                yield {"event": "data", "elapsed": round(last - start, 1), "total": total, "rate": round(total / max(last - start, 0.01), 1), "hex": recent[-256:].hex(" "), "text": recent.decode("ascii", errors="replace"), "analysis": analyse(bytes(buf))}
    finally:
        s.close()
    yield {"event": "end", "total": total}


def network_stream(seconds: float = 60, interval: float = 1.0):
    """Bytes and packets per second on each interface, from the system counters."""
    import psutil

    prev, start = psutil.net_io_counters(pernic=True), time.time()
    while time.time() - start < min(seconds, MAX_SECONDS):
        time.sleep(interval)
        now = psutil.net_io_counters(pernic=True)
        rows = []
        for name, c in now.items():
            p = prev.get(name)
            if p is None:
                continue
            rin, rout = (c.bytes_recv - p.bytes_recv) / interval, (c.bytes_sent - p.bytes_sent) / interval
            if rin or rout or c.bytes_recv:
                rows.append({"name": name, "in": round(rin), "out": round(rout), "packets_in": round((c.packets_recv - p.packets_recv) / interval), "packets_out": round((c.packets_sent - p.packets_sent) / interval), "errors": c.errin + c.errout, "drops": c.dropin + c.dropout})
        prev = now
        yield {"event": "rates", "elapsed": round(time.time() - start, 1), "interfaces": sorted(rows, key=lambda r: -(r["in"] + r["out"]))[:12]}
    yield {"event": "end"}
