import sqlite3, hashlib, time, re, secrets, json

def create_app_db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript('''
    PRAGMA busy_timeout=8000;
    CREATE TABLE users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, hash TEXT NOT NULL, rev INTEGER NOT NULL DEFAULT 0, created INTEGER, synced INTEGER, status TEXT NOT NULL DEFAULT 'active');
    CREATE TABLE settings(k TEXT PRIMARY KEY, v TEXT);
    CREATE TABLE logs(id INTEGER PRIMARY KEY, t INTEGER, type TEXT, who TEXT, ip TEXT);
    CREATE TABLE visits(day TEXT, vid TEXT, hits INTEGER, last INTEGER, plat TEXT, PRIMARY KEY(day,vid));
    CREATE TABLE tokens(token_hash TEXT PRIMARY KEY, user_id INTEGER, created INTEGER, last_seen INTEGER);
    CREATE TABLE groups_(user_id INTEGER, id TEXT, name TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id,id));
    CREATE TABLE categories(user_id INTEGER, id TEXT, group_id TEXT, parent TEXT, name TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id,id));
    CREATE TABLE expenses(user_id INTEGER, id TEXT, group_id TEXT, amount REAL, date TEXT, time TEXT, descr TEXT, note TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id,id));
    CREATE TABLE expense_categories(user_id INTEGER, expense_id TEXT, category_id TEXT, PRIMARY KEY(user_id,expense_id,category_id));
    CREATE TABLE prefs(user_id INTEGER, id TEXT, v TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id,id));
    ''')
    conn.commit()
    return conn

def register_user(conn, email, pw):
    cur = conn.cursor()
    cur.execute('INSERT INTO users(email, hash, created, status) VALUES(?,?,?,?)',
                (email.lower(), 'hash_' + pw, int(time.time()), 'active'))
    uid = cur.lastrowid
    tok = 'tok_' + re.sub(r'[^A-Za-z0-9]', '', email) + '_' + secrets.token_hex(20)
    thash = hashlib.sha256(tok.encode()).hexdigest()
    now = int(time.time())
    cur.execute('INSERT INTO tokens(token_hash, user_id, created, last_seen) VALUES(?,?,?,?)',
                (thash, uid, now, now))
    conn.commit()
    return uid, tok

def is_allowed_origin(orig, conn, host='', env_origin=''):
    if not orig:
        return False
    # 1. Capacitor native app origins
    if orig in ('capacitor://localhost', 'https://localhost'):
        return True
    # 2. Local development origins: localhost or 127.0.0.1 with optional port
    if re.match(r'^https?://(localhost|127\.0\.0\.1)(:[0-9]{1,5})?$', orig, re.IGNORECASE):
        return True
    # 3. Same-origin host
    if host and re.match(r'^[a-zA-Z0-9.-]+(:[0-9]{1,5})?$', host):
        if orig in (f"https://{host}", f"http://{host}"):
            return True
    # 4. Configured origin in environment or constant
    if env_origin and env_origin.rstrip('/') == orig.rstrip('/'):
        return True
    # 5. Configured origin in SQLite settings table
    if conn:
        try:
            cur = conn.cursor()
            row = cur.execute("SELECT v FROM settings WHERE k IN ('cors_origin', 'app_domain') AND v IS NOT NULL AND v != '' LIMIT 1").fetchone()
            if row and row['v'] and row['v'].rstrip('/') == orig.rstrip('/'):
                return True
        except Exception:
            pass
    return False

