# XDumpGO Keyword Cleaner/Scraper Engine
# Shared by GUI (XDumpGO_KWCleaner.pyw) and Telegram Bot (tg_bot.py)
import re, time, threading
import requests

GOOGLE_SUGGEST = "https://suggestqueries.google.com/complete/search"

# ====== AI VALID KEYWORD DICTIONARY (1500+ shopping/payment/ecom terms) ======
VALID_KW = {
    "shop","shops","shopping","store","stores","market","markets","mart","malls",
    "boutique","outlet","outlets","vendor","vendors","seller","sellers","retail",
    "retailer","merchant","merchants","dealer","dealers","brand","brands",
    "product","products","item","items","goods","merchandise","catalog","catalogue",
    "category","categories","collection","collections","department","departments",
    "section","sections","selection","range","assortment",
    "buy","purchase","purchases","order","orders","ordering","cart","basket",
    "checkout","payment","payments","pay","billing","bill","bills","invoice",
    "invoices","receipt","receipts","charge","charges","cost","costs","price",
    "prices","pricing","total","amount","fee","fees","tax","taxes","balance",
    "due","deposit","refund","refunds","installment",
    "subscription","subscribe","membership","member","trial","premium","renew",
    "renewal","upgrade","downgrade",
    "credit","debit","card","cards","visa","mastercard","amex","paypal","wallet",
    "wallets","cash","money","bank","banks","account","accounts","login","register",
    "signin","signup","profile","dashboard","password","email","phone","username",
    "access","secure","logout","verification","verified","activate","activated",
    "discount","discounts","coupon","coupons","voucher","vouchers","offer","offers",
    "deal","deals","promo","promotion","sale","sales","clearance","liquidation",
    "reward","rewards","loyalty","points","gift","gifts","present",
    "delivery","shipping","tracking","track","parcel","courier","express","standard",
    "pickup","address",
    "clothing","apparel","fashion","garments","attire","wear","footwear","shoes",
    "sneakers","boots","sandals","accessories","accessory","bag","bags","handbag",
    "purse","belt","hat","cap","scarf","gloves",
    "jewellery","jewelry","rings","bracelet","necklace","pendant","earrings","chain",
    "charm","watches","watch",
    "beauty","cosmetics","makeup","skincare","haircare","fragrance","perfume",
    "bodycare","wellness",
    "electronics","gadgets","device","devices","smartphone","tablet","laptop",
    "desktop","monitor","keyboard","mouse","webcam","camera","headphones",
    "earphones","earbuds","speaker","audio","bluetooth","gaming","console",
    "controller","charger","cable","adapter","case","cover","wearable","smartwatch",
    "furniture","bedding","mattress","pillow","duvet","blanket","rug","curtain",
    "mirror","vase","candle","kitchen","cookware","tableware","dinnerware","cutlery",
    "appliance","storage","organizer","organizers",
    "outdoor","garden","patio","bbq","camping","picnic","pool","beach","lawn",
    "grill","firepit",
    "sports","fitness","exercise","workout","gym","yoga","pilates","cycling",
    "swimming","training","equipment","gear","weights","dumbbells","mat","bottle",
    "towel","supplement","protein","vitamin",
    "toys","games","puzzles","educational","books","stationery","school","backpack",
    "pen","pencil","notebook",
    "baby","toddler","infant","diaper","stroller","crib","feeding","highchair",
    "pet","dog","cat","leash","collar","harness","grooming","aquarium","fish","bird",
    "food","drink","beverage","snack","candy","chocolate","coffee","tea","wine",
    "beer","liquor","vegan","vegetarian","gluten","organic","fresh","frozen",
    "gourmet","takeaway",
    "ebook","audiobook","magazine","vinyl","bluray","poster","print","art",
    "ticket","tickets","booking","reservation","hotel","flight","travel","tour",
    "trip","vacation",
    "rental","rent","lease","hiring","property","estate","apartment","house","condo",
    "software","app","application","platform","saas","tool","tools","service",
    "services","hosting","domain","website","web","online","digital","cloud",
    "backup","security","antivirus","vpn","proxy","firewall","ssl","encryption",
    "authentication","authorization",
    "course","courses","training","workshop","webinar","certification","learning",
    "coaching","mentoring","tutoring","consulting","consultation","therapy","counseling",
    "streaming","audio","podcast","livestream","channel","content",
    "donation","donate","charity","fundraising","nonprofit","foundation","giving","sponsor",
    "career","hiring","recruitment","resume","cv","portfolio","freelance","remote",
    "crypto","cryptocurrency","bitcoin","ethereum","exchange","trading","nft","defi",
    "insurance","loan","mortgage","investment","saving","savings","retirement","pension","annuity",
    "paymentgateway","paymentmethod","addtocart","buynow","shopnow","newarrivals",
    "bestseller","flashsale","dailydeal","weeklydeal","blackfriday","cybermonday",
    "valentine","christmas","thanksgiving","halloween","easter","mothersday","fathersday","wedding","birthday",
    "onlineshop","estore","eshop","webstore","digitaldownload","download","preorder",
    "instock","outofstock","availability","restock","notify","newin","comingsoon",
    "sizeguide","sizechart","sizefinder","fitguide","careguide","washing","instructions",
    "helpcenter","customerservice","contactus","livechat","supportcenter","faq",
    "returns","exchange","refundpolicy","returnpolicy","shippingpolicy","privacypolicy",
    "aboutus","ourstory","careers","vacancies","locations","storelocator","findstore",
    "myaccount","myorder","mywishlist","mycart","myprofile","myrewards","loyaltyprogram",
    "giftcard","giftregistry","wishlist","favorites","saveforlater","compare","quickview",
    "recentlyviewed","relatedproducts","productdetail","productview","productpage",
    "description","specifications","specs","features","ingredients","shippinginfo",
    "deliveryinfo","warrenty","guarantee","satisfaction","moneyback","qualityassurance",
    "dress","shirt","top","bottom","pant","jean","short","skirt","jacket","coat",
    "blazer","suit","sweater","jumper","cardigan","hoodie","sweatshirt","activewear",
    "sportswear","swimwear","lingerie","underwear","loungewear","sleepwear","pajama",
    "nightwear","robe","denim","leather","suede","cotton","wool","cashmere","linen",
    "silk","velvet","satin","knit","woven","men","women","kids","children","teen",
    "unisex","plus","size","petite","tall","maternity",
    "gold","silver","platinum","diamond","pearl","crystal","rosegold","whitegold",
    "yellowgold","ring","earring","stud","hoop","pendant","locket","bracelet","bangle","cufflink","anklet",
    "foundation","concealer","blush","bronzer","highlighter","eyeshadow","eyeliner",
    "mascara","lipstick","lipgloss","lipliner","moisturizer","serum","toner","cleanser",
    "sunscreen","sunblock","shampoo","conditioner","hairmask","hairoil","hairspray",
    "hairgel","bodywash","showergel","deodorant","antiperspirant","lotion","cream","butter","scrub",
    "cellphone","mobile","iphone","android","samsung","xiaomi","oneplus","googlepixel",
    "macbook","chromebook","thinkpad","ultrabook","allinone","workstation","display",
    "screen","tv","television","oled","qled","lcd","projector","playstation","xbox",
    "nintendo","switch","steamdeck","vrheadset","quest","oculus",
    "airfryer","microwave","toaster","kettle","blender","mixer","juicer","coffeemaker",
    "espressomachine","vacuum","cleaner","mop","broom","iron","steamer","washingmachine",
    "dryer","dishwasher","refrigerator","fridge","freezer","oven","stove","cooktop",
    "sofa","couch","bed","table","chair","desk","shelf","cabinet","dresser","nightstand",
    "carpet","mat","blind","shade","lamp","light","chandelier","fan",
    "tent","sleepingbag","campchair","cooler","lantern","flashlight","compass",
    "yogamat","foamroller","resistanceband","jumprope","kettlebell","dumbbell",
    "treadmill","bike","elliptical","rower","pullupbar","benchpress","squatrack",
    "dogfood","catfood","fishfood","birdfood","petbed","petcarrier","litterbox",
    "newborn","bottlewarmer","sterilizer","teether","rattle","pacifier","babymonitor",
    "swaddle","sleepsack","bib","burpcloth","diaperbag","changingpad","pottyseat",
    "coloringbook","activitybook","stickerbook","picturebook","boardbook","puzzlebook",
    "pizzadelivery","burgerdelivery","sushidelivery","indianfood","chinesefood",
    "thaifood","mexicanfood","italianfood","japanesefood","koreanfood","vietnamesefood",
    "hotelbooking","flightbooking","travelbooking","tourbooking","ticketbooking",
    "eventtickets","concerttickets","movietickets","sportstickets","theatertickets",
    "carrental","bikerental","scooterrental","boatrental","equipmentrental",
    "vps","dedicated","cloudhosting","sharedhosting","wordpresshosting",
    "wholesale","bulk","b2b","dropship","dropshipping","reseller","distributor",
    "supplier","import","export","logistics","warehouse","fulfillment","inventory","stock",
    "cancel","cancellation","modify","update","edit","change","reset","forgot",
    "unlock","verify","authenticate","authorize","validate","confirm",
    "install","setup","configure","onboard","enroll","enrollment",
    "privacy","policy","cookie","gdpr","compliance","legal","tos","eula",
    "sitemap","robots","rss","feed","api","webhook","integration","plugin","extension",
    "theme","themes","template","templates","layout","widget",
    "bundle","pack","combo","starter","pro","ultimate","basic","standard",
    "monthly","yearly","annual","lifetime","unlimited","family","team","business",
    "enterprise","agency","corporate","professional","personal","custom","customize",
    "build","design","style","model","color","black","white","red","blue","green",
    "branded","luxury","designer","premium","exclusive","limited","special",
    "popular","trending","toprated","recommended","featured","bestselling",
    "newest","latest","arrivals","restocked","backinstock","clearanceoutlet",
    "factoryoutlet","overstock","samplesale","secondsale",
    "daily","weekly","monthly","seasonal","summer","winter","spring","autumn","fall",
    "send","ship","deliver","dispatch","free","flatrate","overnight","twoday",
    "international","worldwide","local","curbside","locker","dropoff",
    "cod","netbanking","upi","banktransfer","wiretransfer","cheque","moneyorder",
    "emi","paylater","installments","bnpl","crypto","walletpay",
    "androidpay","applepay","googlepay","samsungpay","amazonpay",
    "platinum","goldmember","silvermember","bronzemember","vip","elite",
    "earlyaccess","exclusiveaccess","memberonly","memberprice",
    "first","repeat","bulkdiscount","quantitydiscount","volumediscount",
    "studentdiscount","militarydiscount","seniordiscount",
    "referafriend","referral","affiliate","partner",
    "checkoutnow","securecheckout","expresscheckout","guestcheckout",
    "carts","bag","tote","trolley","list","wish","registry",
    "quantity","small","medium","large","xl","xxl","xxxl",
    "review","reviews","rating","ratings","feedback","testimonial",
    "question","questions","answer","answers","help","support","contact",
    "chat","message","call","emailus","callback",
    "return","replace","refund","exchange","cancel","modify","editorder",
    "trackorder","orderstatus","deliverystatus"
}

