from topic_info import get_topic_info


def build_prompt(topic_code, difficulty, situation, question_type, skill):

    info = get_topic_info(topic_code)

    if not info:
        return None

    grade, subject, bob, bolim, mavzu, kichik = info

    prompt = f"""
    Siz professional pedagog, metodist va test tuzuvchisiz.

    SINF: {grade}
    FAN: {subject}

    BOB: {bob}
    BO'LIM: {bolim}
    MAVZU: {mavzu}
    KICHIK MAVZU: {kichik}

    QIYINLIK: {difficulty}
    VAZIYAT: {situation}

    TEST_TURI: {question_type}
    SKILL: {skill}

    MUHIM

    SKILL TESTNING ASOSIY MAQSADI HISOBLANADI.

    Savol avvalo SKILL ni tekshirishi shart.

    Agar savol SKILL ni tekshirmasa,
    savol yaroqsiz hisoblanadi.

    MAVZU yordamchi ma'lumot.

    SKILL har doim MAVZUDAN USTUN.

    Masalan:

    skill = ranglarni_guruhlash

    Ruxsat:
    - ranglarni ajratish
    - ranglarni solishtirish
    - bir xil ranglarni topish
    - ranglarni guruhlarga bo'lish

    Taqiqlanadi:
    - qo'shish
    - ayirish
    - ko'paytirish
    - bo'lish
    - skillga aloqasiz savollar

    Savol aynan skillni tekshirsin.

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
