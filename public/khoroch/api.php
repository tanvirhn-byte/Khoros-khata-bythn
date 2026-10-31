<?php
// খরচের খাতা — PHP backend (SQLite)। কোনো database সেটআপ লাগে না।
const ALLOW_REGISTER = true;   // নিজের অ্যাকাউন্ট খোলার পর false করে দিন
const DELETE_CODE = 'TanvirX';   // অ্যাকাউন্ট মুছতে পাসওয়ার্ডের সাথে এই কোডও লাগবে
const CLOUD_BACKUP_B64 = '';     // ঐচ্ছিক: GitHub Token-এর Base64 কোড (অ্যাডমিন প্যানেল থেকে পাবেন)
require_once __DIR__ . '/db_cloud.php';

date_default_timezone_set('Asia/Dhaka');
ob_start();
ini_set('display_errors', '0');
function redactApiLog(string $msg): string {
  return preg_replace('/(password|passwd|hash|token|Bearer|delete_code|admin_hash|ADMIN_PASS)[\s:= "\']+[^\s"\',;]+/i', '$1=[REDACTED]', str_replace(["\n", "\r"], ' ', $msg));
}
set_error_handler(function ($no, $str, $file, $line) {
  @file_put_contents(__DIR__ . '/data/error.log', date('c') . ' [php ' . $no . '] ' . redactApiLog((string)$str) . ' @' . basename($file) . ':' . $line . "\n", FILE_APPEND | LOCK_EX);
  return true;
});
$isHttps = (!empty($_SERVER['HTTPS']) && strtolower((string)$_SERVER['HTTPS']) !== 'off')
  || (strtolower((string)($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '')) === 'https')
  || ((int)($_SERVER['SERVER_PORT'] ?? 0) === 443);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: SAMEORIGIN');
header('Referrer-Policy: strict-origin-when-cross-origin');
header('X-XSS-Protection: 1; mode=block');
header("Content-Security-Policy: default-src 'none'; frame-ancestors 'none'");
header('Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=(), usb=()');
if ($isHttps) {
  header('Strict-Transport-Security: max-age=31536000; includeSubDomains');
}
function out($d, $c = 200) { while (ob_get_level()) ob_end_clean(); http_response_code($c); echo json_encode($d, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE); exit; }

if (!extension_loaded('pdo_sqlite')) out(['error' => 'এই hosting-এ PDO SQLite চালু নেই। hosting support-কে চালু করতে বলুন।'], 500);

