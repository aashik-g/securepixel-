"""PNG RGB LSB payload encoding for SecurePixel."""

import struct
from io import BytesIO

from PIL import Image, UnidentifiedImageError

MAGIC = b"SPX1"
HEADER_SIZE = 8
MAX_PAYLOAD_SIZE = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class SteganographyError(ValueError):
    """Raised when an image cannot contain or yield a valid payload."""


def _payload_bits(payload: bytes):
    for byte in payload:
        for bit_index in range(7, -1, -1):
            yield (byte >> bit_index) & 1


def _read_image(image_data: bytes) -> Image.Image:
    try:
        with Image.open(BytesIO(image_data)) as image:
            image.verify()
        with Image.open(BytesIO(image_data)) as image:
            return image.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise SteganographyError("Unsupported or invalid image.") from exc


def embed_payload(image_data: bytes, payload: bytes) -> bytes:
    """Embed a versioned payload in RGB least-significant bits and return PNG bytes."""
    if len(payload) > MAX_PAYLOAD_SIZE:
        raise SteganographyError("Encrypted payload is too large.")

    image = _read_image(image_data)
    encoded = MAGIC + struct.pack(">I", len(payload)) + payload
    capacity = image.width * image.height * 3 // 8
    if len(encoded) > capacity:
        raise SteganographyError(
            f"Image is too small. It can hold {capacity - HEADER_SIZE:,} payload bytes."
        )

    pixels = list(image.getdata())
    bits = _payload_bits(encoded)
    updated = []
    for red, green, blue in pixels:
        channels = [red, green, blue]
        for channel_index in range(3):
            try:
                channels[channel_index] = (channels[channel_index] & 0xFE) | next(bits)
            except StopIteration:
                pass
        updated.append(tuple(channels))

    image.putdata(updated)
    output = BytesIO()
    image.save(output, format="PNG", optimize=False)
    return output.getvalue()


def _extract_bytes(pixels, byte_count: int) -> bytes:
    bits = []
    for red, green, blue in pixels:
        bits.extend((red & 1, green & 1, blue & 1))
        if len(bits) >= byte_count * 8:
            break
    if len(bits) < byte_count * 8:
        raise SteganographyError("No valid encrypted message found.")
    return bytes(
        sum(bits[index + offset] << (7 - offset) for offset in range(8))
        for index in range(0, byte_count * 8, 8)
    )


def extract_payload(image_data: bytes) -> bytes:
    """Extract and validate a versioned payload from a PNG-compatible image."""
    image = _read_image(image_data)
    pixels = list(image.getdata())
    capacity = image.width * image.height * 3 // 8
    if capacity < HEADER_SIZE:
        raise SteganographyError("No valid encrypted message found.")

    header = _extract_bytes(pixels, HEADER_SIZE)
    if header[:4] != MAGIC:
        raise SteganographyError("No valid encrypted message found.")

    payload_size = struct.unpack(">I", header[4:])[0]
    if payload_size < 1 or payload_size > MAX_PAYLOAD_SIZE:
        raise SteganographyError("Corrupted encrypted payload.")
    if HEADER_SIZE + payload_size > capacity:
        raise SteganographyError("Corrupted encrypted payload.")
    return _extract_bytes(pixels, HEADER_SIZE + payload_size)[HEADER_SIZE:]
