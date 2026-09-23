"""SecurePixel Flask application."""

import re
from io import BytesIO

from cryptography.exceptions import InvalidTag
from flask import Flask, jsonify, render_template, request, send_file

from crypto_utils import NONCE_SIZE, SALT_SIZE, decrypt_message, encrypt_message
from steganography import SteganographyError, embed_payload, extract_payload

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024
app.config["MAX_MESSAGE_BYTES"] = 256 * 1024
app.config["MAX_PASSWORD_LENGTH"] = 256
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


def error_response(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


def password_error(password: str) -> str | None:
    if not password:
        return "Enter a password."
    if len(password) > app.config["MAX_PASSWORD_LENGTH"]:
        return "Password is too long."
    checks = sum(
        bool(re.search(pattern, password))
        for pattern in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]")
    )
    if len(password) < 12 or checks < 3:
        return "Use at least 12 characters with three character types."
    return None


def uploaded_image() -> bytes:
    image = request.files.get("image")
    if image is None or not image.filename:
        raise ValueError("Choose an image first.")
    extension = image.filename.rsplit(".", 1)[-1].lower() if "." in image.filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Upload a PNG, JPG, or JPEG image.")
    data = image.read()
    if not data:
        raise ValueError("The uploaded image is empty.")
    return data


@app.errorhandler(413)
def request_too_large(_error):
    return error_response("Image is too large. Maximum size is 12 MB.", 413)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/encrypt")
def encrypt_page():
    return render_template("encrypt.html")


@app.get("/decrypt")
def decrypt_page():
    return render_template("decrypt.html")


@app.post("/api/encrypt")
def encrypt_api():
    try:
        image_data = uploaded_image()
        message = request.form.get("message", "")
        password = request.form.get("password", "")
        confirmation = request.form.get("confirm_password", "")
        if not message.strip():
            return error_response("Enter a secret message.")
        if len(message.encode("utf-8")) > app.config["MAX_MESSAGE_BYTES"]:
            return error_response("Message is too large. Keep it under 256 KB.")
        password_problem = password_error(password)
        if password_problem:
            return error_response(password_problem)
        if password != confirmation:
            return error_response("Passwords do not match.")

        salt, nonce, ciphertext = encrypt_message(message, password)
        encrypted_png = embed_payload(image_data, salt + nonce + ciphertext)
        return send_file(
            BytesIO(encrypted_png),
            mimetype="image/png",
            as_attachment=True,
            download_name="securepixel-encrypted.png",
        )
    except (ValueError, SteganographyError) as exc:
        return error_response(str(exc))
    except Exception:
        app.logger.exception("Encryption request failed")
        return error_response("Unable to process this image right now.", 500)


@app.post("/api/decrypt")
def decrypt_api():
    try:
        image_data = uploaded_image()
        password = request.form.get("password", "")
        password_problem = password_error(password)
        if password_problem:
            return error_response(password_problem)
        try:
            payload = extract_payload(image_data)
        except SteganographyError as exc:
            message = str(exc)
            if message == "No valid encrypted message found.":
                return error_response(message, 422)
            return error_response("Incorrect password or corrupted encrypted image.", 422)

        if len(payload) <= SALT_SIZE + NONCE_SIZE:
            return error_response("Incorrect password or corrupted encrypted image.", 422)
        try:
            message = decrypt_message(
                payload[SALT_SIZE + NONCE_SIZE :],
                password,
                payload[:SALT_SIZE],
                payload[SALT_SIZE : SALT_SIZE + NONCE_SIZE],
            )
        except (InvalidTag, ValueError, UnicodeDecodeError):
            return error_response("Incorrect password or corrupted encrypted image.", 422)
        return jsonify({"success": True, "message": message})
    except (ValueError, SteganographyError) as exc:
        return error_response(str(exc))
    except Exception:
        app.logger.exception("Decryption request failed")
        return error_response("Unable to process this image right now.", 500)


if __name__ == "__main__":
    app.run(debug=True)
