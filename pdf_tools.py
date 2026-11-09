import os, re
from config import get_now_uz

# RD96 KATALOG KOORDİNATLARI
CATALOG_GRID_MAP = {
    "91661":(2,1),"40642":(2,2),"40645":(2,3),"40643":(2,4),"40644":(2,5),"90802":(2,6),"41370":(3,3),"41381":(3,5),
    "91514":(3,6),"91410":(4,1),"91411":(4,2),"41436":(4,3),"41435":(4,4),"96469":(4,5),"60002":(4,6),"90338":(5,1),
    "91128":(5,2),"91516":(5,4),"41538":(5,5),"41407":(5,6),"41420":(6,1),"93041":(6,2),"93035":(6,3),"60020":(6,4),
    "91517":(7,1),"41430":(7,2),"41408":(7,3),"41415":(7,4),"41419":(7,5),"41414":(7,6),"41425":(8,1),"41427":(8,2),
    "41426":(8,3),"93039":(8,4),"93040":(8,5),"41413":(9,2),"41418":(9,3),"41411":(9,4),"41428":(9,5),"41429":(9,6),
    "93043":(10,1),"93042":(10,2),"93037":(10,3),"93036":(10,4),"60044":(11,1),"41434":(11,2),"90946":(11,3),"41432":(11,4),
    "41409":(11,5),"41424":(11,6),"41433":(12,1),"41416":(12,2),"41417":(12,3),"41533":(12,4),"96541":(12,5),"96540":(12,6),
    "90951":(13,2),"41384":(13,5),"41383":(13,6),"90310":(14,1),"90952":(14,2),"90332":(14,3),"90328":(14,4),"90949":(14,5),
    "90947":(14,6),"90321":(15,3),"16073":(15,4),"90490":(15,5),"91238":(15,6),"90333":(16,1),"90948":(16,2),"91407":(16,3),
    "93008":(16,4),"90345":(16,5),"90325":(16,6),"90320":(17,1),"90950":(17,2),"60003":(17,3),"96112":(17,4),"90827":(17,5),
    "50155":(17,6),"96467":(18,1),"91603":(18,2),"91035":(18,3),"90547":(18,4),"20031":(18,5),"90475":(18,6),"50160":(19,1),
    "91285":(19,2),"50606":(19,3),"91472":(19,4),"50247":(19,5),"50249":(19,6),"15401":(20,3),"41439":(20,4),"91633":(20,5),
    "91448":(20,6),"42595":(21,1),"90861":(21,3),"90817":(21,6),"96683":(22,1),"96097":(22,2),"91598":(22,4),"91037":(22,5),
    "40082":(22,6),"91386":(23,3),"91488":(23,4),"90567":(23,5),"90965":(23,6),"40647":(24,1),"90715":(24,2),"50161":(24,3),
    "50162":(24,4),"90828":(24,5),"90834":(24,6),"96468":(25,1),"91463":(25,3),"91604":(25,4),"90548":(25,5),"91036":(25,6),
    "90832":(26,4),"40634":(26,6),"96412":(27,1),"90878":(27,2),"90881":(27,3),"90880":(27,4),"90879":(27,5),"91284":(28,3),
    "14574":(28,4),"14541":(28,6),"91332":(29,1),"50219":(29,2),"54626":(29,3),"41441":(29,5),"91447":(29,6),"50057":(30,1),
    "54612":(30,2),"50098":(30,3),"50018":(30,4),"91594":(30,5),"91590":(31,3),"15005":(31,4),"50549":(31,5),"40085":(31,6),
    "91451":(32,1),"50023":(32,2),"50273":(32,3),"50021":(32,4),"41442":(32,5),"41404":(32,6),"96517":(33,3),"50257":(33,4),
    "96501":(33,5),"90766":(33,6),"16016":(34,1),"16039":(34,2),"16034":(34,3),"41403":(34,4),"90767":(34,5),"91071":(34,6),
    "90762":(35,1),"90840":(35,2),"41400":(35,3),"41401":(35,4),"41300":(35,5),"41402":(35,6),"91277":(36,1),"54516":(36,2),
    "90768":(36,3),"90769":(36,4),"90782":(36,5),"16032":(36,6),"16041":(37,3),"16035":(37,4),"50260":(37,5),"90759":(37,6),
    "50138":(38,2),"91086":(38,3),"91045":(38,4),"90770":(38,5),"16043":(38,6),"16030":(39,1),"90765":(39,4),"11906":(39,6),
    "12302":(40,1),"41444":(40,2),"91303":(40,3),"50263":(40,4),"91044":(40,5),"54510":(41,3),"90761":(41,4),"50262":(41,6),
    "41399":(42,5),"50259":(42,6),"50258":(43,6),"50261":(44,6),"91269":(45,6),"91270":(46,3),"50278":(46,4),"50293":(46,5),
    "90725":(46,6),"50040":(47,2),"41396":(47,3),"41398":(47,5),"54630":(47,6),"50270":(48,1),"50287":(48,2),"91066":(48,3),
    "91064":(48,4),"41457":(48,5),"50238":(48,6),"50156":(49,1),"91043":(49,2),"50269":(49,3),"50289":(50,6),"50239":(51,4),
    "50291":(52,1),"90781":(52,5),"41407P":(53,1),"96404":(53,2),"41406":(53,3),"41405":(53,4),"90484":(53,5),"91490":(53,6),
    "91489":(54,1),"90930":(54,5),"91495":(54,6),"54661":(55,3),"54662":(55,4),"41437":(55,5),"90568":(55,6),"50014":(56,1),
    "91782":(56,2),"91271":(56,3),"91268":(56,4),"90793":(56,5),"90324":(56,6),"16044":(57,1),"14847":(57,2),"41290":(57,3),
    "41287":(57,4),"41288":(57,5),"41289":(57,6),"54629":(58,1),"54628":(58,2),"54627":(58,3),"50024":(58,5),"50025":(58,6),
    "91586":(59,3),"50027":(59,4),"92038":(59,5),"54620":(59,6),"14577":(60,1),"14317":(60,2),"96449":(60,3),"91950":(60,4),
    "96219":(60,6),"91453":(61,1),"50008":(61,2),"50010":(61,3),"50046":(61,4),"50054":(62,3),"15005":(63,3)
}

