"""ovoz.py — O'zbekcha tabiiy ovoz (BEPUL)

Sifat sirri: neural ovoz o'zi yomon emas. Sun'iylik xom matndan keladi —
raqamlar, matematik belgilar, qisqartmalar noto'g'ri o'qiladi.
Bu modul matnni odam o'qiydigan ko'rinishga keltiradi.

Zanjir:
  1. edge-tts (bepul, cheksiz) — Sardor (o'g'il) / Madina (qiz)
  2. Aisha (ixtiyoriy, pullik) — AISHA_API_KEY qo'shilsa ishlaydi

Kesh: bir marta yaratilgan ovoz Telegram file_id bilan saqlanadi.
"""
import os, re, io, hashlib

EDGE_OVOZ = {
    "ogil": "uz-UZ-SardorNeural",
    "qiz":  "uz-UZ-MadinaNeural",
    "en_ogil": "en-US-GuyNeural",
    "en_qiz":  "en-US-JennyNeural",
}

AISHA_KEY = os.getenv("AISHA_API_KEY", "")   # bo'sh bo'lsa ishlatilmaydi


# ═══════════════ RAQAM VA BELGILAR ═══════════════
BIRLIK = ["", "bir", "ikki", "uch", "to'rt", "besh",
          "olti", "yetti", "sakkiz", "to'qqiz"]
ONLIK  = ["", "o'n", "yigirma", "o'ttiz", "qirq", "ellik",
          "oltmish", "yetmish", "sakson", "to'qson"]
TARTIB = {
    "bir": "birinchi", "ikki": "ikkinchi", "uch": "uchinchi",
    "to'rt": "to'rtinchi", "besh": "beshinchi", "olti": "oltinchi",
    "yetti": "yettinchi", "sakkiz": "sakkizinchi", "to'qqiz": "to'qqizinchi",
    "o'n": "o'ninchi", "yigirma": "yigirmanchi", "o'ttiz": "o'ttizinchi",
    "qirq": "qirqinchi", "ellik": "ellikinchi", "oltmish": "oltmishinchi",
    "yetmish": "yetmishinchi", "sakson": "saksoninchi", "to'qson": "to'qsoninchi",
    "yuz": "yuzinchi", "ming": "minginchi",
}


