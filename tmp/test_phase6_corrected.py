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
    INSERT INTO settings(k,v) VALUES('delete_code', 'TanvirX');
    ''')
    conn.commit()
    return conn

# Helper functions replicating api.php with corrected Phase 6 ownership checks
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
    
    nowMs = int(time.time() * 1000)
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

        # Query user's valid active groups
        owned_groups = [r[0] for r in cur.execute('SELECT id FROM groups_ WHERE user_id=? AND deleted=0', (u,)).fetchall()]
        group_set = set(owned_groups)

        # Query user's valid active categories in DB + any valid new categories in this batch
        owned_cats = [r[0] for r in cur.execute('SELECT id FROM categories WHERE user_id=? AND deleted=0', (u,)).fetchall()]
        cat_set = set(owned_cats)
        for c in C:
            if isinstance(c, dict) and ok_id(c.get('id')) and not c.get('deleted'):
                cat_set.add(c['id'])

        # 2. Process categories with ownership validation
        for c in C:
            if isinstance(c, dict) and ok_id(c.get('id')):
                cid = c['id']
                pushed['categories'].append(cid)
                upd = int(c.get('updated', 0))
                if newer('categories', cid, upd):
                    rev += 1
                    c_pid = c.get('pid') if (ok_id(c.get('pid')) and c.get('pid') in group_set) else ''
                    c_parent = c.get('parent') if (ok_id(c.get('parent')) and c.get('parent') in cat_set and c.get('parent') != cid) else None
                    cur.execute('INSERT OR REPLACE INTO categories VALUES(?,?,?,?,?,?,?,?)',
                                (u, cid, c_pid, c_parent, c.get('name', '')[:100], upd, 1 if c.get('deleted') else 0, rev))

        # Refresh active categories after writing C
        owned_cats = [r[0] for r in cur.execute('SELECT id FROM categories WHERE user_id=? AND deleted=0', (u,)).fetchall()]
        cat_set = set(owned_cats)

        # 3. Process expenses with ownership validation
        for e in E:
            if isinstance(e, dict) and ok_id(e.get('id')):
                eid = e['id']
                pushed['expenses'].append(eid)
                upd = int(e.get('updated', 0))
                if newer('expenses', eid, upd):
                    rev += 1
                    amt = float(e.get('amt', 0))
                    e_pid = e.get('pid') if (ok_id(e.get('pid')) and e.get('pid') in group_set) else ''
                    cur.execute('INSERT OR REPLACE INTO expenses VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                                (u, eid, e_pid, amt, e.get('dt', '')[:10], e.get('tm', '')[:5], e.get('desc', '')[:300], e.get('note', '')[:1000], upd, 1 if e.get('deleted') else 0, rev))
                    cur.execute('DELETE FROM expense_categories WHERE user_id=? AND expense_id=?', (u, eid))
                    for cat_id in e.get('cats', []):
                        if ok_id(cat_id) and cat_id in cat_set:
                            cur.execute('INSERT OR IGNORE INTO expense_categories VALUES(?,?,?)', (u, eid, cat_id))

        for r in R:
            if isinstance(r, dict) and ok_id(r.get('id')):
                rid = r['id']
                pushed['prefs'].append(rid)
                upd = int(r.get('updated', 0))
                if newer('prefs', rid, upd):
                    rev += 1
                    cur.execute('INSERT OR REPLACE INTO prefs VALUES(?,?,?,?,?,?)',
                                (u, rid, str(r.get('v', ''))[:100], upd, 1 if r.get('deleted') else 0, rev))

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

def api_report(conn, tok, group_id, dt_from='0000-01-01', dt_to='9999-12-31'):
    u = get_auth_user(conn, tok)
    if not u:
        return 401, {'error': 'Unauthorized'}
    if not ok_id(group_id):
        return 400, {'error': 'গ্রুপ আইডি সঠিক নয়'}
    
    cur = conn.cursor()
    # Check group belongs to authenticated user and is not deleted
    grp = cur.execute('SELECT 1 FROM groups_ WHERE user_id=? AND id=? AND deleted=0', (u, group_id)).fetchone()
    if not grp:
        return 403, {'error': 'গ্রুপটি পাওয়া যায়নি বা দেখার অনুমতি নেই'}

    base = 'user_id=? AND group_id=? AND deleted=0 AND date>=? AND date<=?'
    t = cur.execute(f'SELECT COALESCE(SUM(amount),0) total, COUNT(*) n FROM expenses WHERE {base}', (u, group_id, dt_from, dt_to)).fetchone()
    
    # Categories query
    cats = []
    top_cats = cur.execute('SELECT id, name FROM categories WHERE user_id=? AND group_id=? AND parent IS NULL AND deleted=0', (u, group_id)).fetchall()
    for c in top_cats:
        cte = f'''WITH RECURSIVE d(id) AS (
            SELECT id FROM categories WHERE user_id=? AND id=? AND deleted=0
            UNION ALL SELECT c.id FROM categories c JOIN d ON c.parent=d.id WHERE c.user_id=? AND c.deleted=0)
          SELECT COALESCE(SUM(amount),0) total, COUNT(*) n FROM expenses e WHERE {base}
            AND EXISTS(SELECT 1 FROM expense_categories x WHERE x.user_id=e.user_id AND x.expense_id=e.id AND x.category_id IN (SELECT id FROM d))'''
        r = cur.execute(cte, (u, c['id'], u, u, group_id, dt_from, dt_to)).fetchone()
        cats.append({'id': c['id'], 'name': c['name'], 'total': float(r['total']), 'n': int(r['n'])})

    return 200, {'total': float(t['total']), 'transactions': int(t['n']), 'categories': cats}

# Execution & Test verification
conn = create_app_db()

# Step 1: Create User A and User B
uid_a, tok_a = register_user(conn, 'usera@example.com', 'PassUserA123')
uid_b, tok_b = register_user(conn, 'userb@example.com', 'PassUserB123')
assert uid_a == 1 and uid_b == 2
print('[PASS 1] User A (id=1) and User B (id=2) created.')

# Step 2: User B creates legitimate private records
sync_b = {
    'since': 0,
    'parents': [{'id': 'grp_b_secret', 'name': 'User B Private Fund', 'updated': 1000}],
    'cats': [
        {'id': 'cat_b_health', 'pid': 'grp_b_secret', 'parent': None, 'name': 'Health & Clinic', 'updated': 1000},
        {'id': 'cat_b_dental', 'pid': 'grp_b_secret', 'parent': 'cat_b_health', 'name': 'Dental Care', 'updated': 1000}
    ],
    'prefs': [{'id': 'budget:grp_b_secret', 'v': '50000', 'updated': 1000}],
    'exps': [{'id': 'exp_b_confidential', 'pid': 'grp_b_secret', 'amt': 12500, 'desc': 'Private Doctor Bill', 'dt': '2026-10-30', 'tm': '10:00', 'cats': ['cat_b_dental'], 'updated': 1000}]
}
code, res_b = api_sync(conn, tok_b, sync_b)
assert code == 200
print('[PASS 2] User B seeded private group, parent/child categories, and expense ($12,500).')

# Step 3: User A creates legitimate records for comparison
sync_a = {
    'since': 0,
    'parents': [{'id': 'grp_a_legit', 'name': 'User A Campus Expenses', 'updated': 1000}],
    'cats': [{'id': 'cat_a_books', 'pid': 'grp_a_legit', 'parent': None, 'name': 'Textbooks', 'updated': 1000}],
    'exps': [{'id': 'exp_a_legit', 'pid': 'grp_a_legit', 'amt': 450, 'desc': 'Math Book', 'dt': '2026-10-30', 'tm': '11:00', 'cats': ['cat_a_books'], 'updated': 1000}]
}
code, res_a = api_sync(conn, tok_a, sync_a)
assert code == 200
print('[PASS 3] User A seeded legitimate group, category, and expense ($450).')

# Step 4: [TEST REQUIRED 1] User A attempts to create an expense using User B's group ID
attack_exp_group = {
    'since': 0,
    'exps': [{'id': 'exp_a_stealg', 'pid': 'grp_b_secret', 'amt': 999, 'desc': 'Intrusion Attempt', 'dt': '2026-10-30', 'cats': [], 'updated': 2000}]
}
code, res = api_sync(conn, tok_a, attack_exp_group)
assert code == 200
cur = conn.cursor()
row = cur.execute('SELECT group_id FROM expenses WHERE user_id=? AND id=?', (uid_a, 'exp_a_stealg')).fetchone()
assert row['group_id'] == '', f"Foreign group ID was not rejected! Got: {row['group_id']}"
print('[PASS 4] TEST REQUIRED 1: User A attempted to use User B group ID "grp_b_secret" on expense. Group was rejected/sanitized to "".')

# Step 5: [TEST REQUIRED 2] User A attempts to attach User B's category ID to an expense
attack_exp_cat = {
    'since': 0,
    'exps': [{'id': 'exp_a_stealcat', 'pid': 'grp_a_legit', 'amt': 333, 'desc': 'Attaching foreign cat', 'dt': '2026-10-30', 'cats': ['cat_b_dental', 'cat_a_books', 'nonexistent_cat_999'], 'updated': 2000}]
}
code, res = api_sync(conn, tok_a, attack_exp_cat)
assert code == 200
attached_cats = [r[0] for r in cur.execute('SELECT category_id FROM expense_categories WHERE user_id=? AND expense_id=?', (uid_a, 'exp_a_stealcat')).fetchall()]
assert 'cat_b_dental' not in attached_cats, f"Foreign category 'cat_b_dental' was attached! {attached_cats}"
assert 'nonexistent_cat_999' not in attached_cats, f"Nonexistent category attached! {attached_cats}"
assert 'cat_a_books' in attached_cats, f"Legitimate category missing! {attached_cats}"
print('[PASS 5] TEST REQUIRED 2: User A attempted to attach User B category "cat_b_dental" and nonexistent cat. Foreign/fake cats rejected; legitimate cat preserved.')

# Step 6: [TEST REQUIRED 3] User A attempts to use User B's parent category ID
attack_cat_parent = {
    'since': 0,
    'cats': [{'id': 'cat_a_forged_child', 'pid': 'grp_a_legit', 'parent': 'cat_b_health', 'name': 'Fake Subcat', 'updated': 2000}]
}
code, res = api_sync(conn, tok_a, attack_cat_parent)
assert code == 200
row = cur.execute('SELECT parent FROM categories WHERE user_id=? AND id=?', (uid_a, 'cat_a_forged_child')).fetchone()
assert row['parent'] is None, f"Foreign parent category was not rejected! Got: {row['parent']}"
print('[PASS 6] TEST REQUIRED 3: User A attempted to set parent to User B category "cat_b_health". Foreign parent rejected/nullified to None.')

# Step 7: [TEST REQUIRED 4] User A requests a report for User B's group
code, rep_a_bgroup = api_report(conn, tok_a, 'grp_b_secret')
assert code == 403, f"User A report request for User B group was not rejected with 403! Got: {code}"
assert rep_a_bgroup.get('error') == 'গ্রুপটি পাওয়া যায়নি বা দেখার অনুমতি নেই'
print('[PASS 7] TEST REQUIRED 4: User A requested report for User B group "grp_b_secret". Request rejected with HTTP 403 Forbidden.')

# Step 8: [TEST REQUIRED 5] Confirm User B's data remains 100% unchanged
b_grp = cur.execute('SELECT * FROM groups_ WHERE user_id=? AND id=?', (uid_b, 'grp_b_secret')).fetchone()
assert b_grp['name'] == 'User B Private Fund' and b_grp['deleted'] == 0

b_cats = cur.execute('SELECT id, parent FROM categories WHERE user_id=? ORDER BY id', (uid_b,)).fetchall()
assert len(b_cats) == 2
assert b_cats[0]['id'] == 'cat_b_dental' and b_cats[0]['parent'] == 'cat_b_health'
assert b_cats[1]['id'] == 'cat_b_health' and b_cats[1]['parent'] is None

b_exp = cur.execute('SELECT * FROM expenses WHERE user_id=? AND id=?', (uid_b, 'exp_b_confidential')).fetchone()
assert b_exp['amount'] == 12500 and b_exp['group_id'] == 'grp_b_secret' and b_exp['descr'] == 'Private Doctor Bill'

b_exp_cats = [r[0] for r in cur.execute('SELECT category_id FROM expense_categories WHERE user_id=? AND expense_id=?', (uid_b, 'exp_b_confidential')).fetchall()]
assert b_exp_cats == ['cat_b_dental']
print("[PASS 8] TEST REQUIRED 5: User B's data verified 100% intact and unchanged.")

# Step 9: [TEST REQUIRED 6] Confirm legitimate operations for both users still work
code, rep_a_legit = api_report(conn, tok_a, 'grp_a_legit')
assert code == 200
assert rep_a_legit['total'] == 783.0  # 450 (Math Book) + 333 (Attaching foreign cat) = 783
assert rep_a_legit['transactions'] == 2

code, rep_b_legit = api_report(conn, tok_b, 'grp_b_secret')
assert code == 200
assert rep_b_legit['total'] == 12500.0
assert rep_b_legit['transactions'] == 1
assert len(rep_b_legit['categories']) == 1
assert rep_b_legit['categories'][0]['id'] == 'cat_b_health'
assert rep_b_legit['categories'][0]['total'] == 12500.0
print("[PASS 9] TEST REQUIRED 6: Legitimate report operations for User A and User B work seamlessly.")

print("\n=== ALL PHASE 6 CORRECTION TESTS EXECUTED AND PASSED SUCCESSFULLY ===")
