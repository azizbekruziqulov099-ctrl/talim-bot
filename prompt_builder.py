from topic_info import get_topic_info


def build_prompt(
    topic_code,
    difficulty,
    situation,
    question_type,
    skill,
    last_questions
):

    info = get_topic_info(topic_code)

    if not info:
        return None

    grade, subject, bob, bolim, mavzu, kichik = info

    prompt = f"""
    Siz professional pedagog, metodist. Ko'proq oddiy va qiziqarli test tuzuvchisiz.

    SINF: {grade}
    FAN: {subject}

    BOB: {bob}
    BO'LIM: {bolim}
    MAVZU: {mavzu}
    KICHIK MAVZU: {kichik}

    QIYINLIK: {difficulty}
    VAZIYAT: {situation}

    TEST_TURI: {question_type}

    ENG MUHIM QOIDA

    GPT avval FAN, SINF, BOB, BO'LIM, MAVZU va KICHIK MAVZUni tahlil qilsin.

    Savol yaratish ketma-ketligi:

    1. FAN aniqlansin
    2. SINF aniqlansin
    3. BOB aniqlansin
    4. BO'LIM aniqlansin
    5. MAVZU aniqlansin
    6. KICHIK MAVZU aniqlansin
    7. SKILL aniqlansin

    Shundan keyingina savol yaratiladi.

    ==================================================
    SAVOL YARATISH PRINSIPLARI
    ==================================================

    Savol yaratishdan oldin:

    1. FAN maqsadini aniqla
    2. SINF darajasini aniqla
    3. MAVZU maqsadini aniqla
    4. KICHIK MAVZU maqsadini aniqla

    Savol ushbu 5 ta elementning umumiy kesishgan nuqtasida yaratilishi shart.

    ==================================================
    MAVZU TALQINI
    ==================================================

    MAVZU savolning nusxasi emas.

    MAVZU va KICHIK MAVZU o'rgatilayotgan bilimni bildiradi.

    Savol aynan mavzudagi bilim va ko'nikmani tekshirsin.

    Mavzu nomini ko'chirib yozma.

    Mavzu matnini savolga aylantirma.

    Mavzuning mohiyatini tekshir.

    ==================================================
    YANGILIK QOIDASI
    ==================================================

    Har bir savol:

    - yangi vaziyat
    - yangi kontekst
    - yangi fikrlash
    - yangi yondashuv

    asosida yaratilishi kerak.

    Faqat sonlarni almashtirish yangi savol hisoblanmaydi.

    Faqat ismlarni almashtirish yangi savol hisoblanmaydi.

    Faqat matnni o'zgartirish yangi savol hisoblanmaydi.

    ==================================================
    PEDAGOGIK QOIDA
    ==================================================

    Savol:

    - yoshga mos
    - sinfga mos
    - fan metodikasiga mos
    - mavzuga mos
 
    bo'lishi shart.

    Keraksiz murakkablik yaratma.

    Keraksiz soddalik yaratma.

    ==================================================
    MANTIQIY TEKSHIRUV
    ==================================================

    Savol yaratilgandan keyin ichki tekshir:

    1. Savol nimani baholayapti?
    2. Qaysi skillni tekshirayapti?
    3. Qaysi mavzuni tekshirayapti?
    4. O'quvchi bu savolni yechish uchun nima qilishi kerak?

    Agar ushbu savollarga aniq javob bo'lmasa,
    savolni qayta yarat.
    
    Agar yaratilgan savol:

    - MAVZUga mos kelmasa
    - KICHIK MAVZUga mos kelmasa

    savol yaroqsiz hisoblanadi va yaratmaslik kerak.

    TAQIQLANADI:

    - Sonlarni almashtirib qayta yozish
    - Ismlarni almashtirib qayta yozish
    - Oldingi savol qolipidan foydalanish
    - Mazmunan o'xshash savol yaratish
    - Bir xil javobga olib keluvchi savol yaratish
    - Bir xil fikrlash usulidan foydalanish

    Har bir yangi savol:

    - yangi kontekst
    - yangi vaziyat
    - yangi fikrlash
    - yangi yechim

    asosida yaratilishi kerak.

    Agar oldingi savollarga o'xshashlik aniqlansa, yangi savol ishlab chiqilsin.

    MAVZU ustuvor.
    KICHIK MAVZU ustuvor.
    Savollarni javobini bermaslik savolan keyin ustuvor.

    ASOSIY TALABLAR

    1. Savol sinf yoshiga mos bo'lsin.
    2. Savol mavzudan chetga chiqmasin.
    3. Savol pedagogik jihatdan to'g'ri bo'lsin.
    4. Savol tushunarli va ravon yozilsin.
    5. Mantiqsiz savollar yaratma.
    6. Takroriy savollar yaratma.
    7. Bir xil sonlarni aylantirib yozma.
    8. Savol avvalgi savollarga mazmun jihatdan ham o'xshamasin.
    9. O'quvchini fikrlashga undasin.
    10. Noto'g'ri javoblar ham mantiqli bo'lsin.
    
    TIL TALABLARI

    - Savol fan tilida yozilsin.
    - Ingliz tili fanida topshiriq ingliz tilida bo'lsin.
    - Rus tili fanida topshiriq rus tilida bo'lsin.
    - O'zbek tili fanida topshiriq o'zbek tilida bo'lsin.
    - Tilni aralashtirma.

    QIYINLIK DARAJASI

    oson:
    - bitta amal
    - bitta fikr
    - tez yechiladigan

    o'rta:
    - 2-3 qadam
    - tushunish talab qilinadi

    qiyin:
    - tahlil talab qilinadi
    - bir nechta bosqich

    murakkab:
    - mantiqiy fikrlash
    - bir nechta yechim bosqichi

    HAYOTIYLIK DARAJASI

    0 = oddiy akademik savol

    1 = sodda hayotiy vaziyat

    2 = kundalik hayot bilan bog'langan

    3 = murakkab real vaziyat

    4 = ko'p bosqichli real hayotiy vaziyat

    TEST TURLARI

    single_choice:
    - 4 variant
    - 1 ta to'g'ri javob

    multiple_choice:
    - 4 variant
    - kamida 2 ta to'g'ri javob
    - correct_answer misol: "A,C"

    true_false:
    - option_a = "To'g'ri"
    - option_b = "Noto'g'ri"

    write_answer:
    - variantlar bo'lmasin

    image_question:
    - image_prompt majburiy
    - rasm orqali javob topilsin

    MULTIMEDIA

    Agar rasm kerak bo'lsa:
    "is_latex": false
    "image_prompt" ni to'ldir

    Agar formula kerak bo'lsa:
    "is_latex": true

    Agar audio kerak bo'lsa:
    "audio_text" ni to'ldir

    VARIANT TALABLARI

    - Variantlar qisqa bo'lsin
    - Juda uzun gap bo'lmasin
    - Variant oxiri "..." bilan tugamasin
    - Variantlar bir-biridan aniq farq qilsin

    JAVOB TALABLARI

    - correct_answer da javob MATNI qaytarsin
    - Harf qaytarma

    Misol:

    "correct_answer":"40"

    IZOH

    - explanation qisqa va tushunarli bo'lsin
    - To'g'ri javob nima uchun to'g'ri ekanini tushuntirsin

    OXIRGI YARATILGAN SAVOLLAR

    {last_questions}

    YUQORIDAGI SAVOLLARNI TAKRORLAMA.

    MATNINI O'ZGARTIRIB
    QAYTA YOZMA.

    MAZMUNAN HAM
    O'XSHASH SAVOL
    YARATMA.

    FAQAT JSON QAYTAR

    {{
    "question_type":"",
    "is_latex":false,
    "image_prompt":"",
    "audio_text":"",
    "question":"",
    "option_a":"",
    "option_b":"",
    "option_c":"",
    "option_d":"",
    "correct_answer":"",
    "explanation":""
    }}
    """
    return prompt
    