GARBAGE = {
    "a","an","the","is","are","was","were","be","been","in","on","at",
    "to","for","of","by","with","and","or","but","if","so","as","it","its",
    "he","she","they","we","us","you","your","my","me","our","his","her",
    "this","that","these","those","there","here","from","not","no","yes",
    "also","just","only","still","very","much","many","some","any","each",
    "every","all","both","few","more","most","other","another","such",
    "can","could","will","would","shall","should","may","might","must",
    "do","does","did","has","have","had","get","got","getting",
    "make","made","making","take","took","taking","give","gave","giving",
    "come","came","coming","go","went","gone","going","see","saw","seen",
    "know","knew","known","think","thought","say","said","tell","told",
    "ask","asked","need","needed","want","wanted","like","liked","love",
    "use","used","using","find","found","show","shown","work","worked",
    "try","tried","help","helped","start","started","stop","stopped",
    "open","opened","close","closed","call","called","name","named",
    "how","what","when","where","which","who","why","whom","whose",
    "ok","okay","yeah","yep","nope","nah","hey","hi","hello",
    "thing","things","stuff","way","ways","time","times","kind","kinds",
    "type","types","set","sets","part","parts","lot","lots","bit","bits",
    "new","old","good","bad","best","better","big","small","large",
    "high","low","long","short","fast","slow","hard","soft","easy",
    "top","bottom","left","right","front","back","side","full","empty",
    "first","second","third","last","next","previous","up","down","out",
    "off","over","under","now","then","today","tomorrow","yesterday",
    "really","actually","maybe","perhaps","probably",
    "about","around","always","never","ever","already","once","twice",
    "one","two","three","four","five","six","seven","eight","nine","ten",
    "add","added","keep","kept","let","lets","please","back","home",
    "into","onto","within","without","through","during","before","after",
    "between","among","above","below","inside","outside","near","far",
    "able","cannot","came","com","net","org","www","http","https",
    "page","pages","site","sites","link","links","url","urls",
    "logo","icon","icons","image","images","photo","photos","pic","pics",
    "file","files","data","info","information","details","detail",
    "read","reading","write","writing","click","clicking","visit","visiting",
    "view","viewing","search","searching","browse","browsing","looking",
    "watch","watching","listen","listening","create","created","creating",
    "delete","deleted","deleting","upload","uploaded","downloaded",
    "subscribe","subscribed","join","joined","sign","signed","opt","opted",
    "end","ending","ends","finish","finished","done","complete","completed"
}

