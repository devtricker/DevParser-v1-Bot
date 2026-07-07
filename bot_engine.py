"""
DorkHunter Pro - Google Dork Search Engine (v3)
Multi-engine, country-wise proxies, ultra-fast proxy checker
"""
import re, random, time, threading, requests, queue
from urllib.parse import urlparse, unquote, quote
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===================== LICENSE CHECK =====================
_LIC_VALID = True
try:
    from key_system import check_license as _check_license
    _lic = _check_license()
    if not _lic.get("valid"):
        _LIC_VALID = False
        _LIC_MSG = _lic.get("message", "No license")
except:
    pass
# ==========================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
]

COUNTRY_CODES = {
    "all": "All Countries", "us": "United States", "uk": "United Kingdom", 
    "jp": "Japan", "in": "India", "de": "Germany", "fr": "France",
    "ca": "Canada", "au": "Australia", "br": "Brazil", "ru": "Russia",
    "nl": "Netherlands", "sg": "Singapore", "kr": "South Korea",
    "cn": "China", "it": "Italy", "es": "Spain", "se": "Sweden",
    "pl": "Poland", "tr": "Turkey", "id": "Indonesia", "mx": "Mexico",
}

IP_TEST_URL = "http://httpbin.org/ip"

def parse_proxy(raw, protocol="http"):
    raw = raw.strip()
    if not raw:
        return None
    if "://" in raw:
        parts = raw.split("://", 1)
        proto = parts[0].lower()
        rest = parts[1]
    else:
        proto = protocol.lower()
        rest = raw
    proto_map = {"http": "http", "https": "http", "socks4": "socks4", "socks5": "socks5h", "socks5h": "socks5h"}
    proto = proto_map.get(proto, "http")
    user = passwd = None
    if "@" in rest:
        auth, hostport = rest.rsplit("@", 1)
        if ":" in auth:
            user, passwd = auth.split(":", 1)
        hp = hostport
    else:
        parts = rest.split(":")
        if len(parts) == 4:
            hp = f"{parts[0]}:{parts[1]}"
            user, passwd = parts[2], parts[3]
        elif len(parts) == 2:
            hp = rest
        else:
            hp = rest
    if user and passwd:
        proxy_url = f"{proto}://{user}:{passwd}@{hp}"
    else:
        proxy_url = f"{proto}://{hp}"
    return {"http": proxy_url, "https": proxy_url}


