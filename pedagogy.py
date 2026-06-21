"""
pedagogy.py — Pedagogik standartlar
Har sinf va fan uchun savol yozish qoidalari
"""

def get_pedagogy(grade, subject):
    """Sinf va fanga qarab pedagogik yo'riqnoma qaytaradi"""
    g = int(grade) if str(grade).isdigit() else 1
    subj = subject.upper()

    # Fan turi
    is_english = any(x in subj for x in ["INGLIZ", "ENGLISH"])
    is_russian = any(x in subj for x in ["RUS", "RUSSIAN"])
    is_math    = any(x in subj for x in ["MATEMA", "MATH"])
    is_native  = any(x in subj for x in ["ONA TILI", "UZBEK", "O'ZBEK"])
    is_science = any(x in subj for x in ["BIOLOGIYA", "KIMYO", "FIZIKA", "TABIIY"])
    is_history = any(x in subj for x in ["TARIX", "HISTORY", "GEOGRAFIYA"])
    is_it      = any(x in subj for x in ["INFORMATIKA", "IT", "TEXNOLOG"])

    # Yosh guruhi
    if g <= 2:
        age_note = f"{g}-sinf o'quvchisi ({6+g}-{7+g} yosh). Rasmli, o'ynoqi, qisqa savollar. Uzoq o'qish yo'q."
    elif g <= 4:
        age_note = f"{g}-sinf o'quvchisi ({g+5}-{g+6} yosh). Oddiy gaplar, kundalik hayot misollari."
    elif g <= 7:
        age_note = f"{g}-sinf o'quvchisi ({g+5}-{g+6} yosh). Mantiqiy fikrlash boshlanadi, tahlil qila oladi."
    elif g <= 9:
        age_note = f"{g}-sinf o'quvchisi ({g+5}-{g+6} yosh). Abstrakt tushunchalar, muammo hal qilish."
    else:
        age_note = f"{g}-sinf o'quvchisi ({g+5}-{g+6} yosh). Murakkab tahlil, ijodiy fikrlash, amaliy qo'llash."

    # Blooming darajalari
    if g <= 2:
        bloom = """DARAJALAR (Blooming taksonomiyasi, {g}-sinf):
- oson (BILISH): Rasmga qarab toping, ko'rsating, nomlang. 1 ta tushuncha.
- o'rta (TUSHUNISH): Jumlani to'ldiring, tarjima qiling. Oddiy misol.
- qiyin (QOLLASH): Qoidani qo'llang, moslashtiring. 2 ta tushuncha.
- murakkab (TAHLIL): Farqlang, solishtiring. Lekin HALI ham oddiy!""".format(g=g)
    elif g <= 4:
        bloom = """DARAJALAR (Blooming taksonomiyasi, {g}-sinf):
- oson (BILISH): Aniqlang, toping, eslang.
- o'rta (TUSHUNISH): Tushuntiring, misolda ko'rsating.
- qiyin (QOLLASH): Yangi vaziyatda qo'llang, hisoblang.
- murakkab (TAHLIL): Solishtiring, guruhlang, sabab-natija.""".format(g=g)
    elif g <= 7:
        bloom = """DARAJALAR (Blooming taksonomiyasi, {g}-sinf):
- oson (BILISH+TUSHUNISH): Eslang, tushuntiring.
- o'rta (QOLLASH): Qoidani yangi misolda qo'llang.
- qiyin (TAHLIL): Tahlil qiling, farqlang, tekshiring.
- murakkab (BAHOLASH): Baholang, tanqid qiling, asoslang.""".format(g=g)
    else:
        bloom = """DARAJALAR (Blooming taksonomiyasi, {g}-sinf):
- oson (BILISH): Asosiy bilimni eslang.
- o'rta (TUSHUNISH+QOLLASH): Tushuntiring, qo'llang.
- qiyin (TAHLIL+BAHOLASH): Tahlil, tanqid, asoslash.
- murakkab (YARATISH): Yangi yechim, ijodiy fikr.""".format(g=g)

    # Fan-specific qoidalar
    if is_english:
        if g <= 2:
            fan_note = """INGLIZ TILI (1-2 sinf) QOIDALARI:
- So'z boyligi: salomlashish, ranglar, sonlar, hayvonlar, maktab buyumlari
- Savol shakli: rasm asosida tanish, ko'rsatish, nomlash
- Grammatika: yo'q (faqat oddiy iboralar)
- Matn uzunligi: 3-5 so'z
- Hayotiy: maktab, uy, o'yin, do'stlar"""
        elif g <= 4:
            fan_note = """INGLIZ TILI (3-4 sinf) QOIDALARI:
- So'z boyligi: harakat fe'llari, sifatlar, vaqt, oila
- Savol shakli: jumlani to'ldirish, tarjima, moslashtirish
- Grammatika: Present Simple asoslari, to be
- Matn: 5-8 so'z
- Hayotiy: kundalik hayot, oila, maktab"""
        elif g <= 7:
            fan_note = """INGLIZ TILI (5-7 sinf) QOIDALARI:
- So'z boyligi: mavzuga oid atamalar, idiomalar
- Grammatika: Present/Past/Future, modal fe'llar
- Savol shakli: gap tuzish, matndan topish, qoida qo'llash
- Hayotiy: sayohat, kasb, texnologiya"""
        else:
            fan_note = """INGLIZ TILI (8-11 sinf) QOIDALARI:
- So'z boyligi: akademik leksika, atamalar
- Grammatika: murakkab zamonlar, Passive, Conditionals
- Savol shakli: matn tahlili, esse, gap o'zgartirish
- Hayotiy: ijtimoiy mavzular, ilm, san'at"""

    elif is_math:
        if g <= 2:
            fan_note = """MATEMATIKA (1-2 sinf) QOIDALARI:
- Mavzular: 1-100 ichida qo'shish/ayirish, geometrik shakllar, o'lchov
- Savol shakli: hisoblash, rasm asosida sanash, to'ldirish
- Kontekst: o'yinchoqlar, mevalar, bolalar
- Murakkablik: 1 amal (oson), 2 amal (o'rta), so'z masala (qiyin)"""
        elif g <= 5:
            fan_note = """MATEMATIKA (3-5 sinf) QOIDALARI:
- Mavzular: ko'paytirish/bo'lish, kasrlar, o'lchov birliklari
- Savol shakli: hisoblash, masala, formula qo'llash
- Kontekst: do'kon, maktab, sport, tabiat"""
        else:
            fan_note = """MATEMATIKA (6-11 sinf) QOIDALARI:
- Mavzular: algebra, geometriya, trigonometriya, statistika
- Savol shakli: hisoblash, isbotlash, grafik, masala
- Kontekst: fizika, iqtisodiyot, muhandislik"""

    elif is_native:
        fan_note = f"""{g}-sinf Ona tili QOIDALARI:
- Grammatika: so'z turkumlari, gap bo'laklari, imlo
- Savol: so'zning turini aniqlash, to'g'ri yozish, gap tuzish
- Kontekst: o'zbek hayoti, adabiyot, maqollar"""

    elif is_science:
        fan_note = f"""{g}-sinf Fan QOIDALARI:
- Nazariya + amaliy
- Rasm/jadval asosida tahlil
- Ilmiy atamalar o'zbekcha izohi bilan
- Hayotiy: tabiat, sog'liq, texnologiya"""

    elif is_history:
        fan_note = f"""{g}-sinf Tarix/Geografiya QOIDALARI:
- Sana, shaxs, joy, voqea
- Sabab-natija munosabati
- Xarita, jadval, rasm asosida
- O'zbek tarixi va madaniyati"""

    elif is_it:
        fan_note = f"""{g}-sinf Informatika QOIDALARI:
- Dasturlash asoslari, algoritm
- Kompyuter tuzilishi, internet
- Amaliy: fayl, dastur, kodlash
- Mantiqiy fikrlash"""

    else:
        fan_note = f"""{g}-sinf {subject} QOIDALARI:
- Mavzuning asosiy tushunchalarini qamrab ol
- Hayotiy misollar ishlat
- Rasmli savollar tavsiya etiladi"""

    # Teg qoidalari
    if is_english:
        if g <= 2:
            tag_rule = """TEG QOIDASI (1-2 sinf Ingliz tili):
OSON: O'zbek savol + 1 ingliz so'z teg bilan
  ✅ "Qaysi bola [en]tall[/en]?"
  ✅ "Bu [en]red[/en] rangmi?"
O'RTA: Aralash + ingliz so'z/ibora teg bilan  
  ✅ "Rasmda kim [en]smiling[/en]?"
  ✅ "Bu [en]a book[/en] yoki [en]a pen[/en]?"
QIYIN: Butun ingliz jumla 1 teg ichida
  ✅ "[en]What color is the ball?[/en]"
  ✅ "[en]Who is tall?[/en]"
MURAKKAB: Ingliz jumla + ingliz javoblar teg bilan
  ✅ Savol: "[en]What does she look like?[/en]"
  ✅ Javob: "[en]She is tall and thin.[/en]"

JAVOBLAR ham teg bilan:
  ✅ "[en]tall[/en]", "[en]short[/en]", "[en]red[/en]"
  
XATO (BUNDAY QILMA):
  ❌ "[en]What color[/en] is [en]the shirt[/en]?"
  ❌ O'zbek so'z teg ichida: "[en]baland[/en]" """
        else:
            tag_rule = f"""TEG QOIDASI ({g}-sinf Ingliz tili):
OSON: O'zbek savol, ingliz so'zlar teg bilan (10-20%)
O'RTA: Aralash, ingliz iboralar/jumlalar teg bilan (30-50%)
QIYIN: Ingliz savollar 1 teg ichida (60-70%)
MURAKKAB: Asosan ingliz teg bilan (80-90%)

QOIDA:
✅ Butun ingliz jumla = 1 ta teg: [en]Who has long hair?[/en]
✅ Ingliz javoblar teg bilan: [en]tall[/en], [en]brown hair[/en]
❌ Jumlani bo'lib teg qo'yma: [en]Who[/en] [en]has[/en] [en]hair[/en]?
❌ O'zbek so'z teg ichida bo'lmasin"""
    elif is_russian:
        tag_rule = f"""TEG QOIDASI ({g}-sinf Rus tili):
✅ Rus so'z/jumla: [en]so'z[/en] o'rniga [ru]so'z[/ru] ishlatiladi
✅ OSON: O'zbek savol + 1-2 rus so'z [ru]teg[/ru] bilan
✅ MURAKKAB: Butun rus jumla [ru]teg[/ru] ichida"""
    else:
        tag_rule = "Barcha savol va javoblar O'ZBEKCHA. Chet el atamalari bo'lsa izohi bilan."

    # Hayotiylik
    if g <= 2:
        life_note = "HAYOTIY KONTEKST: maktab, o'yinchoqlar, uy hayvonlari, mevalar, ranglar, bolalar o'rtasidagi muloqot."
    elif g <= 5:
        life_note = "HAYOTIY KONTEKST: maktab hayoti, oila, do'stlar, sport, tabiat, do'kon, transport."
    elif g <= 8:
        life_note = "HAYOTIY KONTEKST: ijtimoiy hayot, kasb-hunar, texnologiya, ekologiya, sayohat."
    else:
        life_note = "HAYOTIY KONTEKST: kasbiy yo'nalish, ijtimoiy muammolar, ilmiy-texnik taraqqiyot."

    return f"""{age_note}

{bloom}

{fan_note}

{tag_rule}

{life_note}"""


def get_tag_examples(grade, subject):
    """Teg ishlatishga aniq misollar"""
    g = int(grade) if str(grade).isdigit() else 1
    is_english = any(x in subject.upper() for x in ["INGLIZ", "ENGLISH"])

    if not is_english:
        return ""

    if g <= 2:
        return """ANIQ MISOLLAR:
Savol (oson): "Qaysi bola [en]tall[/en]?"
Javoblar: "[en]Tom[/en]" | "[en]Sam[/en]" | "[en]Lily[/en]" | "[en]Bob[/en]"
To'g'ri: "[en]Tom[/en]"

Savol (o'rta): "Bu rasmda kim [en]wearing a hat[/en]?"
Javoblar: "[en]the boy[/en]" | "[en]the girl[/en]" | "[en]the teacher[/en]" | "[en]the baby[/en]"

Savol (qiyin): "[en]What color is her hair?[/en]"
Javoblar: "[en]brown[/en]" | "[en]black[/en]" | "[en]blonde[/en]" | "[en]red[/en]"

Savol (murakkab): "[en]What does she look like?[/en]"
Javoblar: "[en]She is tall and thin.[/en]" | "[en]She is short and fat.[/en]" | ..."""
    else:
        return ""
