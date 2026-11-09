"""Pixel formats as they arrive from cameras and sensors. Each decoder turns bytes into one value per pixel."""
import cv2
import numpy as np

FORMATS = {
    "gray8": {"name": "8-bit grey (or a Bayer mosaic)", "bytes_per_pixel": 1.0, "bits": 8},
    "gray16le": {"name": "16-bit little-endian (depth maps, scientific cameras)", "bytes_per_pixel": 2.0, "bits": 16},
    "gray16be": {"name": "16-bit big-endian", "bytes_per_pixel": 2.0, "bits": 16},
    "raw10": {"name": "RAW10 packed: 4 pixels in 5 bytes (MIPI camera sensors)", "bytes_per_pixel": 1.25, "bits": 10},
    "raw12": {"name": "RAW12 packed: 2 pixels in 3 bytes", "bytes_per_pixel": 1.5, "bits": 12},
    "kinect11": {"name": "11-bit packed bitstream (Kinect for Xbox 360 depth)", "bytes_per_pixel": 1.375, "bits": 11},
    "yuyv": {"name": "YUYV 4:2:2 (USB webcams)", "bytes_per_pixel": 2.0, "bits": 8},
    "rgb24": {"name": "RGB, 3 bytes per pixel", "bytes_per_pixel": 3.0, "bits": 8},
    "rgb565": {"name": "RGB565 little-endian (small displays, microcontrollers)", "bytes_per_pixel": 2.0, "bits": 16},
}


def _trim(b: bytes, unit: int) -> np.ndarray:
    a = np.frombuffer(b, dtype=np.uint8)
    return a[: len(a) - len(a) % unit]


def luminance(b: bytes, fmt: str) -> np.ndarray:
    """One brightness value per pixel, scaled to 0..1, without needing the width."""
    if fmt == "gray8":
        return _trim(b, 1) / 255.0
    if fmt in ("gray16le", "gray16be"):
        v = _trim(b, 2).view("<u2" if fmt == "gray16le" else ">u2").astype(float)
        return v / max(v.max(), 1.0)
    if fmt == "raw10":
        a = _trim(b, 5).reshape(-1, 5).astype(np.uint16)
        px = (a[:, :4] << 2) | ((a[:, 4:5] >> (2 * np.arange(4))) & 3)
        return px.reshape(-1) / 1023.0
    if fmt == "raw12":
        a = _trim(b, 3).reshape(-1, 3).astype(np.uint16)
        p0, p1 = (a[:, 0] << 4) | (a[:, 2] & 15), (a[:, 1] << 4) | (a[:, 2] >> 4)
        return np.stack([p0, p1], axis=1).reshape(-1) / 4095.0
    if fmt == "kinect11":
        bits = np.unpackbits(_trim(b, 11))
        v = bits.reshape(-1, 11) @ (1 << np.arange(10, -1, -1))
        return v / 2047.0
    if fmt == "yuyv":
        return _trim(b, 4)[0::2] / 255.0
    if fmt == "rgb24":
        a = _trim(b, 3).reshape(-1, 3).astype(float)
        return (0.299 * a[:, 0] + 0.587 * a[:, 1] + 0.114 * a[:, 2]) / 255.0
    if fmt == "rgb565":
        v = _trim(b, 2).view("<u2").astype(np.uint32)
        r, g, bl = (v >> 11) & 31, (v >> 5) & 63, v & 31
        return (0.299 * r / 31 + 0.587 * g / 63 + 0.114 * bl / 31)
    raise ValueError(fmt)


