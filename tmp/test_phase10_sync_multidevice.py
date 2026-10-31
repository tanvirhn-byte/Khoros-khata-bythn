#!/usr/bin/env python3
"""
Comprehensive Test Suite for Phase 10: Online Synchronization & Multi-Device Consistency
Covers all 19 required test scenarios from the specification:
1. Device A to Device B synchronization
2. Device B to Device A synchronization
3. New expense synchronization
4. Updated expense synchronization
5. Group and category synchronization
6. Preference synchronization
7. Incremental delta synchronization
8. Pagination and "more" cursor
9. Deletion tombstones
10. Simultaneous edits and conflict resolution (LWW)
11. Clock-skew handling
12. Interrupted upload and retry
13. Interrupted download and retry
14. Duplicate prevention
15. Stale cursor full resynchronization
16. Rejected expense preservation (Phase 6 recovery)
17. Multi-user isolation
18. Expired/revoked token handling
19. Repeated synchronization consistency
"""

import sys
import json
import sqlite3
import hashlib
import time

def setup_server_db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.executescript('''
    CREATE TABLE users(id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, hash TEXT, rev INTEGER DEFAULT 0, created INTEGER, synced INTEGER, status TEXT DEFAULT 'active');
    CREATE TABLE tokens(token_hash TEXT PRIMARY KEY, user_id INTEGER, created INTEGER, last_seen INTEGER);
    CREATE TABLE groups_(user_id INTEGER, id TEXT, name TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id, id));
    CREATE TABLE categories(user_id INTEGER, id TEXT, group_id TEXT, parent TEXT, name TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id, id));
    CREATE TABLE expenses(user_id INTEGER, id TEXT, group_id TEXT, amount REAL, date TEXT, time TEXT, descr TEXT, note TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id, id));
    CREATE TABLE expense_categories(user_id INTEGER, expense_id TEXT, category_id TEXT, PRIMARY KEY(user_id, expense_id, category_id));
    CREATE TABLE prefs(user_id INTEGER, id TEXT, v TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id, id));
    CREATE TABLE settings(k TEXT PRIMARY KEY, v TEXT);
    ''')
    conn.commit()
    return conn