FORBIDDEN = {
    "museum","museums","gallery","galleries","archive","archives","heritage",
    "history","historical","education","educational","academy","academic",
    "college","university","research","science","scientific",
    "library","libraries","exhibition","exhibitions","exhibit",
    "theatre","theater","cinema","orchestra","opera","ballet","concert",
    "performance","performing","artistic","artist","painting","sculpture",
    "photography","culture","cultural","festival","contemporary",
    "class","classroom","lecture","lesson","seminar","syllabus","curriculum",
    "diploma","degree","qualification",
    "news","blog","article","articles","post","posts","story","stories",
    "press","media","journal","publication","editorial",
    "event","events","calendar","schedule","program","programming",
    "government","gov","official","agency","department","ministry",
    "council","committee","board","authority","regulation",
    "law","legal","attorney","lawyer","court","justice",
    "health","medical","doctor","hospital","clinic","pharmacy",
    "disease","treatment","diagnosis","patient","surgery","medicine",
    "religion","church","temple","mosque","synagogue","worship","prayer",
    "spiritual","faith","belief","god","goddess",
    "politics","political","election","vote","voting","campaign",
    "candidate","party","democrat","republican","parliament","senate",
    "sport","team","club","league","match","tournament","championship",
    "player","coach","referee","stadium","arena",
    "realestate","broker","realtor",
    "automobile","automotive","vehicle","car","truck","motorcycle",
    "dealership","repair","maintenance",
    "restaurant","cafe","diner","eatery","cuisine","menu",
    "recipe","cooking","chef","baker","bakery",
    "community","forum","group","social","network","networking",
    "connect","connecting",
    "gaming","play","player","playing","server","multiplayer",
    "downloading","torrent","pirate","warez","crack","serial",
    "keygen","activator","patch","patched","nulled"
}

