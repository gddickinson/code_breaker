"""Find attached devices using what macOS reports without special permissions."""
import json
import subprocess
import time

KNOWN_VENDORS = {"0x045e": "Microsoft", "0x046d": "Logitech", "0x05ac": "Apple", "0x0b95": "ASIX", "0x0bc2": "Seagate", "0x2341": "Arduino", "0x1a86": "QinHeng (CH340 serial)", "0x0403": "FTDI (serial)", "0x10c4": "Silicon Labs (serial)", "0x067b": "Prolific (serial)", "0x0483": "STMicroelectronics", "0x239a": "Adafruit", "0x2e8a": "Raspberry Pi", "0x04d8": "Microchip", "0x1d6b": "Linux Foundation"}
KINECT = {("0x045e", "0x02ae"): "Kinect for Xbox 360 camera", ("0x045e", "0x02b0"): "Kinect for Xbox 360 motor", ("0x045e", "0x02ad"): "Kinect for Xbox 360 audio", ("0x045e", "0x02c4"): "Kinect for Xbox One"}
SERIAL_VENDORS = {"0x1a86", "0x0403", "0x10c4", "0x067b", "0x2341"}
_CACHE = {"at": 0.0, "data": None}


def profiler(kind: str) -> list:
    try:
        r = subprocess.run(["system_profiler", "-json", kind], capture_output=True, text=True, timeout=25)
        return list(json.loads(r.stdout or "{}").values())[0] if r.stdout.strip() else []
    except (subprocess.TimeoutExpired, json.JSONDecodeError, IndexError):
        return []


def usb(tree: list) -> list:
    out = []
    def walk(items, bus):
        for i in items:
            vid, pid = i.get("USBDeviceKeyVendorID") or i.get("vendor_id", ""), i.get("USBDeviceKeyProductID") or i.get("product_id", "")
            if vid:
                vid, pid = vid.split()[0].lower(), pid.split()[0].lower() if pid else ""
                vendor = i.get("USBDeviceKeyVendorName") or KNOWN_VENDORS.get(vid, "")
                note = KINECT.get((vid, pid), "")
                if vid in SERIAL_VENDORS:
                    note = note or "USB serial adapter: monitor it under Serial ports"
                out.append({"category": "USB", "name": i.get("_name", "USB device"), "id": f"{vid}:{pid}", "details": {"Vendor": vendor or "unknown", "Vendor ID": vid, "Product ID": pid, "Speed": i.get("USBDeviceKeyLinkSpeed") or i.get("device_speed", ""), "Bus": bus}, "note": note, "streams": []})
            walk(i.get("_items", []), bus)
    for b in tree:
        walk(b.get("_items", []), b.get("_name", ""))
    return out


def cameras(items: list) -> list:
    return [{"category": "Camera", "name": c.get("_name", "Camera"), "id": c.get("spcamera_unique-id", ""), "details": {"Model": c.get("spcamera_model-id", "")}, "note": "", "streams": ["camera"]} for c in items]


def audio(items: list) -> list:
    out = []
    for group in items:
        for d in group.get("_items", []):
            ins, outs = d.get("coreaudio_device_input", 0), d.get("coreaudio_device_output", 0)
            out.append({"category": "Audio", "name": d.get("_name", "Audio device"), "id": d.get("_name", ""), "details": {"Inputs": ins, "Outputs": outs, "Sample rate": d.get("coreaudio_device_srate", ""), "Connection": str(d.get("coreaudio_device_transport", "")).replace("coreaudio_device_type_", "")}, "note": "", "streams": ["microphone"] if ins else []})
    return out


def displays(items: list) -> list:
    out = []
    for gpu in items:
        for d in gpu.get("spdisplays_ndrvs", []):
            out.append({"category": "Display", "name": d.get("_name", "Display"), "id": d.get("_spdisplays_display-serial-number", d.get("_name", "")), "details": {"Resolution": d.get("_spdisplays_resolution", d.get("spdisplays_resolution", "")), "Connection": d.get("spdisplays_connection_type", "internal" if "LCD" in d.get("_name", "") else ""), "GPU": gpu.get("_name", "")}, "note": "Displays are outputs, so their signal cannot be read back here.", "streams": []})
    return out


def bluetooth(items: list) -> list:
    out = []
    for c in items:
        for key in ("device_connected", "device_not_connected"):
            for entry in c.get(key, []) or []:
                for name, d in entry.items():
                    out.append({"category": "Bluetooth", "name": name, "id": d.get("device_address", name), "details": {"Connected": key == "device_connected", "Type": d.get("device_minorType", ""), "Address": d.get("device_address", "")}, "note": "", "streams": []})
    return out


def serial_ports() -> list:
    from serial.tools import list_ports
    out = []
    for p in list_ports.comports():
        risky = "Bluetooth" in p.device or "debug-console" in p.device or (p.description and "BoseNC" in p.device)
        out.append({"category": "Serial port", "name": p.device, "id": p.device, "details": {"Description": p.description, "USB IDs": f"{p.vid:#06x}:{p.pid:#06x}" if p.vid else "", "Manufacturer": p.manufacturer or ""}, "note": "Opening a Bluetooth or system port may connect to a device or do nothing useful." if risky else "Opening a port can reset some boards, such as an Arduino.", "streams": ["serial"]})
    return out


def network() -> list:
    import psutil
    stats, addrs = psutil.net_if_stats(), psutil.net_if_addrs()
    out = []
    for name, s in stats.items():
        if not s.isup:
            continue
        ip = next((a.address for a in addrs.get(name, []) if a.family.name == "AF_INET"), "")
        out.append({"category": "Network", "name": name, "id": name, "details": {"Address": ip, "Speed (Mb/s)": s.speed or "", "MTU": s.mtu}, "note": "", "streams": ["network"]})
    return out


def discover(force: bool = False) -> dict:
    """Everything attached, grouped by category. Cached briefly because system_profiler is slow."""
    if _CACHE["data"] and not force and time.time() - _CACHE["at"] < 10:
        return _CACHE["data"]
    found, errors = [], []
    for fn, args in ((usb, "SPUSBHostDataType"), (cameras, "SPCameraDataType"), (audio, "SPAudioDataType"), (displays, "SPDisplaysDataType"), (bluetooth, "SPBluetoothDataType")):
        try:
            found += fn(profiler(args))
        except (KeyError, TypeError, AttributeError) as exc:
            errors.append(f"{args}: {exc!r}")
    for fn in (serial_ports, network):
        try:
            found += fn()
        except Exception as exc:  # a missing library or permission is reported, not fatal
            errors.append(f"{fn.__name__}: {exc!r}")
    data = {"devices": found, "errors": errors, "kinect": any(d["note"].startswith("Kinect") for d in found), "at": time.strftime("%H:%M:%S")}
    _CACHE.update(at=time.time(), data=data)
    return data
