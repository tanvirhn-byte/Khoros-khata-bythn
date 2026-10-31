<?php
// খরচের খাতা — অ্যাডমিন প্যানেল by Tanvir (শুধু আপনার জন্য)
// ১) নিচের ADMIN_PASS বদলে লম্বা গোপন পাসওয়ার্ড দিন। না বদলালে এই পেজ চালু হবে না।
// ২) এই ফাইলের নাম বদলে গোপন কিছু রাখুন (যেমন panel-x7k2.php)।
const ADMIN_PASS = 'CHANGE_ME_NOW';
const DEFAULT_CODE = 'TanvirX';   // api.php-এর DELETE_CODE-এর সাথে মিল রাখুন
const NLOC = ['popup' => 'পপআপ নোটিস (সেন্টার্ড)', 'welcome' => 'ওয়েলকাম পপআপ', 'bar' => 'টপ নোটিস বার', 'footer' => 'ফুটার', 'login' => 'লগইন পেজ'];
const SLOC = ['welcome' => 'ওয়েলকাম পপআপ', 'notice' => 'নোটিসের ভেতরে', 'footer' => 'ফুটার', 'login' => 'লগইন পেজ', 'settings' => 'সেটিংস পেজ'];
const NTYPE = ['info' => 'তথ্য', 'success' => 'সুখবর', 'warning' => 'সতর্কতা', 'danger' => 'জরুরি'];
const SOCP = ['fb' => ['Facebook', '#1877F2', 'f'], 'ig' => ['Instagram', '#C13584', '◎'], 'wa' => ['WhatsApp', '#25D366', '✆'], 'tg' => ['Telegram', '#229ED9', '➤'], 'yt' => ['YouTube', '#FF0000', '▶'], 'tt' => ['TikTok', '#111111', '♪'], 'x' => ['X (Twitter)', '#111111', 'X'], 'li' => ['LinkedIn', '#0A66C2', 'in'], 'ms' => ['Messenger', '#0099FF', '✉'], 'em' => ['Email', '#EA4335', '@'], 'web' => ['ওয়েবসাইট', '#1F6F8B', '🌐'], 'ph' => ['ফোন', '#2E9E5B', '☎']];
const NFREQ = ['always' => 'প্রতিবার অ্যাপ খুললে', 'once' => 'শুধু একবার (এই ব্রাউজারে)', 'hours' => 'নির্দিষ্ট সময় পর পর'];
const NAUD = ['all' => 'সবাইকে', 'in' => 'শুধু লগইন করা ব্যবহারকারী', 'out' => 'শুধু লগইন ছাড়া (অতিথি)'];
const WQUOTES = "আজকের ছোট হিসাব, আগামীর বড় নিশ্চিন্ততা।\nপ্রতিটি টাকার একটা গল্প থাকে — আপনি শুধু লিখে রাখুন।\nগুছিয়ে রাখা হিসাবই সবচেয়ে বড় সঞ্চয়।\nযা মাপা হয়, তা-ই ভালো হয়।\nখরচে হিসাব, জীবনে স্বস্তি।";

date_default_timezone_set('Asia/Dhaka');
ini_set('display_errors', '0');
ini_set('session.use_strict_mode', '1');
ini_set('session.use_only_cookies', '1');
ini_set('session.cookie_httponly', '1');
function redactSensitiveLog(string $msg): string {
  return preg_replace('/(password|passwd|hash|token|delete_code|admin_hash|ADMIN_PASS)[\s:= "\']+[^\s"\',;]+/i', '$1=[REDACTED]', str_replace(["\n", "\r"], ' ', $msg));
}
set_error_handler(function ($no, $str, $file, $line) {
  @file_put_contents(__DIR__ . '/data/error.log', date('c') . ' [admin ' . $no . '] ' . redactSensitiveLog((string)$str) . ' @' . basename($file) . ':' . $line . "\n", FILE_APPEND | LOCK_EX);
  return true;
});
set_exception_handler(function ($ex) {
  @file_put_contents(__DIR__ . '/data/error.log', date('c') . ' [admin-ex] ' . redactSensitiveLog($ex->getMessage()) . ' @' . basename($ex->getFile()) . ':' . $ex->getLine() . "\n", FILE_APPEND | LOCK_EX);
  if (!headers_sent()) {
    http_response_code(500);
    header('Content-Type: text/html; charset=utf-8');
  }
  echo '<!doctype html><html lang="bn"><head><meta charset="utf-8"><title>ত্রুটি</title></head><body style="background:#0A111D;color:#E8EEF7;font-family:sans-serif;padding:40px;text-align:center"><h2>সাময়িক কারিগরি ত্রুটি</h2><p>অনুগ্রহ করে কিছুক্ষণ পর আবার চেষ্টা করুন।</p></body></html>';
  exit;
});

$isHttps = (!empty($_SERVER['HTTPS']) && strtolower((string)$_SERVER['HTTPS']) !== 'off')
  || (strtolower((string)($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '')) === 'https')
  || ((int)($_SERVER['SERVER_PORT'] ?? 0) === 443);

session_name('KH_ADMIN_SESS');
session_set_cookie_params([
  'lifetime' => 0,
  'path' => '/',
  'secure' => $isHttps,
  'httponly' => true,
  'samesite' => 'Strict'
]);
session_start();
header('X-Robots-Tag: noindex, nofollow');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
header('Referrer-Policy: no-referrer');
header("Content-Security-Policy: default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'");
header('Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=(), usb=()');
if ($isHttps) {
  header('Strict-Transport-Security: max-age=31536000; includeSubDomains');
}
header('Content-Type: text/html; charset=utf-8');

function destroyAdminSession(bool $isHttps): void {
  $_SESSION = [];
  if (ini_get('session.use_cookies')) {
    $p = session_get_cookie_params();
    setcookie(session_name(), '', [
      'expires' => time() - 3600,
      'path' => $p['path'] ?: '/',
      'domain' => $p['domain'] ?? '',
      'secure' => $isHttps,
      'httponly' => true,
      'samesite' => 'Strict'
    ]);
  }
  @session_destroy();
}

