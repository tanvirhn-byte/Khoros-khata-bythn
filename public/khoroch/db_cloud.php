<?php
// খরচের খাতা — Cloud Database Persistence & Self-Healing Helper (db_cloud.php)
// Render.com Free Tier বা ইফেমেরাল ডকার কন্টেইনার রিস্টার্ট হলেও যেন ডেটাবেস না হারায়।

function getCloudToken(?PDO $db = null): string {
  $envTok = getenv('GITHUB_TOKEN') ?: getenv('CLOUD_BACKUP_TOKEN') ?: '';
  if ($envTok !== '') return trim($envTok);
  if (defined('CLOUD_BACKUP_B64') && CLOUD_BACKUP_B64 !== '') {
    $dec = base64_decode((string)CLOUD_BACKUP_B64, true);
    if (is_string($dec) && $dec !== '') return trim($dec);
  }
  $tokFile = __DIR__ . '/data/.cloud_token';
  if (is_file($tokFile)) {
    $t = trim((string)@file_get_contents($tokFile));
    if ($t !== '') return $t;
  }
  if ($db) {
    try {
      $t = $db->query("SELECT v FROM settings WHERE k='github_token' LIMIT 1")->fetchColumn();
      if (is_string($t) && trim($t) !== '') {
        @file_put_contents($tokFile, trim($t));
        return trim($t);
      }
    } catch (Throwable $e) {}
  }
  return '';
}

function ghApiRequest(string $method, string $url, string $token, ?array $payload = null): ?array {
  $headers = [
    'User-Agent: Khoroch-Er-Khata-Sync',
    'Accept: application/vnd.github+json',
    'Authorization: Bearer ' . $token,
    'X-GitHub-Api-Version: 2022-11-28'
  ];
  $body = $payload !== null ? json_encode($payload, JSON_UNESCAPED_UNICODE) : null;
  if ($body !== null) {
    $headers[] = 'Content-Type: application/json';
  }
  if (function_exists('curl_init')) {
    $ch = curl_init($url);
    curl_setopt_array($ch, [
      CURLOPT_CUSTOMREQUEST => $method,
      CURLOPT_HTTPHEADER => $headers,
      CURLOPT_RETURNTRANSFER => true,
      CURLOPT_TIMEOUT => 12,
      CURLOPT_CONNECTTIMEOUT => 5,
    ]);
    if ($body !== null) {
      curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
    }
    $res = curl_exec($ch);
    $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($res === false || $code < 200 || $code >= 300) return null;
    $json = json_decode((string)$res, true);
    return is_array($json) ? $json : null;
  }
  $opts = [
    'http' => [
      'method' => $method,
      'header' => implode("\r\n", $headers) . "\r\n",
      'timeout' => 12,
      'ignore_errors' => true
    ]
  ];
  if ($body !== null) $opts['http']['content'] = $body;
  $ctx = stream_context_create($opts);
  $res = @file_get_contents($url, false, $ctx);
  if ($res === false) return null;
  $json = json_decode((string)$res, true);
  return is_array($json) ? $json : null;
}

function findBackupGistId(string $token): string {
  $gidFile = __DIR__ . '/data/.gist_id';
  if (is_file($gidFile)) {
    $gid = trim((string)@file_get_contents($gidFile));
    if ($gid !== '') return $gid;
  }
  $envGid = getenv('GITHUB_GIST_ID') ?: '';
  if ($envGid !== '') return trim($envGid);
  $list = ghApiRequest('GET', 'https://api.github.com/gists?per_page=50', $token);
  if (!is_array($list)) return '';
  foreach ($list as $g) {
    if (($g['description'] ?? '') === 'Khoroch-Er-Khata-Auto-DB-Backup' || isset($g['files']['khoroch_sqlite.b64'])) {
      $id = (string)($g['id'] ?? '');
      if ($id !== '') {
        @file_put_contents($gidFile, $id);
        return $id;
      }
    }
  }
  return '';
}