class DorkEngine:
    ENGINES = ["google", "bing", "yahoojp", "duckduckgo", "brave", "startpage"]

    PROXY_APIS = {
        "http": [
            "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=http&proxy_format=protocolipport&format=text&timeout=5000",
            "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
            "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/protocols/http.txt",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
            "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
            "https://raw.githubusercontent.com/yemixzy/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt",
            "https://raw.githubusercontent.com/officialputuid/KangProxy/main/http.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
            "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
            "https://raw.githubusercontent.com/elliottophellia/proxylist/master/results/http/global/http_checked.txt",
            "https://raw.githubusercontent.com/UserR3X/proxy-list/main/online/http.txt",
            "https://raw.githubusercontent.com/HyperBeats/proxy-list/main/http.txt",
            "https://raw.githubusercontent.com/r00tee/Proxy-List/main/Https.txt",
            "https://raw.githubusercontent.com/MrMarble/proxy-list/main/all.txt",
            "https://raw.githubusercontent.com/RX4096/proxy-list/main/online/all.txt",
            "https://raw.githubusercontent.com/B4RC0DE-TM/proxy-list/main/HTTP.txt",
            "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/http.txt",
            "https://www.proxy-list.download/api/v1/get?type=http",
            "http://alexa.lr2b.com/proxylist.txt",
            "https://multiproxy.org/txt_all/proxy.txt",
            "https://proxyspace.pro/http.txt",
            "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt",
            "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt",
        ],
        "socks4": [
            "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=socks4&proxy_format=protocolipport&format=text&timeout=5000",
            "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks4/data.txt",
            "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/protocols/socks4.txt",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt",
            "https://raw.githubusercontent.com/officialputuid/KangProxy/main/socks4.txt",
            "https://raw.githubusercontent.com/yemixzy/proxy-list/main/proxies/socks4.txt",
            "https://www.proxy-list.download/api/v1/get?type=socks4",
        ],
        "socks5": [
            "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol=socks5&proxy_format=protocolipport&format=text&timeout=5000",
            "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
            "https://raw.githubusercontent.com/iplocate/free-proxy-list/main/protocols/socks5.txt",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
            "https://raw.githubusercontent.com/officialputuid/KangProxy/main/socks5.txt",
            "https://raw.githubusercontent.com/yemixzy/proxy-list/main/proxies/socks5.txt",
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            "https://www.proxy-list.download/api/v1/get?type=socks5",
        ],
    }

    def __init__(self, callback=None):
        self.raw_proxies = []
        self.dorks = []
        self.results = set()
        self.filtered = set()
        self.running = False
        self.paused = False
        self.callback = callback
        self.lock = threading.RLock()
        self.dorks_done = 0
        self.dorks_parsing = 0
        self.start_time = 0
        self.pages_per_dork = 3
        self.threads = 75
        self.chunk_size = 3000
        self.param_filter = False
        self.domain_dedup = False
        self.antipublic = False
        self.output_file = "results"
        self.output_ext = ".txt"
        self.search_engine = "google"
        self.country = "all"               # Country code for proxy filtering
        self.proxy_protocol = "http"
        self.dead_proxies = set()
        self.proxy_stats = {"success": 0, "fail": 0}
        self.retry_count = 2
        self.tested_good = set()
        self._domain_set = set()
        self.auto_scrape = False
        self.proxy_min_threshold = 1000
        self._scraping_lock = threading.Lock()
        self.proxies_from_file = False
        self._write_queue = queue.Queue()
        self._writer_thread = None
        self._stop_writer = False

    def load_dorks(self, filepath):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            self.dorks = [l.strip() for l in f if l.strip()]
        return len(self.dorks)

    def load_proxies(self, filepath):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            self.raw_proxies = [l.strip() for l in f if l.strip()]
        self.dead_proxies = set()
        self.proxies_from_file = True
        return len(self.raw_proxies)

    def _country_api_urls(self, protocol, country_code):
        """Generate country-specific proxy URLs"""
        urls = [
            f"https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&protocol={protocol}&proxy_format=protocolipport&format=text&timeout=5000&country={country_code}",
        ]
        # Proxifly country-specific
        cc = country_code.upper()
        urls.append(f"https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/countries/{cc}/data.txt")
        # iplocate country-specific
        urls.append(f"https://raw.githubusercontent.com/iplocate/free-proxy-list/main/countries/{cc}/proxies.txt")
        return urls

    def scrape_proxies(self, protocol="http"):
        if protocol == "all":
            targets = ["http", "socks4", "socks5"]
        else:
            targets = [protocol]

        all_proxies = set()
        self._scraping_count = 0  # Real-time progress for bot UI
        for proto in targets:
            urls = list(self.PROXY_APIS.get(proto, self.PROXY_APIS["http"]))
            # Add country-specific URLs if country selected
            if self.country != "all":
                country_urls = self._country_api_urls(proto, self.country)
                urls = country_urls + urls

            for api_url in urls:
                try:
                    if self.callback:
                        domain = api_url.split("/")[2][:35]
                        self.callback("log", f"  Scraping {proto.upper()} from {domain}...")
                    resp = requests.get(api_url, timeout=12, verify=False,
                                        headers={"User-Agent": random.choice(USER_AGENTS)})
                    if resp.status_code == 200:
                        lines = resp.text.strip().split("\n")
                        count = 0
                        for line in lines:
                            p = line.strip()
                            if p and ":" in p and len(p) > 7:
                                if "://" not in p:
                                    tagged = f"{proto}://{p}"
                                else:
                                    tagged = p
                                all_proxies.add(tagged)
                                count += 1
                        self._scraping_count = len(all_proxies)
                        if self.callback and count > 0:
                            self.callback("log", f"     Got {count} proxies")
                except:
                    pass

        self.raw_proxies = list(all_proxies)
        self.dead_proxies = set()
        self.proxies_from_file = False
        if self.callback:
            http_c = sum(1 for p in self.raw_proxies if p.startswith("http://"))
            s4_c = sum(1 for p in self.raw_proxies if p.startswith("socks4://"))
            s5_c = sum(1 for p in self.raw_proxies if p.startswith("socks5://"))
            ctry = COUNTRY_CODES.get(self.country, "Global")
            self.callback("log", f"  Total: {len(self.raw_proxies)} [{ctry}] | HTTP:{http_c} | S4:{s4_c} | S5:{s5_c}")
        return len(self.raw_proxies)

    def get_alive_proxies(self):
        return max(0, len(self.raw_proxies) - len(self.dead_proxies))

    def _mark_proxy_dead(self, raw):
        if raw:
            self.dead_proxies.add(raw)
            if self.auto_scrape and not self.proxies_from_file:
                alive = len(self.raw_proxies) - len(self.dead_proxies)
                if alive < self.proxy_min_threshold:
                    self._try_background_refill()

    def _try_background_refill(self):
        if not self.running or self.proxies_from_file:
            return
        if not self._scraping_lock.acquire(blocking=False):
            return
        def do_refill():
            try:
                if not self.running:
                    return
                alive = self.get_alive_proxies()
                if self.callback:
                    self.callback("log", f"  Proxy pool low ({alive}). Auto-scraping...")
                self.scrape_proxies(self.proxy_protocol)
                if self.callback:
                    self.callback("log", f"  Refill done: {self.get_alive_proxies()} proxies now")
            finally:
                try: self._scraping_lock.release()
                except RuntimeError: pass
        threading.Thread(target=do_refill, daemon=True).start()

    def _rotate_file_proxies(self):
        if not self.proxies_from_file:
            return False
        self.dead_proxies.clear()
        if self.callback:
            self.callback("log", "  File proxies rotated!")
        return True

    def _refill_or_rotate(self):
        if self.proxies_from_file:
            self._rotate_file_proxies()
            return True
        if self.auto_scrape:
            self._try_background_refill()
            return True
        return False

    def _get_proxy(self):
        if self.proxy_protocol == "none":
            return None, None
        if not self.raw_proxies:
            return None, None
        for _ in range(100):
            raw = random.choice(self.raw_proxies)
            if raw not in self.dead_proxies:
                if "://" in raw:
                    return parse_proxy(raw), raw
                return parse_proxy(raw, self.proxy_protocol), raw
        return None, None

    def test_proxy(self, raw, protocol="http"):
        """Ultra-fast proxy test (single endpoint, 2s timeout)"""
        proxy = parse_proxy(raw, protocol)
        if not proxy:
            return False, 0, ""
        try:
            start = time.time()
            resp = requests.get("http://httpbin.org/ip", proxies=proxy, timeout=2, verify=False)
            if resp.status_code == 200:
                latency = int((time.time() - start) * 1000)
                return True, latency, resp.text.strip()[:50]
        except:
            pass
        return False, 0, ""

    def test_all_proxies(self):
        if self.proxy_protocol == "none":
            if self.callback:
                self.callback("log", "  Proxy Protocol is NONE. Skipping.")
            return
        
        total = len(self.raw_proxies)
        if total == 0:
            if self.callback:
                self.callback("log", "  No proxies to test.")
            return
            
        if self.callback:
            self.callback("log", f"  Testing {total} proxies [100 threads, 2s timeout]...")

        good = 0; dead = 0; alive_proxies = []
        self._tested_count = 0      # Real-time progress
        self._tested_alive = 0      # Real-time progress
        done_count = [0]
        lock = self.lock
        running = self.running
        
        def check(i, raw):
            nonlocal good, dead
            proto = self.proxy_protocol if self.proxy_protocol != "all" else "socks5"
            ok, ms, ip = self.test_proxy(raw, proto)
            with lock:
                if ok:
                    good += 1; alive_proxies.append(raw); self.tested_good.add(raw)
                else:
                    dead += 1; self.dead_proxies.add(raw)
                done_count[0] += 1
                self._tested_count = done_count[0]
                self._tested_alive = good
        
        with ThreadPoolExecutor(max_workers=100) as pool:
            futures = {pool.submit(check, i, raw): raw for i, raw in enumerate(self.raw_proxies[:5000])}
            for f in as_completed(futures, timeout=120):
                if done_count[0] % 500 == 0 and done_count[0] > 0 and self.callback:
                    self.callback("log", f"    Tested: {done_count[0]}/{min(total,5000)} | Alive: {good}")
                if not self.running:
                    for t in futures: t.cancel()
                    break
        
        if self.running and good > 0:
            self.raw_proxies = alive_proxies
            self.dead_proxies = set()
        if self.callback:
            self.callback("log", f"  Test done: {good} alive, {dead} dead (max 5000 tested)")

    def _get_headers(self):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1", "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none", "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    def _extract_urls(self, html, engine="google"):
        urls = set()
        if engine == "google":
            patterns = [
                r'/url\?q=(https?://[^&"\']+)',
                r'<a[^>]+href="(https?://[^"]+)"',
                r'<cite[^>]*>(https?://[^<]+)</cite>',
            ]
        elif engine == "bing":
            patterns = [
                r'<li class="b_algo"[^>]*>.*?<h2><a[^>]+href="(https?://[^"]+)"',
                r'<cite>(https?://[^<]+)</cite>',
            ]
        elif engine == "yahoojp":
            patterns = [
                r'href="(https?://[^"]+)"[^>]*data-bns="algo"',
                r'class="sw-Card__title"[^>]*>.*?<a[^>]+href="(https?://[^"]+)"',
            ]
        elif engine == "duckduckgo":
            patterns = [
                r'class="result__url"[^>]*>(https?://[^<]+)<',
                r'<a[^>]+class="result__a"[^>]+href="(https?://[^"]+)"',
                r'uddg=(https?[^&\s"\']+)',
            ]
        elif engine == "brave":
            patterns = [
                r'class="result-header"[^>]*>.*?<a[^>]+href="(https?://[^"]+)"',
                r'class="snippet-title"[^>]*>.*?<a[^>]+href="(https?://[^"]+)"',
            ]
        elif engine == "startpage":
            patterns = [
                r'class="w-gl__result-title"[^>]*>.*?<a[^>]+href="(https?://[^"]+)"',
                r'class="link-text"[^>]*>(https?://[^<]+)<',
            ]
        else:
            return urls

        for pat in patterns:
            for m in re.findall(pat, html, re.IGNORECASE | re.DOTALL):
                url = unquote(m).split("&")[0]
                if self._valid_url(url):
                    urls.add(url)
        return urls

    def _valid_url(self, url):
        skip_domains = ['google.com', 'google.', '.google', 'youtube.com', 'blogger.com',
                        'schema.org', 'w3.org', 'bing.com', 'yahoo.com', 'microsoft.com',
                        'msn.com', 'live.com', 'yahoo.co.jp', 'duckduckgo.com', 'brave.com',
                        'startpage.com']
        skip_strings = ['googleadservices', 'googlesyndication', 'doubleclick', 'googleapis',
                        'gstatic', 'webcache', 'policies', 'support', 'bingj', 'yimg',
                        'search.yahoo', 'duckduckgo', 'sponsored', 'brave.com/search']
        try:
            p = urlparse(url)
            if p.scheme not in ('http', 'https'):
                return False
            domain = p.netloc.lower()
            for s in skip_domains:
                if s in domain or domain.endswith(s):
                    return False
            for s in skip_strings:
                if s in url.lower():
                    return False
            if len(domain) < 4 or '.' not in domain:
                return False
            return True
        except:
            return False

    def _apply_filters(self, url, dork=None):
        if dork:
            site_match = re.search(r'site:([a-zA-Z0-9.-]+)', dork.lower())
            if site_match:
                required_tld = site_match.group(1)
                domain = urlparse(url).netloc.lower()
                if not domain.endswith('.' + required_tld) and domain != required_tld:
                    with self.lock: self.filtered.add(url)
                    return None
        if self.param_filter:
            if '?' not in url:
                with self.lock: self.filtered.add(url)
                return None
        if self.domain_dedup:
            domain = urlparse(url).netloc
            with self.lock:
                if domain in self._domain_set:
                    self.filtered.add(url)
                    return None
                self._domain_set.add(domain)
        return url

    def _writer_loop(self):
        outfile = f"{self.output_file}{self.output_ext}"
        try:
            with open(outfile, "a", encoding="utf-8", buffering=1) as f:
                while not self._stop_writer:
                    try:
                        item = self._write_queue.get(timeout=0.5)
                        if item is None: break
                        f.write(item + "\n")
                        f.flush()
                        self._write_queue.task_done()
                    except queue.Empty:
                        continue
        except: pass

    def _refill_proxies_if_needed(self):
        if self.proxies_from_file:
            self._rotate_file_proxies()
            return True
        if self.auto_scrape:
            self._try_background_refill()
            return True
        return False

    def _search_dork(self, dork):
        """Search one dork across selected engine(s). Supports 'all' mode."""
        if not self.running:
            return
        
        with self.lock:
            self.dorks_parsing += 1

        # Determine engines to use
        if self.search_engine == "all":
            engines = self.ENGINES
            pages_per_eng = max(1, self.pages_per_dork // 2)  # 1 page per engine in ALL mode for speed
        else:
            engines = [self.search_engine]
            pages_per_eng = self.pages_per_dork

        # Build requests for all engines + pages
        all_requests = []
        for eng in engines:
            for page in range(pages_per_eng):
                offset = page * 10
                if eng == "bing":
                    url = f"https://www.bing.com/search?q={quote(dork)}&first={offset + 1}"
                    all_requests.append(("GET", url, {}, eng))
                elif eng == "yahoojp":
                    url = f"https://search.yahoo.co.jp/search?p={quote(dork)}&b={offset + 1}"
                    all_requests.append(("GET", url, {}, eng))
                elif eng == "duckduckgo":
                    url = "https://html.duckduckgo.com/html/"
                    data = {"q": dork, "b": str(offset), "kl": "wt-wt", "df": ""}
                    all_requests.append(("POST", url, {"data": data}, eng))
                elif eng == "brave":
                    url = f"https://search.brave.com/search?q={quote(dork)}&offset={offset}&source=web"
                    all_requests.append(("GET", url, {}, eng))
                elif eng == "startpage":
                    url = f"https://www.startpage.com/sp/search?q={quote(dork)}&start={offset}"
                    all_requests.append(("GET", url, {}, eng))
                else:  # google
                    url = f"https://www.google.com/search?q={quote(dork)}&start={offset}&num=10&hl=en&gl=us"
                    all_requests.append(("GET", url, {}, eng))

        total_found = 0
        sess = requests.Session()

        for method, url, extra, eng in all_requests:
            if not self.running: break
            while self.paused:
                time.sleep(0.1)

            for attempt in range(self.retry_count + 2):
                if not self.running: break
                
                proxy = None; raw_proxy = None
                if self.proxy_protocol != "none":
                    proxy, raw_proxy = self._get_proxy()
                    if proxy is None:
                        if not self._refill_or_rotate():
                            if self.callback:
                                self.callback("log", "Proxies exhausted. Stopping...")
                            self.stop()
                            try: sess.close()
                            except: pass
                            with self.lock: self.dorks_parsing -= 1
                            return
                        continue

                try:
                    kwargs = {"headers": self._get_headers(), "timeout": (5, 10), "verify": False, "allow_redirects": True}
                    if proxy: kwargs["proxies"] = proxy
                    if extra.get("data"): kwargs["data"] = extra["data"]
                    
                    resp = sess.post(url, **kwargs) if method == "POST" else sess.get(url, **kwargs)

                    if resp.status_code == 200:
                        found = self._extract_urls(resp.text, eng)
                        if not found:
                            # 200 but no URLs => likely captcha/block page: retry with a fresh proxy
                            self._mark_proxy_dead(raw_proxy)
                            continue
                        for u in found:
                            filt = self._apply_filters(u, dork)
                            if filt:
                                with self.lock:
                                    if filt not in self.results:
                                        self.results.add(filt)
                                        total_found += 1
                                self._write_queue.put(filt)
                        break
                    elif resp.status_code in (403, 429, 503):
                        self._mark_proxy_dead(raw_proxy)
                        continue
                    else:
                        break
                except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout,
                        requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
                    self._mark_proxy_dead(raw_proxy)
                    continue
                except Exception:
                    break

        try: sess.close()
        except: pass

        with self.lock:
            self.dorks_done += 1
            self.dorks_parsing -= 1

    def start(self):
        self.running = True; self.paused = False
        self.results = set(); self.filtered = set(); self._domain_set = set()
        self.dorks_done = 0; self.dorks_parsing = 0
        self.dead_proxies = set()
        self.proxy_stats = {"success": 0, "fail": 0}

        while not self._write_queue.empty():
            try: self._write_queue.get_nowait()
            except: break
        self._stop_writer = False
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.executor = None; self.start_time = time.time()
        total = len(self.dorks); chunk = self.chunk_size

        def run():
            if self.get_alive_proxies() == 0 and self.proxy_protocol != "none":
                if self.proxies_from_file:
                    self._rotate_file_proxies()
                elif self.auto_scrape:
                    if self.callback:
                        self.callback("log", "No proxies loaded. Auto-Scraping...")
                    self.scrape_proxies(self.proxy_protocol)

            eng_label = "ALL" if self.search_engine == "all" else self.search_engine.upper()
            if self.callback:
                self.callback("started", None)
                self.callback("log", f"Starting [{eng_label}] | {total} dorks | {len(self.raw_proxies)} proxies | {self.threads} threads")

            outfile = f"{self.output_file}{self.output_ext}"
            with open(outfile, 'w', encoding='utf-8') as f: pass
            self._writer_thread.start()

            for chunk_start in range(0, total, chunk):
                if not self.running: break
                chunk_end = min(chunk_start + chunk, total)
                chunk_dorks = self.dorks[chunk_start:chunk_end]
                if self.callback:
                    self.callback("log", f"Chunk {chunk_start//chunk + 1}/{(total+chunk-1)//chunk} ({chunk_start}-{chunk_end} of {total})")
                self.executor = ThreadPoolExecutor(max_workers=self.threads)
                futs = {self.executor.submit(self._search_dork, d): d for d in chunk_dorks}
                try:
                    for f in as_completed(futs):
                        if not self.running:
                            for task in futs: task.cancel()
                            break
                finally:
                    if self.executor:
                        self.executor.shutdown(wait=True)
                        self.executor = None
                if chunk_start > 0 and chunk_start % (chunk * 5) == 0:
                    import gc; gc.collect()

            self.running = False
            self._stop_writer = True
            self._write_queue.put(None)
            if self._writer_thread and self._writer_thread.is_alive():
                self._writer_thread.join(timeout=5.0)
            if self.callback:
                if self.dorks_done < total:
                    self.callback("log", f"Stopped! {len(self.results)} URLs -> {outfile}")
                else:
                    self.callback("log", f"Done! {len(self.results)} URLs -> {outfile}")
                self.callback("finished", {"file": outfile, "total": len(self.results)})

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self.running = False
        if hasattr(self, 'executor') and self.executor:
            try: self.executor.shutdown(wait=False, cancel_futures=True)
            except: pass
        self._stop_writer = True
        self._write_queue.put(None)

    def pause(self):
        self.paused = not self.paused
        return self.paused

    def get_elapsed(self):
        return time.time() - self.start_time if self.start_time else 0

    def get_dpm(self):
        e = self.get_elapsed()
        return round(self.dorks_done / (e / 60), 1) if e > 1 else 0

    def get_fpm(self):
        e = self.get_elapsed()
        return round(len(self.filtered) / (e / 60), 1) if e > 1 else 0

    def get_eta(self):
        if self.dorks_done == 0: return 0
        rate = self.dorks_done / self.get_elapsed()
        return (len(self.dorks) - self.dorks_done) / rate if rate > 0 else 0

    def get_alive_proxies(self):
        return max(0, len(self.raw_proxies) - len(self.dead_proxies))