class ServerSyncEngine:
    def __init__(self, conn):
        self.conn = conn

    def register_user(self, email, password):
        c = self.conn.cursor()
        c.execute("INSERT INTO users(email, hash, created) VALUES (?, ?, ?)",
                  (email, 'hash_' + password, int(time.time())))
        uid = c.lastrowid
        token = f"tok_{uid}_{int(time.time()*1000)}"
        thash = hashlib.sha256(token.encode()).hexdigest()
        c.execute("INSERT INTO tokens VALUES (?, ?, ?, ?)", (thash, uid, int(time.time()), int(time.time())))
        self.conn.commit()
        return uid, token

    def authenticate_token(self, token):
        if not token:
            return None, "লগইন করুন", 401
        thash = hashlib.sha256(token.encode()).hexdigest()
        c = self.conn.cursor()
        c.execute("SELECT user_id, created, last_seen FROM tokens WHERE token_hash=?", (thash,))
        row = c.fetchone()
        if not row:
            return None, "লগইন করুন", 401
        now = int(time.time())
        if (now - row['last_seen']) > 90 * 86400:
            c.execute("DELETE FROM tokens WHERE token_hash=?", (thash,))
            self.conn.commit()
            return None, "নিষ্ক্রিয়তার কারণে লগইনের মেয়াদ শেষ হয়ে গেছে। পুনরায় লগইন করুন।", 401
        u = row['user_id']
        c.execute("SELECT status FROM users WHERE id=?", (u,))
        stt = c.fetchone()
        if stt and stt['status'] != 'active':
            return None, "অ্যাকাউন্ট বন্ধ আছে", 401
        return u, None, 200

    def sync(self, payload):
        token = payload.get('token', '')
        u, err, status = self.authenticate_token(token)
        if err:
            return {'error': err}, status

        now_ms = int(time.time() * 1000)
        since = max(0, int(payload.get('since', 0)))
        P = payload.get('parents', [])
        C = payload.get('cats', [])
        E = payload.get('exps', [])
        R = payload.get('prefs', [])
        limit = payload.get('limit', 150)
        batch_limit = max(1, min(200, int(limit)))

        clamp = lambda v: min(int(v), now_ms + 300000)
        pushed = {'groups_': [], 'categories': [], 'expenses': [], 'prefs': []}
        rejected = {'expenses': [], 'categories': []}

        c = self.conn.cursor()
        c.execute("SELECT rev FROM users WHERE id=?", (u,))
        rev = c.fetchone()['rev']

        # Conflict resolution helper: Deterministic LWW with Phase 2 tie-breaking and deletion dominance
        def newer(tbl, record_id, upd, is_deleted=False, item_data=None):
            c.execute(f"SELECT updated, deleted FROM {tbl} WHERE user_id=? AND id=?", (u, record_id))
            row = c.fetchone()
            if not row:
                return True
            ex_upd = row['updated']
            ex_del = row['deleted']

            # 1. Different timestamps: higher timestamp always wins (LWW)
            if upd > ex_upd:
                return True
            if upd < ex_upd:
                return False

            # 2. Equal timestamps: Deletions dominate (accepted if incoming.updated >= existing.updated)
            if is_deleted and not ex_del:
                return True
            if not is_deleted and ex_del:
                return False

            # 3. Equal timestamps & same deletion state: Deterministic tie-breaker
            # String comparison of incoming payload hash vs existing database record hash
            if item_data is not None:
                in_hash = hashlib.md5((str(record_id) + '|' + json.dumps(item_data, sort_keys=True)).encode()).hexdigest()
                c.execute(f"SELECT * FROM {tbl} WHERE user_id=? AND id=?", (u, record_id))
                ex_row = dict(c.fetchone())
                ex_row.pop('rev', None)
                ex_hash = hashlib.md5((str(record_id) + '|' + json.dumps(ex_row, sort_keys=True)).encode()).hexdigest()
                return in_hash > ex_hash
            return False

        # 1. Process Groups
        for p in P:
            p_id = p.get('id')
            if p_id:
                pushed['groups_'].append(p_id)
                upd = clamp(p.get('updated', 0))
                p_del = bool(p.get('deleted'))
                if newer('groups_', p_id, upd, p_del, p):
                    rev += 1
                    c.execute("INSERT OR REPLACE INTO groups_ VALUES (?, ?, ?, ?, ?, ?)",
                              (u, p_id, p.get('name', ''), upd, 1 if p_del else 0, rev))

        # Active groups
        c.execute("SELECT id FROM groups_ WHERE user_id=? AND deleted=0", (u,))
        group_set = set(r[0] for r in c.fetchall())

        # Active categories
        c.execute("SELECT id FROM categories WHERE user_id=? AND deleted=0", (u,))
        cat_set = set(r[0] for r in c.fetchall())
        for cat in C:
            if cat.get('id') and not cat.get('deleted'):
                cat_set.add(cat['id'])

        # 2. Process Categories
        for cat in C:
            cid = cat.get('id')
            if not cid:
                continue
            upd = clamp(cat.get('updated', 0))
            c_pid = cat.get('pid') if (cat.get('pid') in group_set) else None
            c_del = bool(cat.get('deleted'))
            if newer('categories', cid, upd, c_del, cat):
                if not c_pid:
                    if c_del:
                        c.execute("SELECT group_id FROM categories WHERE user_id=? AND id=?", (u, cid))
                        if c.fetchone():
                            rev += 1
                            c.execute("UPDATE categories SET deleted=1, updated=?, rev=? WHERE user_id=? AND id=?",
                                      (upd, rev, u, cid))
                            pushed['categories'].append(cid)
                        else:
                            rejected['categories'].append({'id': cid, 'reason': 'invalid_group'})
                    else:
                        rejected['categories'].append({'id': cid, 'reason': 'invalid_group'})
                    continue
                pushed['categories'].append(cid)
                c_parent = cat.get('parent') if (cat.get('parent') in cat_set and cat.get('parent') != cid) else None
                rev += 1
                c.execute("INSERT OR REPLACE INTO categories VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (u, cid, c_pid, c_parent, cat.get('name', ''), upd, 1 if c_del else 0, rev))
            else:
                pushed['categories'].append(cid)

        # Refresh active categories
        c.execute("SELECT id FROM categories WHERE user_id=? AND deleted=0", (u,))
        cat_set = set(r[0] for r in c.fetchall())

        # 3. Process Expenses
        for exp in E:
            eid = exp.get('id')
            if not eid:
                continue
            upd = clamp(exp.get('updated', 0))
            e_pid = exp.get('pid') if (exp.get('pid') in group_set) else None
            e_del = bool(exp.get('deleted'))
            if newer('expenses', eid, upd, e_del, exp):
                if not e_pid:
                    if e_del:
                        c.execute("SELECT group_id FROM expenses WHERE user_id=? AND id=?", (u, eid))
                        if c.fetchone():
                            rev += 1
                            c.execute("UPDATE expenses SET deleted=1, updated=?, rev=? WHERE user_id=? AND id=?",
                                      (upd, rev, u, eid))
                            pushed['expenses'].append(eid)
                        else:
                            rejected['expenses'].append({'id': eid, 'reason': 'invalid_group'})
                    else:
                        rejected['expenses'].append({'id': eid, 'reason': 'invalid_group'})
                    continue
                pushed['expenses'].append(eid)
                amt = max(0.0, float(exp.get('amt', 0)))
                rev += 1
                c.execute("INSERT OR REPLACE INTO expenses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (u, eid, e_pid, amt, exp.get('dt', ''), exp.get('tm', ''), exp.get('desc', ''),
                           exp.get('note', ''), upd, 1 if e_del else 0, rev))
                c.execute("DELETE FROM expense_categories WHERE user_id=? AND expense_id=?", (u, eid))
                for cat_id in exp.get('cats', []):
                    if cat_id in cat_set:
                        c.execute("INSERT OR IGNORE INTO expense_categories VALUES (?, ?, ?)", (u, eid, cat_id))
            else:
                pushed['expenses'].append(eid)

        # 4. Process Preferences
        for pref in R:
            pid = pref.get('id')
            if pid:
                pushed['prefs'].append(pid)
                upd = clamp(pref.get('updated', 0))
                r_del = bool(pref.get('deleted'))
                if newer('prefs', pid, upd, r_del, pref):
                    rev += 1
                    c.execute("INSERT OR REPLACE INTO prefs VALUES (?, ?, ?, ?, ?, ?)",
                              (u, pid, pref.get('v', ''), upd, 1 if r_del else 0, rev))

        c.execute("UPDATE users SET rev=?, synced=? WHERE id=?", (rev, int(time.time()), u))
        self.conn.commit()

        # Stale cursor detection
        if since > rev:
            since = 0

        # Pagination & delta collection
        c.execute('''
        SELECT rev FROM (
            SELECT rev FROM groups_ WHERE user_id=? AND rev>?
            UNION ALL
            SELECT rev FROM categories WHERE user_id=? AND rev>?
            UNION ALL
            SELECT rev FROM expenses WHERE user_id=? AND rev>?
            UNION ALL
            SELECT rev FROM prefs WHERE user_id=? AND rev>?
        ) ORDER BY rev ASC LIMIT ?
        ''', (u, since, u, since, u, since, u, since, batch_limit + 1))
        rev_rows = [r[0] for r in c.fetchall()]

        has_more = len(rev_rows) > batch_limit
        next_since = rev_rows[batch_limit - 1] if has_more else rev

        def sel(tbl):
            ids = list(set(pushed[tbl]))
            if has_more:
                if ids:
                    placeholders = ','.join(['?'] * len(ids))
                    sql = f"SELECT * FROM {tbl} WHERE user_id=? AND ((rev>? AND rev<=?) OR id IN ({placeholders}))"
                    c.execute(sql, [u, since, next_since] + ids)
                else:
                    sql = f"SELECT * FROM {tbl} WHERE user_id=? AND (rev>? AND rev<=?)"
                    c.execute(sql, (u, since, next_since))
            else:
                if ids:
                    placeholders = ','.join(['?'] * len(ids))
                    sql = f"SELECT * FROM {tbl} WHERE user_id=? AND (rev>? OR id IN ({placeholders}))"
                    c.execute(sql, [u, since] + ids)
                else:
                    sql = f"SELECT * FROM {tbl} WHERE user_id=? AND rev>?"
                    c.execute(sql, (u, since))
            return [dict(r) for r in c.fetchall()]

        # Prepare final delta payload
        parents = [{'id': p['id'], 'name': p['name'], 'updated': p['updated'], 'deleted': p['deleted']} for p in sel('groups_')]
        cats = [{'id': ct['id'], 'pid': ct['group_id'], 'parent': ct['parent'], 'name': ct['name'], 'updated': ct['updated'], 'deleted': ct['deleted']} for ct in sel('categories')]
        prefs = [{'id': pr['id'], 'v': pr['v'], 'updated': pr['updated'], 'deleted': pr['deleted']} for pr in sel('prefs')]

        exps = []
        for e in sel('expenses'):
            c.execute("SELECT category_id FROM expense_categories WHERE user_id=? AND expense_id=?", (u, e['id']))
            e_cats = [r[0] for r in c.fetchall()]
            exps.append({
                'id': e['id'], 'pid': e['group_id'], 'amt': float(e['amount']), 'dt': e['date'],
                'tm': e['time'], 'desc': e['descr'], 'note': e['note'], 'updated': e['updated'],
                'deleted': e['deleted'], 'cats': e_cats
            })

        return {
            'since': next_since,
            'more': has_more,
            'now': now_ms,
            'parents': parents,
            'cats': cats,
            'prefs': prefs,
            'exps': exps,
            'rejected': rejected
        }, 200