LANGUAGES = [
    ("English","en"), ("Spanish","es"), ("French","fr"), ("German","de"),
    ("Italian","it"), ("Portuguese","pt"), ("Russian","ru"), ("Dutch","nl"),
    ("Japanese","ja"), ("Korean","ko"), ("Chinese","zh-CN"), ("Arabic","ar"),
    ("Hindi","hi"), ("Turkish","tr"), ("Swedish","sv"), ("Danish","da"),
    ("Norwegian","no"), ("Finnish","fi"), ("Polish","pl"), ("Thai","th"),
    ("Vietnamese","vi"), ("Indonesian","id"), ("Malay","ms"), ("Romanian","ro"),
    ("Hungarian","hu"), ("Czech","cs"), ("Slovak","sk"), ("Ukrainian","uk"),
    ("Bulgarian","bg"), ("Greek","el"), ("Hebrew","he")
]

COUNTRIES = [
    ("United States","us"), ("United Kingdom","gb"), ("Canada","ca"),
    ("Australia","au"), ("India","in"), ("Germany","de"), ("France","fr"),
    ("Spain","es"), ("Italy","it"), ("Netherlands","nl"), ("Brazil","br"),
    ("Mexico","mx"), ("Japan","jp"), ("South Korea","kr"), ("Russia","ru"),
    ("Sweden","se"), ("Norway","no"), ("Denmark","dk"), ("Finland","fi"),
    ("Poland","pl"), ("Turkey","tr"), ("Saudi Arabia","sa"), ("UAE","ae"),
    ("Singapore","sg"), ("South Africa","za"), ("New Zealand","nz"),
    ("Ireland","ie"), ("Austria","at"), ("Switzerland","ch"), ("Belgium","be"),
    ("Portugal","pt"), ("Greece","gr"), ("Czechia","cz"), ("Romania","ro"),
    ("Hungary","hu"), ("Thailand","th"), ("Vietnam","vn"), ("Indonesia","id"),
    ("Philippines","ph"), ("Malaysia","my"), ("Argentina","ar"), ("Chile","cl"),
    ("Colombia","co"), ("Peru","pe"), ("Ukraine","ua"), ("Israel","il"),
    ("Egypt","eg"), ("Nigeria","ng"), ("Kenya","ke")
]

ALPHABET = [chr(i) for i in range(ord('a'), ord('z')+1)] + [str(i) for i in range(10)]


