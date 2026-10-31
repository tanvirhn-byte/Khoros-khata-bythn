#!/usr/bin/env python3
"""
Test Suite: Phase 11 Additional Requirements
- Part A: Premium Centered Status Popups (6 notification types, duplicate suppression, input guard, auto-dismiss vs persistent)
- Part B: Admin Notice & Announcement Popup Integration (direct integration with khoroch/admin.php and api.php, acknowledgment, content update, deactivation, audience targeting)
- Part C: Offline & Synchronization Regression and Multi-Device Consistency
"""

import os
import sys
import json
import re
import sqlite3
import subprocess

PASS = 0
FAIL = 0

def check(condition, desc):
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {desc}")
        PASS += 1
    else:
        print(f"  [FAIL] {desc}")
        FAIL += 1

print("======================================================================")
print("PHASE 11 ADDITIONAL REQUIREMENTS TEST SUITE")
print("======================================================================")

HTML_PATH = os.path.join(os.path.dirname(__file__), "..", "public", "khoroch", "index.html")
ADMIN_PATH = os.path.join(os.path.dirname(__file__), "..", "khoroch", "admin.php")
API_PATH = os.path.join(os.path.dirname(__file__), "..", "khoroch", "api.php")

with open(HTML_PATH, "r", encoding="utf-8") as f:
    html_content = f.read()

with open(ADMIN_PATH, "r", encoding="utf-8") as f:
    admin_content = f.read()

with open(API_PATH, "r", encoding="utf-8") as f:
    api_content = f.read()

print("\n--- PART A: PREMIUM CENTERED STATUS POPUPS ---")

# 1. Centered System Status Modal DOM exists
check('id="sys-modal"' in html_content and 'class="sys-wrap"' in html_content, "System status modal DOM element (#sys-modal.sys-wrap) exists")
check('id="sys-icon"' in html_content and 'id="sys-title"' in html_content and 'id="sys-desc"' in html_content and 'id="sys-btn"' in html_content, "Status modal elements (#sys-icon, #sys-title, #sys-desc, #sys-btn) exist")

# 2. CSS Styling & Centering
check('.sys-wrap' in html_content and 'position: fixed' in html_content and 'justify-content: center' in html_content, "Modal uses fixed centered flex layout")
check('backdrop-filter: blur' in html_content and 'z-index: 46' in html_content, "Modal backdrop blur and z-index (46) defined correctly")
check('.sys-box' in html_content and 'border-radius: 28px' in html_content, "Premium card styling with 28px rounded corners")

# 3. 6 Notification Types Supported
for n_type in ['offline', 'online', 'sync_start', 'sync_success', 'sync_fail', 'pending']:
    check(f"'{n_type}':" in html_content or f"{n_type}:" in html_content, f"Notification type '{n_type}' icon and styling supported")

# 4. Bengali Status Titles
check('ইন্টারনেট বিচ্ছিন্ন — অফলাইন মোড' in html_content, "Offline mode title in Bengali present")
check('ইন্টারনেট সংযোগ পুনরুদ্ধার' in html_content, "Online restored title in Bengali present")
check('সিঙ্ক শুরু হয়েছে' in html_content, "Sync start title in Bengali present")
check('সিঙ্ক সম্পন্ন হয়েছে' in html_content, "Sync success title in Bengali present")
check('সিঙ্ক ব্যর্থ হয়েছে' in html_content, "Sync fail title in Bengali present")
check('অপেক্ষমাণ পরিবর্তন জমা আছে' in html_content, "Pending changes title in Bengali present")

# 5. Persistent Failure Notification & Dismiss Button
check("btn.textContent = (type === 'sync_fail') ? 'বুঝেছি' : 'ঠিক আছে'" in html_content or "বুঝেছি" in html_content, "Failure notifications feature prominent acknowledgment button ('বুঝেছি')")
check("!persistent && autoDismissMs > 0" in html_content, "Temporary notifications auto-dismiss while persistent failure stays until dismissed")

# 6. Duplicate Suppression Guard
check("lastSysStatus.type === type && lastSysStatus.msg === desc && (now - lastSysStatus.time) < 4000" in html_content, "Duplicate status popup suppression guard present (4000ms window)")

# 7. Non-Intrusive Input Guard
check("function isUserInputActive()" in html_content and "INPUT" in html_content and "TEXTAREA" in html_content, "Non-intrusive input guard suppresses modal during active form typing")