def crop_slot_from_page(page, slot: int) -> bytes:
    pw, ph = page.rect.width, page.rect.height
    col = 0 if slot in [1, 3, 5] else 1
    row = 0 if slot in [1, 2] else (1 if slot in [3, 4] else 2)
    x0 = 8 if col == 0 else (pw / 2.0 + 2)
    x1 = (pw / 2.0 - 2) if col == 0 else (pw - 8)
    y0, y1 = [(25, 285), (288, 550), (550, 815)][row]
    try:
        import fitz
        clip_rect = fitz.Rect(max(0, x0), max(0, y0), min(pw, x1), min(ph, y1))
        return page.get_pixmap(clip=clip_rect, dpi=200).tobytes("png")
    except Exception:
        return None

def extract_part_image_from_pdf(code: str, name: str = "") -> bytes:
    pdf_path = None
    for fn in ["Katalog.pdf", "katalog.pdf", "rd96.pdf", "RD96.pdf", "CATALOG.PDF"]:
        if os.path.exists(fn): pdf_path = fn; break
    if not pdf_path: return None

    try:
        import fitz
        doc = fitz.open(pdf_path)
        code_str = str(code).strip()

        # Doğrudan slot koordinatından milimetrik kesim
        if code_str in CATALOG_GRID_MAP:
            page_no, slot = CATALOG_GRID_MAP[code_str]
            p_idx = page_no - 1
            if p_idx < len(doc):
                return crop_slot_from_page(doc[p_idx], slot)

        # Haritada yoksa metin arayarak kırpma
        for p_idx, page in enumerate(doc):
            rects = page.search_for(code_str)
            if rects:
                pw, ph = page.rect.width, page.rect.height
                r = rects[0]
                col = 0 if ((r.x0 + r.x1) / 2.0) < (pw / 2.0) else 1
                x0 = 8 if col == 0 else (pw / 2.0 + 2)
                x1 = (pw / 2.0 - 2) if col == 0 else (pw - 8)
                clip_rect = fitz.Rect(x0, max(10, r.y0 - 32), x1, min(ph - 10, r.y0 + 265))
                return page.get_pixmap(clip=clip_rect, dpi=200).tobytes("png")
        return None
    except Exception:
        return None

def parse_eliar_pdf_locally(pdf_path: str, original_filename: str = "") -> dict:
    full_text, items, firm, ref_no, grand_total, currency = "", [], None, "BELİRTİLMEDİ", "-", "EUR"
    try:
        import fitz
        doc = fitz.open(pdf_path)
        for page in doc: full_text += page.get_text() + "\n"
    except Exception: pass

    m_firm = re.search(r"Müşteri\s*Adı\s*:\s*([^\n\r]+)", full_text, re.IGNORECASE)
    if m_firm:
        val = re.split(r"(?:İlgili|Tel|Adres)", m_firm.group(1).strip(), flags=re.IGNORECASE)[0].strip()
        if len(val) >= 3 and val.upper() != "ADI:": firm = val.upper()

    if not firm or firm == "ADI:":
        clean_fn = re.sub(r"(fiyat|teklif|\.pdf|\.jpg)", "", original_filename, flags=re.IGNORECASE).strip()
        firm = clean_fn.upper() if len(clean_fn) >= 3 else "BİLİNMEYEN FİRMA"

    m_ref = re.search(r"Ref\s*No\s*:\s*([A-Za-z0-9\-]+)", full_text, re.IGNORECASE)
    if m_ref: ref_no = m_ref.group(1).strip()

    m_tot = re.search(r"TOPLAM\s*:\s*([\d\.,]+)\s*([€$£]|EUR|USD)?", full_text, re.IGNORECASE)
    if m_tot: grand_total, currency = m_tot.group(1).strip(), (m_tot.group(2) or "EUR")

    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    for row in table:
                        if not row or len(row) < 3: continue
                        clean_row = [str(c).replace('\n', ' ').strip() if c else '' for c in row]
                        row_str = " ".join(clean_row)
                        if "Ürün Kodu" in row_str or "TOPLAM" in row_str: continue
                        c0, c1 = clean_row[0], clean_row[1] if len(clean_row) > 1 else ""
                        if re.match(r"^\d{4,7}$", c0) or (len(c0) >= 3 and re.match(r"^[A-Za-z0-9\-_./]+$", c0)):
                            q = 1
                            for cell in clean_row[2:]:
                                digits = re.sub(r"[^\d]", "", cell)
                                if digits and 0 < int(digits) < 10000: q = int(digits); break
                            items.append({"code": c0, "name": c1, "qty": q, "unit_price": clean_row[3] if len(clean_row) > 3 else "-"})
    except Exception: pass

    return {"firm": firm, "ref_no": ref_no, "date": get_now_uz().strftime("%d.%m.%Y"), "currency": currency, "grand_total": grand_total, "items": items}