try {
  $dir = __DIR__ . '/data';
  if (!is_dir($dir)) mkdir($dir, 0750, true);
  if (!is_file($dir . '/.htaccess')) {
    @file_put_contents($dir . '/.htaccess', "<IfModule mod_authz_core.c>\nRequire all denied\n</IfModule>\n<IfModule !mod_authz_core.c>\nOrder allow,deny\nDeny from all\n</IfModule>\n");
  }
  if (!is_file($dir . '/index.php')) {
    @file_put_contents($dir . '/index.php', "<?php http_response_code(403); exit('Forbidden');\n");
  }
  $dbf = $dir . '/khoroch.sqlite';
  if (!is_file($dbf) || filesize($dbf) < 4096) {
    @cloudRestoreDb($dbf);
  }
  $db = new PDO('sqlite:' . $dbf);
  $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
  $db->exec('PRAGMA busy_timeout=8000;');
  try {
    $db->exec('PRAGMA journal_mode=WAL;');
    $db->exec('PRAGMA synchronous=NORMAL;');
    $db->exec('PRAGMA temp_store=MEMORY;');
  } catch (Throwable $e) {}
  if ((int)$db->query('PRAGMA user_version')->fetchColumn() < 8) {
  $db->exec("
  CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, hash TEXT NOT NULL, rev INTEGER NOT NULL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
  CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, t INTEGER, type TEXT, who TEXT, ip TEXT);
  CREATE INDEX IF NOT EXISTS ix_logs ON logs(type,ip,t);
  CREATE TABLE IF NOT EXISTS visits(day TEXT, vid TEXT, hits INTEGER, last INTEGER, plat TEXT, PRIMARY KEY(day,vid));
  CREATE TABLE IF NOT EXISTS tokens(token_hash TEXT PRIMARY KEY, user_id INTEGER, created INTEGER, last_seen INTEGER);
  CREATE INDEX IF NOT EXISTS ix_tokens_user ON tokens(user_id);
  CREATE TABLE IF NOT EXISTS groups_(user_id INTEGER, id TEXT, name TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id,id));
  CREATE INDEX IF NOT EXISTS ix_grp_rev ON groups_(user_id, rev);
  CREATE TABLE IF NOT EXISTS categories(user_id INTEGER, id TEXT, group_id TEXT, parent TEXT, name TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id,id));
  CREATE INDEX IF NOT EXISTS ix_cat_rev ON categories(user_id, rev);
  CREATE INDEX IF NOT EXISTS ix_cat_grp ON categories(user_id, group_id, parent);
  CREATE TABLE IF NOT EXISTS expenses(user_id INTEGER, id TEXT, group_id TEXT, amount REAL, date TEXT, time TEXT, descr TEXT, note TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id,id));
  CREATE INDEX IF NOT EXISTS ix_exp ON expenses(user_id,group_id,date);
  CREATE INDEX IF NOT EXISTS ix_exp_rev ON expenses(user_id, rev);
  CREATE TABLE IF NOT EXISTS expense_categories(user_id INTEGER, expense_id TEXT, category_id TEXT, PRIMARY KEY(user_id,expense_id,category_id));
  CREATE INDEX IF NOT EXISTS ix_exp_cats ON expense_categories(user_id, expense_id);
  CREATE TABLE IF NOT EXISTS prefs(user_id INTEGER, id TEXT, v TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id,id));
  CREATE INDEX IF NOT EXISTS ix_prf_rev ON prefs(user_id, rev);
  ");

  $cols = array_column($db->query('PRAGMA table_info(users)')->fetchAll(PDO::FETCH_ASSOC), 'name');
  if (!in_array('created', $cols)) $db->exec('ALTER TABLE users ADD COLUMN created INTEGER');
  if (!in_array('synced', $cols)) $db->exec('ALTER TABLE users ADD COLUMN synced INTEGER');
  if (!in_array('status', $cols)) $db->exec("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'");
  if (!in_array('fullname', $cols)) $db->exec("ALTER TABLE users ADD COLUMN fullname TEXT DEFAULT ''");
  if (!in_array('name', $cols)) $db->exec("ALTER TABLE users ADD COLUMN name TEXT DEFAULT ''");
  $tcols = array_column($db->query('PRAGMA table_info(tokens)')->fetchAll(PDO::FETCH_ASSOC), 'name');
  if (!in_array('last_seen', $tcols)) $db->exec('ALTER TABLE tokens ADD COLUMN last_seen INTEGER');
  $db->exec("INSERT OR IGNORE INTO settings(k,v) VALUES('tombstone_horizon_rev', '0')");
  $db->exec('PRAGMA user_version=8');
  }

  function q($sql, $p = []) { global $db; $s = $db->prepare($sql); $s->execute($p); return $s; }
  function logev($type, $who = '') {
    try {   // লগ লিখতে না পারলেও লগইন/সিঙ্ক যেন না থামে
      q('INSERT INTO logs(t,type,who,ip) VALUES(?,?,?,?)', [time(), $type, $who, $_SERVER['REMOTE_ADDR'] ?? '']);
      if (mt_rand(1, 20) === 1) q('DELETE FROM logs WHERE id < (SELECT MAX(id) FROM logs) - 500');
    } catch (Throwable $exl) {}
  }
  function newToken($uid) { $t = bin2hex(random_bytes(32)); $now = time(); q('INSERT INTO tokens(token_hash,user_id,created,last_seen) VALUES(?,?,?,?)', [hash('sha256', $t), $uid, $now, $now]); return $t; }

  // --- Phase 7: CORS Security & Preflight Handling ---
  $reqMethod = strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET');
  if (!in_array($reqMethod, ['GET', 'POST', 'OPTIONS'], true)) {
    header('Allow: GET, POST, OPTIONS');
    out(['error' => 'অনুমোদিত মেথড নয়'], 405);
  }

  function isAllowedOrigin(string $orig, ?PDO $database = null): bool {
    if ($orig === '') return false;
    // 1. Capacitor native app origins
    if ($orig === 'capacitor://localhost' || $orig === 'https://localhost') {
      return true;
    }
    // 2. Development origins: localhost or 127.0.0.1 with optional port
    if (preg_match('/^https?:\/\/(localhost|127\.0\.0\.1)(:[0-9]{1,5})?$/i', $orig)) {
      return true;
    }
    // 3. Same-origin host
    $h = $_SERVER['HTTP_HOST'] ?? ($_SERVER['SERVER_NAME'] ?? '');
    if ($h !== '' && preg_match('/^[a-zA-Z0-9.-]+(:[0-9]{1,5})?$/', $h)) {
      if ($orig === "https://$h" || $orig === "http://$h") {
        return true;
      }
    }
    // 4. Configured origin in environment or constant
    $envOrig = getenv('APP_ORIGIN') ?: (defined('APP_ORIGIN') ? APP_ORIGIN : '');
    if ($envOrig !== '' && is_string($envOrig) && rtrim($envOrig, '/') === rtrim($orig, '/')) {
      return true;
    }
    // 5. Configured origin in SQLite settings table
    if ($database) {
      try {
        $cfg = $database->query("SELECT v FROM settings WHERE k IN ('cors_origin', 'app_domain') AND v IS NOT NULL AND v != '' LIMIT 1")->fetchColumn();
        if ($cfg && is_string($cfg) && rtrim($cfg, '/') === rtrim($orig, '/')) {
          return true;
        }
      } catch (Throwable $e) {}
    }
    return false;
  }

  $rawOrigin = $_SERVER['HTTP_ORIGIN'] ?? '';
  $origin = is_string($rawOrigin) ? trim($rawOrigin) : '';
  $originAllowed = ($origin !== '') && isAllowedOrigin($origin, $db);

  if ($originAllowed) {
    header("Access-Control-Allow-Origin: $origin");
    header('Access-Control-Allow-Credentials: true');
    header('Vary: Origin');
  }

  // Preflight OPTIONS handling (exits immediately without modifying data)
  if ($reqMethod === 'OPTIONS') {
    if ($origin !== '') {
      if (!$originAllowed) {
        out(['error' => 'অনুমোদিত অরিজিন নয়'], 403);
      }
      $preflightMethod = strtoupper(trim($_SERVER['HTTP_ACCESS_CONTROL_REQUEST_METHOD'] ?? 'POST'));
      if (!in_array($preflightMethod, ['GET', 'POST', 'OPTIONS'], true)) {
        header('Allow: GET, POST, OPTIONS');
        out(['error' => 'মেথড অনুমোদিত নয়'], 405);
      }
      header("Access-Control-Allow-Origin: $origin");
      header('Access-Control-Allow-Credentials: true');
      header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
      header('Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With');
      header('Access-Control-Max-Age: 86400');
      header('Vary: Origin');
      http_response_code(204);
      exit;
    } else {
      header('Allow: GET, POST, OPTIONS');
      http_response_code(204);
      exit;
    }
  }

  // State-changing POST requests: reject unauthorized foreign origins
  if ($reqMethod === 'POST' && $origin !== '' && !$originAllowed) {
    out(['error' => 'অনুমোদিত অরিজিন নয়'], 403);
  }

  $raw = (string)file_get_contents('php://input', false, null, 0, 2500001);
  if (strlen($raw) > 2500000) out(['error' => 'অনুরোধটি অনেক বড়'], 413);
  $in = json_decode($raw, true) ?: [];
  $a = $_GET['a'] ?? '';

  if ($a === 'health') out(['ok' => true]);

  // Enforce POST method for all state-changing actions
  if (in_array($a, ['register', 'login', 'logout', 'passwd', 'delacct', 'sync'], true) && $reqMethod !== 'POST') {
    header('Allow: POST, OPTIONS');
    out(['error' => 'এই অনুরোধে POST মেথড আবশ্যক'], 405);
  }

  if ($a === 'register') {
    $rm = q("SELECT v FROM settings WHERE k='reg_mode'")->fetchColumn();
    if ($rm === false) {
      $ar = q("SELECT v FROM settings WHERE k='allow_register'")->fetchColumn();
      $rm = $ar === false ? (ALLOW_REGISTER ? 'open' : 'closed') : ($ar === '1' ? 'open' : 'closed');
    }
    if ($rm === 'closed') out(['error' => 'নতুন অ্যাকাউন্ট নিবন্ধন বর্তমানে বন্ধ আছে।'], 403);
    $rip = $_SERVER['REMOTE_ADDR'] ?? '';
    if ((int)q("SELECT COUNT(*) FROM logs WHERE type='register' AND ip=? AND t>?", [$rip, time() - 3600])->fetchColumn() >= 5)
      out(['error' => 'একই জায়গা থেকে অনেক অ্যাকাউন্ট খোলা হয়েছে। ১ ঘণ্টা পর আবার চেষ্টা করুন।'], 429);
    $email = strtolower(trim($in['email'] ?? ''));
    $pw = (string)($in['password'] ?? '');
    $fullname = trim(cut((string)($in['fullname'] ?? ''), 100));
    $displayName = trim(cut((string)($in['displayName'] ?? $in['name'] ?? ''), 60));
    if ($displayName === '' && $fullname !== '') {
      $parts = preg_split('/\s+/', $fullname);
      $displayName = $parts[0] ?? $fullname;
    }
    if ($fullname === '' || $displayName === '') {
      out(['error' => 'পূর্ণ নাম ও ডিসপ্লে নাম দিন'], 400);
    }
    if (strlen($email) > 254 || !filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($pw) < 8 || strlen($pw) > 200) {
      out(['error' => 'সঠিক ইমেইল এবং ৮+ অক্ষরের পাসওয়ার্ড দিন'], 400);
    }
    if (q('SELECT 1 FROM users WHERE email=?', [$email])->fetch()) {
      out(['error' => 'এই ইমেইল দিয়ে আগেই অ্যাকাউন্ট খোলা হয়েছে'], 409);
    }
    $initialStatus = ($rm === 'approval') ? 'pending' : 'active';
    q('INSERT INTO users(email,hash,created,status,fullname,name) VALUES(?,?,?,?,?,?)',
      [$email, password_hash($pw, PASSWORD_DEFAULT), time(), $initialStatus, $fullname, $displayName]);
    $newUid = (int)$db->lastInsertId();
    logev('register', $email . ' (' . $fullname . ')');
    @cloudBackupDb($db, $dbf, true);
    if ($rm === 'approval') {
      out([
        'ok' => true,
        'mode' => 'approval',
        'message' => 'আপনার রেজিস্ট্রেশন সফল হয়েছে! অ্যাডমিন অনুমোদন করলে আপনি লগইন করতে পারবেন। অনুমোদনের পর আপনাকে ইমেইলে জানানো হবে।'
      ]);
    }
    $tokOut = newToken($newUid);
    @cloudBackupDb($db, $dbf, true);
    out([
      'ok' => true,
      'mode' => 'open',
      'token' => $tokOut,
      'name' => $displayName,
      'fullname' => $fullname
    ]);
  }

  if ($a === 'login') {
    $ip = $_SERVER['REMOTE_ADDR'] ?? '';
    if ((int)q("SELECT COUNT(*) FROM logs WHERE type='login_fail' AND ip=? AND t>?", [$ip, time() - 900])->fetchColumn() >= 5)
      out(['error' => 'অনেকবার ভুল হয়েছে। ১৫ মিনিট পর আবার চেষ্টা করুন।'], 429);
    $em = strtolower(trim($in['email'] ?? ''));
    $pwIn = (string)($in['password'] ?? '');
    $u = (strlen($em) <= 254 && $em !== '') ? q('SELECT * FROM users WHERE email=?', [$em])->fetch(PDO::FETCH_ASSOC) : false;
    // Self-Healing Account Recovery: if container reset wiped SQLite, restore verified account from client vault
    if (!$u && filter_var($em, FILTER_VALIDATE_EMAIL) && strlen($pwIn) >= 8 && strlen($pwIn) <= 200) {
      $vault = isset($in['vault']) && is_array($in['vault']) ? $in['vault'] : null;
      $vPw = $vault && isset($vault['pw_b64']) ? (string)base64_decode((string)$vault['pw_b64'], true) : '';
      if ($vault && $vPw === $pwIn) {
        $vFn = trim(cut((string)($vault['fullname'] ?? ''), 100));
        $vNm = trim(cut((string)($vault['name'] ?? ''), 60)) ?: ($vFn !== '' ? (preg_split('/\s+/', $vFn)[0] ?? $vFn) : 'User');
        q('INSERT INTO users(email,hash,created,status,fullname,name) VALUES(?,?,?,?,?,?)',
          [$em, password_hash($pwIn, PASSWORD_DEFAULT), time(), 'active', $vFn ?: $vNm, $vNm]);
        $u = q('SELECT * FROM users WHERE email=?', [$em])->fetch(PDO::FETCH_ASSOC);
        logev('register', $em . ' (অটো-রিস্টোর)');
      }
    }
    if (!$u || strlen($pwIn) > 200 || !password_verify($pwIn, $u['hash'])) { logev('login_fail', $em); usleep(400000); out(['error' => 'ইমেইল বা পাসওয়ার্ড ভুল'], 401); }
    if (($u['status'] ?? 'active') === 'pending') out(['error' => 'আপনার অ্যাকাউন্টটি অ্যাডমিনের অনুমোদনের অপেক্ষায় আছে। অনুমোদন সম্পন্ন হলে লগইন করতে পারবেন।'], 403);
    if (($u['status'] ?? 'active') === 'blocked') out(['error' => 'এই অ্যাকাউন্ট বন্ধ করা আছে।'], 403);
    logev('login', $em);
    $newTok = newToken((int)$u['id']);
    @cloudBackupDb($db, $dbf);
    out([
      'token' => $newTok,
      'name' => $u['name'] ?: $u['fullname'] ?: '',
      'fullname' => $u['fullname'] ?? ''
    ]);
  }

  // --- এখান থেকে লগইন লাগে (config ছাড়া) ---
  if ($a === 'config') {
    $vid = (string)($in['vid'] ?? '');
    if (preg_match('/^[a-z0-9]{8,32}$/', $vid)) {
      $day = date('Y-m-d'); $now = time(); $ua = $_SERVER['HTTP_USER_AGENT'] ?? '';
      $plat = stripos($ua, 'android') !== false ? 'Android' : (preg_match('/iphone|ipad|ipod/i', $ua) ? 'iOS' : 'Desktop');
      try {   // ভিজিট গোনা: ১০ মিনিটে একবার; ব্যর্থ হলেও অ্যাপ চলবে
        $lv = q('SELECT last FROM visits WHERE day=? AND vid=?', [$day, $vid])->fetchColumn();
        if ($lv === false) q('INSERT OR IGNORE INTO visits(day,vid,hits,last,plat) VALUES(?,?,1,?,?)', [$day, $vid, $now, $plat]);
        elseif ($now - (int)$lv >= 600) q('UPDATE visits SET hits=hits+1,last=? WHERE day=? AND vid=?', [$now, $day, $vid]);
        if (mt_rand(1, 200) === 1) q('DELETE FROM visits WHERE day<?', [date('Y-m-d', time() - 400 * 86400)]);
      } catch (Throwable $exv) {}
    }
    $cfgMap = q("SELECT k, v FROM settings WHERE k IN ('notices','social','socmode','poll','welcome','brand','maint','app_update','reg_mode')")->fetchAll(PDO::FETCH_KEY_PAIR);
    $get = function ($k, $d) use ($cfgMap) { $v = $cfgMap[$k] ?? false; $j = ($v !== false && $v !== null) ? json_decode($v, true) : null; return $j === null ? $d : $j; };
    $now = date('Y-m-d\TH:i');
    $notices = [];
    foreach ((array)$get('notices', []) as $n) {
      $from = (string)($n['from'] ?? ''); $to = (string)($n['to'] ?? '');
      if (strlen($from) === 10) $from .= 'T00:00';
      if (strlen($to) === 10) $to .= 'T23:59';
      if (empty($n['on']) || ($from !== '' && $from > $now) || ($to !== '' && $to < $now)) continue;
      $notices[] = ['id' => (string)($n['id'] ?? ''), 'title' => (string)($n['title'] ?? ''), 'msg' => (string)($n['msg'] ?? ''), 'link' => (string)($n['link'] ?? ''), 'btn' => (string)($n['btn'] ?? ''),
        'type' => (string)($n['type'] ?? 'info'), 'loc' => array_values((array)($n['loc'] ?? [])), 'freq' => (string)($n['freq'] ?? 'always'), 'every' => (int)($n['every'] ?? 24), 'everyS' => (int)($n['everyS'] ?? 0), 'socs' => array_values((array)($n['socs'] ?? [])),
        'secs' => (int)($n['secs'] ?? 0), 'aud' => (string)($n['aud'] ?? 'all'), 'pri' => (int)($n['pri'] ?? 10), 'soc' => !empty($n['soc']) ? 1 : 0];
    }
    usort($notices, function ($x, $y) { return $x['pri'] <=> $y['pri']; });
    $sraw = (array)$get('social', []);
    if ($sraw && array_keys($sraw) !== range(0, count($sraw) - 1)) {   // পুরনো ফরম্যাট
      $tmp = []; foreach ($sraw as $k => $x) $tmp[] = ['p' => $k, 'label' => '', 'url' => $x['url'] ?? '', 'on' => $x['on'] ?? 0, 'loc' => $x['loc'] ?? []];
      $sraw = $tmp;
    }
    $social = [];
    foreach ($sraw as $x) if (!empty($x['on']) && !empty($x['url'])) $social[] = ['id' => (string)($x['id'] ?? ('k' . substr(md5(($x['p'] ?? '') . '|' . ($x['url'] ?? '')), 0, 6))), 'k' => (string)($x['p'] ?? ''), 'label' => (string)($x['label'] ?? ''), 'url' => (string)$x['url'], 'loc' => array_values((array)($x['loc'] ?? []))];
    $sm = $cfgMap['socmode'] ?? false;
    $pl = isset($cfgMap['poll']) ? (int)$cfgMap['poll'] : 15; if ($pl < 5 || $pl > 120) $pl = 15;
    $regMode = $cfgMap['reg_mode'] ?? (defined('ALLOW_REGISTER') && ALLOW_REGISTER ? 'open' : 'closed');
    $appUpdate = (object)$get('app_update', [
      'on' => 0,
      'ver' => '1.0.1',
      'build' => 2,
      'force' => 0,
      'title' => 'নতুন আপডেট উপলব্ধ!',
      'msg' => 'অ্যাপের একটি নতুন ও উন্নত সংস্করণ প্রস্তুত আছে। নতুন ফিচার এবং ত্রুটিমুক্ত অভিজ্ঞতা পেতে অনুগ্রহ করে এখনই আপডেট করুন।',
      'url' => '',
      'btn' => 'ইনস্টল করুন'
    ]);
    out(['poll' => $pl, 'notices' => $notices, 'social' => $social, 'socmode' => $sm === false ? 'none' : $sm, 'welcome' => (object)$get('welcome', []), 'brand' => (object)$get('brand', []), 'maint' => $get('maint', ['on' => 0, 'msg' => '']), 'reg_mode' => $regMode, 'app_update' => $appUpdate]);
  }

  // Extract token strictly from Authorization Bearer header, POST JSON body, or POST form data (NEVER from $_GET)
  $tok = '';
  $authHeader = $_SERVER['HTTP_AUTHORIZATION'] ?? ($_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '');
  if (preg_match('/^Bearer\s+([A-Za-z0-9_-]{32,128})$/i', trim($authHeader), $m)) {
    $tok = $m[1];
  } elseif (isset($in['token']) && is_string($in['token']) && preg_match('/^[A-Za-z0-9_-]{32,128}$/', trim($in['token']))) {
    $tok = trim($in['token']);
  } elseif (isset($_POST['token']) && is_string($_POST['token']) && preg_match('/^[A-Za-z0-9_-]{32,128}$/', trim($POST_TOKEN = $_POST['token']))) {
    $tok = trim($POST_TOKEN);
  }

  if ($tok === '') out(['error' => 'লগইন করুন'], 401);

  $tokHash = hash('sha256', $tok);
  $row = q('SELECT user_id, created, last_seen FROM tokens WHERE token_hash=?', [$tokHash])->fetch(PDO::FETCH_ASSOC);
  $sessionHealed = false;
  if (!$row && isset($in['vault']) && is_array($in['vault'])) {
    $vEm = strtolower(trim((string)($in['vault']['email'] ?? '')));
    $vPw = (string)base64_decode((string)($in['vault']['pw_b64'] ?? ''), true);
    $vFn = trim(cut((string)($in['vault']['fullname'] ?? ''), 100));
    $vNm = trim(cut((string)($in['vault']['name'] ?? ''), 60)) ?: ($vFn !== '' ? (preg_split('/\s+/', $vFn)[0] ?? $vFn) : 'User');
    if (filter_var($vEm, FILTER_VALIDATE_EMAIL) && strlen($vPw) >= 8 && strlen($vPw) <= 200) {
      $uExist = q('SELECT * FROM users WHERE email=?', [$vEm])->fetch(PDO::FETCH_ASSOC);
      $healedUid = 0;
      if (!$uExist) {
        q('INSERT INTO users(email,hash,created,status,fullname,name) VALUES(?,?,?,?,?,?)',
          [$vEm, password_hash($vPw, PASSWORD_DEFAULT), time(), 'active', $vFn ?: $vNm, $vNm]);
        $healedUid = (int)$db->lastInsertId();
        logev('register', $vEm . ' (সেশন অটো-রিস্টোর)');
      } elseif (password_verify($vPw, $uExist['hash']) && ($uExist['status'] ?? 'active') === 'active') {
        $healedUid = (int)$uExist['id'];
      }
      if ($healedUid > 0) {
        $nowT = time();
        q('INSERT OR REPLACE INTO tokens(token_hash,user_id,created,last_seen) VALUES(?,?,?,?)', [$tokHash, $healedUid, $nowT, $nowT]);
        $row = ['user_id' => $healedUid, 'created' => $nowT, 'last_seen' => $nowT];
        $sessionHealed = true;
      }
    }
  }
  if (!$row) out(['error' => 'লগইন করুন'], 401);

  // 90-Day Inactivity Expiration Policy:
  // Session expires if inactive for more than 90 consecutive days (7,776,000 seconds).
  // The original `created` timestamp is immutable and NEVER overwritten.
  $now = time();
  $createdAt = (int)($row['created'] ?? 0);
  $lastSeenAt = (int)($row['last_seen'] ?? 0) ?: $createdAt;

  if (($now - $lastSeenAt) > 90 * 86400) {
    q('DELETE FROM tokens WHERE token_hash=?', [$tokHash]);
    out(['error' => 'নিষ্ক্রিয়তার কারণে লগইনের মেয়াদ শেষ হয়ে গেছে। পুনরায় লগইন করুন।'], 401);
  }

  // Update last_seen if more than 24 hours elapsed since last update (throttled to avoid DB churn)
  if (($now - $lastSeenAt) > 86400) {
    q('UPDATE tokens SET last_seen=? WHERE token_hash=?', [$now, $tokHash]);
  }

  $u = (int)$row['user_id'];
  $stt = q('SELECT status FROM users WHERE id=?', [$u])->fetchColumn();
  if ($stt !== 'active') {
    if ($stt === false) q('DELETE FROM tokens WHERE token_hash=?', [$tokHash]);
    out(['error' => 'অ্যাকাউন্ট বন্ধ আছে'], 401);
  }

  $okId = function ($v) { return is_string($v) && preg_match('/^[A-Za-z0-9_-]{1,40}$/', $v); };
  $sv = function ($v, $n) { $v = (string)$v; return function_exists('mb_substr') ? mb_substr($v, 0, $n) : substr($v, 0, $n); };

  if ($a === 'logout') {
    q('DELETE FROM tokens WHERE token_hash=?', [$tokHash]);
    logev('logout', 'user#' . $u);
    out(['ok' => true]);
  }

  if ($a === 'ping') {   // খুব হালকা: শুধু জানায় সার্ভারে নতুন পরিবর্তন আছে কি না
    out(['rev' => (int)q('SELECT rev FROM users WHERE id=?', [$u])->fetchColumn(), 'now' => (int)(microtime(true) * 1000)]);
  }

  if ($a === 'passwd') {
    $r = q('SELECT hash FROM users WHERE id=?', [$u])->fetch(PDO::FETCH_ASSOC);
    $new = (string)($in['new'] ?? '');
    $old = (string)($in['old'] ?? '');
    if (!$r || strlen($old) > 200 || !password_verify($old, $r['hash'])) { usleep(400000); out(['error' => 'বর্তমান পাসওয়ার্ড ভুল'], 403); }
    if (strlen($new) < 8 || strlen($new) > 200) out(['error' => 'নতুন পাসওয়ার্ড ৮+ অক্ষরের হতে হবে'], 400);
    q('UPDATE users SET hash=? WHERE id=?', [password_hash($new, PASSWORD_DEFAULT), $u]);
    logev('passwd', 'user#' . $u);
    q('DELETE FROM tokens WHERE user_id=? AND token_hash<>?', [$u, hash('sha256', $tok)]);
    out(['ok' => true]);
  }

  if ($a === 'delacct') {
    $r = q('SELECT hash FROM users WHERE id=?', [$u])->fetch(PDO::FETCH_ASSOC);
    $pw = (string)($in['pw'] ?? '');
    if (!$r || strlen($pw) > 200 || !password_verify($pw, $r['hash'])) { usleep(400000); out(['error' => 'পাসওয়ার্ড ভুল'], 403); }
    $dc = q("SELECT v FROM settings WHERE k='delete_code'")->fetchColumn();
    if ($dc === false) $dc = DELETE_CODE;
    if (!hash_equals((string)$dc, (string)($in['code'] ?? ''))) { usleep(400000); out(['error' => 'ইউনিভার্সাল কোড ভুল'], 403); }
    logev('delacct', 'user#' . $u);
    $db->beginTransaction();
    foreach (['expense_categories', 'expenses', 'categories', 'groups_', 'prefs', 'tokens'] as $t) q("DELETE FROM $t WHERE user_id=?", [$u]);
    q('DELETE FROM users WHERE id=?', [$u]);
    $db->commit();
    out(['ok' => true]);
  }

  if ($a === 'sync') {
    $nowMs = (int)(microtime(true) * 1000);
    $since = max(0, (int)($in['since'] ?? 0));
    $P = (array)($in['parents'] ?? []); $C = (array)($in['cats'] ?? []); $E = (array)($in['exps'] ?? []); $R = (array)($in['prefs'] ?? []);
    if (count($P) + count($C) + count($E) + count($R) > 400) out(['error' => 'একবারে অনেক বেশি পরিবর্তন পাঠানো হয়েছে'], 413);
    $okId = function ($v) { return is_string($v) && preg_match('/^[A-Za-z0-9_-]{1,40}$/', $v); };
    $sv = function ($v, $n) { $v = (string)$v; return function_exists('mb_substr') ? mb_substr($v, 0, $n) : substr($v, 0, $n); };
    $clamp = function ($v) use ($nowMs) { return min((int)$v, $nowMs + 300000); };   // ভুল ঘড়ির ভবিষ্যৎ সময় আটকানো
    $pushed = ['groups_' => [], 'categories' => [], 'expenses' => [], 'prefs' => []];
    $rejected = ['expenses' => [], 'categories' => []];
    if ($P || $C || $E || $R) {
      $tries = 0;
      while (true) {
        $pushed = ['groups_' => [], 'categories' => [], 'expenses' => [], 'prefs' => []];
        $rejected = ['expenses' => [], 'categories' => []];
        try {
          $db->beginTransaction();
          q('UPDATE users SET rev=rev WHERE id=?', [$u]);   // লেখার তালা এখনই নেওয়া — দুই ফোন একসাথে পাঠালেও rev গুলিয়ে যাবে না
          $rev = (int)q('SELECT rev FROM users WHERE id=?', [$u])->fetchColumn();
          $newer = function ($t, $id, $upd, $isDeleted = false, $itemData = null) use ($u) {
            $o = q("SELECT updated, deleted FROM $t WHERE user_id=? AND id=?", [$u, $id])->fetch(PDO::FETCH_ASSOC);
            if (!$o) return true;
            $exUpd = (int)$o['updated'];
            $exDel = (int)$o['deleted'];

            // 1. Different timestamps: higher timestamp always wins (LWW)
            if ($upd > $exUpd) return true;
            if ($upd < $exUpd) return false;

            // 2. Equal timestamps: Deletions dominate (accepted if incoming.updated >= existing.updated)
            if ($isDeleted && !$exDel) return true;
            if (!$isDeleted && $exDel) return false;

            // 3. Equal timestamps & same deletion state: Deterministic tie-breaking by payload string comparison
            if ($itemData !== null) {
              $inHash = md5($id . '|' . json_encode($itemData));
              $exRow = q("SELECT * FROM $t WHERE user_id=? AND id=?", [$u, $id])->fetch(PDO::FETCH_ASSOC);
              unset($exRow['rev']);
              $exHash = md5($id . '|' . json_encode($exRow));
              return strcmp($inHash, $exHash) > 0;
            }
            return false;
          };
          foreach ($P as $p) if (is_array($p) && $okId($p['id'] ?? null)) {
            $pushed['groups_'][] = $p['id']; $upd = $clamp($p['updated'] ?? 0);
            $pDel = !empty($p['deleted']);
            if ($newer('groups_', $p['id'], $upd, $pDel, $p)) q('INSERT OR REPLACE INTO groups_ VALUES(?,?,?,?,?,?)', [$u, $p['id'], $sv($p['name'] ?? '', 100), $upd, $pDel ? 1 : 0, ++$rev]);
          }

          // Authenticated user's active groups (including newly inserted/updated groups in this batch)
          $ownedGroups = q('SELECT id FROM groups_ WHERE user_id=? AND deleted=0', [$u])->fetchAll(PDO::FETCH_COLUMN);
          $groupSet = array_flip($ownedGroups);

          // Authenticated user's active categories in DB + any valid new categories in this batch
          $ownedCats = q('SELECT id FROM categories WHERE user_id=? AND deleted=0', [$u])->fetchAll(PDO::FETCH_COLUMN);
          $catSet = array_flip($ownedCats);
          foreach ($C as $c) {
            if (is_array($c) && $okId($c['id'] ?? null) && empty($c['deleted'])) {
              $catSet[$c['id']] = true;
            }
          }

          foreach ($C as $c) if (is_array($c) && $okId($c['id'] ?? null)) {
            $upd = $clamp($c['updated'] ?? 0);
            $cPid = ($okId($c['pid'] ?? null) && isset($groupSet[$c['pid']])) ? $c['pid'] : null;
            $cDel = !empty($c['deleted']);

            if ($newer('categories', $c['id'], $upd, $cDel, $c)) {
              if (!$cPid) {
                if ($cDel) {
                  $existC = q('SELECT group_id FROM categories WHERE user_id=? AND id=?', [$u, $c['id']])->fetch(PDO::FETCH_ASSOC);
                  if ($existC) {
                    q('UPDATE categories SET deleted=1, updated=?, rev=? WHERE user_id=? AND id=?', [$upd, ++$rev, $u, $c['id']]);
                  }
                  $pushed['categories'][] = $c['id'];
                } else {
                  $rejected['categories'][] = ['id' => $c['id'], 'reason' => 'invalid_group'];
                }
                continue;
              }
              $pushed['categories'][] = $c['id'];
              $cParent = ($okId($c['parent'] ?? null) && isset($catSet[$c['parent']]) && $c['parent'] !== $c['id']) ? $c['parent'] : null;
              q('INSERT OR REPLACE INTO categories VALUES(?,?,?,?,?,?,?,?)', [$u, $c['id'], $cPid, $cParent, $sv($c['name'] ?? '', 100), $upd, $cDel ? 1 : 0, ++$rev]);
            } else {
              $pushed['categories'][] = $c['id'];
            }
          }

          // Refresh active categories after saving $C
          $ownedCats = q('SELECT id FROM categories WHERE user_id=? AND deleted=0', [$u])->fetchAll(PDO::FETCH_COLUMN);
          $catSet = array_flip($ownedCats);

          foreach ($E as $e) if (is_array($e) && $okId($e['id'] ?? null)) {
            $upd = $clamp($e['updated'] ?? 0);
            $ePid = ($okId($e['pid'] ?? null) && isset($groupSet[$e['pid']])) ? $e['pid'] : null;
            $eDel = !empty($e['deleted']);

            if ($newer('expenses', $e['id'], $upd, $eDel, $e)) {
              if (!$ePid) {
                if ($eDel) {
                  $existE = q('SELECT group_id FROM expenses WHERE user_id=? AND id=?', [$u, $e['id']])->fetch(PDO::FETCH_ASSOC);
                  if ($existE) {
                    q('UPDATE expenses SET deleted=1, updated=?, rev=? WHERE user_id=? AND id=?', [$upd, ++$rev, $u, $e['id']]);
                  }
                  $pushed['expenses'][] = $e['id'];
                } else {
                  // Group is mandatory. Reject invalid/foreign/ungrouped expense safely!
                  $rejected['expenses'][] = ['id' => $e['id'], 'reason' => 'invalid_group'];
                }
                continue;
              }
              $pushed['expenses'][] = $e['id'];
              $amt = (float)($e['amt'] ?? 0); if (!is_finite($amt)) $amt = 0; $amt = max(0, min(1e12, $amt));
              q('INSERT OR REPLACE INTO expenses VALUES(?,?,?,?,?,?,?,?,?,?,?)', [$u, $e['id'], $ePid, $amt, $sv($e['dt'] ?? '', 10), $sv($e['tm'] ?? '', 5), $sv($e['desc'] ?? '', 300), $sv($e['note'] ?? '', 1000), $upd, $eDel ? 1 : 0, ++$rev]);
              q('DELETE FROM expense_categories WHERE user_id=? AND expense_id=?', [$u, $e['id']]);
              foreach (array_slice(array_unique((array)($e['cats'] ?? [])), 0, 40) as $cid) {
                if ($okId($cid) && isset($catSet[$cid])) {
                  q('INSERT OR IGNORE INTO expense_categories VALUES(?,?,?)', [$u, $e['id'], $cid]);
                }
              }
            } else {
              $pushed['expenses'][] = $e['id'];
            }
          }
          // সেটিংস (ডিফল্ট গ্রুপ, নাম, মুদ্রার চিহ্ন, মাসিক বাজেট) — অ্যাকাউন্টের সাথে সব ডিভাইসে মিলে যায়
          foreach ($R as $r) if (is_array($r) && is_string($r['id'] ?? null) && preg_match('/^(defg|name|sym|budget:[A-Za-z0-9_-]{1,40})$/', $r['id'])) {
            $pushed['prefs'][] = $r['id']; $upd = $clamp($r['updated'] ?? 0);
            $rDel = !empty($r['deleted']);
            if ($newer('prefs', $r['id'], $upd, $rDel, $r)) q('INSERT OR REPLACE INTO prefs VALUES(?,?,?,?,?,?)', [$u, $r['id'], $sv($r['v'] ?? '', 100), $upd, $rDel ? 1 : 0, ++$rev]);
          }
          q('UPDATE users SET rev=?, synced=? WHERE id=?', [$rev, time(), $u]);
          $db->commit();
          break;
        } catch (Throwable $ex) {
          try { if ($db->inTransaction()) $db->rollBack(); } catch (Throwable $ex2) {}
          $m = strtolower($ex->getMessage());
          if (++$tries >= 4 || (strpos($m, 'lock') === false && strpos($m, 'busy') === false)) throw $ex;
          usleep(250000 * $tries);
        }
      }
    }
    $rev = (int)q('SELECT rev FROM users WHERE id=?', [$u])->fetchColumn();
    $notice = q("SELECT v FROM settings WHERE k='notice'")->fetchColumn();
    if ($notice === false) $notice = '';

    // Stale cursor detection: if client cursor is ahead of server revision, trigger full resynchronization
    if ($since > $rev) {
      $since = 0;
    }

    // Pagination & maximum batch limit handling
    $batchLimit = isset($in['limit']) && (int)$in['limit'] > 0 ? min(200, (int)$in['limit']) : 150;
    $revRows = q("
      SELECT rev FROM (
        SELECT rev FROM groups_ WHERE user_id=? AND rev>?
        UNION ALL
        SELECT rev FROM categories WHERE user_id=? AND rev>?
        UNION ALL
        SELECT rev FROM expenses WHERE user_id=? AND rev>?
        UNION ALL
        SELECT rev FROM prefs WHERE user_id=? AND rev>?
      ) ORDER BY rev ASC LIMIT ?", [$u, $since, $u, $since, $u, $since, $u, $since, $batchLimit + 1])->fetchAll(PDO::FETCH_COLUMN);

    $hasMore = count($revRows) > $batchLimit;
    $nextSince = $hasMore ? (int)$revRows[$batchLimit - 1] : $rev;

    // নতুন পরিবর্তন + এইমাত্র পাঠানো আইটেমের চূড়ান্ত (সার্ভারের) অবস্থা — যাতে কোনো ডিভাইস পিছিয়ে না থাকে
    $sel = function ($t) use ($u, $since, $nextSince, $hasMore, $pushed) {
      $ids = array_values(array_unique($pushed[$t]));
      if ($hasMore) {
        $sql = "SELECT * FROM $t WHERE user_id=? AND ((rev>? AND rev<=?)" . ($ids ? ' OR id IN (' . implode(',', array_fill(0, count($ids), '?')) . ')' : '') . ')';
        return q($sql, array_merge([$u, $since, $nextSince], $ids))->fetchAll(PDO::FETCH_ASSOC);
      } else {
        $sql = "SELECT * FROM $t WHERE user_id=? AND (rev>?" . ($ids ? ' OR id IN (' . implode(',', array_fill(0, count($ids), '?')) . ')' : '') . ')';
        return q($sql, array_merge([$u, $since], $ids))->fetchAll(PDO::FETCH_ASSOC);
      }
    };
    $expRows = $sel('expenses');
    $expCatMap = [];
    if ($expRows) {
      $expIds = array_column($expRows, 'id');
      $ph = implode(',', array_fill(0, count($expIds), '?'));
      $ecRows = q("SELECT expense_id, category_id FROM expense_categories WHERE user_id=? AND expense_id IN ($ph)", array_merge([$u], $expIds))->fetchAll(PDO::FETCH_ASSOC);
      foreach ($ecRows as $ecRow) {
        $expCatMap[$ecRow['expense_id']][] = $ecRow['category_id'];
      }
    }
    if (!empty($in['parents']) || !empty($in['cats']) || !empty($in['exps']) || !empty($in['prefs']) || !empty($sessionHealed)) {
      @cloudBackupDb($db, $dbf);
    }
    $grpTotalOnServer = (int)q('SELECT COUNT(*) FROM groups_ WHERE user_id=? AND deleted=0', [$u])->fetchColumn();
    $needResyncAll = !empty($sessionHealed) || ($since > 0 && $grpTotalOnServer === 0);
    out([
      'since' => $nextSince, 'more' => $hasMore, 'now' => $nowMs, 'notice' => $notice,
      'resync_all' => $needResyncAll,
      'parents' => array_map(fn($p) => ['id' => $p['id'], 'name' => $p['name'], 'updated' => (int)$p['updated'], 'deleted' => (int)$p['deleted']], $sel('groups_')),
      'cats' => array_map(fn($c) => ['id' => $c['id'], 'pid' => $c['group_id'], 'parent' => $c['parent'], 'name' => $c['name'], 'updated' => (int)$c['updated'], 'deleted' => (int)$c['deleted']], $sel('categories')),
      'prefs' => array_map(fn($x) => ['id' => $x['id'], 'v' => $x['v'], 'updated' => (int)$x['updated'], 'deleted' => (int)$x['deleted']], $sel('prefs')),
      'exps' => array_map(function ($e) use ($expCatMap) {
        return ['id' => $e['id'], 'pid' => $e['group_id'], 'amt' => (float)$e['amount'], 'dt' => $e['date'], 'tm' => $e['time'],
          'desc' => $e['descr'], 'note' => $e['note'], 'updated' => (int)$e['updated'], 'deleted' => (int)$e['deleted'], 'cats' => $expCatMap[$e['id']] ?? []];
      }, $expRows),
      'rejected' => $rejected,
    ]);
  }

  // Report: overall total একবারই গোনা হয়; category total-এ sub-category ধরা হয়, কিন্তু একই খরচ দুবার নয়।
  if ($a === 'report') {
    $g = (string)($_GET['group'] ?? '');
    $from = (string)($_GET['from'] ?? '0000-01-01');
    $to = (string)($_GET['to'] ?? '9999-12-31');
    if (!$okId($g)) out(['error' => 'গ্রুপ আইডি সঠিক নয়'], 400);
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $from)) $from = '0000-01-01';
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $to)) $to = '9999-12-31';

    // Verify requested group belongs to authenticated user and is not deleted
    $grp = q('SELECT 1 FROM groups_ WHERE user_id=? AND id=? AND deleted=0', [$u, $g])->fetch();
    if (!$grp) out(['error' => 'গ্রুপটি পাওয়া যায়নি বা দেখার অনুমতি নেই'], 403);

    $base = 'user_id=? AND group_id=? AND deleted=0 AND date>=? AND date<=?';
    $t = q("SELECT COALESCE(SUM(amount),0) total, COUNT(*) n FROM expenses WHERE $base", [$u, $g, $from, $to])->fetch(PDO::FETCH_ASSOC);
    $cats = [];
    foreach (q('SELECT id,name FROM categories WHERE user_id=? AND group_id=? AND parent IS NULL AND deleted=0', [$u, $g])->fetchAll(PDO::FETCH_ASSOC) as $c) {
      $r = q("WITH RECURSIVE d(id) AS (
          SELECT id FROM categories WHERE user_id=? AND id=? AND deleted=0
          UNION ALL SELECT c.id FROM categories c JOIN d ON c.parent=d.id WHERE c.user_id=? AND c.deleted=0)
        SELECT COALESCE(SUM(amount),0) total, COUNT(*) n FROM expenses e WHERE $base
          AND EXISTS(SELECT 1 FROM expense_categories x WHERE x.user_id=e.user_id AND x.expense_id=e.id AND x.category_id IN (SELECT id FROM d))",
        [$u, $c['id'], $u, $u, $g, $from, $to])->fetch(PDO::FETCH_ASSOC);
      $cats[] = ['id' => $c['id'], 'name' => $c['name'], 'total' => (float)$r['total'], 'n' => (int)$r['n']];
    }
    out(['total' => (float)$t['total'], 'transactions' => (int)$t['n'], 'categories' => $cats]);
  }

  out(['error' => 'অজানা অনুরোধ'], 404);
} catch (Throwable $e) {
  try { if (isset($db) && $db->inTransaction()) $db->rollBack(); } catch (Throwable $e2) {}
  $lf = __DIR__ . '/data/error.log';
  @file_put_contents($lf, date('c') . ' [' . ($a ?? '') . '] ' . redactApiLog($e->getMessage()) . ' @' . basename($e->getFile()) . ':' . $e->getLine() . "\n", FILE_APPEND | LOCK_EX);
  if (@filesize($lf) > 200000) @file_put_contents($lf, '');
  out(['error' => 'সার্ভারে সমস্যা হয়েছে'], 500);
}
