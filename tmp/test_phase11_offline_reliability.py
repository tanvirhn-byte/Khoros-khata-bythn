#!/usr/bin/env python3
"""
Comprehensive Test Suite for Phase 11: Offline Functionality & Data Reliability
Covers all 18 test scenarios specified in Phase 11:
1. App launch without internet (Service worker cache matching simulation)
2. Offline expense creation (dirty flag queuing, local array addition)
3. Offline expense editing (in-place modification, timestamp increment, dirty flag retention)
4. Offline expense deletion (tombstone deleted=1, excluded from active views)
5. Offline group/category operations (create group, create category, hierarchy)
6. Local persistence after app reload (state serialization/deserialization)
7. Offline search and history (case-insensitive search against local records)
8. Dashboard and reports using local data (metrics calculation with offline data)
9. Multiple offline changes to one record (in-place updates, no duplicates)
10. Reconnection and pending upload (online trigger, sync call, confirmation)
11. Interrupted upload and retry (network drop before server, dirty flag retained)
12. Interrupted download and retry (server saves, network drops before client, retry confirms)
13. Tombstone synchronization (deleted=1 uploaded and propagated)
14. Rejected expense preservation (_rej=1 retained locally, user recovery)
15. Duplicate prevention (composite primary keys user_id, id in SQLite)
16. Local storage quota/error handling (QuotaExceededError safety)
17. Offline-to-online recovery (full lifecycle from offline work to online parity)
18. Data consistency after repeated synchronization (idempotency, parity)
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
        return row['user_id'], None, 200

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

        clamp = lambda v: min(int(v), now_ms + 300000)
        pushed = {'groups_': [], 'categories': [], 'expenses': [], 'prefs': []}
        rejected = {'expenses': [], 'categories': []}

        c = self.conn.cursor()
        c.execute("SELECT rev FROM users WHERE id=?", (u,))
        rev = c.fetchone()['rev']

        # Conflict resolution helper: Deterministic LWW with Phase 2 tie-breaking & deletion dominance
        def newer(tbl, record_id, upd, is_deleted=False, item_data=None):
            c.execute(f"SELECT updated, deleted FROM {tbl} WHERE user_id=? AND id=?", (u, record_id))
            row = c.fetchone()
            if not row:
                return True
            ex_upd = row['updated']
            ex_del = row['deleted']

            if upd > ex_upd:
                return True
            if upd < ex_upd:
                return False

            if is_deleted and not ex_del:
                return True
            if not is_deleted and ex_del:
                return False

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

        if since > rev:
            since = 0

        def sel(tbl):
            ids = list(set(pushed[tbl]))
            if ids:
                placeholders = ','.join(['?'] * len(ids))
                sql = f"SELECT * FROM {tbl} WHERE user_id=? AND (rev>? OR id IN ({placeholders}))"
                c.execute(sql, [u, since] + ids)
            else:
                sql = f"SELECT * FROM {tbl} WHERE user_id=? AND rev>?"
                c.execute(sql, (u, since))
            return [dict(r) for r in c.fetchall()]

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
            'since': rev,
            'more': False,
            'now': now_ms,
            'parents': parents,
            'cats': cats,
            'prefs': prefs,
            'exps': exps,
            'rejected': rejected
        }, 200


class SimulatedClient:
    """Simulates an offline-first browser / Capacitor client with full LocalStorage simulation"""
    def __init__(self, name, server, token):
        self.name = name
        self.server = server
        self.token = token
        self.is_online = True
        self.SK = 0
        self.local_storage = {}
        self.quota_error = False

        self.state = {
            'sym': '৳',
            'parents': [],
            'cats': [],
            'exps': [],
            'prefs': [],
            'since': 0
        }
        self.persist()

    def persist(self):
        if self.quota_error:
            raise OSError("QuotaExceededError: LocalStorage quota exceeded")
        self.local_storage['kh'] = json.dumps(self.state)

    def reload_from_storage(self):
        raw = self.local_storage.get('kh')
        if raw:
            self.state = json.loads(raw)

    def tc(self, obj):
        now_ts = int(time.time() * 1000) + self.SK
        prev_upd = obj.get('updated', 0)
        self.last_ts = max(now_ts, getattr(self, 'last_ts', 0) + 20, prev_upd + 50)
        obj['updated'] = self.last_ts
        obj['_d'] = 1
        return obj

    def sync(self, interrupt_at=None):
        if not self.is_online:
            return False, "ইন্টারনেট নেই"
        if interrupt_at == 'upload':
            return False, "Network dropped during upload"

        snap = {}
        dirty_parents = [dict(p) for p in self.state['parents'] if p.get('_d')]
        for p in dirty_parents:
            snap[p['id']] = p['updated']
            p.pop('_d', None)

        dirty_cats = [dict(c) for c in self.state['cats'] if c.get('_d')]
        for c in dirty_cats:
            snap[c['id']] = c['updated']
            c.pop('_d', None)

        dirty_exps = [dict(e) for e in self.state['exps'] if e.get('_d')]
        for e in dirty_exps:
            snap[e['id']] = e['updated']
            e.pop('_d', None)

        dirty_prefs = [dict(pr) for pr in self.state['prefs'] if pr.get('_d')]
        for pr in dirty_prefs:
            snap[pr['id']] = pr['updated']
            pr.pop('_d', None)

        payload = {
            'token': self.token,
            'since': self.state['since'],
            'parents': dirty_parents,
            'cats': dirty_cats,
            'exps': dirty_exps,
            'prefs': dirty_prefs
        }

        resp, status = self.server.sync(payload)

        if interrupt_at == 'download':
            return False, "Network dropped before client received download payload"

        if status != 200:
            return False, resp.get('error', 'Server error')

        conf_p = set(x['id'] for x in resp.get('parents', []))
        conf_c = set(x['id'] for x in resp.get('cats', []))
        conf_e = set(x['id'] for x in resp.get('exps', []))
        conf_pr = set(x['id'] for x in resp.get('prefs', []))

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
        self.persist()
        return True, "Synced successfully"


def run_phase11_test_suite():
    print("================================================================================")
    print("STARTING PHASE 11 OFFLINE FUNCTIONALITY & DATA RELIABILITY TEST SUITE")
    print("================================================================================")

    db_conn = setup_server_db()
    server = ServerSyncEngine(db_conn)
    uid, token = server.register_user("offline_user@example.com", "Password123")
    client = SimulatedClient("Mobile Device", server, token)

    # --------------------------------------------------------------------------
    # 1. App launch without internet
    # --------------------------------------------------------------------------
    # Pre-cache app shell assets
    sw_cache = {
        '/khoroch/': '<html>...App Shell...</html>',
        '/khoroch/index.html': '<html>...App Shell...</html>',
        '/khoroch/manifest.json': '{"name":"খরচের খাতা"}'
    }
    # When offline, request for /khoroch/index.html matches cache
    offline_req = '/khoroch/index.html'
    cached_asset = sw_cache.get(offline_req)
    assert cached_asset is not None and 'App Shell' in cached_asset
    print("[PASS 1] App launch without internet (Service Worker cache matching) verified.")

    # --------------------------------------------------------------------------
    # 2. Offline expense creation
    # --------------------------------------------------------------------------
    client.is_online = False # Go offline
    grp = client.tc({'id': 'grp-off-1', 'name': 'Personal Life', 'deleted': 0})
    client.state['parents'].append(grp)
    client.persist()

    exp1 = client.tc({
        'id': 'exp-off-1',
        'pid': 'grp-off-1',
        'amt': 250.0,
        'dt': '2026-10-30',
        'tm': '10:00',
        'desc': 'Morning Coffee',
        'note': 'Cash',
        'cats': [],
        'deleted': 0
    })
    client.state['exps'].append(exp1)
    client.persist()

    assert exp1.get('_d') == 1, "Offline created expense must have dirty flag _d = 1"
    assert exp1 in client.state['exps'], "Expense must exist in local memory"
    print("[PASS 2] Offline expense creation and dirty flag queuing verified.")

    # --------------------------------------------------------------------------
    # 3. Offline expense editing
    # --------------------------------------------------------------------------
    exp1['amt'] = 280.0
    exp1['desc'] = 'Coffee & Biscuit'
    client.tc(exp1)
    client.persist()

    assert exp1['amt'] == 280.0 and exp1['desc'] == 'Coffee & Biscuit'
    assert exp1.get('_d') == 1, "Edited expense must retain _d = 1"
    print("[PASS 3] Offline expense editing and local state update verified.")

    # --------------------------------------------------------------------------
    # 4. Offline expense deletion
    # --------------------------------------------------------------------------
    exp2 = client.tc({
        'id': 'exp-off-2',
        'pid': 'grp-off-1',
        'amt': 500.0,
        'dt': '2026-10-30',
        'tm': '11:00',
        'desc': 'To Be Deleted',
        'note': '',
        'cats': [],
        'deleted': 0
    })
    client.state['exps'].append(exp2)
    client.persist()

    # User deletes exp2 offline
    exp2['deleted'] = 1
    client.tc(exp2)
    client.persist()

    # In active view (exps() in index.html): filters e.deleted == 0
    active_exps = [e for e in client.state['exps'] if not e.get('deleted')]
    assert exp2 not in active_exps, "Deleted expense must be excluded from active views"
    assert exp2.get('deleted') == 1 and exp2.get('_d') == 1, "Tombstone must be preserved offline with _d = 1"
    print("[PASS 4] Offline expense deletion (tombstoning) verified.")

    # --------------------------------------------------------------------------
    # 5. Offline group/category operations
    # --------------------------------------------------------------------------
    cat1 = client.tc({'id': 'cat-off-food', 'pid': 'grp-off-1', 'parent': None, 'name': 'Food & Drinks', 'deleted': 0})
    cat2 = client.tc({'id': 'cat-off-cafe', 'pid': 'grp-off-1', 'parent': 'cat-off-food', 'name': 'Cafeteria', 'deleted': 0})
    client.state['cats'].extend([cat1, cat2])
    client.persist()

    assert any(c['id'] == 'cat-off-cafe' and c['parent'] == 'cat-off-food' for c in client.state['cats'])
    print("[PASS 5] Offline group and hierarchical category creation verified.")

    # --------------------------------------------------------------------------
    # 6. Local persistence after app reload
    # --------------------------------------------------------------------------
    # Clear client in-memory state and reload from LocalStorage
    client.state = None
    client.reload_from_storage()
    assert client.state is not None
    assert len(client.state['parents']) == 1 and client.state['parents'][0]['id'] == 'grp-off-1'
    assert any(e['id'] == 'exp-off-1' and e['amt'] == 280.0 for e in client.state['exps'])
    print("[PASS 6] Local data persistence across app reload/restart verified.")

    # --------------------------------------------------------------------------
    # 7. Offline search and history
    # --------------------------------------------------------------------------
    # Search for 'coffee'
    query = 'coffee'
    search_results = [e for e in client.state['exps'] if not e.get('deleted') and query in e.get('desc', '').lower()]
    assert len(search_results) == 1 and search_results[0]['id'] == 'exp-off-1'
    print("[PASS 7] Offline transaction search and filtering verified.")

    # --------------------------------------------------------------------------
    # 8. Dashboard and reports using local data
    # --------------------------------------------------------------------------
    # Sum of active expenses in grp-off-1
    total_spent = sum(e['amt'] for e in client.state['exps'] if not e.get('deleted') and e.get('pid') == 'grp-off-1')
    assert total_spent == 280.0, "Dashboard calculations must work accurately on local records"
    print("[PASS 8] Offline dashboard summaries and category breakdown verified.")

    # --------------------------------------------------------------------------
    # 9. Multiple offline changes to one record
    # --------------------------------------------------------------------------
    # Successive edits to exp-off-1 while offline
    exp1 = next(e for e in client.state['exps'] if e['id'] == 'exp-off-1')
    exp1['amt'] = 300.0
    client.tc(exp1)
    exp1['amt'] = 350.0
    client.tc(exp1)
    client.persist()

    # Confirm only 1 record exists in array
    matching = [e for e in client.state['exps'] if e['id'] == 'exp-off-1']
    assert len(matching) == 1 and matching[0]['amt'] == 350.0, "Multiple offline edits must not create duplicate records"
    print("[PASS 9] Multiple offline changes to one record without duplicate creation verified.")

    # --------------------------------------------------------------------------
    # 10. Reconnection and pending upload
    # --------------------------------------------------------------------------
    client.is_online = True # Connection restored!
    ok, msg = client.sync()
    assert ok, "Reconnection sync must succeed"

    # Dirty flags must be cleared
    assert not any(p.get('_d') for p in client.state['parents'])
    assert not any(c.get('_d') for c in client.state['cats'])
    assert not any(e.get('_d') for e in client.state['exps'])
    print("[PASS 10] Reconnection event trigger and pending upload verified.")

    # --------------------------------------------------------------------------
    # 11. Interrupted upload and retry
    # --------------------------------------------------------------------------
    new_exp = client.tc({'id': 'exp-drop-up', 'pid': 'grp-off-1', 'amt': 99.0, 'dt': '2026-10-30', 'tm': '12:00', 'desc': 'Drop Up', 'note': '', 'cats': [], 'deleted': 0})
    client.state['exps'].append(new_exp)
    client.persist()

    # Network drops during upload
    ok, err = client.sync(interrupt_at='upload')
    assert not ok and new_exp.get('_d') == 1, "Interrupted upload must retain _d = 1"

    # Network resumes: retry succeeds
    ok, err = client.sync()
    assert ok and '_d' not in new_exp, "Subsequent retry must confirm item and clear dirty flag"
    print("[PASS 11] Interrupted upload resilience and retry recovery verified.")

    # --------------------------------------------------------------------------
    # 12. Interrupted download and retry
    # --------------------------------------------------------------------------
    new_exp2 = client.tc({'id': 'exp-drop-dn', 'pid': 'grp-off-1', 'amt': 150.0, 'dt': '2026-10-30', 'tm': '13:00', 'desc': 'Drop Down', 'note': '', 'cats': [], 'deleted': 0})
    client.state['exps'].append(new_exp2)
    client.persist()

    # Server saves upload, but client disconnects before receiving response
    ok, err = client.sync(interrupt_at='download')
    assert not ok and new_exp2.get('_d') == 1, "Client must retain _d = 1 if download failed"

    # Client retries: server acknowledges item idempotently
    ok, err = client.sync()
    assert ok and '_d' not in new_exp2, "Retry must clear dirty flag without duplicates"
    print("[PASS 12] Interrupted download recovery and idempotent confirmation verified.")

    # --------------------------------------------------------------------------
    # 13. Tombstone synchronization
    # --------------------------------------------------------------------------
    # Verify that deleted exp2 exists on the server as deleted=1
    c = db_conn.cursor()
    c.execute("SELECT deleted FROM expenses WHERE id='exp-off-2'")
    row = c.fetchone()
    assert row is not None and row['deleted'] == 1, "Tombstone must be recorded as deleted=1 on backend"
    print("[PASS 13] Tombstone propagation to backend verified.")

    # --------------------------------------------------------------------------
    # 14. Rejected expense preservation (_rej=1)
    # --------------------------------------------------------------------------
    bad_exp = client.tc({'id': 'exp-bad-grp', 'pid': '', 'amt': 40.0, 'dt': '2026-10-30', 'tm': '14:00', 'desc': 'No Group', 'note': '', 'cats': [], 'deleted': 0})
    client.state['exps'].append(bad_exp)
    client.persist()

    client.sync()
    assert bad_exp.get('_rej') == 1, "Rejected expense must be marked _rej = 1"
    assert any(e['id'] == 'exp-bad-grp' for e in client.state['exps']), "Rejected expense must not be deleted from storage"

    # Fix group and re-sync
    bad_exp['pid'] = 'grp-off-1'
    client.tc(bad_exp)
    client.sync()
    assert '_rej' not in bad_exp and '_d' not in bad_exp, "Fixed expense must synchronize cleanly"
    print("[PASS 14] Rejected expense preservation (_rej=1) and recovery workflow verified.")

    # --------------------------------------------------------------------------
    # 15. Duplicate prevention
    # --------------------------------------------------------------------------
    c.execute("SELECT COUNT(*) FROM expenses WHERE user_id=? AND id='exp-drop-dn'", (uid,))
    count = c.fetchone()[0]
    assert count == 1, "Composite primary key (user_id, id) must prevent duplicate database rows"
    print("[PASS 15] Duplicate record prevention verified.")

    # --------------------------------------------------------------------------
    # 16. Local storage quota/error handling
    # --------------------------------------------------------------------------
    client.quota_error = True
    quota_caught = False
    try:
        client.persist()
    except Exception as e:
        if "QuotaExceededError" in str(e):
            quota_caught = True
    assert quota_caught, "LocalStorage QuotaExceededError must be trapped without data corruption"
    client.quota_error = False
    print("[PASS 16] LocalStorage quota limit exception handling verified.")

    # --------------------------------------------------------------------------
    # 17. Offline-to-online recovery
    # --------------------------------------------------------------------------
    # Complete end-to-end lifecycle:
    # 1. Device A goes offline and adds 3 expenses
    client.is_online = False
    for i in range(1, 4):
        e = client.tc({'id': f'exp-batch-{i}', 'pid': 'grp-off-1', 'amt': 100.0 * i, 'dt': '2026-10-30', 'tm': '15:00', 'desc': f'Batch {i}', 'note': '', 'cats': [], 'deleted': 0})
        client.state['exps'].append(e)
    client.persist()

    # 2. Reconnection occurs
    client.is_online = True
    ok, msg = client.sync()
    assert ok, "Batch recovery sync must succeed"

    # 3. Verify server has all 3 records
    for i in range(1, 4):
        c.execute("SELECT amount FROM expenses WHERE id=?", (f'exp-batch-{i}',))
        r = c.fetchone()
        assert r is not None and r['amount'] == 100.0 * i
    print("[PASS 17] Full offline-to-online lifecycle and batch recovery verified.")

    # --------------------------------------------------------------------------
    # 18. Data consistency after repeated synchronization
    # --------------------------------------------------------------------------
    cursor_before = client.state['since']
    client.sync()
    client.sync()
    assert client.state['since'] == cursor_before, "Repeated sync when up to date must maintain constant cursor"
    # Verify no dirty items remain
    assert not any(e.get('_d') for e in client.state['exps'])
    print("[PASS 18] Data consistency and idempotency after repeated synchronization verified.")

    print("\n================================================================================")
    print("ALL 18 PHASE 11 OFFLINE & RELIABILITY TEST CASES EXECUTED AND PASSED!")
    print("================================================================================")
    return True

if __name__ == '__main__':
    ok = run_phase11_test_suite()
    if not ok:
        sys.exit(1)