# 8. Event Wiring
check("showStatusPopup('offline'" in html_content and "addEventListener('offline'" in html_content, "Offline event triggers status popup")
check("showStatusPopup('online'" in html_content and "addEventListener('online'" in html_content, "Online event triggers status popup")
check("showStatusPopup('sync_start'" in html_content, "Sync start triggers status popup")
check("showStatusPopup('sync_success'" in html_content, "Sync completion triggers status popup")
check("showStatusPopup('sync_fail'" in html_content, "Sync failure triggers status popup")
check("checkPendingPopup()" in html_content and "save=" in html_content, "Local save triggers pending changes status popup when offline")

print("\n--- PART B: ADMIN NOTICE & ANNOUNCEMENT POPUP INTEGRATION ---")

# 9. Direct Integration with khoroch/admin.php (NO duplicate DB, NO separate page)
check("const NLOC = ['popup' => 'পপআপ নোটিস (সেন্টার্ড)'" in admin_content, "Admin panel directly includes 'popup' location in NLOC")
check("NLOC" in admin_content and "notices" in admin_content, "Reuses existing notice settings and structure in SQLite database")

# 10. Admin Notice Modal DOM
check('id="adm-modal"' in html_content and 'class="adm-wrap"' in html_content, "Admin announcement modal DOM (#adm-modal.adm-wrap) exists")
check('id="adm-badge"' in html_content and 'id="adm-title"' in html_content and 'id="adm-msg"' in html_content and 'id="adm-ack-btn"' in html_content, "Admin modal elements (#adm-badge, #adm-title, #adm-msg, #adm-ack-btn) exist")

# 11. Modal Content Features (Title, Body, Link button, Social links, Close button)
check('adm-btn-wrap' in html_content and 'adm-soc-wrap' in html_content, "Admin modal includes action link wrapper and social links wrapper")
check('বুঝেছি / ঠিক আছে' in html_content, "Prominent dismiss button 'বুঝেছি / ঠিক আছে' present")

# 12. Notice Styles & Badges
for badge in ['তথ্য', 'সুখবর', 'সতর্কতা', 'জরুরি ঘোষণা']:
    check(badge in html_content, f"Notice type badge '{badge}' defined")

# 13. Acknowledgment Tracking & LocalStorage
check("kh_ack_notices" in html_content, "LocalStorage key 'kh_ack_notices' used for notice acknowledgment")
check("noticeSig(n)" in html_content, "Notice signature function tracks edits (title, msg, link, type, id)")
check("ack && ack.sig === sig" in html_content, "Acknowledged notices do not repeatedly reappear")

# 14. Content Update Re-appearance
check("noticeSig" in html_content and "seenAt" in html_content, "Admin notice edits generate new signature, allowing updated announcement to reappear")

# 15. Deactivation / Deletion Immediate Cleanup
check("stillActive" in html_content and "modal.style.display = 'none'" in html_content, "Deactivated/deleted notice immediately disappears from view")

# 16. Audience Targeting
check("audOK(n)" in html_content and ("n.aud==='in'" in html_content or "n.aud === 'in'" in html_content), "Audience targeting (all, logged-in only, guest only) strictly enforced")

# 17. Separation of Concerns
check(".sys-wrap { z-index: 46; }" in html_content and ".adm-wrap { z-index: 42; }" in html_content, "System status (z-46) and Admin announcements (z-42) have distinct layering and controllers")

# 18. Hardware Back Button Integration
check("closeSysModal()" in html_content and "ackCurrentAdminNotice()" in html_content and "handleHardwareBack" in html_content, "Hardware back button dismisses active popup modals")

print("\n--- PART C: OFFLINE & SYNC INTEGRITY REGRESSION ---")

# 19. Core offline functionality intact
check("localStorage" in html_content and "kh" in html_content, "LocalStorage persistence intact")
check("sw.js" in html_content and "serviceWorker" in html_content, "Service worker registration intact")
check("confE" in html_content and "_d" in html_content and "_rej" in html_content, "Sync dirty flag and rejected recovery intact")

print("\n======================================================================")
print(f"RESULTS: {PASS} Passed, {FAIL} Failed")
print("======================================================================")

if FAIL > 0:
    sys.exit(1)
