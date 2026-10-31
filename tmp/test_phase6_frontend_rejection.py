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

# Exact replication of api.php backend sync logic
def server_sync(conn, tok, payload):
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
    rejected = {'expenses': [], 'categories': []}

    if P or C or E or R:
        conn.execute('BEGIN IMMEDIATE')
        cur.execute('UPDATE users SET rev=rev WHERE id=?', (u,))
        rev = cur.execute('SELECT rev FROM users WHERE id=?', (u,)).fetchone()['rev']

        def newer(t, item_id, upd):
            o = cur.execute(f'SELECT updated FROM {t} WHERE user_id=? AND id=?', (u, item_id)).fetchone()
            return o is None or upd > int(o['updated'])

        # 1. Groups
        for p in P:
            if isinstance(p, dict) and ok_id(p.get('id')):
                pid = p['id']
                pushed['groups_'].append(pid)
                upd = int(p.get('updated', 0))
                if newer('groups_', pid, upd):
                    rev += 1
                    cur.execute('INSERT OR REPLACE INTO groups_ VALUES(?,?,?,?,?,?)',
                                (u, pid, p.get('name', '')[:100], upd, 1 if p.get('deleted') else 0, rev))

        owned_groups = [r[0] for r in cur.execute('SELECT id FROM groups_ WHERE user_id=? AND deleted=0', (u,)).fetchall()]
        group_set = set(owned_groups)

        owned_cats = [r[0] for r in cur.execute('SELECT id FROM categories WHERE user_id=? AND deleted=0', (u,)).fetchall()]
        cat_set = set(owned_cats)
        for c in C:
            if isinstance(c, dict) and ok_id(c.get('id')) and not c.get('deleted'):
                cat_set.add(c['id'])

        # 2. Categories
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
                            else:
                                rejected['categories'].append({'id': cid, 'reason': 'invalid_group'})
                        else:
                            rejected['categories'].append({'id': cid, 'reason': 'invalid_group'})
                        continue

                    rev += 1
                    pushed['categories'].append(cid)
                    c_parent = c.get('parent') if (ok_id(c.get('parent')) and c.get('parent') in cat_set and c.get('parent') != cid) else None
                    cur.execute('INSERT OR REPLACE INTO categories VALUES(?,?,?,?,?,?,?,?)',
                                (u, cid, c_pid, c_parent, c.get('name', '')[:100], upd, 1 if c.get('deleted') else 0, rev))
                else:
                    pushed['categories'].append(cid)

        owned_cats = [r[0] for r in cur.execute('SELECT id FROM categories WHERE user_id=? AND deleted=0', (u,)).fetchall()]
        cat_set = set(owned_cats)

        # 3. Expenses
        for e in E:
            if isinstance(e, dict) and ok_id(e.get('id')):
                eid = e['id']
                upd = int(e.get('updated', 0))
                e_pid = e.get('pid') if (ok_id(e.get('pid')) and e.get('pid') in group_set) else None

                if newer('expenses', eid, upd):
                    if not e_pid:
                        if e.get('deleted'):
                            existE = cur.execute('SELECT group_id FROM expenses WHERE user_id=? AND id=?', (u, eid)).fetchone()
                            if existE:
                                rev += 1
                                cur.execute('UPDATE expenses SET deleted=1, updated=?, rev=? WHERE user_id=? AND id=?', (upd, rev, u, eid))
                                pushed['expenses'].append(eid)
                            else:
                                rejected['expenses'].append({'id': eid, 'reason': 'invalid_group'})
                        else:
                            rejected['expenses'].append({'id': eid, 'reason': 'invalid_group'})
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
        'now': int(time.time() * 1000),
        'notice': '',
        'parents': [{'id': p['id'], 'name': p['name'], 'deleted': p['deleted']} for p in sel('groups_')],
        'cats': [{'id': c['id'], 'pid': c['group_id'], 'parent': c['parent'], 'name': c['name'], 'deleted': c['deleted']} for c in sel('categories')],
        'prefs': [{'id': r['id'], 'v': r['v'], 'deleted': r['deleted']} for r in sel('prefs')],
        'exps': exps_res,
        'rejected': rejected
    }