def son_soz(n: int) -> str:
    """25 -> yigirma besh"""
    if n == 0: return "nol"
    if n < 0:  return "minus " + son_soz(-n)
    q = []
    if n >= 1000:
        m = n // 1000
        q.append("ming" if m == 1 else son_soz(m) + " ming"); n %= 1000
    if n >= 100:
        y = n // 100
        q.append("yuz" if y == 1 else BIRLIK[y] + " yuz"); n %= 100
    if n >= 10:
        q.append(ONLIK[n // 10]); n %= 10
    if n > 0:
        q.append(BIRLIK[n])
    return " ".join(x for x in q if x)


def tartib_son(n: int) -> str:
    """5 -> beshinchi"""
    s = son_soz(n).split()
    s[-1] = TARTIB.get(s[-1], s[-1] + "inchi")
    return " ".join(s)


MATH_MAP = [
    (r"\s*\+\s*", " qo'shuv "),
    (r"(?<=\d)\s*-\s*(?=\d)", " ayirish "),
    (r"\s*×\s*|\s*\*\s*", " ko'paytiruv "),
    (r"\s*÷\s*", " bo'linadi "),
    (r"\s*=\s*", " teng "),
    (r"\s*>\s*", " katta "),
    (r"\s*<\s*", " kichik "),
    (r"\s*%\s*", " foiz "),
    (r"\s*≈\s*", " taxminan "),
]

QISQARTMA = {"sm": "santimetr", "mm": "millimetr", "km": "kilometr",
             "kg": "kilogramm", "gr": "gramm", "min": "daqiqa"}


def _tozalash(m: str) -> str:
    """Emoji, HTML, markdown — ovozga kerak emas."""
    m = re.sub(r"<[^>]+>", " ", m)
    m = re.sub(r"[*_`#]+", "", m)
    m = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", " ", m)
    m = re.sub(r"https?://\S+", " havola ", m)
    return m


def _kasrlar(m: str) -> str:
    """1/2 -> ikkidan bir  (matematikadan OLDIN)"""
    def _k(x):
        a, b = int(x.group(1)), int(x.group(2))
        return f" {son_soz(b)}dan {son_soz(a)} "
    return re.sub(r"\b(\d{1,3})\s*/\s*(\d{1,3})\b", _k, m)


def _sonlar(m: str) -> str:
    # 5-sinf -> beshinchi sinf
    def _t(x): return f"{tartib_son(int(x.group(1)))} {x.group(2)}"
    m = re.sub(r"\b(\d{1,4})-(sinf|mashq|dars|savol|misol|bob|bet|mavzu|qism)\b",
               _t, m, flags=re.I)
    # 3,5 -> uch butun besh
    def _b(x): return f"{son_soz(int(x.group(1)))} butun {son_soz(int(x.group(2)))}"
    m = re.sub(r"\b(\d+)[,.](\d+)\b", _b, m)
    # 100 dan -> yuzdan  (tovush uyg'unligi)
    def _q(x):
        soz = son_soz(int(x.group(1))); qosh = x.group(2).lower()
        if soz[-1] in "kqptsxch" and qosh in ("gacha", "ga", "dan", "da"):
            qosh = {"gacha": "kacha", "ga": "ka", "dan": "tan", "da": "ta"}[qosh]
        return f"{soz}{qosh}"
    m = re.sub(r"\b(\d{1,6})\s*(dan|gacha|ta|ga|da|ni|dagi)\b", _q, m, flags=re.I)
    # qolgan sonlar
    def _o(x):
        n = int(x.group(0))
        return son_soz(n) if n < 1000000 else x.group(0)
    return re.sub(r"\b\d{1,6}\b", _o, m)


def _ritm(m: str) -> str:
    """Tabiiy nafas va ohang."""
    # Gap oxirida uzunroq pauza
    m = re.sub(r"([.!?])\s+", r"\1 … ", m)
    # Ikki nuqta — kutish ohangi
    m = m.replace(":", ": …")
    # Vergul — qisqa nafas (ovoz ba'zan o'tkazib yuboradi)
    m = re.sub(r",\s*", ", ", m)
    # Sanoq belgilari
    m = re.sub(r"\s*[•▪–—]\s*", " … ", m)
    # Qavs ichi — pasaytirilgan ohang uchun pauza
    m = re.sub(r"\s*\(\s*", " … ", m)
    m = re.sub(r"\s*\)\s*", " … ", m)
    return re.sub(r"\s{2,}", " ", m).strip()


def tayyorla(matn: str, kirillga=True) -> str:
    """Xom matn -> odam o'qiydigan matn.

    kirillga=True — lotinni kirillga o'giradi (ovoz aniqroq o'qiydi).
    """
    m = _tozalash(matn)
    m = _kasrlar(m)
    for naqsh, alm in MATH_MAP:
        m = re.sub(naqsh, alm, m)
    for q, t in QISQARTMA.items():
        m = re.sub(rf"(?<=\d)\s*{re.escape(q)}\b", f" {t}", m, flags=re.I)
    m = _sonlar(m)
    m = _ritm(m)
    if kirillga:
        m = lotin_kirill(m)
    else:
        m = _apostrof(m)   # hech bo'lmasa apostrofni to'g'rilaymiz
    return m


# ═══════════════ APOSTROF VA HARFLAR ═══════════════
# O'zbek lotinida 2 xil belgi bor:
#   ʻ (U+02BB) — oʻ, gʻ harflarida
#   ʼ (U+02BC) — tutuq belgisi (aʼzo, sanʼat)
# Odamlar ikkalasini ham ' deb yozadi — ovoz chalkashadi.

def _apostrof(m: str) -> str:
    """Barcha apostrof turlarini to'g'ri Unicode belgiga keltiradi."""
    # Avval hammasini oddiy ' ga keltiramiz
    for x in ("\u2018", "\u2019", "\u02bb", "\u02bc", "\u0060", "\u00b4", "`"):
        m = m.replace(x, "'")
    # o' va g' -> maxsus belgi (harf qismi)
    m = re.sub(r"([oOgG])'", lambda x: x.group(1) + "\u02bb", m)
    # Qolgani — tutuq belgisi
    m = m.replace("'", "\u02bc")
    return m


# ═══════════════ LOTIN -> KIRILL ═══════════════
# Kirill o'zbekchada har harf bitta tovush. Ovoz aniq o'qiydi.

_KIRILL_KOP = [
    ("o\u02bb", "ў"), ("O\u02bb", "Ў"),
    ("g\u02bb", "ғ"), ("G\u02bb", "Ғ"),
    ("sh", "ш"), ("Sh", "Ш"), ("SH", "Ш"),
    ("ch", "ч"), ("Ch", "Ч"), ("CH", "Ч"),
    ("yo", "ё"), ("Yo", "Ё"), ("YO", "Ё"),
    ("yu", "ю"), ("Yu", "Ю"), ("YU", "Ю"),
    ("ya", "я"), ("Ya", "Я"), ("YA", "Я"),
    ("ts", "ц"), ("Ts", "Ц"),
]

_KIRILL_BIR = {
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г",
    "h": "ҳ", "i": "и", "j": "ж", "k": "к", "l": "л", "m": "м",
    "n": "н", "o": "о", "p": "п", "q": "қ", "r": "р", "s": "с",
    "t": "т", "u": "у", "v": "в", "x": "х", "y": "й", "z": "з",
    "c": "с", "w": "в",
    "A": "А", "B": "Б", "D": "Д", "E": "Е", "F": "Ф", "G": "Г",
    "H": "Ҳ", "I": "И", "J": "Ж", "K": "К", "L": "Л", "M": "М",
    "N": "Н", "O": "О", "P": "П", "Q": "Қ", "R": "Р", "S": "С",
    "T": "Т", "U": "У", "V": "В", "X": "Х", "Y": "Й", "Z": "З",
    "\u02bc": "ъ",   # tutuq belgisi
}


def lotin_kirill(m: str) -> str:
    """Lotin o'zbekchani kirillga o'giradi. Ovoz aniqroq o'qiydi."""
    m = _apostrof(m)
    # So'z boshidagi ye -> е  (yetti -> етти, yer -> ер)
    m = re.sub(r"\b[yY]e", lambda x: "Е" if x.group(0)[0] == "Y" else "е", m)
    for lot, kir in _KIRILL_KOP:
        m = m.replace(lot, kir)
    natija = []
    for i, ch in enumerate(m):
        # So'z boshidagi e -> э  (Elbek -> Элбек)
        if ch in "eE":
            oldingi = m[i-1] if i > 0 else " "
            if not oldingi.isalpha() and oldingi not in "ЁёЮюЯя":
                natija.append("э" if ch == "e" else "Э")
                continue
        natija.append(_KIRILL_BIR.get(ch, ch))
    return "".join(natija)


async def edge_ovoz(matn, jins="qiz", tezlik=0, balandlik=0):
    """edge-tts — bepul, cheksiz."""
    import edge_tts
    voice = EDGE_OVOZ.get(jins, EDGE_OVOZ["qiz"])
    buf = io.BytesIO()
    com = edge_tts.Communicate(matn, voice,
                               rate=f"{tezlik:+d}%", pitch=f"{balandlik:+d}Hz")
    async for c in com.stream():
        if c["type"] == "audio":
            buf.write(c["data"])
    return buf.getvalue()


def _sozlama(yosh):
    """Yoshga qarab tezlik va ohang."""
    if yosh <= 8:    return -14, 12   # sekin, baland — bolalar uchun jonli
    if yosh <= 11:   return -8, 7
    if yosh <= 14:   return -3, 3
    return 0, 0


def _bolakla(matn, uzunlik=1500):
    """Gaplarni buzmasdan bo'laklaydi."""
    if len(matn) <= uzunlik:
        return [matn]
    gaplar = re.split(r"(?<=[.!?])\s+", matn)
    bolaklar, joriy = [], ""
    for g in gaplar:
        if len(joriy) + len(g) + 1 <= uzunlik:
            joriy = (joriy + " " + g).strip()
        else:
            if joriy: bolaklar.append(joriy)
            joriy = g[:uzunlik]
    if joriy: bolaklar.append(joriy)
    return bolaklar


async def ovoz_yarat(matn, jins="qiz", yosh=10, tayyorlansinmi=True, kirillga=True):
    """Matndan mp3 bayt. BEPUL.

    jins:     'qiz' | 'ogil'
    yosh:     tezlik va ohangni belgilaydi
    kirillga: True -> lotin kirillga o'giriladi (o', g' to'g'ri o'qiladi)
    """
    if tayyorlansinmi:
        matn = tayyorla(matn, kirillga=kirillga)
    if not matn.strip():
        return b""

    tezlik, balandlik = _sozlama(yosh)
    natija = io.BytesIO()
    for b in _bolakla(matn):
        try:
            audio = await edge_ovoz(b, jins, tezlik, balandlik)
            if audio: natija.write(audio)
        except Exception as e:
            print(f"[ovoz] {e}")
    return natija.getvalue()


async def ovoz_ikki_tilli(matn, jins="qiz", yosh=10, kirillga=True):
    """[en]hello[/en] bo'laklar inglizcha o'qiladi."""
    import edge_tts
    tezlik, balandlik = _sozlama(yosh)
    qismlar = re.split(r"(\[en\].*?\[/en\])", matn, flags=re.S)
    natija = io.BytesIO()
    for q in qismlar:
        if not q.strip(): continue
        if q.startswith("[en]"):
            ichi = q[4:-5].strip()
            voice = EDGE_OVOZ["en_qiz" if jins == "qiz" else "en_ogil"]
            tayyor = _tozalash(ichi)
        else:
            voice = EDGE_OVOZ.get(jins, EDGE_OVOZ["qiz"])
            tayyor = tayyorla(q, kirillga=kirillga)
        if not tayyor.strip(): continue
        com = edge_tts.Communicate(tayyor, voice,
                                   rate=f"{tezlik:+d}%", pitch=f"{balandlik:+d}Hz")
        async for c in com.stream():
            if c["type"] == "audio":
                natija.write(c["data"])
    return natija.getvalue()


# ═══════════════ KESH ═══════════════

def _hash(matn, jins, yosh):
    return hashlib.md5(f"{jins}|{yosh}|{matn}".encode()).hexdigest()


def kesh_ol(db_conn, matn, jins="qiz", yosh=10):
    """Saqlangan Telegram file_id (bo'lmasa None)."""
    try:
        cur = db_conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS ovoz_kesh(
            hash TEXT PRIMARY KEY, file_id TEXT, yaratilgan TIMESTAMP DEFAULT NOW())""")
        db_conn.commit()
        cur.execute("SELECT file_id FROM ovoz_kesh WHERE hash=%s", (_hash(matn, jins, yosh),))
        r = cur.fetchone(); cur.close()
        return r[0] if r else None
    except Exception as e:
        print(f"[ovoz_kesh] {e}")
        return None


def kesh_saqla(db_conn, matn, file_id, jins="qiz", yosh=10):
    try:
        cur = db_conn.cursor()
        cur.execute("""INSERT INTO ovoz_kesh(hash,file_id) VALUES(%s,%s)
            ON CONFLICT(hash) DO UPDATE SET file_id=EXCLUDED.file_id""",
            (_hash(matn, jins, yosh), file_id))
        db_conn.commit(); cur.close()
    except Exception as e:
        print(f"[ovoz_kesh] saqlash: {e}")


# ═══════════════ SINOV ═══════════════
if __name__ == "__main__":
    for s in ["5-sinf o'quvchilari uchun 3-mashq.",
              "2 + 3 = 5, kvadrat tomoni 12 sm",
              "100 dan 250 gacha sanang!",
              "To'g'ri javob: to'qqiz. San'at va a'zo.",
              "O'zbekiston Respublikasi bug'doy yetishtiradi."]:
        print(f"XOM    : {s}")
        print(f"KIRILL : {tayyorla(s)}")
        print(f"LOTIN  : {tayyorla(s, kirillga=False)}\n")


# ═══════════════ SOLISHTIRISH (admin uchun) ═══════════════

async def sinov_ovozlari(matn, yosh=10):
    """4 xil variantni qaytaradi — qaysi biri yaxshiroq eshitiladi?

    Qaytaradi: [(nom, audio_bytes), ...]
    """
    variantlar = []
    for jins in ("qiz", "ogil"):
        for kir in (True, False):
            nom = f"{'👧 Qiz' if jins=='qiz' else '👦 Ogil'} · {'Kirill' if kir else 'Lotin'}"
            try:
                a = await ovoz_yarat(matn, jins=jins, yosh=yosh, kirillga=kir)
                if a: variantlar.append((nom, a))
            except Exception as e:
                print(f"[sinov] {nom}: {e}")
    return variantlar
