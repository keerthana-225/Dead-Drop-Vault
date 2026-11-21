from flask import Flask, request, jsonify, send_from_directory
import sqlite3, secrets, hashlib, time, os

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, 'vault.db')
app = Flask(__name__, static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024  # encrypted payload cap


def db():
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('''CREATE TABLE IF NOT EXISTS drops (
        token_hash TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        expires_at INTEGER NOT NULL,
        created_at INTEGER NOT NULL,
        claimed INTEGER NOT NULL DEFAULT 0
    )''')
    return conn


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


@app.get('/')
def home():
    return send_from_directory(app.static_folder, 'index.html')


@app.post('/api/drops')
def create_drop():
    data = request.get_json(silent=True) or {}
    payload = data.get('payload')
    ttl = data.get('ttl')
    if not isinstance(payload, str) or not payload or len(payload) > 10_000_000:
        return jsonify(error='Missing or oversized encrypted payload.'), 400
    if ttl not in (300, 3600, 86400, 604800):
        return jsonify(error='Invalid expiration selection.'), 400
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    conn = db()
    try:
        conn.execute('INSERT INTO drops(token_hash,payload,expires_at,created_at) VALUES(?,?,?,?)',
                    (token_digest(token), payload, now + ttl, now))
    finally:
        conn.close()
    return jsonify(token=token, expiresAt=now + ttl), 201


@app.post('/api/drops/<token>/claim')
def claim_drop(token):
    digest = token_digest(token)
    conn = db()
    try:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT payload,expires_at,claimed FROM drops WHERE token_hash=?', (digest,)).fetchone()
        now = int(time.time())
        if row is None:
            conn.execute('COMMIT')
            return jsonify(error='This drop is unavailable, expired, or already claimed.'), 404
        if row['expires_at'] <= now or row['claimed']:
            conn.execute('DELETE FROM drops WHERE token_hash=?', (digest,))
            conn.execute('COMMIT')
            return jsonify(error='This drop is unavailable, expired, or already claimed.'), 410
        # Lock + claim + remove payload within the same transaction; only one request wins.
        payload = row['payload']
        conn.execute('UPDATE drops SET claimed=1 WHERE token_hash=?', (digest,))
        conn.execute('DELETE FROM drops WHERE token_hash=?', (digest,))
        conn.execute('COMMIT')
        return jsonify(payload=payload)
    except Exception:
        try: conn.execute('ROLLBACK')
        except Exception: pass
        return jsonify(error='Unable to claim this drop. Try again.'), 500
    finally:
        conn.close()


@app.delete('/api/drops/<token>')
def revoke_drop(token):
    conn = db()
    try:
        cur = conn.execute('DELETE FROM drops WHERE token_hash=?', (token_digest(token),))
        return jsonify(revoked=cur.rowcount > 0)
    finally:
        conn.close()


@app.get('/health')
def health():
    return jsonify(status='ok')


if __name__ == '__main__':
    print('Dead-Drop Vault is starting at http://127.0.0.1:5000')
    app.run(host='127.0.0.1', port=5000, debug=False)