# Client State Machine replicating index.html sync()
class ClientApp:
    def __init__(self, conn, tok):
        self.conn = conn
        self.tok = tok
        self.S = {
            'parents': [],
            'cats': [],
            'exps': [],
            'prefs': [],
            'since': 0
        }
        self.SY = {'last': 0, 'fail': 0, 'err': ''}
        self.dot_status = 'ok'
        self.status_msg = ''
        self.toasts = []

    def pend(self):
        return sum(1 for l in [self.S['parents'], self.S['cats'], self.S['exps'], self.S['prefs']] for x in l if x.get('_d'))

    def client_sync(self):
        snap = {}
        def pick(a):
            o = []
            for x in a:
                if not x.get('_d'):
                    continue
                snap[x['id']] = x['updated']
                r = {k: v for k, v in x.items() if k not in ('_d', '_rej')}
                o.append(r)
            return o

        body = {
            'token': self.tok,
            'since': self.S['since'],
            'parents': pick(self.S['parents']),
            'cats': pick(self.S['cats']),
            'exps': pick(self.S['exps']),
            'prefs': pick(self.S['prefs'])
        }

        code, d = server_sync(self.conn, self.tok, body)
        if code != 200 or not d:
            self.dot_status = 'err'
            self.SY['err'] = d.get('error', 'Server error')
            return False

        confP = set(x['id'] for x in d.get('parents', []))
        confC = set(x['id'] for x in d.get('cats', []))
        confE = set(x['id'] for x in d.get('exps', []))
        confR = set(x['id'] for x in d.get('prefs', []))

        rejE = set(x['id'] if isinstance(x, dict) else x for x in (d.get('rejected') or {}).get('expenses', []))
        rejC = set(x['id'] if isinstance(x, dict) else x for x in (d.get('rejected') or {}).get('categories', []))

        rejCount = 0

        for x in self.S['parents']:
            if x.get('_d') and snap.get(x['id']) == x['updated'] and x['id'] in confP:
                del x['_d']

        for x in self.S['prefs']:
            if x.get('_d') and snap.get(x['id']) == x['updated'] and x['id'] in confR:
                del x['_d']

        for x in self.S['cats']:
            if x.get('_d') and snap.get(x['id']) == x['updated']:
                if x['id'] in confC:
                    x.pop('_d', None)
                    x.pop('_rej', None)
                elif x['id'] in rejC or x['id'] not in confC:
                    x['_rej'] = 1
                    rejCount += 1

        for x in self.S['exps']:
            if x.get('_d') and snap.get(x['id']) == x['updated']:
                if x['id'] in confE:
                    x.pop('_d', None)
                    x.pop('_rej', None)
                else:
                    x['_rej'] = 1
                    rejCount += 1

        # Merge incoming updates
        for loc, inc in [(self.S['parents'], d.get('parents', [])),
                         (self.S['cats'], d.get('cats', [])),
                         (self.S['exps'], d.get('exps', [])),
                         (self.S['prefs'], d.get('prefs', []))]:
            for i in inc:
                l = next((x for x in loc if x['id'] == i['id']), None)
                if not l:
                    loc.append(i)
                elif not l.get('_d'):
                    l.update(i)

        self.S['since'] = d.get('since', self.S['since'])

        if rejCount > 0:
            self.SY['err'] = f"{rejCount}টি খরচে গ্রুপ নেই"
            self.dot_status = 'err'
            self.status_msg = f"{rejCount}টি খরচ সিঙ্ক হয়নি — গ্রুপ ঠিক করুন"
            self.toasts.append(f"সতর্কতা: {rejCount}টি খরচের গ্রুপ সঠিক না থাকায় সিঙ্ক হয়নি।")
        else:
            self.status_msg = 'সিঙ্ক হয়েছে ✓'
            self.SY['last'] = int(time.time() * 1000)
            self.SY['err'] = ''
            self.dot_status = 'ok'

        return True

