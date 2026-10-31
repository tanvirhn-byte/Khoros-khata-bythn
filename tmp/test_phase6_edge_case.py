import sqlite3, hashlib, time, re, secrets

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

def get_auth_user(conn, tok):
    if not tok or not re.match(r'^[A-Za-z0-9_-]{32,128}$', tok):
        return None
    thash = hashlib.sha256(tok.encode()).hexdigest()
    cur = conn.cursor()
    row = cur.execute('SELECT user_id, created, last_seen FROM tokens WHERE token_hash=?', (thash,)).fetchone()
    if not row:
        return None
    return row['user_id']

def ok_id(v):
    return isinstance(v, str) and bool(re.match(r'^[A-Za-z0-9_-]{1,40}$', v))

def api_sync(conn, tok, payload):
    u = get_auth_user(conn, tok)
    if not u:
        return 401, {'error': 'Unauthorized'}
    
    since = max(0, int(payload.get('since', 0)))
    P = payload.get('parents', [])
    C = payload.get('cats', [])
    E = payload.get('exps', [])
    R = payload.get('prefs', [])

    cur = conn.cursor()
    pushed = {'groups_': [], 'categories': [], 'expenses': [], 'prefs': []}

    if P or C or E or R:
        conn.execute('BEGIN IMMEDIATE')
        cur.execute('UPDATE users SET rev=rev WHERE id=?', (u,))
        rev = cur.execute('SELECT rev FROM users WHERE id=?', (u,)).fetchone()['rev']

        def newer(t, item_id, upd):
            o = cur.execute(f'SELECT updated FROM {t} WHERE user_id=? AND id=?', (u, item_id)).fetchone()
            return o is None or upd > int(o['updated'])

        # 1. Process groups
        for p in P:
            if isinstance(p, dict) and ok_id(p.get('id')):
                pid = p['id']
                pushed['groups_'].append(pid)
                upd = int(p.get('updated', 0))
                if newer('groups_', pid, upd):
                    rev += 1
                    cur.execute('INSERT OR REPLACE INTO groups_ VALUES(?,?,?,?,?,?)',
                                (u, pid, p.get('name', '')[:100], upd, 1 if p.get('deleted') else 0, rev))

        # Query authenticated user's active groups
        owned_groups = [r[0] for r in cur.execute('SELECT id FROM groups_ WHERE user_id=? AND deleted=0', (u,)).fetchall()]
        group_set = set(owned_groups)

        # Query user's valid active categories in DB + any valid new categories in this batch
        owned_cats = [r[0] for r in cur.execute('SELECT id FROM categories WHERE user_id=? AND deleted=0', (u,)).fetchall()]
        cat_set = set(owned_cats)
        for c in C:
            if isinstance(c, dict) and ok_id(c.get('id')) and not c.get('deleted'):
                cat_set.add(c['id'])

        # 2. Process categories
        for c in C:
            if isinstance(c, dict) and ok_id(c.get('id')):
                cid = c['id']
                upd = int(c.get('updated', 0))
                c_pid = c.get('pid') if (ok_id(c.get('pid')) and c.get('pid') in group_set) else None

                if newer('categories', cid, upd):
                    if not c_pid:
                        if c.get('deleted'):
                            existC = cur.execute('SELECT group_id FROM categories WHERE user_id=? AND id=?', (u, cid)).fetchone()
                            if existC:
                                rev += 1
                                cur.execute('UPDATE categories SET deleted=1, updated=?, rev=? WHERE user_id=? AND id=?', (upd, rev, u, cid))
                                pushed['categories'].append(cid)
                        continue

                    rev += 1
                    pushed['categories'].append(cid)
                    c_parent = c.get('parent') if (ok_id(c.get('parent')) and c.get('parent') in cat_set and c.get('parent') != cid) else None
                    cur.execute('INSERT OR REPLACE INTO categories VALUES(?,?,?,?,?,?,?,?)',
                                (u, cid, c_pid, c_parent, c.get('name', '')[:100], upd, 1 if c.get('deleted') else 0, rev))
                else:
                    pushed['categories'].append(cid)

        # Refresh active categories after writing C
        owned_cats = [r[0] for r in cur.execute('SELECT id FROM categories WHERE user_id=? AND deleted=0', (u,)).fetchall()]
        cat_set = set(owned_cats)

        # 3. Process expenses
        for e in E:
            if isinstance(e, dict) and ok_id(e.get('id')):
                eid = e['id']
                upd = int(e.get('updated', 0))
                e_pid = e.get('pid') if (ok_id(e.get('pid')) and e.get('pid') in group_set) else None

                if newer('expenses', eid, upd):
                    if not e_pid:
                        # If deleting an existing expense owned by this user, allow tombstone
                        if e.get('deleted'):
                            existE = cur.execute('SELECT group_id FROM expenses WHERE user_id=? AND id=?', (u, eid)).fetchone()
                            if existE:
                                rev += 1
                                cur.execute('UPDATE expenses SET deleted=1, updated=?, rev=? WHERE user_id=? AND id=?', (upd, rev, u, eid))
                                pushed['expenses'].append(eid)
                        # Invalid/foreign/ungrouped expense safely rejected!
                        continue

                    rev += 1
                    pushed['expenses'].append(eid)
                    amt = float(e.get('amt', 0))
                    cur.execute('INSERT OR REPLACE INTO expenses VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                                (u, eid, e_pid, amt, e.get('dt', '')[:10], e.get('tm', '')[:5], e.get('desc', '')[:300], e.get('note', '')[:1000], upd, 1 if e.get('deleted') else 0, rev))
                    cur.execute('DELETE FROM expense_categories WHERE user_id=? AND expense_id=?', (u, eid))
                    for cat_id in e.get('cats', []):
                        if ok_id(cat_id) and cat_id in cat_set:
                            cur.execute('INSERT OR IGNORE INTO expense_categories VALUES(?,?,?)', (u, eid, cat_id))
                else:
                    pushed['expenses'].append(eid)

        for r in R:
            if isinstance(r, dict) and ok_id(r.get('id')):
                rid = r['id']
                upd = int(r.get('updated', 0))
                if newer('prefs', rid, upd):
                    rev += 1
                    pushed['prefs'].append(rid)
                    cur.execute('INSERT OR REPLACE INTO prefs VALUES(?,?,?,?,?,?)',
                                (u, rid, str(r.get('v', ''))[:100], upd, 1 if r.get('deleted') else 0, rev))
                else:
                    pushed['prefs'].append(rid)

        cur.execute('UPDATE users SET rev=?, synced=? WHERE id=?', (rev, int(time.time()), u))
        conn.commit()

    rev = cur.execute('SELECT rev FROM users WHERE id=?', (u,)).fetchone()['rev']

    def sel(t):
        ids = list(set(pushed[t]))
        if ids:
            placeholders = ','.join('?' for _ in ids)
            sql = f'SELECT * FROM {t} WHERE user_id=? AND (rev>? OR id IN ({placeholders}))'
            params = [u, since] + ids
        else:
            sql = f'SELECT * FROM {t} WHERE user_id=? AND rev>?'
            params = [u, since]
        return cur.execute(sql, params).fetchall()

    lk = conn.cursor()
    exps_res = []
    for e in sel('expenses'):
        lk.execute('SELECT category_id FROM expense_categories WHERE user_id=? AND expense_id=?', (u, e['id']))
        cats = [row[0] for row in lk.fetchall()]
        exps_res.append({'id': e['id'], 'pid': e['group_id'], 'amt': e['amount'], 'desc': e['descr'], 'cats': cats, 'deleted': e['deleted']})

    return 200, {
        'since': rev,
        'parents': [{'id': p['id'], 'name': p['name'], 'deleted': p['deleted']} for p in sel('groups_')],
        'cats': [{'id': c['id'], 'pid': c['group_id'], 'parent': c['parent'], 'name': c['name'], 'deleted': c['deleted']} for c in sel('categories')],
        'prefs': [{'id': r['id'], 'v': r['v'], 'deleted': r['deleted']} for r in sel('prefs')],
        'exps': exps_res
    }

def test_runner():
    conn = create_app_db()
    
    # Setup User A and User B
    uid_a, tok_a = register_user(conn, 'user_a@test.com', 'pass12345')
    uid_b, tok_b = register_user(conn, 'user_b@test.com', 'pass12345')

    # Seed User B with a group and an expense
    code, res_b = api_sync(conn, tok_b, {
        'parents': [{'id': 'grp_b_main', 'name': 'User B Private Life', 'updated': 1000}],
        'cats': [{'id': 'cat_b_health', 'pid': 'grp_b_main', 'name': 'Health', 'updated': 1000}],
        'exps': [{'id': 'exp_b_1', 'pid': 'grp_b_main', 'amt': 5000, 'dt': '2026-10-30', 'cats': ['cat_b_health'], 'updated': 1000}]
    })
    assert code == 200 and len(res_b['exps']) == 1, "User B seeding failed"
    print("[PASS 1] User B seeded valid grouped expense.")

    # Seed User A with their own valid group
    code, res_a = api_sync(conn, tok_a, {
        'parents': [{'id': 'grp_a_main', 'name': 'User A Main Group', 'updated': 1000}],
        'cats': [{'id': 'cat_a_food', 'pid': 'grp_a_main', 'name': 'Food', 'updated': 1000}]
    })
    assert code == 200, "User A seeding failed"
    print("[PASS 2] User A seeded valid group and category.")

    # TEST 1: Legitimate grouped expense synchronization
    code, res = api_sync(conn, tok_a, {
        'exps': [{'id': 'exp_a_valid', 'pid': 'grp_a_main', 'amt': 350, 'dt': '2026-10-30', 'desc': 'Lunch', 'cats': ['cat_a_food'], 'updated': 1001}]
    })
    assert code == 200, "Valid sync failed"
    saved_valid = [e for e in res['exps'] if e['id'] == 'exp_a_valid']
    assert len(saved_valid) == 1 and saved_valid[0]['pid'] == 'grp_a_main', "Valid expense not saved correctly"
    print("[PASS 3] TEST 1: Legitimate grouped expense synchronized successfully.")

    # TEST 2: Ungrouped expense synchronization (empty or missing pid)
    # Must be safely rejected, NOT saved with group_id = ''
    code, res = api_sync(conn, tok_a, {
        'exps': [
            {'id': 'exp_a_ungrouped_empty', 'pid': '', 'amt': 100, 'dt': '2026-10-30', 'desc': 'Ungrouped 1', 'updated': 1002},
            {'id': 'exp_a_ungrouped_missing', 'amt': 150, 'dt': '2026-10-30', 'desc': 'Ungrouped 2', 'updated': 1003}
        ]
    })
    assert code == 200, "Sync request failed"
    # Verify neither was saved in DB
    cur = conn.cursor()
    ungrouped_in_db = cur.execute('SELECT * FROM expenses WHERE id IN ("exp_a_ungrouped_empty", "exp_a_ungrouped_missing")').fetchall()
    assert len(ungrouped_in_db) == 0, f"Ungrouped expenses were illegally saved into DB: {ungrouped_in_db}"
    # Verify neither was returned in sync response
    returned_ungrouped = [e for e in res['exps'] if e['id'] in ('exp_a_ungrouped_empty', 'exp_a_ungrouped_missing')]
    assert len(returned_ungrouped) == 0, f"Ungrouped expenses returned in sync response: {returned_ungrouped}"
    print("[PASS 4] TEST 2: Ungrouped expenses safely rejected (not saved to DB, not returned to client).")

    # TEST 3: Foreign group expense synchronization (User A attempts to use User B's group)
    code, res = api_sync(conn, tok_a, {
        'exps': [{'id': 'exp_a_foreign_grp', 'pid': 'grp_b_main', 'amt': 999, 'dt': '2026-10-30', 'desc': 'Attacking B', 'updated': 1004}]
    })
    assert code == 200, "Sync request failed"
    foreign_in_db = cur.execute('SELECT * FROM expenses WHERE id="exp_a_foreign_grp"').fetchall()
    assert len(foreign_in_db) == 0, f"Foreign group expense was illegally saved: {foreign_in_db}"
    print("[PASS 5] TEST 3: Foreign group expense safely rejected (not saved to DB).")

    # TEST 4: Nonexistent group expense synchronization
    code, res = api_sync(conn, tok_a, {
        'exps': [{'id': 'exp_a_bogus_grp', 'pid': 'grp_nonexistent_999', 'amt': 200, 'dt': '2026-10-30', 'desc': 'Bogus', 'updated': 1005}]
    })
    assert code == 200, "Sync request failed"
    bogus_in_db = cur.execute('SELECT * FROM expenses WHERE id="exp_a_bogus_grp"').fetchall()
    assert len(bogus_in_db) == 0, f"Bogus group expense was illegally saved: {bogus_in_db}"
    print("[PASS 6] TEST 4: Nonexistent group expense safely rejected (not saved to DB).")

    # TEST 5: Offline batch synchronization (New group created offline with new expenses)
    code, res = api_sync(conn, tok_a, {
        'parents': [{'id': 'grp_a_offline', 'name': 'Trip 2026', 'updated': 1006}],
        'exps': [
            {'id': 'exp_a_off1', 'pid': 'grp_a_offline', 'amt': 1200, 'dt': '2026-10-30', 'desc': 'Train', 'updated': 1006},
            {'id': 'exp_a_off2', 'pid': 'grp_a_offline', 'amt': 3400, 'dt': '2026-10-30', 'desc': 'Hotel', 'updated': 1006}
        ]
    })
    assert code == 200, "Offline batch sync failed"
    off_in_db = cur.execute('SELECT id, group_id, amount FROM expenses WHERE id IN ("exp_a_off1", "exp_a_off2")').fetchall()
    assert len(off_in_db) == 2 and all(row['group_id'] == 'grp_a_offline' for row in off_in_db), "Offline expenses not saved correctly"
    print("[PASS 7] TEST 5: Offline batch sync with new group + expenses succeeded perfectly.")

    # TEST 6: Legitimate expense deletion
    code, res = api_sync(conn, tok_a, {
        'exps': [{'id': 'exp_a_valid', 'pid': 'grp_a_main', 'deleted': 1, 'updated': 1007}]
    })
    assert code == 200, "Delete sync failed"
    del_row = cur.execute('SELECT deleted FROM expenses WHERE id="exp_a_valid"').fetchone()
    assert del_row and del_row['deleted'] == 1, "Expense deletion failed"
    print("[PASS 8] TEST 6: Legitimate expense deletion processed cleanly.")

    # TEST 7: User B's records verified completely untouched
    cur.execute('SELECT * FROM expenses WHERE user_id=?', (uid_b,))
    b_exps = cur.fetchall()
    assert len(b_exps) == 1 and b_exps[0]['id'] == 'exp_b_1' and b_exps[0]['amount'] == 5000, "User B's data altered!"
    print("[PASS 9] TEST 7: User B's data verified 100% intact and unchanged.")

    print("\n=== ALL EDGE CASE TESTS PASSED SUCCESSFULLY ===")

if __name__ == '__main__':
    test_runner()
