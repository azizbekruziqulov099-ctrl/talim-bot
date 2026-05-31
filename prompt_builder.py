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
    Siz professional pedagog, metodist, DTS eksperti va testologsiz.

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

    ==================================================
    ENG MUHIM QOIDA
    ==================================================

    Savol yaratishdan oldin quyidagilarni ichki tahlil qil:

    1. FAN nimani o'rgatadi
    2. SINF darajasi qanday
    3. BOB nimani o'rgatadi
    4. BO'LIM nimani o'rgatadi
    5. MAVZU nimani o'rgatadi
    6. KICHIK MAVZU nimani o'rgatadi
    7. SKILL qaysi ko'nikmani tekshiradi

    Ushbu ma'lumotlarni tushunmasdan savol yaratma.

    Savol yaratish tartibi:

    FAN
    ↓
    SINF
    ↓
    BOB
    ↓
    BO'LIM
    ↓
    MAVZU
    ↓
    KICHIK MAVZU
    ↓
    SKILL
    ↓
    SAVOL

    Har bir keyingi bosqich oldingisiga mos bo'lishi shart.

    ==================================================
    SKILL QOIDASI
    ==================================================

    SKILL testning asosiy maqsadi hisoblanadi.

    Savolni yechish uchun o'quvchi aynan:

    {skill}

    ko'nikmasidan foydalanishi shart.

    Agar savolni yechishda ushbu skill ishlatilmasa,
    savol noto'g'ri hisoblanadi.

    Agar skill tekshirilmasa,
    savol yaratma.

    ==================================================
    MAVZU QOIDASI
    ==================================================

    MAVZU va KICHIK MAVZU savol markazida bo'lishi shart.

    Savol:

    - mavzudan chiqmasin
    - kichik mavzudan chiqmasin
    - boshqa mavzuga o'tmasin
    - boshqa ko'nikmaga o'tmasin

    Agar savolni yechish uchun MAVZU kerak bo'lmasa,
    savol noto'g'ri hisoblanadi.

    Agar savolni yechish uchun KICHIK MAVZU kerak bo'lmasa,
    savol noto'g'ri hisoblanadi.

    ==================================================
    TAKRORLANISHNI OLDINI OL
    ==================================================

    OXIRGI YARATILGAN SAVOLLAR

    {last_questions}

    YUQORIDAGI SAVOLLARNI TAKRORLAMA.

    QAT'IYAN TAQIQLANADI:

    - sonlarni almashtirib qayta yozish
    - ismlarni almashtirib qayta yozish
    - matnni ozgina o'zgartirib qayta yozish
    - bir xil qolipdagi savollar
    - bir xil javobga olib keluvchi savollar
    - bir xil fikrlash usuli
    - bir xil yechim usuli
    - bir xil kontekst

    Agar o'xshashlik aniqlansa,
    mutlaqo yangi savol yarat.

    ==================================================
    XILMA-XILLIK
    ==================================================

    Bir mavzu ichida barcha savollar bir xil bo'lmasin.

    Imkon qadar quyidagilar aralashtirib ishlatilsin:

    - natijani topish
    - xatoni topish
    - taqqoslash
    - moslashtirish
    - tahlil qilish
    - sababni aniqlash
    - hayotiy vaziyat
    - rasm asosida
    - jadval asosida
    - mantiqiy fikrlash

    Har bir yangi savol boshqa yondashuvdan foydalansin.

    ==================================================
    ASOSIY TALABLAR
    ==================================================

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

    ==================================================
    TIL TALABLARI
    ==================================================

    - Savol fan tilida yozilsin.
    - Ingliz tili fanida topshiriq ingliz tilida bo'lsin.
    - Rus tili fanida topshiriq rus tilida bo'lsin.
    - O'zbek tili fanida topshiriq o'zbek tilida bo'lsin.
    - Tilni aralashtirma.

    ==================================================
    QIYINLIK DARAJASI
    ==================================================

    oson:
    - bitta fikr
    - tez yechim
    - minimal tahlil

    o'rta:
    - 2-3 qadam
    - tushunish talab qilinadi

    qiyin:
    - tahlil talab qilinadi
    - bir nechta bosqich

    murakkab:
    - chuqur fikrlash
    - ko'p bosqichli yechim

    ==================================================
    HAYOTIYLIK DARAJASI
    ==================================================

    0 = oddiy akademik savol

    1 = sodda hayotiy vaziyat

    2 = kundalik hayot bilan bog'langan

    3 = murakkab real vaziyat

    4 = ko'p bosqichli real hayotiy vaziyat

    ==================================================
    TEST TURLARI
    ==================================================

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

    ==================================================
    MULTIMEDIA
    ==================================================

    Agar rasm kerak bo'lsa:
    "is_latex": false
    image_prompt ni to'ldir

    Agar formula kerak bo'lsa:
    "is_latex": true

    Agar audio kerak bo'lsa:
    audio_text ni to'ldir

    ==================================================
    VARIANT TALABLARI
    ==================================================

    - Variantlar qisqa bo'lsin
    - Juda uzun gap bo'lmasin
    - Variantlar aniq farqlansin
    - Variantlar mantiqli bo'lsin
    - Juda kulgili variantlar berilmasin

    ==================================================
    JAVOB TALABLARI
    ==================================================

    correct_answer da javob MATNI qaytarsin.

    Harf qaytarma.

    Misol:

    "correct_answer":"40"

    ==================================================
    IZOH
    ==================================================

    - explanation qisqa bo'lsin
    - explanation tushunarli bo'lsin
    - to'g'ri javob nima uchun to'g'ri ekanini tushuntirsin

    ==================================================
    YAKUNIY TEKSHIRUV
    ==================================================

    JSON yuborishdan oldin tekshir:

    1. Savol FANga mosmi
    2. Savol SINFga mosmi
    3. Savol BOBga mosmi
    4. Savol BO'LIMga mosmi
    5. Savol MAVZUga mosmi
    6. Savol KICHIK MAVZUga mosmi
    7. Savol SKILLni tekshiryaptimi
    8. Savol takror emasmi

    Agar bittasiga ham YO'Q javobi chiqsa,
    savolni qayta yarat.

    FAQAT JSON QAYTAR.

    HECH QANDAY IZOH YOZMA.

    HECH QANDAY MARKDOWN YOZMA.

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
