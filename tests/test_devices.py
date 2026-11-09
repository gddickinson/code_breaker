"""Live devices: discovery parsing, stream analysis, simulated serial streaming and the API."""
import json

from fastapi.testclient import TestClient

from codebreaker.devices import analysis as A, discover as D
from codebreaker.devices.sim import SimPort, nmea_line
from codebreaker.web.app import app

client = TestClient(app)


def test_usb_tree_is_flattened_with_vendors_and_kinect():
    tree = [{"_name": "USB 3.1 Bus", "_items": [{"_name": "Hub", "USBDeviceKeyVendorID": "0x05ac", "USBDeviceKeyProductID": "0x1234", "_items": [{"_name": "Xbox NUI Camera", "USBDeviceKeyVendorID": "0x045e", "USBDeviceKeyProductID": "0x02ae"}]}]}]
    got = D.usb(tree)
    assert [d["name"] for d in got] == ["Hub", "Xbox NUI Camera"]
    assert got[1]["note"].startswith("Kinect") and got[0]["details"]["Vendor"] == "Apple"


def test_cameras_and_audio_inputs_offer_streams():
    cams = D.cameras([{"_name": "Webcam", "spcamera_unique-id": "x"}])
    aud = D.audio([{"_items": [{"_name": "Mic", "coreaudio_device_input": 1}, {"_name": "Speaker", "coreaudio_device_output": 2}]}])
    assert cams[0]["streams"] == ["camera"] and aud[0]["streams"] == ["microphone"] and aud[1]["streams"] == []


def test_nmea_checksums_are_verified():
    lines = [nmea_line(1_700_000_000 + i).decode().strip() for i in range(5)] + ["$GPGGA,123519,4807.038,N*00"]
    r = A.nmea(lines)
    assert r["valid_checksums"] == 5 and r["bad_checksums"] == 1


def test_analysis_recognises_text_formats():
    csv = "".join(f"{20 + i * 0.1:.2f},{50 + i},{1013}\n" for i in range(20)).encode()
    assert "Numeric columns (sensor readings)" in A.analyse(csv)["formats"]
    js = b"".join(json.dumps({"t": i, "v": i * 2}).encode() + b"\n" for i in range(5))
    assert "JSON lines" in A.analyse(js)["formats"]


def test_binary_packets_are_framed():
    port = SimPort("sim://packets")
    port.read = port.read.__func__.__get__(port)
    data = b"".join(SimPort.read(port) for _ in range(30))
    f = A.analyse(data)["formats"]["Fixed-length binary packets"]
    assert f["period"] == 16 and "AA" in f["sync"] and "55" in f["sync"]


def test_random_bytes_are_called_random():
    import os

    assert A.analyse(os.urandom(4096))["kind"] == "random, compressed or encrypted"


def stream(port, seconds=1.6):
    r = client.post("/api/devices/serial", json={"port": port, "seconds": seconds})
    assert r.status_code == 200
    return [json.loads(l) for l in r.text.splitlines() if l.strip()]


def test_simulated_gps_streams_and_is_recognised():
    ev = stream("sim://gps")
    data = [e for e in ev if e["event"] == "data" and e["total"]]
    assert data and ev[-1]["event"] == "end"
    assert "NMEA sentences (GPS, marine)" in data[-1]["analysis"]["formats"]


def test_unknown_ports_are_refused():
    assert client.post("/api/devices/serial", json={"port": "/dev/nonexistent"}).status_code == 400


def test_network_rates_stream():
    ev = [json.loads(l) for l in client.get("/api/devices/network?seconds=1.2").text.splitlines() if l.strip()]
    assert ev[0]["event"] == "rates" and ev[-1]["event"] == "end"


def test_pasted_hex_is_analysed():
    r = client.post("/api/devices/analyse", json={"text": "AA 55 01 02 " * 40}).json()
    assert r["bytes"] == 160