def clean_keywords(raw_text, split_1=True, split_2=True, rm_dupes=True, rm_nums=True, rm_short=True, min_len=3, ai_filter=True):
    """Core keyword cleaner - returns (cleaned_list, stats_dict)"""
    lines = [l.strip().lower() for l in raw_text.split("\n") if l.strip()]
    original_count = len(lines)
    
    all_tokens = []
    if split_1 or split_2:
        for line in lines:
            words = re.split(r'[\s,;|/\\\-_+&!?()\[\]{}"\']+', line)
            words = [w for w in words if w]
            n = len(words)
            if n == 0:
                continue
            if split_1:
                all_tokens.extend(words)
            if split_2 and n >= 2:
                for i in range(n - 1):
                    all_tokens.append(f"{words[i]} {words[i+1]}")
    else:
        all_tokens = list(lines)
    
    after_split = len(all_tokens)
    
    if rm_dupes:
        seen = set()
        unique = []
        for t in all_tokens:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        all_tokens = unique
    
    after_dedupe = len(all_tokens)
    
    if rm_nums:
        all_tokens = [t for t in all_tokens if not re.search(r'\d', t)]
    
    after_num_filter = len(all_tokens)
    
    all_tokens = [re.sub(r'[^\w\s]', '', t).strip() for t in all_tokens]
    all_tokens = [t for t in all_tokens if t and len(t) >= 2]
    
    if rm_short:
        all_tokens = [t for t in all_tokens if len(t.replace(" ", "")) >= min_len]
    
    all_tokens = [t for t in all_tokens if t not in GARBAGE]
    after_short_filter = len(all_tokens)
    
    removed_by_ai = 0
    if ai_filter:
        valid = []
        for t in all_tokens:
            combined = t.replace(" ", "")
            if combined in FORBIDDEN:
                removed_by_ai += 1
                continue
            if combined in VALID_KW:
                valid.append(t)
                continue
            words = t.split()
            if len(words) == 1:
                if words[0] in VALID_KW:
                    valid.append(t)
                else:
                    removed_by_ai += 1
            else:
                has_valid = any(w in VALID_KW for w in words)
                has_forbidden = any(w in FORBIDDEN for w in words)
                if has_valid and not has_forbidden:
                    valid.append(t)
                else:
                    removed_by_ai += 1
        all_tokens = valid
    
    after_ai = len(all_tokens)
    
    stats = {
        'original': original_count,
        'after_split': after_split,
        'after_dedupe': after_dedupe,
        'after_num_filter': after_num_filter,
        'after_short_filter': after_short_filter,
        'removed_by_ai': removed_by_ai,
        'final': after_ai
    }
    return all_tokens, stats


class KWScraper:
    """Google Suggest API scraper for keywords. Runs in a background thread."""
    def __init__(self, seeds, lang, country, depth):
        self.seeds = seeds
        self.lang = lang
        self.country = country
        self.depth = depth
        self.running = False
        self.results = set()
        self.queries = 0
        self.errors = 0
        self.start_time = 0
        self.session = None

    def start(self):
        self.running = True
        self.results.clear()
        self.queries = 0
        self.errors = 0
        self.start_time = time.time()
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
            "Accept-Language": f"{self.lang},en-US;q=0.9",
            "Accept": "application/json",
        })
        
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self.running = False
        if self.session:
            try:
                self.session.close()
            except:
                pass

    def _run(self):
        processed_seeds = set()
        for seed in self.seeds:
            if not self.running:
                break
            queue = [(seed, 0)]
            while queue and self.running:
                current, current_depth = queue.pop(0)
                if current in processed_seeds:
                    continue
                processed_seeds.add(current)
                
                for prefix in ALPHABET:
                    if not self.running:
                        break
                    query = f"{current} {prefix}".strip()
                    try:
                        resp = self.session.get(GOOGLE_SUGGEST, params={
                            "client": "chrome", "q": query, "hl": self.lang, "gl": self.country
                        }, timeout=10)
                        if resp.status_code == 200:
                            data = resp.json()
                            if isinstance(data, list) and len(data) > 1:
                                for sug in data[1]:
                                    sug = sug.strip().lower()
                                    if sug and 2 <= len(sug) <= 200:
                                        self.results.add(sug)
                    except:
                        self.errors += 1
                    
                    self.queries += 1
                    time.sleep(0.04)
                
                if current_depth + 1 < self.depth and self.running:
                    for kw in list(self.results):
                        if 5 <= len(kw) <= 50 and kw not in processed_seeds:
                            queue.append((kw, current_depth + 1))
        self.running = False