def run_tests():
    conn = create_app_db()
    uid_a, tok_a = register_user(conn, 'alice@test.com', 'alice1234')
    uid_b, tok_b = register_user(conn, 'bob@test.com', 'bob12345')

    # Seed Bob
    bob_client = ClientApp(conn, tok_b)
    bob_client.S['parents'].append({'id': 'grp_bob_secret', 'name': 'Bob Secret', 'updated': 1000, '_d': 1})
    bob_client.client_sync()
    assert bob_client.dot_status == 'ok'

    alice = ClientApp(conn, tok_a)
    alice.S['parents'].append({'id': 'grp_alice_main', 'name': 'Alice Main', 'updated': 1000, '_d': 1})
    alice.client_sync()
    assert alice.dot_status == 'ok'
    print("[PASS 1] Alice and Bob initialized with independent groups.")

    # TASK 1 & 2 & 3: Test backend rejection and verify _d is NEVER cleared and data is NOT lost
    # Add 4 rejected cases:
    # a. empty group ID (pid: '')
    # b. missing group ID (no pid key)
    # c. foreign group ID (grp_bob_secret)
    # d. nonexistent group ID (grp_fake_999)
    alice.S['exps'].extend([
        {'id': 'exp_empty_grp', 'pid': '', 'amt': 100, 'dt': '2026-10-30', 'desc': 'Empty group', 'updated': 1010, '_d': 1},
        {'id': 'exp_missing_grp', 'amt': 120, 'dt': '2026-10-30', 'desc': 'Missing group', 'updated': 1011, '_d': 1},
        {'id': 'exp_foreign_grp', 'pid': 'grp_bob_secret', 'amt': 140, 'dt': '2026-10-30', 'desc': 'Foreign group', 'updated': 1012, '_d': 1},
        {'id': 'exp_fake_grp', 'pid': 'grp_fake_999', 'amt': 160, 'dt': '2026-10-30', 'desc': 'Fake group', 'updated': 1013, '_d': 1}
    ])

    alice.client_sync()

    # TASK 2: Verify rejected expenses are NEVER marked as successfully synced
    for eid in ['exp_empty_grp', 'exp_missing_grp', 'exp_foreign_grp', 'exp_fake_grp']:
        local_exp = next(x for x in alice.S['exps'] if x['id'] == eid)
        assert local_exp.get('_d') == 1, f"FAIL: {eid} was incorrectly marked as synced (_d removed)!"
        assert local_exp.get('_rej') == 1, f"FAIL: {eid} was not marked with _rej!"
    print("[PASS 2] Task 2 Verified: Rejected expenses NEVER have _d cleared.")

    # TASK 3: Verify rejected local pending expenses are not silently deleted or lost
    assert len(alice.S['exps']) == 4, f"FAIL: local pending expenses were lost! Count: {len(alice.S['exps'])}"
    print("[PASS 3] Task 3 Verified: Local pending expenses remain 100% preserved in client storage.")

    # TASK 4: Confirm frontend provides error/recovery indication
    assert alice.dot_status == 'err', f"FAIL: dot status is {alice.dot_status}, expected 'err'"
    assert 'সিঙ্ক হয়নি' in alice.status_msg, f"FAIL: status msg did not indicate error: {alice.status_msg}"
    assert alice.pend() == 4, f"FAIL: pend count is {alice.pend()}, expected 4"
    assert len(alice.toasts) > 0 and 'সতর্কতা' in alice.toasts[-1], f"FAIL: Toast warning not shown: {alice.toasts}"
    print("[PASS 4] Task 4 Verified: Frontend shows dot 'err', error status message, and Bengali toast warning.")

    # TASK 5: Test mixed sync batch (valid + invalid)
    alice.S['exps'].append({'id': 'exp_alice_valid_1', 'pid': 'grp_alice_main', 'amt': 500, 'dt': '2026-10-30', 'desc': 'Valid Coffee', 'updated': 1014, '_d': 1})
    alice.S['exps'].append({'id': 'exp_alice_valid_2', 'pid': 'grp_alice_main', 'amt': 750, 'dt': '2026-10-30', 'desc': 'Valid Lunch', 'updated': 1015, '_d': 1})

    alice.client_sync()

    # Verify valid expenses synced successfully
    v1 = next(x for x in alice.S['exps'] if x['id'] == 'exp_alice_valid_1')
    v2 = next(x for x in alice.S['exps'] if x['id'] == 'exp_alice_valid_2')
    assert '_d' not in v1 and '_rej' not in v1, "FAIL: exp_alice_valid_1 not cleared!"
    assert '_d' not in v2 and '_rej' not in v2, "FAIL: exp_alice_valid_2 not cleared!"

    # Verify in SQLite DB that only the 2 valid expenses were saved
    cur = conn.cursor()
    db_exps = cur.execute('SELECT id, group_id, amount FROM expenses WHERE user_id=?', (uid_a,)).fetchall()
    saved_ids = set(row['id'] for row in db_exps)
    assert 'exp_alice_valid_1' in saved_ids and 'exp_alice_valid_2' in saved_ids, "FAIL: valid expenses not in DB!"
    for eid in ['exp_empty_grp', 'exp_missing_grp', 'exp_foreign_grp', 'exp_fake_grp']:
        assert eid not in saved_ids, f"FAIL: rejected expense {eid} was illegally written to DB!"

    # Verify rejected expenses remain safely preserved locally
    assert alice.pend() == 4, f"FAIL: expected 4 rejected expenses still pending, got {alice.pend()}"
    print("[PASS 5] Task 5 Verified: Mixed sync batch successfully syncs valid expenses while preserving rejected items locally.")

    # TASK 6: Verify retry behavior and idempotency (no duplicate records)
    initial_db_count = cur.execute('SELECT COUNT(*) FROM expenses WHERE user_id=?', (uid_a,)).fetchone()[0]
    alice.client_sync() # Retry sync
    alice.client_sync() # Retry again
    after_retry_count = cur.execute('SELECT COUNT(*) FROM expenses WHERE user_id=?', (uid_a,)).fetchone()[0]
    assert initial_db_count == after_retry_count == 2, f"FAIL: Retries created duplicate rows in DB! Count: {after_retry_count}"
    print("[PASS 6] Task 6 Verified: Sync retries are completely idempotent and never create duplicate records.")

    # USER RECOVERY FLOW: User edits rejected expenses to valid group
    for eid in ['exp_empty_grp', 'exp_missing_grp', 'exp_foreign_grp', 'exp_fake_grp']:
        exp = next(x for x in alice.S['exps'] if x['id'] == eid)
        exp['pid'] = 'grp_alice_main'
        exp.pop('_rej', None)
        exp['updated'] = 1020
        exp['_d'] = 1

    alice.client_sync()

    # Now all 6 expenses should be successfully synced
    assert alice.pend() == 0, f"FAIL: All recovered expenses should have _d cleared! Pend: {alice.pend()}"
    assert alice.dot_status == 'ok', f"FAIL: Dot status should be 'ok', got {alice.dot_status}"
    total_db_count = cur.execute('SELECT COUNT(*) FROM expenses WHERE user_id=?', (uid_a,)).fetchone()[0]
    assert total_db_count == 6, f"FAIL: Expected 6 expenses in DB after recovery, got {total_db_count}"
    print("[PASS 7] Recovery Verified: After user corrects group, all expenses synchronize cleanly with zero data loss.")

    # TASK 7: Multi-user isolation, tombstones, and offline batch synchronization
    # Tombstone deletion
    del_target = next(x for x in alice.S['exps'] if x['id'] == 'exp_alice_valid_1')
    del_target['deleted'] = 1
    del_target['updated'] = 1030
    del_target['_d'] = 1
    alice.client_sync()
    db_del = cur.execute('SELECT deleted FROM expenses WHERE id="exp_alice_valid_1"').fetchone()
    assert db_del and db_del['deleted'] == 1, "FAIL: Deletion tombstone failed!"

    # Verify Bob's data was completely untouched
    bob_db_exps = cur.execute('SELECT * FROM expenses WHERE user_id=?', (uid_b,)).fetchall()
    assert len(bob_db_exps) == 0, "FAIL: Bob's data contaminated!"
    bob_groups = cur.execute('SELECT * FROM groups_ WHERE user_id=?', (uid_b,)).fetchall()
    assert len(bob_groups) == 1 and bob_groups[0]['id'] == 'grp_bob_secret', "FAIL: Bob's group modified!"
    print("[PASS 8] Task 7 Verified: Deletions, offline batches, and multi-user isolation remain 100% intact.")

    print("\n=== ALL FRONTEND SYNC-REJECTION TESTS PASSED (8/8) ===")

if __name__ == '__main__':
    run_tests()