function h($s) { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }
function css() { return <<<'CSS'
*{box-sizing:border-box}
body{margin:0;color:#E8EEF7;font:16px/1.55 'Hind Siliguri',system-ui,sans-serif;padding:0 14px 40px;background:radial-gradient(800px 380px at 90% -8%,rgba(201,162,75,.16),transparent 62%),radial-gradient(640px 380px at -12% 8%,rgba(31,111,139,.2),transparent 60%),#0A111D;background-attachment:fixed;min-height:100vh}
.w{max-width:860px;margin:0 auto}
.top{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:14px 16px;margin:0 -14px 14px;background:linear-gradient(135deg,#0F1B2D,#1A3550);border-radius:0 0 22px 22px;box-shadow:0 8px 22px rgba(0,0,0,.35);position:relative}
.top::after{content:"";position:absolute;left:20px;right:20px;bottom:0;height:1px;background:linear-gradient(90deg,transparent,#E3B95C,transparent)}
.br{display:flex;align-items:center;gap:11px}.br b{display:block;font-size:17px;line-height:1.15}
.br small{font:italic 600 12px 'Playfair Display',Georgia,serif;color:#E3B95C;letter-spacing:.5px}
.lg{width:38px;height:38px;border-radius:12px;background:linear-gradient(135deg,#F5D888,#B8902F);color:#0F1B2D;display:grid;place-items:center;font:700 22px 'Playfair Display',Georgia,serif}
.tb{display:flex;gap:8px;overflow-x:auto;padding:2px 0 14px}
.tb a{flex:none;padding:8px 16px;border-radius:14px;background:#121C2E;border:1px solid #22314A;color:#B9C7DA;text-decoration:none;font-weight:600}
.tb a.on{background:linear-gradient(135deg,#F5D888,#B8902F);color:#0F1B2D;border-color:transparent}
.stats{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:14px}
@media(min-width:620px){.stats{grid-template-columns:repeat(4,1fr)}}
.st{border-radius:18px;padding:12px 14px;border:1px solid transparent;background:linear-gradient(#121C2E,#121C2E) padding-box,linear-gradient(145deg,rgba(201,162,75,.6),rgba(201,162,75,.07) 45%,#22314A) border-box}
.st small{display:block;color:#8CA0B8;font-size:12px}
.st b{font:700 24px 'Playfair Display','Hind Siliguri',Georgia,serif;color:#F5DD9B;font-feature-settings:'lnum'}
.c{border-radius:20px;padding:15px;margin-bottom:14px;border:1px solid transparent;background:linear-gradient(#121C2E,#121C2E) padding-box,linear-gradient(145deg,rgba(201,162,75,.55),rgba(201,162,75,.06) 42%,#22314A) border-box}
h2{font-size:16px;margin:0 0 10px}h2::before{content:"";display:inline-block;width:4px;height:14px;border-radius:2px;background:#C9A24B;margin-right:8px;vertical-align:-2px}
.m{color:#8CA0B8;font-size:13px}
input,textarea,select{width:100%;padding:11px 12px;border-radius:12px;border:1px solid #2c3f5c;background:#0A111D;color:#fff;margin:4px 0 8px;font:inherit}
input:focus,textarea:focus,select:focus{outline:2px solid #C9A24B;border-color:transparent}
button,.btn{display:inline-block;padding:10px 15px;border-radius:12px;border:0;background:linear-gradient(135deg,#F5D888,#B8902F);color:#0F1B2D;font:inherit;font-weight:700;text-decoration:none;cursor:pointer;box-shadow:0 6px 16px rgba(184,144,47,.3)}
button.g,.btn.g{background:#1b2a42;color:#E8EEF7;border:1px solid #2c3f5c;box-shadow:none}
button.r{background:#3a1d22;color:#ff8a7a;border:1px solid #6b2c34;box-shadow:none}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.row>input{flex:1;min-width:150px;margin:0}
.two{display:grid;grid-template-columns:1fr 1fr;gap:8px}
label.ch{display:inline-flex;gap:7px;align-items:center;padding:6px 11px;border:1px solid #2c3f5c;border-radius:12px;margin:3px 5px 3px 0;background:#0A111D;font-size:14px;cursor:pointer}
label.ch input{width:auto;margin:0}
.lb{font-size:12px;color:#8CA0B8;margin-top:6px}
.u{border-top:1px solid #22314A;padding:14px 0}.u:first-of-type{border:0}
.uh{display:flex;align-items:center;gap:12px}.ui{min-width:0}.ui b{display:block;overflow:hidden;text-overflow:ellipsis}
.av{flex:none;width:44px;height:44px;border-radius:15px;display:grid;place-items:center;font:700 19px 'Playfair Display',Georgia,serif;background:linear-gradient(135deg,#F5D888,#B8902F);color:#0F1B2D}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}
.chips span{font-size:12px;padding:2px 10px;border-radius:12px;background:#0A111D;border:1px solid #22314A;color:#B9C7DA}
details summary{cursor:pointer;color:#E3B95C;font-weight:600;list-style:none;padding:4px 0}
details summary::-webkit-details-marker{display:none}details summary::after{content:" ⌄"}details[open] summary::after{content:" ⌃"}
.fl{background:linear-gradient(135deg,rgba(45,106,65,.35),rgba(22,48,31,.6));border:1px solid #2d6a41;border-radius:14px;padding:11px 14px;margin-bottom:14px}
.tg{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.sw{display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:700}.on{background:#16301f;color:#7be0a0}.off{background:#3a1d22;color:#ff8a7a}.nt0{background:#1b2a42;color:#B9C7DA}
.chart{display:flex;align-items:flex-end;gap:5px;height:140px}.chart div{flex:1;text-align:center;font-size:10px;color:#8CA0B8}
.chart i{display:block;border-radius:6px 6px 0 0;background:linear-gradient(#F5D888,#1F6F8B);min-height:2px;margin-top:2px}
.pb{height:8px;background:#0A111D;border-radius:4px;overflow:hidden;margin:4px 0 10px}.pb i{display:block;height:100%;background:linear-gradient(90deg,#1F6F8B,#E3B95C)}
.soci{width:36px;height:36px;border-radius:12px;display:grid;place-items:center;color:#fff;font-weight:700;flex:none}
.sr{padding:12px 0;border-top:1px solid #22314A}.sr:first-of-type{border:0}
.lg2{font-size:13px;color:#B9C7DA;padding:6px 0;border-top:1px solid #22314A}.lg2:first-child{border:0}
.pv{border-radius:14px;padding:10px 12px;margin:8px 0;border:1px solid #2c3f5c;background:#0A111D;font-size:14px}
.pv-success{border-color:#2d6a41}.pv-warning{border-color:#8a6a1f}.pv-danger{border-color:#7a2f38}.pv-info{border-color:#1f6f8b}
.pvb{display:inline-block;margin-top:6px;padding:3px 12px;border-radius:14px;background:linear-gradient(135deg,#F5D888,#B8902F);color:#0F1B2D;font-weight:700;font-size:13px}
.pvs{display:inline-grid;place-items:center;width:24px;height:24px;border-radius:8px;color:#fff;font-size:12px;margin:6px 4px 0 0}
#cm{position:fixed;inset:0;background:rgba(6,10,20,.7);backdrop-filter:blur(5px);display:none;align-items:center;justify-content:center;padding:20px;z-index:20}
.cb{width:100%;max-width:380px;border-radius:26px;padding:22px 20px;text-align:center;border:1px solid transparent;background:linear-gradient(#121C2E,#121C2E) padding-box,linear-gradient(145deg,#E3B95C,rgba(201,162,75,.1) 45%,#E3B95C) border-box}
.cb .ic{width:52px;height:52px;border-radius:17px;margin:0 auto 10px;display:grid;place-items:center;font-size:24px;font-weight:700;background:linear-gradient(135deg,#FF8A7A,#C8443A);color:#fff}
.cb .row{margin-top:10px}.cb .row button{flex:1}
.ft{text-align:center;color:#8CA0B8;font-size:12px;margin-top:8px}.ft b{font:italic 700 15px 'Playfair Display',Georgia,serif;color:#E3B95C}
CSS;
}
function page($title, $body, $js = '') {
  echo '<!doctype html><html lang="bn"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><meta name="theme-color" content="#0F1B2D"><title>' . h($title) . '</title>'
    . '<link href="https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;700&family=Playfair+Display:ital,wght@0,700;1,600;1,700&display=swap" rel="stylesheet"><style>' . css() . '</style></head><body><div class="w">' . $body . '<div class="ft">Crafted with care by <b>Tanvir</b></div></div>' . $js . '</body></html>';
}
function hid($cs, $act, $tab = '', $id = null) {
  return '<input type="hidden" name="csrf" value="' . $cs . '"><input type="hidden" name="act" value="' . $act . '"><input type="hidden" name="tab" value="' . $tab . '">' . ($id !== null ? '<input type="hidden" name="id" value="' . h($id) . '">' : '');
}
function top($right = '') {
  return '<div class="top"><div class="br"><span class="lg">T</span><div><b>অ্যাডমিন প্যানেল</b><small>খরচের খাতা · by Tanvir</small></div></div>' . $right . '</div>';
}
function cut($s, $n) { $s = trim((string)$s); return function_exists('mb_substr') ? mb_substr($s, 0, $n) : substr($s, 0, $n * 3); }
function cleanUrl($u, $k = '') {
  $u = trim((string)$u);
  if ($u === '') return '';
  if (preg_match('/^(javascript|data|vbscript|file|blob):/i', $u)) return false;
  if ($k === 'em') { $u = preg_replace('/^mailto:/i', '', $u); return filter_var($u, FILTER_VALIDATE_EMAIL) ? 'mailto:' . $u : false; }
  if ($k === 'ph') { $d = preg_replace('/[^\d+]/', '', $u); return preg_match('/^\+?\d{5,15}$/', $d) ? 'tel:' . $d : false; }
  if ($k === 'wa' && preg_match('/^\+?\d{6,15}$/', $u)) return 'https://wa.me/' . ltrim($u, '+');
  if (!preg_match('#^https?://#i', $u)) $u = 'https://' . $u;
  return (filter_var($u, FILTER_VALIDATE_URL) && preg_match('#^https?://#i', $u)) ? $u : false;
}
function socList($S) {
  if (!is_array($S) || !$S) return [];
  if (array_keys($S) === range(0, count($S) - 1)) $out = array_values($S);
  else { $out = []; foreach ($S as $k => $x) if (isset(SOCP[$k])) $out[] = ['p' => $k, 'label' => '', 'url' => $x['url'] ?? '', 'on' => $x['on'] ?? 0, 'loc' => $x['loc'] ?? []]; }
  foreach ($out as $i => $x) $out[$i]['id'] = sid($x);
  return $out;
}
function selb($name, $opts, $cur) {
  $o = '<select name="' . $name . '">';
  foreach ($opts as $k => $v) $o .= '<option value="' . h($k) . '"' . ((string)$k === (string)$cur ? ' selected' : '') . '>' . h($v) . '</option>';
  return $o . '</select>';
}
function sid($x) { return $x['id'] ?? ('k' . substr(md5(($x['p'] ?? '') . '|' . ($x['url'] ?? '')), 0, 6)); }
function fmtT($s) { $s = (int)$s; if ($s >= 3600 && $s % 3600 === 0) return ($s / 3600) . ' ঘণ্টা'; if ($s >= 60 && $s % 60 === 0) return ($s / 60) . ' মিনিট'; return $s . ' সেকেন্ড'; }
function tu($name, $secs) {
  $secs = (int)$secs; $u = ($secs >= 3600 && $secs % 3600 === 0) ? 3600 : (($secs >= 60 && $secs % 60 === 0) ? 60 : 1); $v = (int)($secs / $u);
  return '<div class="row"><input type="number" name="' . $name . '_v" min="0" value="' . $v . '"><select name="' . $name . '_u" style="width:auto;margin:0"><option value="1"' . ($u === 1 ? ' selected' : '') . '>সেকেন্ড</option><option value="60"' . ($u === 60 ? ' selected' : '') . '>মিনিট</option><option value="3600"' . ($u === 3600 ? ' selected' : '') . '>ঘণ্টা</option></select></div>';
}
function tsec($name, $max, $def = 0) {
  $v = isset($_POST[$name . '_v']) ? (int)$_POST[$name . '_v'] : $def; $u = (int)($_POST[$name . '_u'] ?? 1);
  if (!in_array($u, [1, 60, 3600], true)) $u = 1;
  return max(0, min($max, $v * $u));
}
function fx($v) { $v = (string)$v; if (strlen($v) === 10) $v .= 'T00:00'; return $v; }

if (ADMIN_PASS === 'CHANGE_ME_NOW') {
  page('সেটআপ দরকার', top() . '<div class="c"><h2>সেটআপ দরকার</h2><p>এই ফাইলটি (admin.php) খুলে একদম উপরের <b>ADMIN_PASS</b>-এর লেখা বদলে একটি লম্বা গোপন পাসওয়ার্ড দিন। তারপর এই পেজ আবার খুলুন।</p></div>');
  exit;
}
require_once __DIR__ . '/db_cloud.php';
$dataDir = __DIR__ . '/data';
if (!is_dir($dataDir)) @mkdir($dataDir, 0750, true);
if (is_dir($dataDir)) {
  if (!is_file($dataDir . '/.htaccess')) {
    @file_put_contents($dataDir . '/.htaccess', "<IfModule mod_authz_core.c>\nRequire all denied\n</IfModule>\n<IfModule !mod_authz_core.c>\nOrder allow,deny\nDeny from all\n</IfModule>\n");
  }
  if (!is_file($dataDir . '/index.php')) {
    @file_put_contents($dataDir . '/index.php', "<?php http_response_code(403); exit('Forbidden');\n");
  }
}
$dbf = $dataDir . '/khoroch.sqlite';
if (!extension_loaded('pdo_sqlite')) {
  page('ডেটাবেস ত্রুটি', top() . '<div class="c"><h2>PDO SQLite চালু নেই</h2><p>এই hosting-এ PDO SQLite এক্সটেনশন চালু নেই।</p></div>');
  exit;
}
if (!is_file($dbf) || filesize($dbf) < 4096) {
  @cloudRestoreDb($dbf);
}
$db = new PDO('sqlite:' . $dbf);
$db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
$db->exec('PRAGMA busy_timeout=5000');
try {
  $db->exec('PRAGMA journal_mode=WAL;');
  $db->exec('PRAGMA synchronous=NORMAL;');
  $db->exec('PRAGMA temp_store=MEMORY;');
} catch (Throwable $e) {}
$db->exec("
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, hash TEXT NOT NULL, rev INTEGER NOT NULL DEFAULT 0, created INTEGER, synced INTEGER, status TEXT NOT NULL DEFAULT 'active', fullname TEXT DEFAULT '', name TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, t INTEGER, type TEXT, who TEXT, ip TEXT);
CREATE INDEX IF NOT EXISTS ix_logs ON logs(type,ip,t);
CREATE TABLE IF NOT EXISTS visits(day TEXT, vid TEXT, hits INTEGER, last INTEGER, plat TEXT, PRIMARY KEY(day,vid));
CREATE TABLE IF NOT EXISTS tokens(token_hash TEXT PRIMARY KEY, user_id INTEGER, created INTEGER, last_seen INTEGER);
CREATE INDEX IF NOT EXISTS ix_tokens_user ON tokens(user_id);
CREATE TABLE IF NOT EXISTS groups_(user_id INTEGER, id TEXT, name TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id,id));
CREATE TABLE IF NOT EXISTS categories(user_id INTEGER, id TEXT, group_id TEXT, parent TEXT, name TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id,id));
CREATE TABLE IF NOT EXISTS expenses(user_id INTEGER, id TEXT, group_id TEXT, amount REAL, date TEXT, time TEXT, descr TEXT, note TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id,id));
CREATE TABLE IF NOT EXISTS expense_categories(user_id INTEGER, expense_id TEXT, category_id TEXT, PRIMARY KEY(user_id,expense_id,category_id));
CREATE TABLE IF NOT EXISTS prefs(user_id INTEGER, id TEXT, v TEXT, updated INTEGER, deleted INTEGER DEFAULT 0, rev INTEGER, PRIMARY KEY(user_id,id));
");
$ucolsInit = array_column($db->query('PRAGMA table_info(users)')->fetchAll(PDO::FETCH_ASSOC), 'name');
if (!in_array('created', $ucolsInit)) $db->exec('ALTER TABLE users ADD COLUMN created INTEGER');
if (!in_array('synced', $ucolsInit)) $db->exec('ALTER TABLE users ADD COLUMN synced INTEGER');
if (!in_array('status', $ucolsInit)) $db->exec("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'");
if (!in_array('fullname', $ucolsInit)) $db->exec("ALTER TABLE users ADD COLUMN fullname TEXT DEFAULT ''");
if (!in_array('name', $ucolsInit)) $db->exec("ALTER TABLE users ADD COLUMN name TEXT DEFAULT ''");
$tcols = array_column($db->query('PRAGMA table_info(tokens)')->fetchAll(PDO::FETCH_ASSOC), 'name');
if ($tcols && !in_array('last_seen', $tcols)) $db->exec('ALTER TABLE tokens ADD COLUMN last_seen INTEGER');
function q($sql, $p = []) { global $db; $s = $db->prepare($sql); $s->execute($p); return $s; }
function sraw($k) { return q('SELECT v FROM settings WHERE k=?', [$k])->fetchColumn(); }
function sset($k, $v) { q('INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)', [$k, $v]); }
function sj($k, $d) { $v = sraw($k); if ($v === false) return $d; $j = json_decode($v, true); return $j === null ? $d : $j; }
function sjset($k, $v) { sset($k, json_encode($v, JSON_UNESCAPED_UNICODE)); }
function ev($type, $who = '') { q('INSERT INTO logs(t,type,who,ip) VALUES(?,?,?,?)', [time(), $type, $who, $_SERVER['REMOTE_ADDR'] ?? '']); }
function logit($m) { ev('a_misc', $m); }
function adminOk($pw) {
  $pw = (string)$pw;
  if ($pw === '') return false;
  $hh = sraw('admin_hash');
  if ($hh !== false && $hh !== '') {
    return password_verify($pw, $hh);
  }
  if (hash_equals(ADMIN_PASS, $pw)) {
    sset('admin_hash', password_hash($pw, PASSWORD_DEFAULT));
    return true;
  }
  return false;
}

$self = basename(__FILE__);
$clientIp = (string)($_SERVER['REMOTE_ADDR'] ?? '');
$fn = (int)sraw('fail_n'); $ft = (int)sraw('fail_t');
$ipFails = (int)q("SELECT COUNT(*) FROM logs WHERE type='admin_fail' AND ip=? AND t>?", [$clientIp, time() - 600])->fetchColumn();
$locked = ($fn >= 5 && time() - $ft < 600) || ($ipFails >= 5);

if (isset($_POST['login'])) {
  $loginCsrfOk = !isset($_POST['csrf']) || (isset($_SESSION['login_csrf']) && hash_equals((string)$_SESSION['login_csrf'], (string)$_POST['csrf']));
  if (!$loginCsrfOk) {
    http_response_code(403);
    $_SESSION['bad'] = 'csrf';
  } elseif ($locked) {
    $_SESSION['bad'] = 'locked';
  } elseif (adminOk((string)($_POST['pw'] ?? ''))) {
    sset('fail_n', '0');
    session_regenerate_id(true);
    $_SESSION['ok'] = 1;
    $_SESSION['admin_auth'] = true;
    $_SESSION['created_at'] = time();
    $_SESSION['last_active'] = time();
    $_SESSION['ua_hash'] = hash('sha256', (string)($_SERVER['HTTP_USER_AGENT'] ?? ''));
    $_SESSION['csrf'] = bin2hex(random_bytes(32));
    unset($_SESSION['login_csrf']);
    ev('admin_login');
    header('Location: ' . $self);
    exit;
  } else {
    ev('admin_fail'); usleep(800000);
    $fn = (time() - $ft > 600) ? 1 : $fn + 1;
    sset('fail_n', (string)$fn); sset('fail_t', (string)time());
    $_SESSION['bad'] = ($fn >= 5 || ($ipFails + 1) >= 5) ? 'locked' : 'wrong';
  }
  header('Location: ' . $self);
  exit;
}

// Validate active admin session integrity & timeouts (30m idle, 12h absolute)
if (!empty($_SESSION['ok'])) {
  $now = time();
  $idleExpired = ($now - (int)($_SESSION['last_active'] ?? 0)) > 1800;
  $absExpired = ($now - (int)($_SESSION['created_at'] ?? $now)) > 43200;
  $uaNow = hash('sha256', (string)($_SERVER['HTTP_USER_AGENT'] ?? ''));
  $uaMismatch = isset($_SESSION['ua_hash']) && !hash_equals((string)$_SESSION['ua_hash'], $uaNow);
  $missingAuthFlag = empty($_SESSION['admin_auth']) || empty($_SESSION['csrf']);

  if ($idleExpired || $absExpired || $uaMismatch || $missingAuthFlag) {
    destroyAdminSession($isHttps);
    session_start();
    $_SESSION['bad'] = 'expired';
  } else {
    $_SESSION['last_active'] = $now;
  }
}

if (empty($_SESSION['ok']) || empty($_SESSION['admin_auth'])) {
  if ($_SERVER['REQUEST_METHOD'] === 'POST' || isset($_GET['cfgdl']) || isset($_GET['usercsv']) || isset($_GET['dbdl'])) {
    http_response_code(403);
  }
  if (empty($_SESSION['login_csrf'])) {
    $_SESSION['login_csrf'] = bin2hex(random_bytes(16));
  }
  $bad = $_SESSION['bad'] ?? ''; unset($_SESSION['bad']);
  $em = $bad === 'locked' ? 'অনেকবার ভুল হয়েছে। ১০ মিনিট পর আবার চেষ্টা করুন।'
    : ($bad === 'wrong' ? 'পাসওয়ার্ড ভুল'
    : ($bad === 'expired' ? 'সেশনের মেয়াদ শেষ হয়েছে। অনুগ্রহ করে আবার লগইন করুন।'
    : ($bad === 'csrf' ? 'নিরাপত্তা টোকেন মেলেনি, আবার চেষ্টা করুন।' : '')));
  page('অ্যাডমিন লগইন', top() . '<div class="c" style="max-width:420px;margin:40px auto"><h2>লগইন</h2>' . ($em ? '<p style="color:#ff8a7a">' . h($em) . '</p>' : '') .
    '<form method="post"><input type="hidden" name="csrf" value="' . h($_SESSION['login_csrf']) . '"><input type="password" name="pw" placeholder="অ্যাডমিন পাসওয়ার্ড" autocomplete="current-password" autofocus><button name="login" value="1" style="width:100%">ঢুকুন</button></form></div>');
  exit;
}

if (isset($_GET['cfgdl']) || isset($_GET['usercsv']) || isset($_GET['dbdl'])) {
  $dlCsrf = (string)($_GET['csrf'] ?? $_POST['csrf'] ?? '');
  if (!hash_equals((string)$_SESSION['csrf'], $dlCsrf)) {
    http_response_code(403);
    page('অনুমতি নেই', top() . '<div class="c"><h2>অনুরোধ বাতিল হয়েছে</h2><p class="m">নিরাপত্তা টোকেন (CSRF) সঠিক নয়। অ্যাডমিন প্যানেল রিফ্রেশ করে আবার চেষ্টা করুন।</p><div class="row"><a class="btn g" href="' . h($self) . '">ফিরে যান</a></div></div>');
    exit;
  }
}

if (isset($_GET['cfgdl'])) {
  $d = [];
  foreach (['notices', 'social', 'socmode', 'welcome', 'brand', 'maint', 'reg_mode'] as $k) { $v = sraw($k); if ($v !== false) $d[$k] = $v; }
  logit('কনফিগ ব্যাকআপ ডাউনলোড');
  header('Content-Type: application/json; charset=utf-8');
  header('Content-Disposition: attachment; filename="khoroch-config-' . date('Ymd-His') . '.json"');
  echo json_encode(['v' => 1, 'data' => $d], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
  exit;
}
if (isset($_GET['usercsv'])) {
  $cols = array_column($db->query('PRAGMA table_info(users)')->fetchAll(PDO::FETCH_ASSOC), 'name');
  $sel = 'u.id, u.email, ' . (in_array('status', $cols) ? 'u.status' : "'active'") . ' st, ' . (in_array('created', $cols) ? 'u.created' : 'NULL') . ' cr, ' . (in_array('synced', $cols) ? 'u.synced' : 'NULL') . ' sy, (SELECT MAX(created) FROM tokens t WHERE t.user_id=u.id) lg';
  $f = fn($t) => $t ? date('Y-m-d H:i', (int)$t) : '';
  header('Content-Type: text/csv; charset=utf-8');
  header('Content-Disposition: attachment; filename="users-' . date('Ymd') . '.csv"');
  echo "\xEF\xBB\xBFid,email,status,created,last_login,last_sync\n";
  foreach (q("SELECT $sel FROM users u ORDER BY u.id")->fetchAll(PDO::FETCH_ASSOC) as $r) echo implode(',', [(int)$r['id'], '"' . str_replace('"', '""', $r['email']) . '"', $r['st'], $f($r['cr']), $f($r['lg']), $f($r['sy'])]) . "\n";
  logit('ইউজার তালিকা CSV ডাউনলোড');
  exit;
}
if (isset($_GET['dbdl'])) {
  $backupDir = dirname($dbf);
  $tmpBackup = $backupDir . '/backup_' . bin2hex(random_bytes(8)) . '.sqlite';
  $success = false;

  // 1. Primary Strategy: SQLite 3.27+ VACUUM INTO (atomic, crash-consistent snapshot)
  try {
    $escapedPath = str_replace("'", "''", $tmpBackup);
    $db->exec("VACUUM INTO '{$escapedPath}'");
    if (is_file($tmpBackup) && filesize($tmpBackup) > 0) {
      $success = true;
    }
  } catch (Throwable $eVacuum) {
    if (is_file($tmpBackup)) @unlink($tmpBackup);
    $success = false;
  }

  // 2. Secondary Fallback: Verified Checkpoint + File Copy
  if (!$success) {
    try {
      $stmt = $db->query('PRAGMA wal_checkpoint(TRUNCATE)');
      $chk = $stmt ? $stmt->fetch(PDO::FETCH_NUM) : null;
      if ($chk && (int)$chk[0] === 0) {
        if (@copy($dbf, $tmpBackup) && is_file($tmpBackup) && filesize($tmpBackup) > 0) {
          $success = true;
        }
      }
    } catch (Throwable $eChk) {
      $success = false;
    }
  }

  // 3. Verify physical integrity before streaming
  if ($success && is_file($tmpBackup)) {
    try {
      $testDb = new PDO('sqlite:' . $tmpBackup);
      $testDb->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
      $quickCheck = $testDb->query('PRAGMA quick_check')->fetchColumn();
      if ($quickCheck !== 'ok') {
        $success = false;
      }
      $testDb = null;
    } catch (Throwable $eTest) {
      $success = false;
    }
  }

  if ($success && is_file($tmpBackup)) {
    logit('নিরাপদ ডেটাবেস ব্যাকআপ ডাউনলোড');
    header('Content-Type: application/octet-stream');
    header('Content-Disposition: attachment; filename="khoroch-' . date('Ymd-His') . '.sqlite"');
    header('Content-Length: ' . filesize($tmpBackup));
    header('Cache-Control: no-store, no-cache, must-revalidate');
    readfile($tmpBackup);
    @unlink($tmpBackup);
    exit;
  } else {
    if (is_file($tmpBackup)) @unlink($tmpBackup);
    header('HTTP/1.1 503 Service Unavailable');
    page('ব্যাকআপ ত্রুটি', top() . '<div class="c"><h2>ব্যাকআপ নেওয়া যায়নি</h2><p class="m">ডেটাবেস ব্যস্ত থাকার কারণে এই মুহূর্তে নিরাপদ স্ন্যাপশট তৈরি করা যায়নি। অনুগ্রহ করে কয়েক সেকেন্ড পর আবার চেষ্টা করুন।</p><div class="row"><a class="btn g" href="' . basename(__FILE__) . '">ফিরে যান</a></div></div>');
    exit;
  }
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['act'])) {
  $msg = '';
  $tab = preg_replace('/[^a-z]/', '', (string)($_POST['tab'] ?? '')) ?: 'ov';
  if (!hash_equals((string)$_SESSION['csrf'], (string)($_POST['csrf'] ?? ''))) {
    http_response_code(403);
    $msg = 'অনুরোধ বাতিল হয়েছে (CSRF টোকেন মেলেনি), পেজ রিফ্রেশ করে আবার চেষ্টা করুন।';
    $_SESSION['flash'] = $msg;
    page('অনুরোধ বাতিল', top() . '<div class="c"><h2>অনুরোধ বাতিল হয়েছে</h2><p class="m">' . h($msg) . '</p><div class="row"><a class="btn g" href="' . h($self) . '#' . h($tab) . '">ফিরে যান</a></div></div>');
    exit;
  } else {
    $id = (string)($_POST['id'] ?? '');
    $uid = (int)$id;
    switch ($_POST['act']) {
      case 'logout':
        logit('অ্যাডমিন লগআউট');
        destroyAdminSession($isHttps);
        header('Location: ' . $self);
        exit;
      case 'reset':
        $pw = (string)($_POST['pw'] ?? '');
        if (strlen($pw) < 8) { $msg = 'নতুন পাসওয়ার্ড ৮+ অক্ষরের হতে হবে।'; break; }
        q('UPDATE users SET hash=? WHERE id=?', [password_hash($pw, PASSWORD_DEFAULT), $uid]);
        q('DELETE FROM tokens WHERE user_id=?', [$uid]);
        logit("ব্যবহারকারী #$uid-এর পাসওয়ার্ড রিসেট");
        $msg = 'পাসওয়ার্ড বদলানো হয়েছে। ব্যবহারকারীকে নতুন পাসওয়ার্ডে আবার লগইন করতে হবে।';
        break;
      case 'approve':
        q("UPDATE users SET status='active' WHERE id=?", [$uid]); logit("ব্যবহারকারী #$uid অনুমোদিত");
        $msg = 'ব্যবহারকারী অনুমোদিত হয়েছে। এখন লগইন করতে পারবে।';
        break;
      case 'block':
        q("UPDATE users SET status='blocked' WHERE id=?", [$uid]); q('DELETE FROM tokens WHERE user_id=?', [$uid]); logit("ব্যবহারকারী #$uid ব্লক");
        $msg = 'ব্যবহারকারী ব্লক হয়েছে ও লগআউট হয়েছে।';
        break;
      case 'unblock':
        q("UPDATE users SET status='active' WHERE id=?", [$uid]); logit("ব্যবহারকারী #$uid আনব্লক");
        $msg = 'ব্যবহারকারী আনব্লক হয়েছে।';
        break;
      case 'purge':
        $n = q('DELETE FROM tokens WHERE COALESCE(last_seen, created) < ?', [time() - 90 * 86400])->rowCount();
        logit('পুরনো লগইন সেশন পরিষ্কার'); $msg = $n . 'টি পুরনো লগইন সেশন মুছে ফেলা হয়েছে।';
        break;
      case 'poll_save':
        $pl = max(5, min(120, (int)($_POST['poll'] ?? 15)));
        sset('poll', (string)$pl); logit('সিঙ্ক চেকের ব্যবধান: ' . $pl . ' সেকেন্ড');
        $msg = 'সিঙ্ক চেকের ব্যবধান ' . $pl . ' সেকেন্ড করা হয়েছে।';
        break;
      case 'errclear':
        @file_put_contents(__DIR__ . '/data/error.log', ''); logit('সার্ভার ত্রুটির লগ পরিষ্কার');
        $msg = 'সার্ভার ত্রুটির লগ পরিষ্কার হয়েছে।';
        break;
      case 'vacuum':
        try { $db->exec('VACUUM'); $msg = 'ডেটাবেস অপ্টিমাইজ হয়েছে।'; } catch (Throwable $e) { $msg = 'অপ্টিমাইজ করা যায়নি।'; }
        break;
      case 'kick':
        q('DELETE FROM tokens WHERE user_id=?', [$uid]);
        logit("ব্যবহারকারী #$uid লগআউট করা হয়েছে");
        $msg = 'ব্যবহারকারীকে লগআউট করা হয়েছে।';
        break;
      case 'deluser':
        $db->beginTransaction();
        foreach (['expense_categories', 'expenses', 'categories', 'groups_', 'prefs', 'tokens'] as $t) q("DELETE FROM $t WHERE user_id=?", [$uid]);
        q('DELETE FROM users WHERE id=?', [$uid]);
        $db->commit();
        logit("ব্যবহারকারী #$uid মুছে ফেলা হয়েছে");
        $msg = 'ব্যবহারকারী ও তার সব ডেটা মুছে ফেলা হয়েছে।';
        break;
      case 'code':
        $c = (string)($_POST['code'] ?? '');
        if (strlen($c) < 4) { $msg = 'কোড কমপক্ষে ৪ অক্ষরের হতে হবে।'; break; }
        sset('delete_code', $c); logit('ইউনিভার্সাল কোড বদলানো হয়েছে');
        $msg = 'ইউনিভার্সাল কোড বদলানো হয়েছে।';
        break;
      case 'regmode':
        $v = (string)($_POST['v'] ?? '');
        if (!in_array($v, ['open', 'approval', 'closed'], true)) break;
        sset('reg_mode', $v); logit('রেজিস্ট্রেশন মোড: ' . $v);
        $msg = 'নতুন অ্যাকাউন্ট খোলার নিয়ম বদলানো হয়েছে।';
        break;
      case 'maint':
        $on = !empty($_POST['on']) ? 1 : 0;
        sjset('maint', ['on' => $on, 'msg' => cut($_POST['msg'] ?? '', 200)]);
        logit($on ? 'মেইনটেন্যান্স মোড চালু' : 'মেইনটেন্যান্স মোড বন্ধ');
        $msg = $on ? 'মেইনটেন্যান্স মোড চালু হয়েছে। অ্যাপ খুললে ব্যবহারকারীরা বার্তা দেখবে।' : 'মেইনটেন্যান্স মোড বন্ধ হয়েছে।';
        break;
      case 'apw':
        $new = (string)($_POST['new'] ?? '');
        if (!adminOk((string)($_POST['old'] ?? ''))) { $msg = 'বর্তমান অ্যাডমিন পাসওয়ার্ড ভুল।'; break; }
        if (strlen($new) < 10) { $msg = 'নতুন পাসওয়ার্ড কমপক্ষে ১০ অক্ষরের হতে হবে।'; break; }
        sset('admin_hash', password_hash($new, PASSWORD_DEFAULT)); logit('অ্যাডমিন পাসওয়ার্ড বদলানো হয়েছে');
        $msg = 'অ্যাডমিন পাসওয়ার্ড বদলানো হয়েছে।';
        break;
      case 'legacy_clear':
        sset('notice', ''); logit('পুরনো নোটিস মুছে ফেলা হয়েছে');
        $msg = 'পুরনো নোটিস মুছে ফেলা হয়েছে।';
        break;
      case 'notice_dup':
        $N = sj('notices', []);
        foreach ($N as $n) if (($n['id'] ?? '') === $id) { $c = $n; $c['id'] = substr(bin2hex(random_bytes(4)), 0, 8); $c['title'] = cut(($n['title'] ?? '') . ' (কপি)', 80); $c['on'] = 0; $N[] = $c; break; }
        sjset('notices', array_values($N)); logit('নোটিস কপি');
        $msg = 'নোটিস কপি হয়েছে (বন্ধ অবস্থায়)। এডিট করে চালু করুন।';
        break;
      case 'cfg_import':
        $f = $_FILES['f'] ?? null;
        if (!$f || $f['error'] !== UPLOAD_ERR_OK || $f['size'] > 300000) { $msg = 'ফাইল আপলোড হয়নি বা অনেক বড়।'; break; }
        $j = json_decode((string)file_get_contents($f['tmp_name']), true);
        if (!is_array($j) || !isset($j['data']) || !is_array($j['data'])) { $msg = 'এটি সঠিক কনফিগ ব্যাকআপ ফাইল নয়।'; break; }
        $cnt = 0;
        foreach (['notices', 'social', 'welcome', 'brand', 'maint'] as $k) if (isset($j['data'][$k]) && is_string($j['data'][$k]) && json_decode($j['data'][$k], true) !== null) { sset($k, $j['data'][$k]); $cnt++; }
        foreach (['socmode', 'reg_mode'] as $k) if (isset($j['data'][$k]) && is_string($j['data'][$k]) && strlen($j['data'][$k]) < 20) { sset($k, $j['data'][$k]); $cnt++; }
        logit('কনফিগ ইমপোর্ট (' . $cnt . 'টি)');
        $msg = $cnt . 'টি সেটিং ইমপোর্ট হয়েছে।';
        break;
      case 'notice_save':
        $N = sj('notices', []);
        $nid = preg_replace('/[^a-z0-9]/', '', (string)($_POST['nid'] ?? ''));
        $link = cleanUrl($_POST['link'] ?? '');
        if ($link === false) { $msg = 'লিংকটি সঠিক নয়।'; break; }
        $loc = array_values(array_intersect(array_keys(NLOC), (array)($_POST['loc'] ?? [])));
        $title = cut($_POST['title'] ?? '', 80); $body = cut($_POST['msg'] ?? '', 400);
        if (($title === '' && $body === '') || !$loc) { $msg = 'শিরোনাম বা বার্তা এবং কমপক্ষে একটি লোকেশন দিন।'; break; }
        $type = (string)($_POST['type'] ?? 'info'); if (!isset(NTYPE[$type])) $type = 'info';
        $freq = (string)($_POST['freq'] ?? 'always'); if (!isset(NFREQ[$freq])) $freq = 'always';
        $aud = (string)($_POST['aud'] ?? 'all'); if (!isset(NAUD[$aud])) $aud = 'all';
        $dt = function ($d) { $d = (string)$d; return preg_match('/^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?$/', $d) ? $d : ''; };
        $everyS = tsec('every', 30 * 86400, 86400); if ($everyS < 1) $everyS = 86400;
        $valid = array_column(socList(sj('social', [])), 'id');
        $row = ['id' => $nid ?: substr(bin2hex(random_bytes(4)), 0, 8), 'title' => $title, 'msg' => $body, 'link' => $link, 'btn' => cut($_POST['btn'] ?? '', 30), 'type' => $type, 'loc' => $loc,
          'on' => !empty($_POST['on']) ? 1 : 0, 'from' => $dt($_POST['from'] ?? ''), 'to' => $dt($_POST['to'] ?? ''), 'freq' => $freq,
          'every' => (int)ceil($everyS / 3600), 'everyS' => $everyS, 'secs' => tsec('secs', 86400, 0), 'aud' => $aud,
          'pri' => max(0, min(999, (int)($_POST['pri'] ?? 10))), 'socs' => array_values(array_intersect($valid, (array)($_POST['socs'] ?? [])))];
        $found = false;
        foreach ($N as $k => $n) if (($n['id'] ?? '') === $row['id']) { $N[$k] = $row; $found = true; }
        if (!$found) $N[] = $row;
        sjset('notices', array_values($N)); logit('নোটিস সেভ: ' . ($title ?: $body));
        $msg = 'নোটিস সেভ হয়েছে।';
        break;
      case 'notice_tog':
      case 'notice_del':
        $N = sj('notices', []); $out = [];
        foreach ($N as $n) {
          if (($n['id'] ?? '') === $id) { if ($_POST['act'] === 'notice_del') continue; $n['on'] = empty($n['on']) ? 1 : 0; }
          $out[] = $n;
        }
        sjset('notices', $out); logit($_POST['act'] === 'notice_del' ? 'নোটিস মুছে ফেলা হয়েছে' : 'নোটিস চালু/বন্ধ');
        $msg = $_POST['act'] === 'notice_del' ? 'নোটিস মুছে ফেলা হয়েছে।' : 'নোটিসের অবস্থা বদলানো হয়েছে।';
        break;
      case 'social':
        $L = []; $bad = false;
        foreach ((array)($_POST['s'] ?? []) as $r) {
          $p = (string)($r['p'] ?? ''); if (!isset(SOCP[$p])) continue;
          $u = cleanUrl($r['url'] ?? '', $p);
          if ($u === false) { $msg = SOCP[$p][0] . '-এর লিংকটি সঠিক নয়।'; $bad = true; break; }
          if ($u === '') continue;
          $L[] = ['id' => (preg_replace('/[^A-Za-z0-9]/', '', (string)($r['id'] ?? '')) ?: substr(bin2hex(random_bytes(3)), 0, 6)), 'p' => $p, 'label' => cut($r['label'] ?? '', 30), 'url' => $u, 'on' => !empty($r['on']) ? 1 : 0, 'loc' => array_values(array_intersect(array_keys(SLOC), (array)($r['loc'] ?? [])))];
        }
        if ($bad) break;
        $m = (string)($_POST['socmode'] ?? 'none'); if (!in_array($m, ['none', 'all', 'sel'], true)) $m = 'none';
        sjset('social', $L); sset('socmode', $m); logit('সোশ্যাল লিংক আপডেট');
        $msg = 'সোশ্যাল মিডিয়া সেটিংস সেভ হয়েছে।';
        break;
      case 'welcome_save':
        $qs = array_values(array_filter(array_map(function ($x) { return cut($x, 140); }, preg_split('/\r?\n/', (string)($_POST['quotes'] ?? ''))), function ($x) { return $x !== ''; }));
        $fq = (string)($_POST['freq'] ?? 'always'); if (!isset(NFREQ[$fq])) $fq = 'always';
        $au = (string)($_POST['aud'] ?? 'all'); if (!isset(NAUD[$au])) $au = 'all';
        $W = ['on' => !empty($_POST['on']) ? 1 : 0, 'logo' => cut($_POST['logo'] ?? 'T', 2) ?: 'T', 'title' => cut($_POST['title'] ?? '', 40), 'tag' => cut($_POST['tag'] ?? '', 80),
          'greet' => !empty($_POST['greet']) ? 1 : 0, 'quotesOn' => !empty($_POST['quotesOn']) ? 1 : 0, 'quotes' => array_slice($qs, 0, 30),
          'btn' => cut($_POST['btn'] ?? '', 30) ?: 'শুরু করুন →', 'dur' => tsec('dur', 86400, 5), 'bar' => !empty($_POST['bar']) ? 1 : 0,
          'credit' => !empty($_POST['credit']) ? 1 : 0, 'creditText' => cut($_POST['creditText'] ?? '', 40), 'creditName' => cut($_POST['creditName'] ?? '', 30) ?: 'Tanvir',
          'freq' => $fq, 'every' => (int)ceil(max(1, tsec('every', 30 * 86400, 86400)) / 3600), 'everyS' => max(1, tsec('every', 30 * 86400, 86400)), 'aud' => $au];
        sjset('welcome', $W); logit('ওয়েলকাম পপআপ আপডেট');
        $msg = 'ওয়েলকাম পপআপের সেটিংস সেভ হয়েছে।';
        break;
      case 'welcome_reset':
        q("DELETE FROM settings WHERE k='welcome'"); logit('ওয়েলকাম পপআপ ডিফল্টে ফেরানো হয়েছে');
        $msg = 'ওয়েলকাম পপআপ ডিফল্ট অবস্থায় ফিরেছে।';
        break;
      case 'brand_save':
        sjset('brand', ['logo' => cut($_POST['logo'] ?? 'T', 3) ?: 'T', 'name' => cut($_POST['name'] ?? '', 30), 'by' => cut($_POST['by'] ?? '', 30), 'foot' => cut($_POST['foot'] ?? '', 50), 'sig' => cut($_POST['sig'] ?? '', 30)]);
        logit('ব্র্যান্ডিং আপডেট');
        $msg = 'হেডার, লগইন পেজ ও ফুটারের ব্র্যান্ডিং সেভ হয়েছে।';
        break;
      case 'app_update_save':
        $on = !empty($_POST['on']) ? 1 : 0;
        $ver = cut(trim((string)($_POST['ver'] ?? '1.0.1')), 20) ?: '1.0.1';
        $build = max(1, min(99999, (int)($_POST['build'] ?? 2)));
        $force = !empty($_POST['force']) ? 1 : 0;
        $title = cut(trim((string)($_POST['title'] ?? '')), 80) ?: 'নতুন আপডেট উপলব্ধ!';
        $msgTxt = cut(trim((string)($_POST['msg'] ?? '')), 500) ?: 'অ্যাপের একটি নতুন ও উন্নত সংস্করণ প্রস্তুত আছে।';
        $url = cleanUrl($_POST['url'] ?? '');
        $btn = cut(trim((string)($_POST['btn'] ?? '')), 30) ?: 'ইনস্টল করুন';
        if ($url === false || ($on && empty($url))) {
          $msg = 'সঠিক ডাউনলোড বা ইনস্টলেশন লিংক (URL) দিন।';
          break;
        }
        $appUp = ['on' => $on, 'ver' => $ver, 'build' => $build, 'force' => $force, 'title' => $title, 'msg' => $msgTxt, 'url' => $url, 'btn' => $btn];
        sjset('app_update', $appUp);
        logit('অ্যাপ আপডেট সেটিংস সেভ: v' . $ver . ' (' . ($on ? 'চালু' : 'বন্ধ') . ')');
        $msg = 'অ্যান্ড্রয়েড অ্যাপ আপডেট সেটিংস সেভ হয়েছে।';
        break;
      case 'cloud_sync_save':
        $ghTok = trim((string)($_POST['github_token'] ?? ''));
        if ($ghTok === '') {
          q("DELETE FROM settings WHERE k='github_token'");
          @unlink($dataDir . '/.cloud_token');
          $msg = 'ক্লাউড সিঙ্ক টোকেন সরানো হয়েছে।';
          break;
        }
        $curUsers = (int)q('SELECT COUNT(*) FROM users')->fetchColumn();
        if ($curUsers === 0) {
          $db = null;
          if (@cloudRestoreDb($dbf, $ghTok)) {
            $db = new PDO('sqlite:' . $dbf);
            $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            sset('github_token', $ghTok);
            @file_put_contents($dataDir . '/.cloud_token', $ghTok);
            $msg = '✓ ক্লাউড থেকে পূর্বের সম্পূর্ণ ডেটাবেস (সব ইউজার ও সেটিংস) সফলভাবে রিস্টোর হয়েছে!';
            break;
          }
          $db = new PDO('sqlite:' . $dbf);
          $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        }
        sset('github_token', $ghTok);
        @file_put_contents($dataDir . '/.cloud_token', $ghTok);
        if (@cloudBackupDb($db, $dbf, true)) {
          $msg = '✓ ক্লাউড ব্যাকআপ সফলভাবে চালু হয়েছে এবং ডেটাবেস GitHub Gist-এ সংরক্ষিত হয়েছে!';
        } else {
          $msg = 'টোকেন সেভ হয়েছে, তবে GitHub Gist-এ সংযোগ করা যায়নি। টোকেনে gist পারমিশন আছে কি না দেখুন।';
        }
        break;
      case 'auto_restore_vault':
        $rawVault = (string)($_POST['vault_json'] ?? '');
        $vData = json_decode($rawVault, true);
        if (is_array($vData)) {
          if (!empty($vData['github_token']) && (int)q('SELECT COUNT(*) FROM users')->fetchColumn() === 0) {
            $ghT = trim((string)$vData['github_token']);
            $db = null;
            if (@cloudRestoreDb($dbf, $ghT)) {
              $db = new PDO('sqlite:' . $dbf);
              $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            } else {
              $db = new PDO('sqlite:' . $dbf);
              $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            }
            sset('github_token', $ghT);
            @file_put_contents($dataDir . '/.cloud_token', $ghT);
          }
          foreach (['notices', 'social', 'welcome', 'brand', 'maint', 'app_update', 'socmode', 'reg_mode', 'poll'] as $vk) {
            if (isset($vData[$vk]) && is_string($vData[$vk]) && $vData[$vk] !== '' && sraw($vk) === false) {
              sset($vk, $vData[$vk]);
            }
          }
          $msg = '✓ সার্ভার রিস্টার্টের পর আপনার পূর্বের অ্যাডমিন সেটিংস স্বয়ংক্রিয়ভাবে রিস্টোর করা হয়েছে!';
        }
        break;
    }
    @cloudBackupDb($db, $dbf, true);
  }
  $_SESSION['flash'] = $msg;
  header('Location: ' . $self . '#' . $tab);
  exit;
}
$flash = $_SESSION['flash'] ?? ''; unset($_SESSION['flash']);

$ucols = array_column($db->query('PRAGMA table_info(users)')->fetchAll(PDO::FETCH_ASSOC), 'name');
$hasC = in_array('created', $ucols); $hasS = in_array('synced', $ucols);
$hasFn = in_array('fullname', $ucols); $hasNm = in_array('name', $ucols);
$syn24 = $hasS ? (int)q('SELECT COUNT(*) FROM users WHERE synced>=?', [time() - 86400])->fetchColumn() : 0;
$fails24 = (int)q("SELECT COUNT(*) FROM logs WHERE type IN ('login_fail','admin_fail') AND t>=?", [time() - 86400])->fetchColumn();
$today = date('Y-m-d'); $d7 = date('Y-m-d', strtotime('-6 days')); $d30 = date('Y-m-d', strtotime('-29 days'));
$nUsers = (int)q('SELECT COUNT(*) FROM users')->fetchColumn();
$nPend = (int)q("SELECT COUNT(*) FROM users WHERE status='pending'")->fetchColumn();
$nBlk = (int)q("SELECT COUNT(*) FROM users WHERE status='blocked'")->fetchColumn();
$oldTok = (int)q('SELECT COUNT(*) FROM tokens WHERE COALESCE(last_seen, created) < ?', [time() - 90 * 86400])->fetchColumn();
$vToday = (int)q('SELECT COUNT(*) FROM visits WHERE day=?', [$today])->fetchColumn();
$hToday = (int)q('SELECT COALESCE(SUM(hits),0) FROM visits WHERE day=?', [$today])->fetchColumn();
$v7 = (int)q('SELECT COUNT(DISTINCT vid) FROM visits WHERE day>=?', [$d7])->fetchColumn();
$vAll = (int)q('SELECT COUNT(DISTINCT vid) FROM visits')->fetchColumn();
$online = (int)q('SELECT COUNT(*) FROM visits WHERE last>=?', [time() - 300])->fetchColumn();
$newU = $hasC ? (int)q('SELECT COUNT(*) FROM users WHERE created>=?', [time() - 7 * 86400])->fetchColumn() : 0;
$devs = (int)q('SELECT COUNT(*) FROM tokens')->fetchColumn();
$byDay = [];
foreach (q('SELECT day,COUNT(*) c FROM visits WHERE day>=? GROUP BY day', [date('Y-m-d', strtotime('-13 days'))])->fetchAll(PDO::FETCH_ASSOC) as $r) $byDay[$r['day']] = (int)$r['c'];
$plat = q('SELECT plat,COUNT(DISTINCT vid) c FROM visits WHERE day>=? GROUP BY plat ORDER BY c DESC', [$d30])->fetchAll(PDO::FETCH_ASSOC);
$sz = filesize($dbf);
$szt = $sz > 1048576 ? number_format($sz / 1048576, 2) . ' MB' : number_format($sz / 1024, 1) . ' KB';
$users = q('SELECT u.id, u.email, u.status, ' . ($hasFn ? 'u.fullname' : "''") . ' fullname, ' . ($hasNm ? 'u.name' : "''") . ' name, ' . ($hasC ? 'u.created' : 'NULL') . ' created, ' . ($hasS ? 'u.synced' : 'NULL') . ' synced,
  (SELECT COUNT(*) FROM tokens t WHERE t.user_id=u.id) tk,
  (SELECT MAX(created) FROM tokens t WHERE t.user_id=u.id) last FROM users u ORDER BY (u.status=\'pending\') DESC, u.id DESC')->fetchAll(PDO::FETCH_ASSOC);
$code = sraw('delete_code'); if ($code === false) $code = DEFAULT_CODE;
$ar = sraw('allow_register');
$maint = sj('maint', ['on' => 0, 'msg' => '']);
$N = sj('notices', []); $SL = socList(sj('social', [])); $socmode = sraw('socmode') ?: 'none';
$WD = ['on' => 1, 'logo' => 'T', 'title' => 'খরচের খাতা', 'tag' => 'Your money, beautifully kept', 'greet' => 1, 'quotesOn' => 1, 'quotes' => explode("\n", WQUOTES), 'btn' => 'শুরু করুন →', 'dur' => 5, 'bar' => 1, 'credit' => 1, 'creditText' => 'Designed & crafted with', 'creditName' => 'Tanvir', 'freq' => 'always', 'every' => 24, 'everyS' => 86400, 'aud' => 'all'];
$W = array_merge($WD, sj('welcome', []));
$BR = array_merge(['logo' => 'T', 'name' => 'খরচের খাতা', 'by' => 'by Tanvir', 'foot' => 'Crafted with care by', 'sig' => 'Tanvir'], sj('brand', []));
$APP_UP = array_merge(['on' => 0, 'ver' => '1.0.1', 'build' => 2, 'force' => 0, 'title' => 'নতুন আপডেট উপলব্ধ!', 'msg' => 'অ্যাপের একটি নতুন ও উন্নত সংস্করণ প্রস্তুত আছে। নতুন ফিচার এবং ত্রুটিমুক্ত অভিজ্ঞতা পেতে অনুগ্রহ করে এখনই আপডেট করুন।', 'url' => '', 'btn' => 'ইনস্টল করুন'], sj('app_update', []));
$pollV = (int)sraw('poll'); if ($pollV < 5 || $pollV > 120) $pollV = 15;
$legacy = sraw('notice'); if ($legacy === false) $legacy = '';
$lf = (string)($_GET['lf'] ?? 'all');
$LF = ['all' => ['সব', ''], 'login' => ['লগইন', "WHERE type IN ('login','register','passwd','delacct')"], 'admin' => ['অ্যাডমিন', "WHERE type LIKE 'a%'"], 'fail' => ['ব্যর্থ চেষ্টা', "WHERE type IN ('login_fail','admin_fail')"]];
if (!isset($LF[$lf])) $lf = 'all';
$lp = max(1, (int)($_GET['lp'] ?? 1)); $per = 15;
$ltotal = (int)q('SELECT COUNT(*) FROM logs ' . $LF[$lf][1])->fetchColumn();
$lpages = max(1, (int)ceil($ltotal / $per)); if ($lp > $lpages) $lp = $lpages;
$logs = q('SELECT * FROM logs ' . $LF[$lf][1] . ' ORDER BY id DESC LIMIT ? OFFSET ?', [$per, ($lp - 1) * $per])->fetchAll(PDO::FETCH_ASSOC);
$cs = h($_SESSION['csrf']);

function nform($n, $cs) {
  global $SL;
  $loc = $n['loc'] ?? ['welcome'];
  $o = '<form method="post">' . hid($cs, 'notice_save', 'notice') . '<input type="hidden" name="nid" value="' . h($n['id'] ?? '') . '">';
  $o .= '<input name="title" maxlength="80" placeholder="শিরোনাম" value="' . h($n['title'] ?? '') . '"><textarea name="msg" rows="3" maxlength="400" placeholder="বার্তা লিখুন">' . h($n['msg'] ?? '') . '</textarea>';
  $o .= '<div class="two"><input name="link" placeholder="লিংক (ঐচ্ছিক)" value="' . h($n['link'] ?? '') . '"><input name="btn" maxlength="30" placeholder="বোতামের লেখা (যেমন: বিস্তারিত)" value="' . h($n['btn'] ?? '') . '"></div>';
  $o .= '<div class="two"><div><div class="lb">ধরন</div>' . selb('type', NTYPE, $n['type'] ?? 'info') . '</div><div><div class="lb">কাদের দেখাবে</div>' . selb('aud', NAUD, $n['aud'] ?? 'all') . '</div></div>';
  $o .= '<div class="lb">কোথায় দেখাবে (লোকেশন)</div><div>';
  foreach (NLOC as $k => $v) $o .= '<label class="ch"><input type="checkbox" name="loc[]" value="' . $k . '"' . (in_array($k, $loc) ? ' checked' : '') . '>' . h($v) . '</label>';
  $o .= '</div><div class="two"><div><div class="lb">শুরুর সময় (ঐচ্ছিক)</div><input type="datetime-local" name="from" value="' . h(fx($n['from'] ?? '')) . '"></div><div><div class="lb">শেষের সময় (ঐচ্ছিক)</div><input type="datetime-local" name="to" value="' . h(fx(strlen((string)($n['to'] ?? '')) === 10 ? $n['to'] . 'T23:59' : ($n['to'] ?? ''))) . '"></div></div>';
  $o .= '<div class="lb">কতবার দেখাবে</div>' . selb('freq', NFREQ, $n['freq'] ?? 'always') . '<div class="lb">"নির্দিষ্ট সময় পর পর" হলে কত পর পর (সেকেন্ড / মিনিট / ঘণ্টা)</div>' . tu('every', $n['everyS'] ?? (($n['every'] ?? 24) * 3600));
  $o .= '<div class="lb">কতক্ষণ দেখাবে (০ = ব্যবহারকারী নিজে বন্ধ না করা পর্যন্ত)</div>' . tu('secs', $n['secs'] ?? 0) . '<div class="lb">ক্রম (ছোট সংখ্যা আগে দেখাবে)</div><input type="number" name="pri" min="0" max="999" value="' . (int)($n['pri'] ?? 10) . '">';
  $o .= '<div class="lb">এই নোটিসে যে সোশ্যাল লিংক দেখাবে (প্রতিটি নোটিসে আলাদা বাছা যায়)</div><div>';
  if (!$SL) $o .= '<span class="m">আগে সোশ্যাল ট্যাবে লিংক যোগ করুন।</span>';
  foreach ($SL as $x) $o .= '<label class="ch"><input type="checkbox" name="socs[]" value="' . h($x['id']) . '"' . (in_array($x['id'], $n['socs'] ?? []) ? ' checked' : '') . '>' . h(($x['label'] ?: (SOCP[$x['p']][0] ?? '')) . ' · ' . (SOCP[$x['p']][0] ?? '')) . '</label>';
  $o .= '</div><label class="ch"><input type="checkbox" name="on" value="1"' . (!isset($n['on']) || $n['on'] ? ' checked' : '') . '>চালু</label> <button>সেভ করুন</button></form>';
  return $o;
}
function srow($i, $s) {
  $p = $s['p'] ?? 'fb'; if (!isset(SOCP[$p])) $p = 'fb';
  $loc = $s['loc'] ?? ['footer'];
  $o = '<div class="sr"><input type="hidden" name="s[' . $i . '][id]" value="' . h($s['id'] ?? '') . '"><div class="tg"><div class="row"><span class="soci" style="background:' . h(SOCP[$p][1]) . '">' . h(SOCP[$p][2]) . '</span><select name="s[' . $i . '][p]" style="width:auto;margin:0">';
  foreach (SOCP as $k => $v) $o .= '<option value="' . $k . '"' . ($k === $p ? ' selected' : '') . '>' . h($v[0]) . '</option>';
  $o .= '</select></div><div class="row"><label class="ch"><input type="checkbox" name="s[' . $i . '][on]" value="1"' . (!empty($s['on']) ? ' checked' : '') . '>চালু</label><button type="button" class="g" onclick="mv(this,-1)">↑</button><button type="button" class="g" onclick="mv(this,1)">↓</button><button type="button" class="r" onclick="this.closest(\'.sr\').remove()">মুছুন</button></div></div>';
  $o .= '<div class="two"><input name="s[' . $i . '][label]" maxlength="30" placeholder="নাম (যেমন: Facebook গ্রুপ)" value="' . h($s['label'] ?? '') . '"><input name="s[' . $i . '][url]" placeholder="লিংক / নম্বর / ইমেইল" value="' . h($s['url'] ?? '') . '"></div><div>';
  foreach (SLOC as $lk => $lv) $o .= '<label class="ch"><input type="checkbox" name="s[' . $i . '][loc][]" value="' . $lk . '"' . (in_array($lk, $loc) ? ' checked' : '') . '>' . h($lv) . '</label>';
  return $o . '</div></div>';
}
function secs($ts) { return $ts ? date('d/m/Y H:i', (int)$ts) : '—'; }

$b = top('<form method="post">' . hid($cs, 'logout') . '<button class="g">লগআউট</button></form>');
$b .= '<div class="tb"><a href="#ov" data-k="ov">ওভারভিউ</a><a href="#notice" data-k="notice">নোটিস</a><a href="#social" data-k="social">সোশ্যাল</a><a href="#welcome" data-k="welcome">ওয়েলকাম</a><a href="#appup" data-k="appup">অ্যাপ আপডেট</a><a href="#users" data-k="users">ব্যবহারকারী</a><a href="#set" data-k="set">সেটিংস</a></div>';
if ($flash) $b .= '<div class="fl">' . h($flash) . '</div>';

// ওভারভিউ
$b .= '<section data-t="ov"><div class="stats">
<div class="st"><small>আজকের ভিজিটর</small><b>' . $vToday . '</b></div>
<div class="st"><small>এখন অনলাইন</small><b>' . $online . '</b></div>
<div class="st"><small>৭ দিনে ভিজিটর</small><b>' . $v7 . '</b></div>
<div class="st"><small>মোট ইউনিক ভিজিটর</small><b>' . $vAll . '</b></div>
<div class="st"><small>মোট ব্যবহারকারী</small><b>' . $nUsers . '</b></div>
<div class="st"><small>অনুমোদনের অপেক্ষায়</small><b>' . $nPend . '</b></div>
<div class="st"><small>নতুন (৭ দিনে)</small><b>' . $newU . '</b></div>
<div class="st"><small>ডেটাবেস</small><b style="font-size:19px">' . h($szt) . '</b></div>
<div class="st"><small>২৪ ঘণ্টায় সিঙ্ক করেছে</small><b>' . $syn24 . '</b></div>
<div class="st"><small>ব্যর্থ চেষ্টা (২৪ ঘণ্টা)</small><b>' . $fails24 . '</b></div>
<div class="st"><small>ব্লক করা</small><b>' . $nBlk . '</b></div>
<div class="st"><small>আজকের পেজ ভিউ</small><b>' . $hToday . '</b></div></div>';
$mx = 1; $days = [];
for ($i = 13; $i >= 0; $i--) { $d = date('Y-m-d', strtotime("-$i days")); $c = $byDay[$d] ?? 0; $days[] = [$d, $c]; if ($c > $mx) $mx = $c; }
$b .= '<div class="c"><h2>ভিজিটর (গত ১৪ দিন)</h2><div class="chart">';
foreach ($days as $dd) $b .= '<div><span>' . ($dd[1] ?: '') . '</span><i style="height:' . round($dd[1] / $mx * 100) . 'px"></i>' . h(date('d', strtotime($dd[0]))) . '</div>';
$b .= '</div><p class="m">একজন ভিজিটর দিনে একবারই গোনা হয় (ডিভাইস অনুযায়ী)। অ্যাপ খুললেই ভিজিট ধরা হয়, লগইন না করলেও।</p></div>';
if ($hasC) {
  $su = [];
  foreach (q('SELECT created FROM users WHERE created>=?', [strtotime('-13 days 00:00')])->fetchAll(PDO::FETCH_ASSOC) as $r) { $dk = date('Y-m-d', (int)$r['created']); $su[$dk] = ($su[$dk] ?? 0) + 1; }
  $mx2 = 1; $d2 = [];
  for ($i = 13; $i >= 0; $i--) { $d = date('Y-m-d', strtotime("-$i days")); $c = $su[$d] ?? 0; $d2[] = [$d, $c]; if ($c > $mx2) $mx2 = $c; }
  $b .= '<div class="c"><h2>নতুন ব্যবহারকারী (গত ১৪ দিন)</h2><div class="chart">';
  foreach ($d2 as $dd) $b .= '<div><span>' . ($dd[1] ?: '') . '</span><i style="height:' . round($dd[1] / $mx2 * 100) . 'px"></i>' . h(date('d', strtotime($dd[0]))) . '</div>';
  $b .= '</div></div>';
}
$tot = 0; foreach ($plat as $p) $tot += (int)$p['c'];
$b .= '<div class="c"><h2>কোন ডিভাইস থেকে আসছে (৩০ দিন)</h2>';
if (!$plat) $b .= '<p class="m">এখনো কোনো ভিজিট নেই।</p>';
foreach ($plat as $p) { $pc = $tot ? round($p['c'] / $tot * 100) : 0; $b .= '<div class="tg"><span>' . h($p['plat']) . '</span><span class="m">' . (int)$p['c'] . ' জন · ' . $pc . '%</span></div><div class="pb"><i style="width:' . $pc . '%"></i></div>'; }
$elog = @is_file(__DIR__ . '/data/error.log') ? array_slice(array_filter(explode("\n", (string)@file_get_contents(__DIR__ . '/data/error.log'))), -8) : [];
$b .= '</div><div class="c"><h2>সার্ভার ত্রুটির লগ</h2>';
if (!$elog) $b .= '<p class="m">কোনো ত্রুটি নেই। সিঙ্ক বা লগইনে সমস্যা হলে কারণটা এখানে লেখা থাকবে।</p>';
else {
  foreach (array_reverse($elog) as $ln) {
    $safeLn = preg_replace('/(password|passwd|token|secret|hash|code)\s*[:=]\s*\S+/i', '$1=[REDACTED]', (string)$ln);
    $safeLn = str_replace(__DIR__, '[APP_DIR]', (string)$safeLn);
    $b .= '<div class="lg2" style="word-break:break-all">' . h($safeLn) . '</div>';
  }
  $b .= '<form method="post" style="margin-top:8px">' . hid($cs, 'errclear', 'ov') . '<button class="g">লগ পরিষ্কার করুন</button></form>';
}
$b .= '</div><div class="c"><h2>সাম্প্রতিক কার্যকলাপ (প্রতি পৃষ্ঠায় ১৫টি)</h2><div class="row" style="margin-bottom:8px">';
foreach ($LF as $k => $v) $b .= '<a class="btn ' . ($k === $lf ? '' : 'g') . '" style="padding:6px 12px;font-size:14px" href="?lf=' . $k . '#ov">' . h($v[0]) . '</a>';
$b .= '</div>';
if (!$logs) $b .= '<p class="m">কিছু নেই।</p>';
$LBL = ['login' => 'ব্যবহারকারীর লগইন', 'login_fail' => 'ভুল লগইন চেষ্টা', 'register' => 'নতুন অ্যাকাউন্ট', 'passwd' => 'পাসওয়ার্ড পরিবর্তন', 'delacct' => 'নিজে অ্যাকাউন্ট মুছেছে', 'admin_login' => 'অ্যাডমিন লগইন', 'admin_fail' => 'ভুল অ্যাডমিন লগইন', 'a_misc' => 'অ্যাডমিন কাজ'];
foreach ($logs as $l) $b .= '<div class="lg2"><span class="m">' . h(secs($l['t'])) . '</span> · ' . h($LBL[$l['type']] ?? $l['type']) . ($l['who'] !== '' && $l['who'] !== null ? ' — ' . h($l['who']) : '') . ' <span class="m">' . h($l['ip']) . '</span></div>';
$b .= '<div class="tg" style="margin-top:10px"><span class="m">পৃষ্ঠা ' . $lp . ' / ' . $lpages . ' · মোট ' . $ltotal . 'টি</span><div class="row">'
  . ($lp > 1 ? '<a class="btn g" style="padding:6px 12px" href="?lf=' . $lf . '&lp=' . ($lp - 1) . '#ov">← আগের</a>' : '')
  . ($lp < $lpages ? '<a class="btn g" style="padding:6px 12px" href="?lf=' . $lf . '&lp=' . ($lp + 1) . '#ov">পরের →</a>' : '') . '</div></div>';
$b .= '</div></section>';

// নোটিস
$b .= '<section data-t="notice">' . ($legacy !== '' ? '<div class="c"><h2>পুরনো নোটিস</h2><p>' . h($legacy) . '</p><form method="post">' . hid($cs, 'legacy_clear', 'notice') . '<button class="r">পুরনো নোটিস মুছুন</button></form></div>' : '') . '<div class="c"><h2>নতুন নোটিস যোগ করুন</h2><p class="m">নোটিস অ্যাপের কোথায় দেখাবে তা লোকেশন থেকে বাছুন। তারিখ দিলে নির্দিষ্ট সময়ের জন্য নিজে চালু-বন্ধ হবে।</p>' . nform([], $cs) . '</div>';
$b .= '<div class="c"><h2>আপনার নোটিস (' . count($N) . ')</h2>';
if (!$N) $b .= '<p class="m">এখনো কোনো নোটিস নেই।</p>';
foreach ($N as $n) {
  $locs = ''; foreach (($n['loc'] ?? []) as $k) if (isset(NLOC[$k])) $locs .= '<span>' . h(NLOC[$k]) . '</span>';
  $date = (!empty($n['from']) || !empty($n['to'])) ? '<span>' . h(str_replace('T', ' ', ($n['from'] ?? '…') . ' → ' . ($n['to'] ?? '…'))) . '</span>' : '';
  $date .= '<span>' . h(NFREQ[$n['freq'] ?? 'always'] ?? '') . (($n['freq'] ?? '') === 'hours' ? ' (' . fmtT($n['everyS'] ?? (($n['every'] ?? 24) * 3600)) . ')' : '') . '</span>';
  if (!empty($n['secs'])) $date .= '<span>' . fmtT($n['secs']) . ' দেখাবে</span>';
  if (($n['aud'] ?? 'all') !== 'all') $date .= '<span>' . h(NAUD[$n['aud']] ?? '') . '</span>';
  if (!empty($n['socs'])) $date .= '<span>সোশ্যাল ' . count($n['socs']) . 'টি</span>';
  $nowS = date('Y-m-d\TH:i'); $nf = fx($n['from'] ?? ''); $nt = (string)($n['to'] ?? ''); if (strlen($nt) === 10) $nt .= 'T23:59';
  if (empty($n['on'])) { $stc = 'off'; $stl = 'বন্ধ'; } elseif ($nf !== '' && $nf > $nowS) { $stc = 'nt0'; $stl = 'নির্ধারিত'; } elseif ($nt !== '' && $nt < $nowS) { $stc = 'off'; $stl = 'মেয়াদ শেষ'; } else { $stc = 'on'; $stl = 'চালু'; }
  $btnpv = !empty($n['link']) ? '<span class="pvb">' . h($n['btn'] ?: 'বিস্তারিত') . ' →</span>' : '';
  $socpv = ''; foreach (($n['socs'] ?? []) as $sv) foreach ($SL as $x) if ($x['id'] === $sv) $socpv .= '<span class="pvs" title="' . h($x['label'] ?: '') . '" style="background:' . h(SOCP[$x['p']][1] ?? '#444') . '">' . h(SOCP[$x['p']][2] ?? '') . '</span>';
  $b .= '<div class="u"><div class="tg"><div><b>' . h($n['title'] ?: cut($n['msg'], 40)) . '</b> <span class="sw ' . $stc . '">' . $stl . '</span> <span class="sw nt0">' . h(NTYPE[$n['type'] ?? 'info'] ?? '') . '</span></div>
  <div class="row"><form method="post">' . hid($cs, 'notice_tog', 'notice', $n['id']) . '<button class="g">' . (!empty($n['on']) ? 'বন্ধ করুন' : 'চালু করুন') . '</button></form>
  <form method="post">' . hid($cs, 'notice_dup', 'notice', $n['id']) . '<button class="g">কপি</button></form><form method="post" data-confirm="নোটিসটি মুছে ফেলবেন?">' . hid($cs, 'notice_del', 'notice', $n['id']) . '<button class="r">মুছুন</button></form></div></div>
  <div class="chips">' . $locs . $date . '</div><div class="pv pv-' . h($n['type'] ?? 'info') . '"><b>' . h($n['title'] ?? '') . '</b><div>' . h($n['msg'] ?? '') . '</div>' . $btnpv . ($socpv ? '<div>' . $socpv . '</div>' : '') . '</div><details><summary>এডিট করুন</summary>' . nform($n, $cs) . '</details></div>';
}
$b .= '</div></section>';

// সোশ্যাল
$b .= '<section data-t="social"><div class="c"><h2>সোশ্যাল মিডিয়া লিংক</h2><p class="m">একই প্ল্যাটফর্মের একাধিক লিংকও দেওয়া যায় (যেমন: Facebook পেজ ও গ্রুপ)। প্রতিটির জন্য আলাদা অন-অফ ও লোকেশন বাছুন। WhatsApp-এ শুধু নম্বর দিলেও চলবে।</p><form method="post">' . hid($cs, 'social', 'social') . '<div id="sl">';
foreach ($SL as $i => $x) $b .= srow($i, $x);
$b .= '</div><button type="button" class="g" onclick="addS()">+ নতুন লিংক যোগ করুন</button>
<div class="lb" style="margin-top:14px">যে নোটিসে আলাদা করে লিংক বাছা হয়নি, সেখানে</div>' . selb('socmode', ['none' => 'কিছু দেখাবে না', 'all' => '"নোটিসের ভেতরে" লোকেশন টিক দেওয়া সব লিংক দেখাবে'], $socmode === 'all' ? 'all' : 'none') . '
<p class="m">কোন নোটিসে কোন লিংক যাবে তা নোটিসের এডিট ফর্মে আলাদা করে বাছুন। যেমন নোটিস ১-এ Facebook ১, নোটিস ২-এ Facebook ২।</p><button style="margin-top:8px">সব সেভ করুন</button></form><template id="stp">' . srow('__I__', ['p' => 'fb', 'on' => 1, 'loc' => ['footer']]) . '</template></div></section>';

// ওয়েলকাম
$b .= '<section data-t="welcome"><div class="c"><h2>ওয়েলকাম পপআপ</h2><p class="m">অ্যাপ খুললে প্রথম যে স্ক্রিন আসে তার সবকিছু এখান থেকে নিয়ন্ত্রণ করুন।</p><form method="post">' . hid($cs, 'welcome_save', 'welcome') . '
<label class="ch"><input type="checkbox" name="on" value="1"' . (!empty($W['on']) ? ' checked' : '') . '>ওয়েলকাম পপআপ চালু</label>
<div class="two"><div><div class="lb">লোগোর অক্ষর (১-২টি)</div><input name="logo" maxlength="2" value="' . h($W['logo']) . '"></div><div><div class="lb">শিরোনাম</div><input name="title" maxlength="40" value="' . h($W['title']) . '"></div></div>
<div class="lb">ট্যাগলাইন</div><input name="tag" maxlength="80" value="' . h($W['tag']) . '">
<label class="ch"><input type="checkbox" name="greet" value="1"' . (!empty($W['greet']) ? ' checked' : '') . '>সময় অনুযায়ী অভিবাদন (শুভ সকাল, নাম)</label>
<label class="ch"><input type="checkbox" name="quotesOn" value="1"' . (!empty($W['quotesOn']) ? ' checked' : '') . '>অনুপ্রেরণার লাইন দেখাবে</label>
<div class="lb">অনুপ্রেরণার লাইন (প্রতি লাইনে একটি, বদলে বদলে আসবে)</div><textarea name="quotes" rows="5">' . h(implode("\n", (array)$W['quotes'])) . '</textarea>
<div class="lb">বোতামের লেখা</div><input name="btn" maxlength="30" value="' . h($W['btn']) . '">
<div class="lb">কতক্ষণ পর নিজে বন্ধ হবে (০ = শুধু বোতামে) — সেকেন্ড / মিনিট / ঘণ্টা</div>' . tu('dur', $W['dur']) . '
<label class="ch"><input type="checkbox" name="bar" value="1"' . (!empty($W['bar']) ? ' checked' : '') . '>নিচে প্রগ্রেস বার দেখাবে</label>
<label class="ch"><input type="checkbox" name="credit" value="1"' . (!empty($W['credit']) ? ' checked' : '') . '>ক্রেডিট দেখাবে</label>
<div class="two"><div><div class="lb">ক্রেডিটের লেখা</div><input name="creditText" maxlength="40" value="' . h($W['creditText']) . '"></div><div><div class="lb">ক্রেডিটের নাম</div><input name="creditName" maxlength="30" value="' . h($W['creditName']) . '"></div></div>
<div class="lb">কতবার দেখাবে</div>' . selb('freq', NFREQ, $W['freq']) . '<div class="lb">"নির্দিষ্ট সময় পর পর" হলে কত পর পর</div>' . tu('every', $W['everyS'] ?? ($W['every'] * 3600)) . '
<div class="lb">কাদের দেখাবে</div>' . selb('aud', NAUD, $W['aud']) . '
<div class="row" style="margin-top:8px"><button>সেভ করুন</button><a class="btn g" href="index.html?pv=1" target="_blank" rel="noopener">প্রিভিউ দেখুন</a></div></form>
<form method="post" data-confirm="ওয়েলকাম পপআপ ডিফল্ট অবস্থায় ফেরাবেন?" style="margin-top:10px">' . hid($cs, 'welcome_reset', 'welcome') . '<button class="g">ডিফল্টে ফিরুন</button></form></div>
<div class="c"><h2>হেডার, লগইন পেজ ও ফুটারের লেখা (ব্র্যান্ডিং)</h2><form method="post">' . hid($cs, 'brand_save', 'welcome') . '
<div class="lb">লোগোর অক্ষর (১-২টি, যেমন: T — হেডার ও লগইন পেজে দেখাবে)</div><input name="logo" maxlength="3" value="' . h($BR['logo'] ?? 'T') . '">
<div class="two"><div><div class="lb">অ্যাপের নাম (হেডার ও লগইন পেজ)</div><input name="name" maxlength="30" value="' . h($BR['name']) . '"></div><div><div class="lb">সাবটাইটেল / ছোট লেখা (যেমন: by Tanvir)</div><input name="by" maxlength="30" value="' . h($BR['by']) . '"></div></div>
<div class="two"><div><div class="lb">ফুটারের লেখা</div><input name="foot" maxlength="50" value="' . h($BR['foot']) . '"></div><div><div class="lb">ফুটারের নাম</div><input name="sig" maxlength="30" value="' . h($BR['sig']) . '"></div></div><button>সেভ করুন</button></form></div></section>';

// অ্যাপ আপডেট
$b .= '<section data-t="appup"><div class="c"><h2>📱 অ্যান্ড্রয়েড অ্যাপ আপডেট নিয়ন্ত্রণ</h2>
<div class="pv pv-info" style="margin-bottom:14px;border-left:4px solid #2DD4BF"><b>💡 শুধুমাত্র অ্যান্ড্রয়েড অ্যাপের জন্য:</b> এই আপডেট পপআপটি <b>শুধুমাত্র ফোনে ইনস্টল থাকা অ্যান্ড্রয়েড অ্যাপের (APK) ভেতরে দেখাবে</b>। সাধারণ ওয়েবসাইট বা ব্রাউজারে এটি কখনো আসবে না।</div>
<form method="post">' . hid($cs, 'app_update_save', 'appup') . '
<label class="ch" style="font-weight:700;font-size:16px"><input type="checkbox" name="on" value="1"' . (!empty($APP_UP['on']) ? ' checked' : '') . '>অ্যাপ আপডেট পপআপ চালু রাখুন</label>
<div class="two">
  <div><div class="lb">সর্বশেষ সংস্করণ (Version)</div><input name="ver" maxlength="20" placeholder="যেমন: 1.1.0" value="' . h($APP_UP['ver']) . '"></div>
  <div><div class="lb">বিল্ড কোড (Build Number)</div><input type="number" name="build" min="1" max="99999" placeholder="যেমন: 2" value="' . (int)$APP_UP['build'] . '"></div>
</div>
<label class="ch" style="margin:10px 0"><input type="checkbox" name="force" value="1"' . (!empty($APP_UP['force']) ? ' checked' : '') . '>বাধ্যতামূলক আপডেট (Force Update — ব্যবহারকারী আপডেট না করা পর্যন্ত অ্যাপ ব্যবহার করতে পারবে না)</label>
<div class="lb">আপডেট শিরোনাম (Title)</div>
<input name="title" maxlength="80" placeholder="শিরোনাম" value="' . h($APP_UP['title']) . '">
<div class="lb">আপডেটের বিবরণ / কি নতুন যুক্ত হলো (Changelog)</div>
<textarea name="msg" rows="3" maxlength="500" placeholder="আপডেটের বিস্তারিত লিখুন">' . h($APP_UP['msg']) . '</textarea>
<div class="lb">ডাউনলোড / ইনস্টলেশন লিংক (URL — Google Drive / GitHub Releases / MediaFire / Direct APK)</div>
<input name="url" placeholder="https://..." value="' . h($APP_UP['url']) . '">
<div class="lb">ইনস্টল বোতামের লেখা (Button Text)</div>
<input name="btn" maxlength="30" placeholder="যেমন: ইনস্টল করুন" value="' . h($APP_UP['btn']) . '">
<div class="row" style="margin-top:14px"><button>সেভ করুন</button></div></form></div>
<div class="c"><h2>পপআপ প্রিভিউ (ফোনে যেমন দেখাবে)</h2>
<div class="pv" style="max-width:380px;margin:10px auto;text-align:center;padding:22px 18px;border-radius:22px;background:#0F1B2D;border:1px solid rgba(45,212,191,0.35);box-shadow:0 8px 24px rgba(0,0,0,0.5)">
  <div style="width:48px;height:48px;border-radius:15px;background:rgba(45,212,191,0.15);color:#2DD4BF;display:flex;align-items:center;justify-content:center;margin:0 auto 10px;font-size:22px">⬇</div>
  <span class="pvb" style="margin-bottom:8px">v' . h($APP_UP['ver']) . '</span>
  <h3 style="margin:6px 0 8px;color:#fff;font-size:17px">' . h($APP_UP['title']) . '</h3>
  <p style="font-size:13px;color:#94A3B8;margin:0 0 16px;line-height:1.5">' . h($APP_UP['msg']) . '</p>
  <div class="row" style="gap:8px">
    ' . (empty($APP_UP['force']) ? '<span class="btn g" style="flex:1">পরে করব</span>' : '') . '
    <span class="btn" style="flex:1">' . h($APP_UP['btn']) . ' →</span>
  </div>
</div></div></section>';

// ব্যবহারকারী
$b .= '<section data-t="users"><div class="c"><h2>ব্যবহারকারী (' . count($users) . ' জন)</h2><a class="btn g" style="padding:6px 12px;font-size:14px;float:right" href="?usercsv=1&csrf=' . $cs . '">CSV</a><input id="qs" placeholder="নাম বা ইমেইল দিয়ে খুঁজুন…" autocomplete="off"><div class="row" style="margin:2px 0 8px"><button class="g" type="button" data-f="all">সব</button><button class="g" type="button" data-f="pending">অপেক্ষায়</button><button class="g" type="button" data-f="blocked">ব্লক</button></div><p class="m">পাসওয়ার্ড কেউ দেখতে পারে না (এনক্রিপ্টেড থাকে)। শুধু নতুন পাসওয়ার্ড বসানো যায়। ব্যবহারকারীর খরচ বা টাকার তথ্য এখানে দেখানো হয় না।</p>';
if (!$users) $b .= '<p class="m">এখনো কেউ নেই।</p>';
foreach ($users as $u) {
  $i = (int)$u['id']; $stt = $u['status'] ?: 'active';
  $fn = trim((string)($u['fullname'] ?? ''));
  $dn = trim((string)($u['name'] ?? ''));
  $displayName = $fn !== '' ? $fn : ($dn !== '' ? $dn : $u['email']);
  $sub = ($fn !== '' && $dn !== '' && $fn !== $dn) ? ' (' . $dn . ') · ' : '';
  $initial = strtoupper(substr($fn !== '' ? $fn : ($dn !== '' ? $dn : $u['email']), 0, 1));
  $searchStr = strtolower($u['email'] . ' ' . $fn . ' ' . $dn);
  $b .= '<div class="u" data-s="' . h($stt) . '" data-q="' . h($searchStr) . '"><div class="uh"><span class="av">' . h($initial) . '</span><div class="ui"><b>' . h($displayName) . '</b><div class="m">' . h($sub) . h($u['email']) . ' · #' . $i . ' · যোগ: ' . h(secs($u['created'])) . '</div></div><span class="sw ' . ($stt === 'active' ? 'on' : ($stt === 'pending' ? 'nt0' : 'off')) . '" style="margin-left:auto">' . ($stt === 'active' ? 'সক্রিয়' : ($stt === 'pending' ? 'অনুমোদনের অপেক্ষায়' : 'ব্লক')) . '</span></div>
  ' . ($stt === 'pending' ? '<form method="post" style="margin:8px 0">' . hid($cs, 'approve', 'users', $i) . '<button>অনুমোদন দিন</button></form>' : '') . '
  <div class="chips"><span>শেষ লগইন: ' . h(secs($u['last'])) . '</span><span>শেষ সিঙ্ক: ' . h(secs($u['synced'])) . '</span><span>সক্রিয় ডিভাইস: ' . (int)$u['tk'] . 'টি</span></div>
  <details><summary>ম্যানেজ করুন</summary>
  <form method="post" class="row" style="margin:8px 0">' . hid($cs, 'reset', 'users', $i) . '<input type="text" id="pw' . $i . '" name="pw" placeholder="নতুন পাসওয়ার্ড (৮+ অক্ষর)" autocomplete="off"><button type="button" class="g" onclick="gen(' . $i . ')">র‍্যান্ডম</button><button>পাসওয়ার্ড বদলান</button></form>
  <div class="row">  ' . ($stt === 'blocked' ? '<form method="post">' . hid($cs, 'unblock', 'users', $i) . '<button>আনব্লক করুন</button></form>' : '<form method="post" data-confirm="এই ব্যবহারকারীকে ব্লক করবেন? সে আর লগইন করতে পারবে না।">' . hid($cs, 'block', 'users', $i) . '<button class="g">ব্লক করুন</button></form>') .
  ((int)$u['tk'] > 0 ? '<form method="post">' . hid($cs, 'kick', 'users', $i) . '<button class="g">সব ডিভাইস থেকে লগআউট</button></form>' : '') . '
  <form method="post" data-confirm="এই ব্যবহারকারী ও তার সব ডেটা চিরতরে মুছে যাবে।" data-type="' . h($u['email']) . '">' . hid($cs, 'deluser', 'users', $i) . '<button class="r">ব্যবহারকারী মুছুন</button></form></div></details></div>';
}
$b .= '</div></section>';

// সেটিংস
$rmode = sraw('reg_mode'); if ($rmode === false) { $rmode = $ar === false ? 'file' : ($ar === '1' ? 'open' : 'closed'); }
$regState = ['open' => '<span class="sw on">সবার জন্য খোলা</span>', 'approval' => '<span class="sw nt0">অনুমোদন সাপেক্ষে</span>', 'closed' => '<span class="sw off">বন্ধ</span>', 'file' => '<span class="sw nt0">ফাইল অনুযায়ী (api.php)</span>'][$rmode];
$b .= '<section data-t="set">
<div class="c"><h2>রিয়েল-টাইম সিঙ্কের গতি</h2><p class="m">অ্যাপ খোলা থাকলে প্রতি কয়েক সেকেন্ডে সার্ভারে নতুন ডেটা আছে কি না দেখে (খুব হালকা অনুরোধ)। এক ফোনে খরচ যোগ করলে অন্য ফোনে এই সময়ের মধ্যে চলে আসে। সংখ্যা কম হলে দ্রুত, কিন্তু hosting-এর অনুরোধ বেশি লাগে — ফ্রি hosting-এ ১৫-৩০ সেকেন্ড রাখা নিরাপদ।</p>
<form method="post" class="row">' . hid($cs, 'poll_save', 'set') . '<input type="number" name="poll" min="5" max="120" value="' . (int)($pollV) . '"><button>সেভ করুন</button></form></div>
<div class="c"><h2>মেইনটেন্যান্স মোড</h2><p class="m">চালু করলে অ্যাপ খুললেই ব্যবহারকারীরা আপনার বার্তাসহ একটি "সাময়িকভাবে বন্ধ" স্ক্রিন দেখবে।</p>
<form method="post">' . hid($cs, 'maint', 'set') . '<input name="msg" maxlength="200" placeholder="বার্তা (যেমন: আজ রাত ১০টা পর্যন্ত আপডেটের কাজ চলছে)" value="' . h($maint['msg'] ?? '') . '"><label class="ch"><input type="checkbox" name="on" value="1"' . (!empty($maint['on']) ? ' checked' : '') . '>মেইনটেন্যান্স চালু</label> <button>সেভ করুন</button></form></div>
<div class="c"><h2>নতুন অ্যাকাউন্ট খোলার নিয়ম</h2><p class="m">বর্তমান: ' . $regState . '</p><div class="row">
<form method="post">' . hid($cs, 'regmode', 'set') . '<input type="hidden" name="v" value="open"><button class="g">সবার জন্য খোলা</button></form>
<form method="post">' . hid($cs, 'regmode', 'set') . '<input type="hidden" name="v" value="approval"><button class="g">অনুমোদন সাপেক্ষে</button></form>
<form method="post">' . hid($cs, 'regmode', 'set') . '<input type="hidden" name="v" value="closed"><button class="r">বন্ধ</button></form></div>
<p class="m" style="margin-top:8px">"অনুমোদন সাপেক্ষে" মোডে নতুনরা অ্যাকাউন্ট খুলতে পারে, কিন্তু আপনি অনুমোদন না দেওয়া পর্যন্ত লগইন করতে পারে না।</p></div>
<div class="c"><h2>ইউনিভার্সাল কোড (অ্যাকাউন্ট ডিলিটের জন্য)</h2><p class="m">বর্তমান কোড: <b id="cd" style="color:#E3B95C">•••••• (সুরক্ষিত)</b></p>
<form method="post" class="row">' . hid($cs, 'code', 'set') . '<input type="password" name="code" placeholder="নতুন কোড (কমপক্ষে ৪ অক্ষর)" autocomplete="new-password"><button>কোড বদলান</button></form></div>
<div class="c"><h2>অ্যাডমিন পাসওয়ার্ড বদলান</h2><form method="post">' . hid($cs, 'apw', 'set') . '<input type="password" name="old" placeholder="বর্তমান অ্যাডমিন পাসওয়ার্ড" autocomplete="current-password"><input type="password" name="new" placeholder="নতুন পাসওয়ার্ড (কমপক্ষে ১০ অক্ষর)" autocomplete="new-password"><button>পাসওয়ার্ড বদলান</button></form></div>';
$ghTokCur = getCloudToken($db);
$ghB64 = $ghTokCur !== '' ? base64_encode($ghTokCur) : '';
$vaultMap = [];
foreach (['notices', 'social', 'welcome', 'brand', 'maint', 'app_update', 'socmode', 'reg_mode', 'poll', 'github_token'] as $vk) {
  $vv = sraw($vk);
  if ($vv !== false && $vv !== '') $vaultMap[$vk] = $vv;
}
$vaultJson = json_encode((object)$vaultMap, JSON_UNESCAPED_UNICODE) ?: '{}';
$isFreshReset = ($nUsers === 0 && empty($vaultMap));

$b .= '<div class="c" style="border-color:rgba(45,212,191,0.45);background:linear-gradient(145deg,#101B2B,#0D2235)"><h2>☁️ স্থায়ী ক্লাউড ডাটাবেস সিঙ্ক (Render.com Auto-Restore)</h2>
<p class="m">Render.com-এর ফ্রি টিয়ারে ১৫ মিনিট ভিজিটর না থাকলে বা গিটহাবে কোড আপডেট করলে সার্ভার কন্টেইনার রিস্টার্ট হয়। নিচে আপনার GitHub Personal Access Token (<code>gist</code> পারমিশনসহ) দিয়ে রাখলে প্রতিবার ডেটাবেস স্বয়ংক্রিয়ভাবে আপনার গোপন GitHub Gist-এ ব্যাকআপ হবে এবং কন্টেইনার রিস্টার্ট হলে নিজে নিজেই রিস্টোর হয়ে যাবে!</p>
<p class="m">বর্তমান অবস্থা: ' . ($ghTokCur !== '' ? '<span class="sw on">ক্লাউড অটো-ব্যাকআপ চালু আছে ✓</span>' : '<span class="sw nt0">ব্রাউজার ও ডিভাইস সেলফ-হিলিং চালু (ক্লাউড টোকেন দেওয়া হয়নি)</span>') . '</p>
<form method="post">' . hid($cs, 'cloud_sync_save', 'set') . '
<input type="password" name="github_token" placeholder="GitHub Token (যেমন: ghp_xxxxxxxxxxxx)" value="' . h($ghTokCur) . '" autocomplete="off">
<div class="row"><button>টোকেন সেভ ও ক্লাউড সিঙ্ক করুন</button></div></form>
' . ($ghB64 !== '' ? '<p class="m" style="margin-top:8px">স্থায়ীভাবে চালু রাখতে Render.com-এর Environment Variables-এ <b>GITHUB_TOKEN</b> যোগ করুন, অথবা <code>khoroch/api.php</code> ফাইলের ৫ নম্বর লাইনে বসান:<br><code style="color:#5CE1E6;user-select:all">const CLOUD_BACKUP_B64 = \'' . h($ghB64) . '\';</code></p>' : '') . '</div>
<div class="c"><h2>সেটিংস ব্যাকআপ ও রিস্টোর</h2><p class="m">নোটিস, সোশ্যাল লিংক, ওয়েলকাম পপআপ, ব্র্যান্ডিং ও মেইনটেন্যান্স সেটিংস একটি ফাইলে নামিয়ে রাখুন, পরে ফিরিয়ে আনুন। (পাসওয়ার্ড বা ব্যবহারকারীর ডেটা এতে থাকে না।)</p><div class="row"><a class="btn g" href="?cfgdl=1&csrf=' . $cs . '">কনফিগ ডাউনলোড</a></div>
<form method="post" enctype="multipart/form-data" style="margin-top:10px">' . hid($cs, 'cfg_import', 'set') . '<input type="file" name="f" accept=".json,application/json"><button class="g">ইমপোর্ট করুন</button></form></div>
<div class="c"><h2>রক্ষণাবেক্ষণ</h2><div class="row"><form method="post">' . hid($cs, 'vacuum', 'set') . '<button class="g">ডেটাবেস অপ্টিমাইজ</button></form><form method="post">' . hid($cs, 'purge', 'set') . '<button class="g">পুরনো সেশন পরিষ্কার (' . (int)$oldTok . 'টি)</button></form></div></div>
<div class="c"><h2>পুরো ডেটাবেসের ব্যাকআপ</h2><p class="m">সব ব্যবহারকারীর ডেটাসহ ফাইলটি নামিয়ে নিরাপদ জায়গায় রাখুন।</p><a class="btn" href="?dbdl=1&csrf=' . $cs . '">ডেটাবেস ডাউনলোড (.sqlite)</a></div></section>';

$b .= '<form id="arf" method="post" style="display:none">' . hid($cs, 'auto_restore_vault', 'ov') . '<input type="hidden" name="vault_json" id="arvj"></form>';
$b .= '<div id="cm"><div class="cb"><div class="ic">!</div><h2 id="cmt" style="margin:0 0 6px"></h2><div class="m" id="cms"></div><input id="cmi" style="display:none;text-align:center"><div class="row"><button class="g" id="cmx" type="button">বাতিল</button><button class="r" id="cmo" type="button">নিশ্চিত করুন</button></div></div></div>';

$js = '<script>
const SERVER_VAULT = ' . $vaultJson . ';
const IS_FRESH_RESET = ' . ($isFreshReset ? 'true' : 'false') . ';
try {
  if (!IS_FRESH_RESET && Object.keys(SERVER_VAULT).length > 0) {
    const prev = JSON.parse(localStorage.getItem("kh_adm_vault") || "{}");
    localStorage.setItem("kh_adm_vault", JSON.stringify(Object.assign({}, prev, SERVER_VAULT)));
  } else if (IS_FRESH_RESET) {
    const saved = localStorage.getItem("kh_adm_vault");
    if (saved && saved.length > 5 && !sessionStorage.getItem("kh_adm_restored")) {
      sessionStorage.setItem("kh_adm_restored", "1");
      document.getElementById("arvj").value = saved;
      document.getElementById("arf").submit();
    }
  }
} catch(e) {}
' . <<<'JS'
const $=(s)=>document.querySelector(s);
const TABS=['ov','notice','social','welcome','appup','users','set'];
function mv(b,d){const r=b.closest('.sr'),p=r.parentNode;if(d<0&&r.previousElementSibling)p.insertBefore(r,r.previousElementSibling);if(d>0&&r.nextElementSibling)p.insertBefore(r.nextElementSibling,r)}
function addS(){$('#sl').insertAdjacentHTML('beforeend',$('#stp').innerHTML.replace(/__I__/g,'n'+Date.now()))}
function tab(t){document.querySelectorAll('[data-t]').forEach(s=>{s.style.display=s.dataset.t===t?'':'none'});document.querySelectorAll('.tb a').forEach(a=>a.classList.toggle('on',a.dataset.k===t))}
document.querySelectorAll('.tb a').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();tab(a.dataset.k);history.replaceState(null,'','#'+a.dataset.k)}));
tab(TABS.includes(location.hash.slice(1))?location.hash.slice(1):'ov');
function gen(id){const c='ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789',a=new Uint32Array(12);crypto.getRandomValues(a);$('#pw'+id).value=[...a].map(x=>c[x%c.length]).join('')}
document.querySelectorAll('form[data-confirm]').forEach(f=>f.addEventListener('submit',e=>{e.preventDefault();const t=f.dataset.type,m=$('#cm'),i=$('#cmi');
$('#cmt').textContent=f.dataset.confirm;$('#cms').textContent=t?'চালিয়ে যেতে নিচে ইমেইলটি লিখুন:  '+t:'';i.style.display=t?'':'none';i.value='';i.placeholder=t||'';m.style.display='flex';
$('#cmo').onclick=()=>{if(t&&i.value.trim().toLowerCase()!==t.toLowerCase()){i.focus();return}m.style.display='none';f.submit()};
$('#cmx').onclick=()=>{m.style.display='none'}}));
let FS='all';const flt=()=>{const q=($('#qs')||{value:''}).value.toLowerCase();document.querySelectorAll('.u[data-q]').forEach(u=>{u.style.display=(u.dataset.q.includes(q)&&(FS==='all'||u.dataset.s===FS))?'':'none'})};
const qs=$('#qs');if(qs)qs.addEventListener('input',flt);document.querySelectorAll('[data-f]').forEach(b=>b.addEventListener('click',()=>{FS=b.dataset.f;flt()}));
</script>
JS;
page('অ্যাডমিন প্যানেল', $b, $js);
