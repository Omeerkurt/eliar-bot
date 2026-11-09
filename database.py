import json, os, time, re, difflib
from config import STOCKS_FILE, SALES_FILE, QUOTES_FILE, TEST_MODE

def load_data(path, default):
    if not os.path.exists(path):
        save_data(path, default)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def save_data(path, data):
    tmp_file = f"{path}.tmp_{int(time.time()*1000)}"
    with open(tmp_file, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, path)

load_stocks = lambda: load_data(STOCKS_FILE, [])
load_sales = lambda: load_data(SALES_FILE, [])
load_quotes = lambda: load_data(QUOTES_FILE, [])
save_stocks = lambda d: save_data(STOCKS_FILE, d) if not TEST_MODE else None
save_sales = lambda d: save_data(SALES_FILE, d) if not TEST_MODE else None
save_quotes = lambda d: save_data(QUOTES_FILE, d)

def normalize_tr(text: str) -> str:
    if not text: return ""
    m = {'ı':'i','İ':'i','I':'i','ş':'s','Ş':'s','ğ':'g','Ğ':'g','ü':'u','Ü':'u','ö':'o','Ö':'o','ç':'c','Ç':'c'}
    res = str(text).lower()
    for k, v in m.items(): res = res.replace(k, v)
    res = res.replace("diayfram", "diyafram").replace("diafram", "diyafram").replace("dayfram", "diyafram")
    res = res.replace("cekvalf", "çekvalf").replace("selonoid", "solenoid")
    return res

def parse_qty_safe(text: str) -> int:
    digits = re.findall(r"\d+", str(text))
    if digits and int(digits[0]) > 0: return int(digits[0])
    raise ValueError()

def safe_stock_qty(val, default=0) -> int:
    if val is None: return default
    try: return max(0, int(val))
    except Exception:
        digits = re.findall(r"\d+", str(val))
        return int(digits[0]) if digits else default

def calculate_similarity(query: str, part: dict) -> float:
    q_norm = normalize_tr(query.strip())
    name_norm = normalize_tr(part.get("name", ""))
    code_norm = normalize_tr(part.get("code", ""))

    if q_norm == code_norm: return 1.0
    if q_norm in code_norm: return 0.95
    if q_norm in name_norm: return 0.88

    q_words = q_norm.split()
    name_words = name_norm.split()
    word_scores = [max([difflib.SequenceMatcher(None, qw, nw).ratio() for nw in name_words] or [0]) for qw in q_words]
    avg_word = sum(word_scores) / len(word_scores) if word_scores else 0.0

    return max(avg_word, difflib.SequenceMatcher(None, q_norm, name_norm).ratio())

def find_best_matches(query: str):
    stocks = load_stocks()
    scored = [(p, calculate_similarity(query, p)) for p in stocks if calculate_similarity(query, p) > 0.30]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored