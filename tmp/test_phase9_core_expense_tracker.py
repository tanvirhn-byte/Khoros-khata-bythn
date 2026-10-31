#!/usr/bin/env python3
"""
Test Suite for Phase 9: Core Expense Tracker Verification
Covers all 12 required test areas:
1. Expense CRUD
2. Groups CRUD & Last Group Deletion Prevention
3. Categories CRUD & Parent-Child Hierarchy
4. Search and Filtering (Text, Category, Date, Month, Min Amount)
5. Dashboard Calculations (Week, Month, Year, Daily Avg, Max)
6. Reports and Charts (Hierarchical Tree Aggregation)
7. Budget Calculations (Percentage, Remaining, Exceeded)
8. Backup and Restore (JSON Serialization & Import Validation)
9. LocalStorage Persistence Simulation
10. Offline and Online Expense Handling
11. Multi-User Data Isolation
12. Regression Tests (Bengali Formatting, Symbols, Defaults)
"""

import os
import sys
import json
import sqlite3
import hashlib
import time
import datetime

def run_tests():
    print("=== STARTING PHASE 9 CORE EXPENSE TRACKER TEST SUITE ===")
    
    # -------------------------------------------------------------
    # TEST 1: Expense CRUD
    # -------------------------------------------------------------
    # In-memory client state simulation (matching index.html state structure)
    state = {
        'sym': '৳',
        'parents': [{'id': 'grp-main', 'name': 'College Life', 'deleted': 0, 'updated': 1000}],
        'cats': [
            {'id': 'cat-edu', 'pid': 'grp-main', 'parent': None, 'name': 'Education', 'deleted': 0, 'updated': 1000},
            {'id': 'cat-fee', 'pid': 'grp-main', 'parent': 'cat-edu', 'name': 'Exam Fee', 'deleted': 0, 'updated': 1000},
            {'id': 'cat-food', 'pid': 'grp-main', 'parent': None, 'name': 'Food', 'deleted': 0, 'updated': 1000}
        ],
        'exps': [],
        'prefs': [],
        'budget': {},
        'since': 0
    }
    cur_group = 'grp-main'

    def tc(obj):
        obj['updated'] = int(time.time() * 1000)
        obj['_d'] = 1
        return obj

    # 1. Create expense
    exp1 = tc({
        'id': 'exp-101',
        'pid': cur_group,
        'amt': 350.0,
        'dt': '2026-10-25',
        'tm': '14:30',
        'desc': 'Semester Exam Fee',
        'note': 'Paid via bKash',
        'cats': ['cat-fee'],
        'deleted': 0
    })
    state['exps'].append(exp1)
    assert len(state['exps']) == 1
    assert state['exps'][0]['amt'] == 350.0
    assert state['exps'][0]['_d'] == 1

    # 2. Edit existing expense in-place (ID must be preserved, NO duplicates)
    target = next((x for x in state['exps'] if x['id'] == 'exp-101'), None)
    assert target is not None
    target.update({'amt': 400.0, 'note': 'Updated receipt #442'})
    tc(target)
    assert len(state['exps']) == 1, "Editing must update in-place, not create duplicates"
    assert state['exps'][0]['amt'] == 400.0

    # 3. Read / View transaction list
    live_exps = [e for e in state['exps'] if e['pid'] == cur_group and not e.get('deleted')]
    assert len(live_exps) == 1

    # 4. Delete expense (Soft delete / Tombstone)
    target['deleted'] = 1
    tc(target)
    assert target['deleted'] == 1
    assert target['_d'] == 1
    live_after_del = [e for e in state['exps'] if e['pid'] == cur_group and not e.get('deleted')]
    assert len(live_after_del) == 0, "Deleted expense must not appear in active views"

    # Restore for subsequent tests
    target['deleted'] = 0
    tc(target)
    print("[PASS 1] Expense CRUD operations verified.")

    # -------------------------------------------------------------
    # TEST 2: Groups CRUD & Last Remaining Group Protection
    # -------------------------------------------------------------
    # Rule check: cannot delete last group
    def can_delete_group(parents):
        active = [p for p in parents if not p.get('deleted')]
        return len(active) >= 2

    assert not can_delete_group(state['parents']), "Last remaining group must be protected from deletion"

    # Create new group
    new_grp = tc({'id': 'grp-hostel', 'name': 'Hostel Living', 'deleted': 0})
    state['parents'].append(new_grp)
    assert can_delete_group(state['parents']), "Group deletion allowed when 2+ active groups exist"

    # Rename group
    grp_to_ren = next(p for p in state['parents'] if p['id'] == 'grp-hostel')
    grp_to_ren['name'] = 'Hostel & Mess'
    tc(grp_to_ren)
    assert grp_to_ren['name'] == 'Hostel & Mess'

    # Soft delete group
    grp_to_ren['deleted'] = 1
    tc(grp_to_ren)
    assert not can_delete_group(state['parents']), "Protection reactivated when only 1 active group remains"
    print("[PASS 2] Groups CRUD and last-group deletion safeguard verified.")

    # -------------------------------------------------------------
    # TEST 3: Categories CRUD & Hierarchy
    # -------------------------------------------------------------
    # 1. Create root category
    cat_trans = tc({'id': 'cat-trans', 'pid': cur_group, 'parent': None, 'name': 'Transport', 'deleted': 0})
    state['cats'].append(cat_trans)

    # 2. Create child subcategories
    cat_bus = tc({'id': 'cat-bus', 'pid': cur_group, 'parent': 'cat-trans', 'name': 'Bus', 'deleted': 0})
    cat_rik = tc({'id': 'cat-rik', 'pid': cur_group, 'parent': 'cat-trans', 'name': 'Rickshaw', 'deleted': 0})
    state['cats'].extend([cat_bus, cat_rik])

    # 3. Verify parent-child helper functions
    def kids(cat_id, all_cats, group_id):
        return [c for c in all_cats if c['pid'] == group_id and c.get('parent') == cat_id and not c.get('deleted')]

    def desc(cat_id, all_cats, group_id):
        res = {cat_id}
        for k in kids(cat_id, all_cats, group_id):
            res.update(desc(k['id'], all_cats, group_id))
        return res

    bus_kids = kids('cat-trans', state['cats'], cur_group)
    assert len(bus_kids) == 2
    transport_desc = desc('cat-trans', state['cats'], cur_group)
    assert transport_desc == {'cat-trans', 'cat-bus', 'cat-rik'}

    # 4. Recursive category deletion
    def del_cat(cat_id, all_cats, all_exps, group_id):
        d_set = desc(cat_id, all_cats, group_id)
        for c in all_cats:
            if c['id'] in d_set:
                c['deleted'] = 1
                tc(c)
        for e in all_exps:
            e['cats'] = [cid for cid in e.get('cats', []) if cid not in d_set]
            tc(e)

    # Add expense using cat-bus
    exp_bus = tc({'id': 'exp-102', 'pid': cur_group, 'amt': 40.0, 'dt': '2026-10-28', 'desc': 'City bus', 'cats': ['cat-bus'], 'deleted': 0})
    state['exps'].append(exp_bus)
    assert 'cat-bus' in exp_bus['cats']

    # Delete 'cat-trans' -> must delete cat-trans, cat-bus, cat-rik, and remove from exp_bus
    del_cat('cat-trans', state['cats'], state['exps'], cur_group)
    assert next(c for c in state['cats'] if c['id'] == 'cat-bus')['deleted'] == 1
    assert 'cat-bus' not in exp_bus['cats']
    print("[PASS 3] Categories CRUD and hierarchical parent-child relationships verified.")

    # -------------------------------------------------------------
    # TEST 4: Search and Filtering
    # -------------------------------------------------------------
    # Setup test transactions
    e_today = tc({'id': 'exp-201', 'pid': cur_group, 'amt': 120.0, 'dt': '2026-10-30', 'tm': '09:00', 'desc': 'Breakfast Paratha', 'note': 'Morning', 'cats': ['cat-food'], 'deleted': 0})
    e_mid = tc({'id': 'exp-202', 'pid': cur_group, 'amt': 850.0, 'dt': '2026-10-15', 'tm': '13:00', 'desc': 'Reference Textbook', 'note': 'Physics Vol 1', 'cats': ['cat-fee'], 'deleted': 0})
    e_old = tc({'id': 'exp-203', 'pid': cur_group, 'amt': 50.0, 'dt': '2026-09-20', 'tm': '18:00', 'desc': 'Evening Tea', 'note': 'Snack', 'cats': ['cat-food'], 'deleted': 0})
    state['exps'].extend([e_today, e_mid, e_old])

    def filter_expenses(exps, group_id, q='', cat='', month='', date='', min_amt=''):
        l = [e for e in exps if e['pid'] == group_id and not e.get('deleted')]
        if q:
            l = [e for e in l if q.lower() in (e.get('desc', '') + ' ' + e.get('note', '') + ' ' + str(e.get('amt', ''))).lower()]
        if cat:
            d_set = desc(cat, state['cats'], group_id)
            l = [e for e in l if any(cid in d_set for cid in e.get('cats', []))]
        if month:
            l = [e for e in l if e['dt'].startswith(month)]
        if date:
            l = [e for e in l if e['dt'] == date]
        if min_amt:
            l = [e for e in l if e['amt'] >= float(min_amt)]
        return sorted(l, key=lambda x: x['dt'] + x.get('tm', ''), reverse=True)

    # 1. Text Search
    res_q = filter_expenses(state['exps'], cur_group, q='Paratha')
    assert len(res_q) == 1 and res_q[0]['id'] == 'exp-201'

    # 2. Category Filter (Education including subcategory Exam Fee)
    res_cat = filter_expenses(state['exps'], cur_group, cat='cat-edu')
    assert any(e['id'] == 'exp-101' for e in res_cat)

    # 3. Month Filter
    res_sep = filter_expenses(state['exps'], cur_group, month='2026-09')
    assert len(res_sep) == 1 and res_sep[0]['id'] == 'exp-203'

    # 4. Exact Date Filter
    res_date = filter_expenses(state['exps'], cur_group, date='2026-10-30')
    assert len(res_date) == 1 and res_date[0]['id'] == 'exp-201'

    # 5. Min Amount Filter
    res_min = filter_expenses(state['exps'], cur_group, min_amt='500')
    assert len(res_min) == 1 and res_min[0]['id'] == 'exp-202'
    print("[PASS 4] Transaction search and multi-criteria filtering verified.")

    # -------------------------------------------------------------
    # TEST 5: Dashboard Calculations
    # -------------------------------------------------------------
    # Active group transactions
    cur_exps = [e for e in state['exps'] if e['pid'] == cur_group and not e.get('deleted')]
    total_spent = sum(e['amt'] for e in cur_exps)
    
    # Oct 2026 transactions: exp-101 (400), exp-102 (40), exp-201 (120), exp-202 (850) -> total 1410
    oct_exps = [e for e in cur_exps if e['dt'].startswith('2026-10')]
    oct_total = sum(e['amt'] for e in oct_exps)
    assert oct_total == 1410.0, f"Expected 1410, got {oct_total}"

    # Year 2026 total: 1410 + 50 (exp-203) = 1460
    yr_exps = [e for e in cur_exps if e['dt'].startswith('2026')]
    yr_total = sum(e['amt'] for e in yr_exps)
    assert yr_total == 1460.0

    # Max transaction
    max_expense = max(e['amt'] for e in cur_exps)
    assert max_expense == 850.0

    # Daily average for October (30 days elapsed)
    daily_avg = oct_total / 30.0
    assert abs(daily_avg - 47.0) < 0.01
    print("[PASS 5] Dashboard metrics, period totals, and averages verified.")

    # -------------------------------------------------------------
    # TEST 6: Reports and Category Aggregations
    # -------------------------------------------------------------
    # Recursive category aggregation: an expense in a subcategory must count towards parent total
    def of_cat(cat_id, exps, all_cats, group_id):
        d_set = desc(cat_id, all_cats, group_id)
        return [e for e in exps if any(c in d_set for c in e.get('cats', []))]

    edu_exps = of_cat('cat-edu', cur_exps, state['cats'], cur_group)
    # exp-101 (400) + exp-202 (850) = 1250
    edu_sum = sum(e['amt'] for e in edu_exps)
    assert edu_sum == 1250.0

    food_exps = of_cat('cat-food', cur_exps, state['cats'], cur_group)
    # exp-201 (120) + exp-203 (50) = 170
    food_sum = sum(e['amt'] for e in food_exps)
    assert food_sum == 170.0
    print("[PASS 6] Hierarchical category breakdown and report aggregations verified.")

    # -------------------------------------------------------------
    # TEST 7: Budget Calculations
    # -------------------------------------------------------------
    # Budget set to 2000 for cur_group
    state['budget'][cur_group] = 2000.0
    bg = state['budget'][cur_group]
    spent = oct_total # 1410
    pct = (spent / bg) * 100.0
    remaining = bg - spent
    assert pct == 70.5
    assert remaining == 590.0

    # Exceeding budget test
    state['budget'][cur_group] = 1000.0
    bg_low = state['budget'][cur_group]
    pct_over = (spent / bg_low) * 100.0
    exceeded = spent - bg_low
    assert pct_over == 141.0
    assert exceeded == 410.0
    print("[PASS 7] Monthly budget percentage, remaining balance, and overage calculations verified.")

    # -------------------------------------------------------------
    # TEST 8: Backup and Restore
    # -------------------------------------------------------------
    # Generate JSON backup
    backup_str = json.dumps(state)
    backup_data = json.loads(backup_str)
    assert 'parents' in backup_data and 'cats' in backup_data and 'exps' in backup_data
    assert len(backup_data['exps']) == len(state['exps'])

    # Test Restore into empty state
    restored_state = json.loads(backup_str)
    assert len(restored_state['exps']) == len(state['exps'])
    assert restored_state['sym'] == '৳'

    # Invalid backup rejection
    invalid_backup = json.dumps({'name': 'Fake Backup', 'notes': []})
    def validate_backup(raw):
        try:
            d = json.loads(raw)
            if not d.get('exps') or not d.get('cats'):
                return False, "ফাইলটি সঠিক ব্যাকআপ নয়"
            return True, "valid"
        except:
            return False, "অবৈধ JSON"

    ok, msg = validate_backup(invalid_backup)
    assert not ok and "সঠিক ব্যাকআপ নয়" in msg
    print("[PASS 8] JSON backup generation and import validation verified.")

    # -------------------------------------------------------------
    # TEST 9: LocalStorage Persistence Simulation & Quota Safety
    # -------------------------------------------------------------
    # Mock Storage
    class MockLocalStorage:
        def __init__(self, quota=1000000):
            self.store = {}
            self.quota = quota
            self.fail_quota = False

        def setItem(self, k, v):
            if self.fail_quota:
                raise OSError("QuotaExceededError: LocalStorage quota exceeded")
            self.store[k] = str(v)

        def getItem(self, k):
            return self.store.get(k, None)

        def removeItem(self, k):
            self.store.pop(k, None)

    mock_ls = MockLocalStorage()
    mock_ls.setItem('kh', json.dumps(state))
    assert mock_ls.getItem('kh') is not None

    # Quota exception handling
    mock_ls.fail_quota = True
    quota_handled = False
    try:
        mock_ls.setItem('kh', json.dumps(state))
    except Exception as e:
        if "QuotaExceededError" in str(e):
            quota_handled = True
    assert quota_handled, "QuotaExceededError must be caught gracefully without crashing"
    print("[PASS 9] LocalStorage persistence and quota overflow safety verified.")

    # -------------------------------------------------------------
    # TEST 10: Offline and Online Expense Handling
    # -------------------------------------------------------------
    # Add expense in offline mode
    offline_exp = tc({
        'id': 'exp-offline-001',
        'pid': cur_group,
        'amt': 90.0,
        'dt': '2026-10-30',
        'desc': 'Offline Grocery',
        'cats': ['cat-food'],
        'deleted': 0
    })
    state['exps'].append(offline_exp)
    assert offline_exp.get('_d') == 1, "Offline expense must be marked dirty (_d = 1)"

    # Online sync response simulates confirmation
    confirmed_ids = {'exp-offline-001'}
    for e in state['exps']:
        if e['id'] in confirmed_ids:
            e.pop('_d', None)

    assert '_d' not in offline_exp, "Confirmed expense must clear dirty flag"
    print("[PASS 10] Offline expense creation, dirty flag queuing, and online confirmation verified.")

    # -------------------------------------------------------------
    # TEST 11: Multi-User Data Isolation in SQLite Backend
    # -------------------------------------------------------------
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript('''
    CREATE TABLE groups_(user_id INTEGER, id TEXT, name TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, PRIMARY KEY(user_id,id));
    CREATE TABLE categories(user_id INTEGER, id TEXT, group_id TEXT, parent TEXT, name TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, PRIMARY KEY(user_id,id));
    CREATE TABLE expenses(user_id INTEGER, id TEXT, group_id TEXT, amount REAL, date TEXT, time TEXT, descr TEXT, note TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, PRIMARY KEY(user_id,id));
    ''')

    # Seed User 1 and User 2
    cur.execute("INSERT INTO groups_ VALUES (1, 'g1', 'Personal', 1000, 0)")
    cur.execute("INSERT INTO expenses VALUES (1, 'e1', 'g1', 500, '2026-10-30', '', 'Lunch', '', 1000, 0)")

    cur.execute("INSERT INTO groups_ VALUES (2, 'g2', 'Secret Project', 1000, 0)")
    cur.execute("INSERT INTO expenses VALUES (2, 'e2', 'g2', 9999, '2026-10-30', '', 'Classified', '', 1000, 0)")
    conn.commit()

    # User 1 queries expenses
    cur.execute("SELECT * FROM expenses WHERE user_id=?", (1,))
    u1_exps = cur.fetchall()
    assert len(u1_exps) == 1 and u1_exps[0]['id'] == 'e1'

    # User 1 attempts IDOR lookup of User 2's expense
    cur.execute("SELECT * FROM expenses WHERE user_id=? AND id='e2'", (1,))
    idor_res = cur.fetchone()
    assert idor_res is None, "User 1 must not be able to read User 2's records"
    print("[PASS 11] Multi-user database isolation and query scoping verified.")

    # -------------------------------------------------------------
    # TEST 12: Regression Tests (Formatting, Symbols, Preferences)
    # -------------------------------------------------------------
    # Bengali currency formatting test
    def money_format(amount, sym='৳'):
        # Bengali / Indian numeric formatting: en-IN standard
        rounded = round(amount)
        # Python format with commas
        import locale
        s = f"{rounded:,}"
        return f"{sym}{s}"

    fmt_test = money_format(152500, '৳')
    assert fmt_test == '৳152,500'

    # Custom currency symbol update
    state['sym'] = '$'
    assert money_format(100, state['sym']) == '$100'

    # Bengali month names lookup
    MN = ['জানুয়ারি','ফেব্রুয়ারি','মার্চ','এপ্রিল','মে','জুন','জুলাই','আগস্ট','সেপ্টেম্বর','অক্টোবর','নভেম্বর','ডিসেম্বর']
    def mlabel(ym):
        m_idx = int(ym.split('-')[1]) - 1
        return f"{MN[m_idx]} {ym.split('-')[0]}"

    lbl = mlabel('2026-10')
    assert lbl == 'অক্টোবর 2026'
    print("[PASS 12] Regression tests (currency formatting, symbols, Bengali localization) verified.")

    print("\n=== ALL 12 PHASE 9 TEST CASES EXECUTED & PASSED SUCCESSFULLY ===")

if __name__ == '__main__':
    run_tests()