class SimulatedClientDevice:
    """Simulates a browser or Capacitor client running the exact logic of index.html"""
    def __init__(self, name, server_engine, token):
        self.device_name = name
        self.server = server_engine
        self.token = token
        self.SK = 0
        self.state = {
            'sym': '৳',
            'parents': [],
            'cats': [],
            'exps': [],
            'prefs': [],
            'since': 0
        }

    def tc(self, obj):
        now_ts = int(time.time() * 1000) + self.SK
        prev_upd = obj.get('updated', 0)
        self.last_ts = max(now_ts, getattr(self, 'last_ts', 0) + 20, prev_upd + 50)
        obj['updated'] = self.last_ts
        obj['_d'] = 1
        return obj

    def sync(self, limit=150, interrupt_at=None):
        """
        Executes client sync algorithm.
        interrupt_at:
          - 'upload': network fails before server gets upload
          - 'download': server processes upload, but network drops before client gets response
        """
        if interrupt_at == 'upload':
            return False, "Network dropped during upload"

        snap = {}
        room = 200
        dirty_parents = []
        dirty_cats = []
        dirty_exps = []
        dirty_prefs = []

        for p in self.state['parents']:
            if p.get('_d') and room > 0:
                room -= 1
                snap[p['id']] = p['updated']
                r = dict(p)
                r.pop('_d', None)
                dirty_parents.append(r)

        for c in self.state['cats']:
            if c.get('_d') and room > 0:
                room -= 1
                snap[c['id']] = c['updated']
                r = dict(c)
                r.pop('_d', None)
                dirty_cats.append(r)

        for e in self.state['exps']:
            if e.get('_d') and room > 0:
                room -= 1
                snap[e['id']] = e['updated']
                r = dict(e)
                r.pop('_d', None)
                dirty_exps.append(r)

        for pr in self.state['prefs']:
            if pr.get('_d') and room > 0:
                room -= 1
                snap[pr['id']] = pr['updated']
                r = dict(pr)
                r.pop('_d', None)
                dirty_prefs.append(r)

        payload = {
            'token': self.token,
            'since': self.state['since'],
            'parents': dirty_parents,
            'cats': dirty_cats,
            'exps': dirty_exps,
            'prefs': dirty_prefs,
            'limit': limit
        }

        resp, status = self.server.sync(payload)

        if interrupt_at == 'download':
            return False, "Network dropped before client received download payload"

        if status != 200:
            return False, resp.get('error', 'Server error')

        # Adjust clock skew
        if resp.get('now'):
            self.SK = resp['now'] - int(time.time() * 1000)

        conf_p = set(x['id'] for x in resp.get('parents', []))
        conf_c = set(x['id'] for x in resp.get('cats', []))
        conf_e = set(x['id'] for x in resp.get('exps', []))
        conf_pr = set(x['id'] for x in resp.get('prefs', []))
        rej_e = set(x['id'] if isinstance(x, dict) else x for x in resp.get('rejected', {}).get('expenses', []))

        # Clear _d flags for confirmed items
        for p in self.state['parents']:
            if p.get('_d') and snap.get(p['id']) == p['updated'] and p['id'] in conf_p:
                p.pop('_d', None)

        for pr in self.state['prefs']:
            if pr.get('_d') and snap.get(pr['id']) == pr['updated'] and pr['id'] in conf_pr:
                pr.pop('_d', None)

        for c in self.state['cats']:
            if c.get('_d') and snap.get(c['id']) == c['updated']:
                if c['id'] in conf_c:
                    c.pop('_d', None)
                    c.pop('_rej', None)
                else:
                    c['_rej'] = 1

        for e in self.state['exps']:
            if e.get('_d') and snap.get(e['id']) == e['updated']:
                if e['id'] in conf_e:
                    e.pop('_d', None)
                    e.pop('_rej', None)
                else:
                    e['_rej'] = 1

        # Merge incoming deltas
        pairs = [
            (self.state['parents'], resp.get('parents', [])),
            (self.state['cats'], resp.get('cats', [])),
            (self.state['exps'], resp.get('exps', [])),
            (self.state['prefs'], resp.get('prefs', []))
        ]

        for loc, inc in pairs:
            for item in inc:
                existing = next((x for x in loc if x['id'] == item['id']), None)
                if not existing:
                    loc.append(item)
                elif not existing.get('_d'):
                    existing.update(item)

        self.state['since'] = resp['since']

        # If server says more, client loops again
        if resp.get('more'):
            self.sync(limit=limit)

        return True, "Synced successfully"