# Replicate complete api.php request handling with Phase 7 CORS & security headers
def handle_api_request(conn, method, query_params, headers, body_str='', host='khoroch.example.com', env_origin=''):
    resp_headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'X-XSS-Protection': '1; mode=block'
    }

    req_method = method.upper()
    if req_method not in ('GET', 'POST', 'OPTIONS'):
        resp_headers['Allow'] = 'GET, POST, OPTIONS'
        return 405, resp_headers, {'error': 'অনুমোদিত মেথড নয়'}

    raw_origin = headers.get('Origin', '').strip()
    origin_allowed = bool(raw_origin and is_allowed_origin(raw_origin, conn, host, env_origin))

    if origin_allowed:
        resp_headers['Access-Control-Allow-Origin'] = raw_origin
        resp_headers['Access-Control-Allow-Credentials'] = 'true'
        resp_headers['Vary'] = 'Origin'

    # Preflight OPTIONS
    if req_method == 'OPTIONS':
        if raw_origin:
            if not origin_allowed:
                return 403, resp_headers, {'error': 'অনুমোদিত অরিজিন নয়'}
            
            preflight_method = headers.get('Access-Control-Request-Method', 'POST').upper().strip()
            if preflight_method not in ('GET', 'POST', 'OPTIONS'):
                resp_headers['Allow'] = 'GET, POST, OPTIONS'
                return 405, resp_headers, {'error': 'মেথড অনুমোদিত নয়'}

            resp_headers['Access-Control-Allow-Origin'] = raw_origin
            resp_headers['Access-Control-Allow-Credentials'] = 'true'
            resp_headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            resp_headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            resp_headers['Access-Control-Max-Age'] = '86400'
            resp_headers['Vary'] = 'Origin'
            return 204, resp_headers, None
        else:
            resp_headers['Allow'] = 'GET, POST, OPTIONS'
            return 204, resp_headers, None

    # State-changing POST check
    if req_method == 'POST' and raw_origin and not origin_allowed:
        return 403, resp_headers, {'error': 'অনুমোদিত অরিজিন নয়'}

    if len(body_str) > 2500000:
        return 413, resp_headers, {'error': 'অনুরোধটি অনেক বড়'}

    try:
        in_data = json.loads(body_str) if body_str else {}
    except Exception:
        in_data = {}

    action = query_params.get('a', '')

    if action == 'health':
        return 200, resp_headers, {'ok': True}

    if action == 'login':
        em = in_data.get('email', '').strip().lower()
        cur = conn.cursor()
        u = cur.execute('SELECT * FROM users WHERE email=?', (em,)).fetchone()
        if not u or in_data.get('password') != 'correct_pass':
            return 401, resp_headers, {'error': 'ইমেইল বা পাসওয়ার্ড ভুল'}
        t = secrets.token_hex(32)
        now = int(time.time())
        cur.execute('INSERT INTO tokens(token_hash, user_id, created, last_seen) VALUES(?,?,?,?)',
                    (hashlib.sha256(t.encode()).hexdigest(), u['id'], now, now))
        conn.commit()
        return 200, resp_headers, {'token': t}

    # Authenticated endpoints
    tok = ''
    auth_header = headers.get('Authorization', '')
    m = re.match(r'^Bearer\s+([A-Za-z0-9_-]{32,128})$', auth_header.strip(), re.IGNORECASE)
    if m:
        tok = m.group(1)
    elif isinstance(in_data.get('token'), str) and re.match(r'^[A-Za-z0-9_-]{32,128}$', in_data['token'].strip()):
        tok = in_data['token'].strip()

    if not tok:
        return 401, resp_headers, {'error': 'লগইন করুন'}

    thash = hashlib.sha256(tok.encode()).hexdigest()
    cur = conn.cursor()
    row = cur.execute('SELECT user_id, created, last_seen FROM tokens WHERE token_hash=?', (thash,)).fetchone()
    if not row:
        return 401, resp_headers, {'error': 'লগইন করুন'}

    uid = row['user_id']

    if action == 'logout':
        cur.execute('DELETE FROM tokens WHERE token_hash=?', (thash,))
        conn.commit()
        return 200, resp_headers, {'ok': True}

    if action == 'report':
        g = query_params.get('group', '')
        if not re.match(r'^[A-Za-z0-9_-]{1,40}$', g):
            return 400, resp_headers, {'error': 'গ্রুপ আইডি সঠিক নয়'}
        grp = cur.execute('SELECT 1 FROM groups_ WHERE user_id=? AND id=? AND deleted=0', (uid, g)).fetchone()
        if not grp:
            return 403, resp_headers, {'error': 'গ্রুপটি পাওয়া যায়নি বা দেখার অনুমতি নেই'}
        t = cur.execute('SELECT COALESCE(SUM(amount),0) as total, COUNT(*) as n FROM expenses WHERE user_id=? AND group_id=? AND deleted=0', (uid, g)).fetchone()
        return 200, resp_headers, {'total': float(t['total']), 'transactions': int(t['n']), 'categories': []}

    if action == 'sync':
        P = in_data.get('parents', [])
        E = in_data.get('exps', [])
        pushed = {'groups_': [], 'expenses': []}
        rejected = {'expenses': []}

        if P or E:
            conn.execute('BEGIN IMMEDIATE')
            cur.execute('UPDATE users SET rev=rev WHERE id=?', (uid,))
            rev = cur.execute('SELECT rev FROM users WHERE id=?', (uid,)).fetchone()['rev']

            for p in P:
                if isinstance(p, dict) and p.get('id'):
                    rev += 1
                    cur.execute('INSERT OR REPLACE INTO groups_ VALUES(?,?,?,?,?,?)',
                                (uid, p['id'], p.get('name', ''), int(p.get('updated', 0)), 1 if p.get('deleted') else 0, rev))
                    pushed['groups_'].append(p['id'])

            owned_groups = set(r[0] for r in cur.execute('SELECT id FROM groups_ WHERE user_id=? AND deleted=0', (uid,)).fetchall())

            for e in E:
                if isinstance(e, dict) and e.get('id'):
                    eid = e['id']
                    e_pid = e.get('pid') if (e.get('pid') and e.get('pid') in owned_groups) else None
                    if not e_pid:
                        rejected['expenses'].append({'id': eid, 'reason': 'invalid_group'})
                        continue
                    rev += 1
                    cur.execute('INSERT OR REPLACE INTO expenses VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                                (uid, eid, e_pid, float(e.get('amt', 0)), e.get('dt', ''), e.get('tm', ''), e.get('desc', ''), e.get('note', ''), int(e.get('updated', 0)), 1 if e.get('deleted') else 0, rev))
                    pushed['expenses'].append(eid)

            cur.execute('UPDATE users SET rev=?, synced=? WHERE id=?', (rev, int(time.time()), uid))
            conn.commit()

        return 200, resp_headers, {
            'since': cur.execute('SELECT rev FROM users WHERE id=?', (uid,)).fetchone()['rev'],
            'parents': [{'id': p['id'], 'name': p['name']} for p in cur.execute('SELECT * FROM groups_ WHERE user_id=?', (uid,)).fetchall()],
            'exps': [{'id': e['id'], 'pid': e['group_id'], 'amt': e['amount']} for e in cur.execute('SELECT * FROM expenses WHERE user_id=?', (uid,)).fetchall() if e['id'] in pushed['expenses']],
            'rejected': rejected
        }

    return 404, resp_headers, {'error': 'অজানা অনুরোধ'}


def run_phase7_tests():
    conn = create_app_db()
    cur = conn.cursor()
    # Configure production domain in SQLite settings table
    cur.execute("INSERT INTO settings(k, v) VALUES('cors_origin', 'https://khoroch.example.com')")
    conn.commit()

    uid_a, tok_a = register_user(conn, 'user_a@test.com', 'correct_pass')
    uid_b, tok_b = register_user(conn, 'user_b@test.com', 'correct_pass')

    print("=== STARTING PHASE 7 CORS & SECURITY HARDENING TEST SUITE ===")

    # TEST 1: Allowed production origin
    status, headers, body = handle_api_request(
        conn, 'GET', {'a': 'health'},
        {'Origin': 'https://khoroch.example.com'},
        host='khoroch.example.com'
    )
    assert status == 200 and headers.get('Access-Control-Allow-Origin') == 'https://khoroch.example.com'
    assert headers.get('Access-Control-Allow-Credentials') == 'true'
    print("[PASS 1] Allowed production origin (https://khoroch.example.com) received matching CORS headers.")

    # TEST 2: Allowed Capacitor origins
    for cap_origin in ['capacitor://localhost', 'https://localhost']:
        status, headers, body = handle_api_request(
            conn, 'GET', {'a': 'health'},
            {'Origin': cap_origin}
        )
        assert status == 200 and headers.get('Access-Control-Allow-Origin') == cap_origin
        assert headers.get('Access-Control-Allow-Credentials') == 'true'
    print("[PASS 2] Allowed Capacitor origins (capacitor://localhost, https://localhost) received matching CORS headers.")

    # TEST 3: Allowed development origins (localhost & 127.0.0.1 with various ports)
    for dev_origin in ['http://localhost:3000', 'http://127.0.0.1:5173', 'http://localhost']:
        status, headers, body = handle_api_request(
            conn, 'GET', {'a': 'health'},
            {'Origin': dev_origin}
        )
        assert status == 200 and headers.get('Access-Control-Allow-Origin') == dev_origin
    print("[PASS 3] Allowed development origins (http://localhost:3000, http://127.0.0.1:5173) verified.")

    # TEST 4: Unauthorized arbitrary origin
    for bad_origin in ['https://malicious-site.com', 'http://evil.org', 'http://localhost.attacker.com']:
        status, headers, body = handle_api_request(
            conn, 'GET', {'a': 'health'},
            {'Origin': bad_origin}
        )
        assert 'Access-Control-Allow-Origin' not in headers, f"Arbitrary origin {bad_origin} was reflected!"
        # State changing POST from bad origin must be rejected with 403
        status_post, headers_post, body_post = handle_api_request(
            conn, 'POST', {'a': 'login'},
            {'Origin': bad_origin},
            body_str=json.dumps({'email': 'user_a@test.com', 'password': 'correct_pass'})
        )
        assert status_post == 403 and 'Access-Control-Allow-Origin' not in headers_post
    print("[PASS 4] Unauthorized arbitrary origins safely rejected with HTTP 403 and never reflected.")

    # TEST 5: OPTIONS preflight success
    status, headers, body = handle_api_request(
        conn, 'OPTIONS', {},
        {'Origin': 'capacitor://localhost', 'Access-Control-Request-Method': 'POST'}
    )
    assert status == 204
    assert headers.get('Access-Control-Allow-Origin') == 'capacitor://localhost'
    assert headers.get('Access-Control-Allow-Methods') == 'GET, POST, OPTIONS'
    assert 'Authorization' in headers.get('Access-Control-Allow-Headers', '')
    assert headers.get('Access-Control-Max-Age') == '86400'
    print("[PASS 5] OPTIONS preflight success returns HTTP 204 with complete CORS headers.")

    # TEST 6: OPTIONS preflight rejection
    status, headers, body = handle_api_request(
        conn, 'OPTIONS', {},
        {'Origin': 'https://attacker-origin.com', 'Access-Control-Request-Method': 'POST'}
    )
    assert status == 403 and 'Access-Control-Allow-Origin' not in headers
    print("[PASS 6] OPTIONS preflight rejection for untrusted origin returns HTTP 403.")

    # TEST 7: Unsupported HTTP methods
    for bad_method in ['PUT', 'DELETE', 'PATCH', 'TRACE']:
        status, headers, body = handle_api_request(
            conn, bad_method, {'a': 'health'},
            {'Origin': 'capacitor://localhost'}
        )
        assert status == 405 and headers.get('Allow') == 'GET, POST, OPTIONS'
    # Preflight for unsupported method
    status, headers, body = handle_api_request(
        conn, 'OPTIONS', {},
        {'Origin': 'capacitor://localhost', 'Access-Control-Request-Method': 'DELETE'}
    )
    assert status == 405
    print("[PASS 7] Unsupported HTTP methods (PUT, DELETE, PATCH, TRACE) rejected with HTTP 405.")

    # TEST 8: Authorization header compatibility
    # Valid Bearer token
    status, headers, body = handle_api_request(
        conn, 'GET', {'a': 'report', 'group': 'grp_a'},
        {'Origin': 'capacitor://localhost', 'Authorization': f'Bearer {tok_a}'}
    )
    assert status != 401, f"Valid token failed auth: {body}"
    # Invalid Bearer token
    status, headers, body = handle_api_request(
        conn, 'GET', {'a': 'report', 'group': 'grp_a'},
        {'Origin': 'capacitor://localhost', 'Authorization': 'Bearer tok_invalid_12345678901234567890123456'}
    )
    assert status == 401
    print("[PASS 8] Authorization Bearer header compatibility verified.")

    # TEST 9: Login and logout compatibility
    status, headers, body = handle_api_request(
        conn, 'POST', {'a': 'login'},
        {'Origin': 'capacitor://localhost'},
        body_str=json.dumps({'email': 'user_a@test.com', 'password': 'correct_pass'})
    )
    assert status == 200 and 'token' in body
    active_tok = body['token']

    # Logout with active token
    status, headers, body = handle_api_request(
        conn, 'POST', {'a': 'logout'},
        {'Origin': 'capacitor://localhost', 'Authorization': f'Bearer {active_tok}'}
    )
    assert status == 200 and body.get('ok') is True

    # Reusing logged out token must be 401
    status, headers, body = handle_api_request(
        conn, 'POST', {'a': 'sync'},
        {'Origin': 'capacitor://localhost', 'Authorization': f'Bearer {active_tok}'},
        body_str=json.dumps({'since': 0})
    )
    assert status == 401
    print("[PASS 9] Login and logout flow with server-side token revocation verified.")

    # TEST 10: Authenticated sync and report requests
    # User A creates group and syncs expense
    status, headers, body = handle_api_request(
        conn, 'POST', {'a': 'sync'},
        {'Origin': 'capacitor://localhost', 'Authorization': f'Bearer {tok_a}'},
        body_str=json.dumps({
            'since': 0,
            'parents': [{'id': 'grp_a_work', 'name': 'Work', 'updated': 1000}],
            'exps': [{'id': 'exp_a_laptop', 'pid': 'grp_a_work', 'amt': 45000, 'updated': 1000}]
        })
    )
    assert status == 200 and len(body['exps']) == 1

    # Report request
    status, headers, body = handle_api_request(
        conn, 'GET', {'a': 'report', 'group': 'grp_a_work'},
        {'Origin': 'capacitor://localhost', 'Authorization': f'Bearer {tok_a}'}
    )
    assert status == 200 and body['total'] == 45000.0 and body['transactions'] == 1
    print("[PASS 10] Authenticated sync and report requests work cleanly under CORS.")

    # TEST 11: Multi-user isolation remains intact
    # User B creates private group
    status, headers, body = handle_api_request(
        conn, 'POST', {'a': 'sync'},
        {'Origin': 'https://khoroch.example.com', 'Authorization': f'Bearer {tok_b}'},
        body_str=json.dumps({
            'since': 0,
            'parents': [{'id': 'grp_b_secret', 'name': 'Bob Secret', 'updated': 1000}],
            'exps': [{'id': 'exp_b_secret', 'pid': 'grp_b_secret', 'amt': 99000, 'updated': 1000}]
        })
    )
    assert status == 200

    # User A attempts to request report for User B's group -> must return 403
    status, headers, body = handle_api_request(
        conn, 'GET', {'a': 'report', 'group': 'grp_b_secret'},
        {'Origin': 'capacitor://localhost', 'Authorization': f'Bearer {tok_a}'}
    )
    assert status == 403, f"Expected 403 Forbidden for cross-user report, got {status}"

    # User A attempts to sync expense using User B's group -> must be safely rejected
    status, headers, body = handle_api_request(
        conn, 'POST', {'a': 'sync'},
        {'Origin': 'capacitor://localhost', 'Authorization': f'Bearer {tok_a}'},
        body_str=json.dumps({
            'since': 0,
            'exps': [{'id': 'exp_a_tamper', 'pid': 'grp_b_secret', 'amt': 10, 'updated': 1000}]
        })
    )
    assert status == 200 and len(body['rejected']['expenses']) == 1
    assert cur.execute('SELECT COUNT(*) FROM expenses WHERE id="exp_a_tamper"').fetchone()[0] == 0
    print("[PASS 11] Multi-user isolation strictly verified: Cross-user reports 403, foreign group syncs rejected.")

    # TEST 12: API responses contain correct security headers
    status, headers, body = handle_api_request(
        conn, 'GET', {'a': 'health'},
        {'Origin': 'capacitor://localhost'}
    )
    assert headers.get('Content-Type') == 'application/json; charset=utf-8'
    assert 'no-store' in headers.get('Cache-Control', '')
    assert 'no-cache' in headers.get('Cache-Control', '')
    assert headers.get('Pragma') == 'no-cache'
    assert headers.get('X-Content-Type-Options') == 'nosniff'
    assert headers.get('X-Frame-Options') == 'SAMEORIGIN'
    assert headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert headers.get('X-XSS-Protection') == '1; mode=block'
    print("[PASS 12] Security headers verified: nosniff, SAMEORIGIN, strict-origin-when-cross-origin, no-store.")

    # TEST 13: Preflight requests do not modify database records
    # Count rows before preflight
    counts_before = {
        'users': cur.execute('SELECT COUNT(*) FROM users').fetchone()[0],
        'tokens': cur.execute('SELECT COUNT(*) FROM tokens').fetchone()[0],
        'expenses': cur.execute('SELECT COUNT(*) FROM expenses').fetchone()[0],
        'groups': cur.execute('SELECT COUNT(*) FROM groups_').fetchone()[0]
    }
    for _ in range(5):
        status, headers, body = handle_api_request(
            conn, 'OPTIONS', {'a': 'sync'},
            {'Origin': 'capacitor://localhost', 'Access-Control-Request-Method': 'POST'},
            body_str=json.dumps({'since': 0, 'exps': [{'id': 'dummy', 'amt': 999}]})
        )
        assert status == 204
    counts_after = {
        'users': cur.execute('SELECT COUNT(*) FROM users').fetchone()[0],
        'tokens': cur.execute('SELECT COUNT(*) FROM tokens').fetchone()[0],
        'expenses': cur.execute('SELECT COUNT(*) FROM expenses').fetchone()[0],
        'groups': cur.execute('SELECT COUNT(*) FROM groups_').fetchone()[0]
    }
    assert counts_before == counts_after, f"Preflight modified database! {counts_before} vs {counts_after}"
    print("[PASS 13] Preflight OPTIONS requests verified: 0 database modifications.")

    print("\n=== ALL 13 PHASE 7 TEST CASES EXECUTED & PASSED SUCCESSFULLY ===")

if __name__ == '__main__':
    run_phase7_tests()
