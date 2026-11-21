# Dead-Drop Vault (Local MVP)

A local-first demo for one-time encrypted text/file drops. Encryption and decryption happen in the browser with Web Crypto AES-GCM. The Flask server stores only the ciphertext, a SHA-256 token digest, and expiration metadata. The decryption key is carried in the URL fragment (`#`), which browsers do not send in HTTP requests.


## Features
- Text secret and file drop (up to 8 MB original file size)
- Browser-side AES-GCM encryption with a fresh key and IV per drop
- One-time retrieval with a SQLite transaction (`BEGIN IMMEDIATE`)
- Expiration: 5 minutes, 1 hour, 24 hours, 7 days
- Sender revocation before claim
- No accounts needed; SQLite DB created automatically

## Run locally (VS Code on Windows)
1. Extract this ZIP into a folder, e.g. `Dead-Drop-Vault`.
2. Open the folder in VS Code (`File > Open Folder`).
3. Open Terminal > New Terminal.
4. Run:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   py app.py
   ```
   If PowerShell blocks activation, use `cmd` terminal and activate with `\.venv\Scripts\activate.bat`, or run `py -m pip install -r requirements.txt` and `py app.py` without activating.
5. Open **http://127.0.0.1:5000**.

## Try it
- Create a text secret or choose a file.
- Pick an expiration.
- Click Encrypt & create link, then Copy.
- Open the link in a private/incognito window (same computer is fine for this local demo).
- Claim it once. The link should fail on a second claim.
- Create another drop and test Revoke before claiming.


## Security caveats (prototype)
- This is a learning/demo build, not audited production software.
- A recipient can copy, screenshot, or save plaintext after decrypting it.
- Local demo runs on HTTP localhost. Do not deploy publicly as-is.
- SQLite deletion is logical; secure forensic erasure is not guaranteed. WAL files, backups, OS storage and SSD wear-leveling may retain data.
- Token hash is SHA-256; tokens are high entropy random values. This is appropriate for random bearer tokens, not user passwords.
- There is no authentication for revoke; anyone holding the drop token can revoke. In this MVP the sender has that token from the generated URL.
- Do not use real production credentials in this demo.

## API
- `POST /api/drops` JSON `{ "payload": "<encrypted JSON string>", "ttl": 300|3600|86400|604800 }`
- `POST /api/drops/<token>/claim` atomically consumes the drop and returns its ciphertext payload
- `DELETE /api/drops/<token>` revokes the drop
- `GET /health` health check