def image(b: bytes, fmt: str, width: int, offset: int = 0, bayer: str | None = None) -> np.ndarray:
    """The picture as 8-bit RGB, for display."""
    b = b[offset:]
    if fmt == "yuyv":
        a = _trim(b, 2 * width * 2)
        h = len(a) // (2 * width)
        return cv2.cvtColor(a[: h * width * 2].reshape(h, width, 2), cv2.COLOR_YUV2RGB_YUYV)
    if fmt == "rgb24":
        a = _trim(b, 3 * width)
        return a.reshape(-1, width, 3).copy()
    if fmt == "rgb565":
        v = _trim(b, 2 * width).view("<u2").astype(np.uint32).reshape(-1, width)
        return np.stack([((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31], axis=2).astype(np.uint8)
    lum = luminance(b, fmt)
    h = len(lum) // width
    g = (np.clip(lum[: h * width], 0, 1) * 255).astype(np.uint8).reshape(h, width)
    if fmt == "gray8" and bayer:
        code = {"RGGB": cv2.COLOR_BayerRG2RGB, "BGGR": cv2.COLOR_BayerBG2RGB, "GRBG": cv2.COLOR_BayerGR2RGB, "GBRG": cv2.COLOR_BayerGB2RGB}[bayer]
        return cv2.cvtColor(g[: h - h % 2, : width - width % 2], code)
    if fmt == "kinect11":
        return cv2.cvtColor(cv2.applyColorMap(g, cv2.COLORMAP_TURBO), cv2.COLOR_BGR2RGB)
    return np.stack([g, g, g], axis=2)


def encode(rgb: np.ndarray, fmt: str, bayer: str = "RGGB") -> bytes:
    """Write an RGB picture (or a depth map, for kinect11 and 16-bit) in a device format, for examples and tests."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY) if rgb.ndim == 3 else rgb
    if fmt == "gray8":
        return gray.astype(np.uint8).tobytes()
    if fmt == "bayer":
        h, w = rgb.shape[:2]
        out = np.zeros((h, w), np.uint8)
        idx = {"R": 0, "G": 1, "B": 2}
        for dy in range(2):
            for dx in range(2):
                out[dy::2, dx::2] = rgb[dy::2, dx::2, idx[bayer[dy * 2 + dx]]]
        return out.tobytes()
    if fmt in ("gray16le", "gray16be"):
        # An 8-bit picture becomes a realistic 12-bit sensor value: the low bits carry noise, not a copy of the high byte.
        v = gray.astype(np.uint16) * 16 + np.random.default_rng(5).integers(0, 16, gray.shape).astype(np.uint16) if gray.dtype == np.uint8 else gray.astype(np.uint16)
        return v.astype("<u2" if fmt == "gray16le" else ">u2").tobytes()
    if fmt == "raw10":
        v = (gray.astype(np.uint16) * 4).reshape(-1, 4)
        low = sum((v[:, i] & 3) << (2 * i) for i in range(4)).astype(np.uint8)
        return np.concatenate([(v >> 2).astype(np.uint8), low[:, None]], axis=1).tobytes()
    if fmt == "raw12":
        v = (gray.astype(np.uint16) * 16).reshape(-1, 2)
        return np.stack([(v[:, 0] >> 4), (v[:, 1] >> 4), ((v[:, 1] & 15) << 4) | (v[:, 0] & 15)], axis=1).astype(np.uint8).tobytes()
    if fmt == "kinect11":
        v = gray.astype(np.uint16).reshape(-1) if gray.dtype != np.uint8 else gray.astype(np.uint16).reshape(-1) * 8
        bits = ((v[:, None] >> np.arange(10, -1, -1)) & 1).astype(np.uint8).reshape(-1)
        return np.packbits(bits).tobytes()
    if fmt == "yuyv":
        yuv = cv2.cvtColor(rgb, cv2.COLOR_RGB2YUV)
        h, w = gray.shape
        out = np.empty((h, w, 2), np.uint8)
        out[:, :, 0] = yuv[:, :, 0]
        out[:, 0::2, 1] = yuv[:, 0::2, 1]
        out[:, 1::2, 1] = yuv[:, 1::2, 2]
        return out.tobytes()
    if fmt == "rgb24":
        return rgb.astype(np.uint8).tobytes()
    if fmt == "rgb565":
        r, g, b = (rgb[:, :, i].astype(np.uint16) for i in range(3))
        return (((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)).astype("<u2").tobytes()
    raise ValueError(fmt)
