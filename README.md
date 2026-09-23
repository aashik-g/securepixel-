# SecurePixel

SecurePixel is a local Flask web application that encrypts a secret message and hides the resulting binary payload inside an image. A recipient needs both the generated image and the correct password to recover the message.

> Hide it. Encrypt it. Share it securely.

## How It Works

1. The sender chooses an image and enters a message and password.
2. A cryptographically secure random 16-byte salt and 12-byte nonce are generated.
3. PBKDF2-HMAC-SHA256 derives a 256-bit AES key from the password and salt using 600,000 iterations.
4. AES-256-GCM encrypts and authenticates the UTF-8 message. The authentication tag is included in the AES-GCM ciphertext returned by the library.
5. SecurePixel stores a versioned binary payload in RGB least-significant bits:

   `SPX1 | 4-byte payload length | salt | nonce | AES-GCM ciphertext + tag`

6. The image is written as a lossless PNG and returned directly as a download.
7. Decryption extracts and validates the payload, derives the same key, and only releases the message after AES-GCM authentication succeeds.

The original plaintext message is never intentionally written to the image, database, URL, cookie, local storage, or a server-side file.

## Installation

Python 3.11 or newer is recommended.

```powershell
cd d:\project_2
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

```powershell
python app.py
```

Open <http://127.0.0.1:5000> in a browser.

## Project Structure

```text
securepixel/
├── app.py                 Flask pages and JSON/file API routes
├── crypto_utils.py        PBKDF2 and AES-256-GCM helpers
├── steganography.py       Versioned RGB LSB PNG payload format
├── requirements.txt
├── README.md
├── templates/
│   ├── index.html
│   ├── encrypt.html
│   └── decrypt.html
├── static/
│   ├── css/style.css
│   └── js/script.js
└── temp/.gitkeep
```

## Security Considerations

- AES-256-GCM provides confidentiality and tamper detection. A wrong password, modified payload, or corrupted image produces the same generic decryption error.
- PBKDF2-HMAC-SHA256 uses a unique random salt for every encryption operation. Passwords are never stored.
- AES-GCM uses a fresh cryptographically secure nonce for every encryption operation.
- Upload size is limited to 12 MB. Image content is decoded and verified with Pillow rather than trusting only the filename extension.
- Uploaded images are held in memory for processing and are not saved by the application. The generated PNG is also held in memory and streamed to the client.
- The frontend never receives the encryption key and does not place messages or passwords in local storage, cookies, URLs, or HTML.
- The payload contains a magic header and version marker (`SPX1`) so the format can evolve.
- Passwords should be shared through a separate trusted channel from the encrypted image.

## Why PNG?

LSB steganography changes individual pixel channel bits. PNG preserves those values exactly, while JPEG compression can rewrite pixel data and destroy hidden bits. JPG and JPEG uploads are accepted for convenience but are converted to PNG before embedding.

## Limitations

- A steganographic image is not an anonymity guarantee. Statistical analysis may identify that an image has been modified.
- The output image may be larger than the source and its capacity depends on width, height, and RGB channels.
- Resizing, recompressing, filtering, or editing the output image can destroy the hidden payload.
- The password is not recoverable. If it is forgotten, the message cannot be decrypted.
- This initial version has no database, accounts, rate limiting, or external key exchange. It is intended for local/private use and educational cybersecurity work.

## API Routes

- `GET /` home page
- `GET /encrypt` encryption page
- `GET /decrypt` decryption page
- `POST /api/encrypt` multipart form with `image`, `message`, `password`, and `confirm_password`; returns a PNG download
- `POST /api/decrypt` multipart form with `image` and `password`; returns JSON containing the decrypted `message` on success