function cloudRestoreDb(string $dbf, string $overrideToken = ''): bool {
  if ($overrideToken === '' && is_file($dbf) && filesize($dbf) > 4096) {
    return false;
  }
  $tok = $overrideToken !== '' ? trim($overrideToken) : getCloudToken(null);
  if ($tok === '') return false;
  $gid = findBackupGistId($tok);
  if ($gid === '') return false;
  $gist = ghApiRequest('GET', 'https://api.github.com/gists/' . rawurlencode($gid), $tok);
  if (!$gist || empty($gist['files']['khoroch_sqlite.b64'])) return false;
  $fileObj = $gist['files']['khoroch_sqlite.b64'];
  $b64 = (string)($fileObj['content'] ?? '');
  if ((!empty($fileObj['truncated']) || $b64 === '') && !empty($fileObj['raw_url'])) {
    $raw = @file_get_contents((string)$fileObj['raw_url']);
    if (is_string($raw) && $raw !== '') $b64 = $raw;
  }
  if ($b64 === '') return false;
  $rawBytes = base64_decode(preg_replace('/\s+/', '', $b64), true);
  if (!is_string($rawBytes) || strlen($rawBytes) < 100 || substr($rawBytes, 0, 15) !== 'SQLite format 3') {
    return false;
  }
  $dir = dirname($dbf);
  if (!is_dir($dir)) @mkdir($dir, 0750, true);
  $tmp = $dbf . '.restore_' . bin2hex(random_bytes(4));
  if (@file_put_contents($tmp, $rawBytes) === false) return false;
  // Remove stale WAL/SHM files before replacing main DB
  if (is_file($dbf . '-wal')) @unlink($dbf . '-wal');
  if (is_file($dbf . '-shm')) @unlink($dbf . '-shm');
  $ok = @rename($tmp, $dbf);
  if (!$ok) {
    $ok = @copy($tmp, $dbf);
    @unlink($tmp);
  }
  if ($ok && $overrideToken !== '') {
    @file_put_contents($dir . '/.cloud_token', $tok);
  }
  return $ok;
}

function cloudBackupDb(PDO $db, string $dbf, bool $force = false): bool {
  $tok = getCloudToken($db);
  if ($tok === '') return false;
  $dir = dirname($dbf);
  $stampFile = $dir . '/.last_cloud_sync';
  if (!$force && is_file($stampFile) && (time() - (int)@filemtime($stampFile)) < 8) {
    return true; // Throttle rapid consecutive writes within 8s
  }
  $snap = $dir . '/snap_' . bin2hex(random_bytes(4)) . '.sqlite';
  $snapOk = false;
  try {
    $esc = str_replace("'", "''", $snap);
    $db->exec("VACUUM INTO '{$esc}'");
    if (is_file($snap) && filesize($snap) > 0) $snapOk = true;
  } catch (Throwable $e) {
    if (is_file($snap)) @unlink($snap);
  }
  if (!$snapOk) {
    try {
      $db->query('PRAGMA wal_checkpoint(TRUNCATE)');
      if (@copy($dbf, $snap) && is_file($snap) && filesize($snap) > 0) $snapOk = true;
    } catch (Throwable $e2) {}
  }
  if (!$snapOk || !is_file($snap)) return false;
  $bytes = @file_get_contents($snap);
  @unlink($snap);
  if (!is_string($bytes) || strlen($bytes) < 100) return false;
  $b64 = base64_encode($bytes);
  $gid = findBackupGistId($tok);
  $payload = [
    'description' => 'Khoroch-Er-Khata-Auto-DB-Backup',
    'public' => false,
    'files' => [
      'khoroch_sqlite.b64' => [
        'content' => $b64
      ]
    ]
  ];
  if ($gid !== '') {
    $res = ghApiRequest('PATCH', 'https://api.github.com/gists/' . rawurlencode($gid), $tok, $payload);
  } else {
    $res = ghApiRequest('POST', 'https://api.github.com/gists', $tok, $payload);
    if ($res && !empty($res['id'])) {
      @file_put_contents($dir . '/.gist_id', (string)$res['id']);
    }
  }
  if ($res && !empty($res['id'])) {
    @touch($stampFile);
    return true;
  }
  return false;
}