def run_phase10_test_suite():
    print("================================================================================")
    print("STARTING PHASE 10 MULTI-DEVICE ONLINE SYNCHRONIZATION TEST SUITE")
    print("================================================================================")

    db_conn = setup_server_db()
    server = ServerSyncEngine(db_conn)

    # Setup User 1 (Multi-Device) and User 2 (Isolation Check)
    u1_id, u1_token = server.register_user("albert@example.com", "SecretPass123")
    u2_id, u2_token = server.register_user("other@example.com", "OtherPass123")

    devA = SimulatedClientDevice("Device A", server, u1_token)
    devB = SimulatedClientDevice("Device B", server, u1_token)
    devOther = SimulatedClientDevice("Foreign Device", server, u2_token)

    # --------------------------------------------------------------------------
    # 1. Device A to Device B synchronization
    # --------------------------------------------------------------------------
    grp1 = devA.tc({'id': 'grp-college', 'name': 'College Life', 'deleted': 0})
    devA.state['parents'].append(grp1)
    expA1 = devA.tc({'id': 'exp-a1', 'pid': 'grp-college', 'amt': 450.0, 'dt': '2026-10-30', 'tm': '10:00', 'desc': 'Books', 'note': '', 'cats': [], 'deleted': 0})
    devA.state['exps'].append(expA1)

    ok, msg = devA.sync()
    assert ok and '_d' not in expA1, "Device A must sync successfully and clear dirty flags"

    ok, msg = devB.sync()
    assert ok, "Device B must download Device A's data"
    b_exp = next((e for e in devB.state['exps'] if e['id'] == 'exp-a1'), None)
    assert b_exp is not None and b_exp['amt'] == 450.0, "Device B must possess Device A's expense"
    print("[PASS 1] Device A to Device B synchronization verified.")

    # --------------------------------------------------------------------------
    # 2. Device B to Device A synchronization
    # --------------------------------------------------------------------------
    expB1 = devB.tc({'id': 'exp-b1', 'pid': 'grp-college', 'amt': 120.0, 'dt': '2026-10-30', 'tm': '11:00', 'desc': 'Snacks', 'note': '', 'cats': [], 'deleted': 0})
    devB.state['exps'].append(expB1)
    devB.sync()

    devA.sync()
    a_exp = next((e for e in devA.state['exps'] if e['id'] == 'exp-b1'), None)
    assert a_exp is not None and a_exp['amt'] == 120.0, "Device A must receive changes made on Device B"
    print("[PASS 2] Device B to Device A synchronization verified.")

    # --------------------------------------------------------------------------
    # 3. New expense synchronization
    # --------------------------------------------------------------------------
    exp_new = devA.tc({'id': 'exp-new-99', 'pid': 'grp-college', 'amt': 800.0, 'dt': '2026-10-30', 'tm': '12:00', 'desc': 'Lab Fee', 'note': '', 'cats': [], 'deleted': 0})
    devA.state['exps'].append(exp_new)
    devA.sync()
    devB.sync()
    assert any(e['id'] == 'exp-new-99' and e['amt'] == 800.0 for e in devB.state['exps'])
    print("[PASS 3] New expense synchronization verified.")

    # --------------------------------------------------------------------------
    # 4. Updated expense synchronization
    # --------------------------------------------------------------------------
    b_target = next(e for e in devB.state['exps'] if e['id'] == 'exp-new-99')
    b_target['amt'] = 850.0
    b_target['desc'] = 'Lab Fee & Materials'
    devB.tc(b_target)
    devB.sync()

    devA.sync()
    a_target = next(e for e in devA.state['exps'] if e['id'] == 'exp-new-99')
    assert a_target['amt'] == 850.0 and a_target['desc'] == 'Lab Fee & Materials', "Updated expense must sync correctly"
    print("[PASS 4] Updated expense synchronization verified.")

    # --------------------------------------------------------------------------
    # 5. Group and category synchronization
    # --------------------------------------------------------------------------
    cat1 = devA.tc({'id': 'cat-tuition', 'pid': 'grp-college', 'parent': None, 'name': 'Tuition', 'deleted': 0})
    cat2 = devA.tc({'id': 'cat-monthly', 'pid': 'grp-college', 'parent': 'cat-tuition', 'name': 'Monthly Fee', 'deleted': 0})
    devA.state['cats'].extend([cat1, cat2])
    devA.sync()

    devB.sync()
    assert any(c['id'] == 'cat-monthly' and c['parent'] == 'cat-tuition' for c in devB.state['cats'])
    print("[PASS 5] Group and hierarchical category synchronization verified.")

    # --------------------------------------------------------------------------
    # 6. Preference synchronization
    # --------------------------------------------------------------------------
    pref1 = devA.tc({'id': 'defg', 'v': 'grp-college', 'deleted': 0})
    pref2 = devA.tc({'id': 'sym', 'v': '৳', 'deleted': 0})
    pref3 = devA.tc({'id': 'budget:grp-college', 'v': '18000', 'deleted': 0})
    devA.state['prefs'].extend([pref1, pref2, pref3])
    devA.sync()

    devB.sync()
    assert any(p['id'] == 'budget:grp-college' and p['v'] == '18000' for p in devB.state['prefs'])
    print("[PASS 6] Preference and budget limits synchronization verified.")

    # --------------------------------------------------------------------------
    # 7. Incremental delta synchronization
    # --------------------------------------------------------------------------
    old_cursor = devB.state['since']
    exp_inc = devA.tc({'id': 'exp-inc-1', 'pid': 'grp-college', 'amt': 50.0, 'dt': '2026-10-30', 'tm': '13:00', 'desc': 'Tea', 'note': '', 'cats': [], 'deleted': 0})
    devA.state['exps'].append(exp_inc)
    devA.sync()

    # Device B syncs only delta (since old_cursor)
    devB.sync()
    assert devB.state['since'] > old_cursor, "Delta sync must advance synchronization cursor"
    assert any(e['id'] == 'exp-inc-1' for e in devB.state['exps'])
    print("[PASS 7] Incremental delta synchronization verified.")

    # --------------------------------------------------------------------------
    # 8. Pagination and 'more' cursor
    # --------------------------------------------------------------------------
    # Create 8 expenses on Device A
    for i in range(1, 9):
        e = devA.tc({'id': f'exp-page-{i}', 'pid': 'grp-college', 'amt': 10.0 * i, 'dt': '2026-10-30', 'tm': '14:00', 'desc': f'Bulk {i}', 'note': '', 'cats': [], 'deleted': 0})
        devA.state['exps'].append(e)
    devA.sync()

    # Create fresh Device C for same user with since=0 and limit=3
    devC = SimulatedClientDevice("Device C", server, u1_token)
    devC.sync(limit=3) # Will trigger multi-page pagination with more=true
    # Device C should have received all items
    for i in range(1, 9):
        assert any(e['id'] == f'exp-page-{i}' for e in devC.state['exps']), f"Pagination must not skip item {i}"
    print("[PASS 8] Pagination, batch limit, and 'more' cursor multi-page downloads verified.")

    # --------------------------------------------------------------------------
    # 9. Deletion tombstones
    # --------------------------------------------------------------------------
    del_target = next(e for e in devA.state['exps'] if e['id'] == 'exp-page-1')
    del_target['deleted'] = 1
    devA.tc(del_target)
    devA.sync()

    devB.sync()
    b_del = next(e for e in devB.state['exps'] if e['id'] == 'exp-page-1')
    assert b_del['deleted'] == 1, "Tombstones must propagate deletion to other devices"
    print("[PASS 9] Deletion tombstones and multi-device propagation verified.")

    # --------------------------------------------------------------------------
    # 10. Simultaneous edits and conflict resolution (Phase 2 Deterministic Policy)
    # --------------------------------------------------------------------------
    # 10.A: Different timestamps: higher timestamp wins (LWW)
    target_a = next(e for e in devA.state['exps'] if e['id'] == 'exp-page-2')
    target_b = next(e for e in devB.state['exps'] if e['id'] == 'exp-page-2')

    base_ts = target_a['updated']
    target_a['amt'] = 222.0
    devA.tc(target_a)
    target_a['updated'] = base_ts + 1000 # Device A edit (+1s)

    target_b['amt'] = 333.0
    devB.tc(target_b)
    target_b['updated'] = base_ts + 5000 # Device B edit (+5s, newer, LWW should win)

    devA.sync()
    devB.sync()
    devA.sync()

    res_a = next(e for e in devA.state['exps'] if e['id'] == 'exp-page-2')
    res_b = next(e for e in devB.state['exps'] if e['id'] == 'exp-page-2')
    assert res_a['amt'] == 333.0 and res_b['amt'] == 333.0, "Newer edit (LWW) must win deterministically"

    # 10.B: Equal timestamps edit vs edit: Deterministic tie-breaker
    # Edit 'exp-page-3' on both devices at the EXACT same timestamp
    p3_a = next(e for e in devA.state['exps'] if e['id'] == 'exp-page-3')
    p3_b = next(e for e in devB.state['exps'] if e['id'] == 'exp-page-3')
    equal_ts = base_ts + 9000

    p3_a['desc'] = 'Equal TS Edit A'
    p3_a['updated'] = equal_ts
    p3_a['_d'] = 1

    p3_b['desc'] = 'Equal TS Edit B'
    p3_b['updated'] = equal_ts
    p3_b['_d'] = 1

    # Device A syncs, then Device B syncs
    devA.sync()
    devB.sync()
    devA.sync()

    final_p3_a = next(e for e in devA.state['exps'] if e['id'] == 'exp-page-3')
    final_p3_b = next(e for e in devB.state['exps'] if e['id'] == 'exp-page-3')
    assert final_p3_a['desc'] == final_p3_b['desc'], "Equal timestamp edits must deterministically converge"

    # 10.C: Equal timestamps deletion vs update: Deletion dominates
    # Device A edits 'exp-page-4' at equal_del_ts, Device B deletes 'exp-page-4' at equal_del_ts
    p4_a = next(e for e in devA.state['exps'] if e['id'] == 'exp-page-4')
    p4_b = next(e for e in devB.state['exps'] if e['id'] == 'exp-page-4')
    equal_del_ts = base_ts + 12000

    p4_a['amt'] = 777.0
    p4_a['updated'] = equal_del_ts
    p4_a['_d'] = 1

    p4_b['deleted'] = 1
    p4_b['updated'] = equal_del_ts
    p4_b['_d'] = 1

    devA.sync()
    devB.sync()
    devA.sync()

    final_p4_a = next(e for e in devA.state['exps'] if e['id'] == 'exp-page-4')
    final_p4_b = next(e for e in devB.state['exps'] if e['id'] == 'exp-page-4')
    assert final_p4_a['deleted'] == 1 and final_p4_b['deleted'] == 1, "Deletions must dominate when timestamps are equal"
    print("[PASS 10] Simultaneous edits, deterministic tie-breaking, and deletion dominance verified.")

    # --------------------------------------------------------------------------
    # 11. Clock-skew handling
    # --------------------------------------------------------------------------
    # Device A has a clock set 2 hours in the future
    skew_exp = devA.tc({'id': 'exp-skew-1', 'pid': 'grp-college', 'amt': 75.0, 'dt': '2026-10-30', 'tm': '15:00', 'desc': 'Future Clock', 'note': '', 'cats': [], 'deleted': 0})
    skew_exp['updated'] = int(time.time() * 1000) + (7200 * 1000)
    devA.state['exps'].append(skew_exp)
    devA.sync()

    # Server should have clamped it to server_now + 300,000 ms
    c = db_conn.cursor()
    c.execute("SELECT updated FROM expenses WHERE id='exp-skew-1'")
    clamped_upd = c.fetchone()['updated']
    server_now = int(time.time() * 1000)
    assert clamped_upd <= server_now + 305000, "Future clock skew must be safely clamped"
    print("[PASS 11] Clock-skew clamping and future timestamp protection verified.")

    # --------------------------------------------------------------------------
    # 12. Interrupted upload and retry
    # --------------------------------------------------------------------------
    retry_exp = devA.tc({'id': 'exp-retry-up', 'pid': 'grp-college', 'amt': 99.0, 'dt': '2026-10-30', 'tm': '16:00', 'desc': 'Upload Retry', 'note': '', 'cats': [], 'deleted': 0})
    devA.state['exps'].append(retry_exp)

    # Interrupt during upload (network dropped before reaching server)
    ok, err = devA.sync(interrupt_at='upload')
    assert not ok and retry_exp.get('_d') == 1, "Failed upload must retain dirty flag"

    # Retry upload
    ok, err = devA.sync()
    assert ok and '_d' not in retry_exp, "Retry must successfully sync and clear dirty flag"
    print("[PASS 12] Interrupted upload and safe retry without data loss verified.")

    # --------------------------------------------------------------------------
    # 13. Interrupted download and retry
    # --------------------------------------------------------------------------
    dn_exp = devA.tc({'id': 'exp-retry-dn', 'pid': 'grp-college', 'amt': 140.0, 'dt': '2026-10-30', 'tm': '17:00', 'desc': 'Download Retry', 'note': '', 'cats': [], 'deleted': 0})
    devA.state['exps'].append(dn_exp)

    # Server processes upload, but client network drops before receiving payload
    ok, err = devA.sync(interrupt_at='download')
    assert not ok and dn_exp.get('_d') == 1, "Client must not clear dirty flag if download was interrupted"

    # Client retries sync: server idempotently accepts it and returns confirmation
    ok, err = devA.sync()
    assert ok and '_d' not in dn_exp, "Subsequent retry must confirm item and clear dirty flag"
    print("[PASS 13] Interrupted download recovery and idempotent server confirmation verified.")

    # --------------------------------------------------------------------------
    # 14. Duplicate prevention
    # --------------------------------------------------------------------------
    # Ensure repeated syncs never duplicate expense records
    c.execute("SELECT COUNT(*) FROM expenses WHERE user_id=? AND id='exp-retry-dn'", (u1_id,))
    count_dn = c.fetchone()[0]
    assert count_dn == 1, "Primary key composite (user_id, id) must prevent duplicate records"
    print("[PASS 14] Duplicate record prevention verified.")

    # --------------------------------------------------------------------------
    # 15. Stale cursor full resynchronization
    # --------------------------------------------------------------------------
    # Corrupt Device C cursor to 999999 (ahead of server)
    devC.state['since'] = 999999
    # Add a new expense on Device A
    stale_test_exp = devA.tc({'id': 'exp-stale-test', 'pid': 'grp-college', 'amt': 300.0, 'dt': '2026-10-30', 'tm': '18:00', 'desc': 'Stale Test', 'note': '', 'cats': [], 'deleted': 0})
    devA.state['exps'].append(stale_test_exp)
    devA.sync()

    # Device C syncs with stale cursor: server resets since to 0 and returns all deltas
    devC.sync()
    assert any(e['id'] == 'exp-stale-test' for e in devC.state['exps']), "Stale cursor must trigger full resync"
    print("[PASS 15] Stale cursor detection and full delta resynchronization verified.")

    # --------------------------------------------------------------------------
    # 16. Rejected expense preservation (Phase 6 recovery flow)
    # --------------------------------------------------------------------------
    # Device A creates an expense with an invalid/empty group ID
    invalid_exp = devA.tc({'id': 'exp-invalid-grp', 'pid': '', 'amt': 60.0, 'dt': '2026-10-30', 'tm': '19:00', 'desc': 'No Group', 'note': '', 'cats': [], 'deleted': 0})
    devA.state['exps'].append(invalid_exp)
    devA.sync()

    # The expense MUST NOT be confirmed and MUST NOT be deleted; it must be preserved with _rej=1
    assert invalid_exp.get('_rej') == 1, "Rejected expense must be marked _rej=1"
    assert any(e['id'] == 'exp-invalid-grp' for e in devA.state['exps']), "Rejected expense must be preserved locally"

    # User fixes group ID
    invalid_exp['pid'] = 'grp-college'
    devA.tc(invalid_exp) # Sets _d = 1
    devA.sync()
    assert '_d' not in invalid_exp and '_rej' not in invalid_exp, "Fixed expense must synchronize cleanly"
    print("[PASS 16] Rejected expense preservation and user recovery verified.")

    # --------------------------------------------------------------------------
    # 17. Multi-user isolation
    # --------------------------------------------------------------------------
    # Foreign device (User 2) syncs
    grp_foreign = devOther.tc({'id': 'grp-other', 'name': 'Secret User 2 Group', 'deleted': 0})
    devOther.state['parents'].append(grp_foreign)
    exp_foreign = devOther.tc({'id': 'exp-other-1', 'pid': 'grp-other', 'amt': 9999.0, 'dt': '2026-10-30', 'tm': '20:00', 'desc': 'Private', 'note': '', 'cats': [], 'deleted': 0})
    devOther.state['exps'].append(exp_foreign)
    devOther.sync()

    # User 1 syncs on Device A and Device B
    devA.sync()
    devB.sync()
    assert not any(e['id'] == 'exp-other-1' for e in devA.state['exps']), "User 1 must NEVER receive User 2's data"
    assert not any(e['id'] == 'exp-other-1' for e in devB.state['exps']), "User 1 must NEVER receive User 2's data"
    print("[PASS 17] Strict multi-user data isolation verified.")

    # --------------------------------------------------------------------------
    # 18. Expired/revoked token handling
    # --------------------------------------------------------------------------
    # Revoke User 2 token
    thash2 = hashlib.sha256(u2_token.encode()).hexdigest()
    c.execute("DELETE FROM tokens WHERE token_hash=?", (thash2,))
    db_conn.commit()

    ok, err = devOther.sync()
    assert not ok and "লগইন করুন" in str(err), "Revoked token must be rejected with 401"
    print("[PASS 18] Expired/revoked token rejection verified.")

    # --------------------------------------------------------------------------
    # 19. Repeated synchronization consistency
    # --------------------------------------------------------------------------
    # Repeated sync calls when up to date should be no-ops and preserve total state
    cur_since_a = devA.state['since']
    devA.sync()
    devA.sync()
    assert devA.state['since'] == cur_since_a, "Repeated sync when up to date must remain consistent"

    # Confirm record counts match between Device A and Device B for active expenses
    active_a = sorted([e['id'] for e in devA.state['exps'] if not e.get('deleted')])
    active_b = sorted([e['id'] for e in devB.state['exps'] if not e.get('deleted')])
    assert active_a == active_b, f"Device A and Device B active expenses must match exactly: {active_a} vs {active_b}"
    print("[PASS 19] Repeated synchronization consistency and cross-device parity verified.")

    print("\n================================================================================")
    print("ALL 19 PHASE 10 MULTI-DEVICE SYNCHRONIZATION TESTS EXECUTED AND PASSED!")
    print("================================================================================")
    return True

if __name__ == '__main__':
    success = run_phase10_test_suite()
    if not success:
        sys.exit(1)
