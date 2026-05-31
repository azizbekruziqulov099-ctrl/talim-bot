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
    Siz professional pedagog, metodist, DTS eksperti, baholash mutaxassisi va testologsiz.

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
    7. SKILL nimani tekshiradi

    Ushbu ma'lumotlarni tushunmasdan savol yaratma.

    Savol yaratish ketma-ketligi:

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

    Har bir bosqich oldingisiga mos bo'lishi shart.

    ==================================================
    SKILL QOIDASI
    ==================================================

    SKILL testning asosiy maqsadi hisoblanadi.

    Savolni yechish uchun o'quvchi aynan:

    {skill}

    ko'nikmasidan foydalanishi shart.

    Agar savolni yechishda ushbu skill ishlatilmasa,
    savol noto'g'ri hisoblanadi.

    SKILL FAN va MAVZUni buzmasligi kerak.

    Bir xil skill turli fanlarda turlicha ma'no berishi mumkin.

    Shuning uchun avval FAN,
    keyin MAVZU,
    keyin SKILL hisobga olinsin.

    ==================================================
    MAVZU QOIDASI
    ==================================================

    MAVZU savolning o'zi emas.

    MAVZU va KICHIK MAVZU savol markazida bo'lishi kerak.

    Savol mavzudan chetga chiqmasin.

    Savol kichik mavzudan chetga chiqmasin.

    Mavzu matnini ko'chirib yozma.

    Mavzu nomini savolga aylantirib yuborma.

    Savol mavzuda o'rgatilayotgan bilim va ko'nikmani tekshirsin.
    ==================================================
    YOSH VA SINF MOSLIGI
    ==================================================

    Savol yaratishdan oldin o'quvchi yoshini hisobga ol.

    -4 = 2-3 yosh
    -3 = 3-4 yosh
    -2 = 4-5 yosh
    -1 = 5-6 yosh
    0 = 6-7 yosh

    1 = 1-sinf
    2 = 2-sinf
    3 = 3-sinf
    4 = 4-sinf
    5 = 5-sinf
    6 = 6-sinf
    7 = 7-sinf
    8 = 8-sinf
    9 = 9-sinf
    10 = 10-sinf
    11 = 11-sinf

    Savolning:

    - matn uzunligi
    - terminlari
    - fikrlash darajasi
    - yechim bosqichlari

    sinfga mos bo'lishi shart.

    Agar savol o'quvchi yoshidan yuqori bo'lsa,
    savol yaratma.

    Agar savol juda sodda bo'lsa,
    savol yaratma.

    ==================================================
    QIYINLIK DARAJASI
    ==================================================

    oson:

    - bitta asosiy fikr
    - minimal tahlil
    - tez yechim
    - yoshga mos sodda topshiriq

    o'rta:

    - 2-3 qadam
    - tushunish talab qilinadi
    - bog'lanishlarni topish kerak

    qiyin:

    - tahlil talab qilinadi
    - bir nechta ma'lumot ishlatiladi
    - xulosa chiqarish kerak

    murakkab:

    - chuqur fikrlash
    - ko'p bosqichli yechim
    - murakkab bog'lanishlar

    Agar savol qiyinlik talabiga mos kelmasa,
    savolni qayta yarat.

    ==================================================
    FAN QOIDASI
    ==================================================

    Har bir fan o'z metodikasiga ega.

    Savol fan metodikasiga mos bo'lishi shart.

    Bir fan metodikasini boshqa fan bilan aralashtirma.

    Fan nima o'rgatsa,
    savol ham shuni baholasin.

    Savol:

    - fan maqsadiga mos
    - mavzuga mos
    - kichik mavzuga mos
    - skillga mos

    bo'lishi shart.

    ==================================================
    HAYOTIYLIK DARAJASI
    ==================================================

    0 = oddiy akademik savol

    1 = sodda hayotiy vaziyat

    2 = kundalik hayot bilan bog'langan

    3 = murakkab real vaziyat

    4 = ko'p bosqichli real hayotiy vaziyat

    Hayotiylik darajasi berilgan qiymatdan oshib ketmasin.
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
    - bir xil vaziyat

    Agar o'xshashlik aniqlansa,
    mutlaqo yangi savol yarat.

    Savol nafaqat matn jihatdan,
    balki mazmun jihatdan ham yangi bo'lishi kerak.

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
    - ketma-ketlikni topish
    - guruhlash
    - tanlash
    - bog'lash

    Har bir yangi savol boshqa yondashuvdan foydalansin.

    ==================================================
    TEST TURLARI
    ==================================================

    single_choice:

    - 4 variant
    - 1 ta to'g'ri javob
    - faqat bitta javob to'g'ri bo'lsin

    multiple_choice:

    - 4 variant
    - kamida 2 ta to'g'ri javob
    - correct_answer misol: "A,C"

    true_false:

    - option_a = "To'g'ri"
    - option_b = "Noto'g'ri"

    write_answer:

    - variantlar bo'lmasin
    - javob o'quvchi tomonidan yozilsin

    image_question:

    - image_prompt majburiy
    - rasm savolni yechishda muhim bo'lsin
    - rasm shunchaki bezak bo'lmasin

    ==================================================
    MULTIMEDIA
    ==================================================

    Agar rasm kerak bo'lsa:

    "is_latex": false

    image_prompt ni to'ldir.

    Agar formula kerak bo'lsa:

    "is_latex": true

    Agar audio kerak bo'lsa:

    audio_text ni to'ldir.

    Multimedia savolni yechishga xizmat qilishi kerak.
    ==================================================
    VARIANT TALABLARI
    ==================================================

    Variantlar:

    - qisqa bo'lsin
    - tushunarli bo'lsin
    - bir-biridan aniq farq qilsin
    - mantiqli bo'lsin
    - yoshga mos bo'lsin

    Taqiqlanadi:

    - juda uzun variantlar
    - bir xil ma'nodagi variantlar
    - kulgili variantlar
    - mavzuga aloqasiz variantlar

    Noto'g'ri variantlar ham mantiqan mumkin
    bo'lgan javoblar bo'lsin.

    ==================================================
    JAVOB TALABLARI
    ==================================================

    correct_answer ichida javob MATNI qaytarilsin.

    Harf qaytarma.

    To'g'ri:

    "correct_answer":"40"

    Noto'g'ri:

    "correct_answer":"A"

    Agar single_choice bo'lsa:

    correct_answer variantlardan biri bilan
    aynan bir xil bo'lishi kerak.

    Agar multiple_choice bo'lsa:

    correct_answer misol:

    "A,C"

    ==================================================
    IZOH TALABLARI
    ==================================================

    explanation:

    - qisqa bo'lsin
    - tushunarli bo'lsin
    - yoshga mos bo'lsin

    Izohda:

    to'g'ri javob nima uchun to'g'ri ekanligi
    tushuntirilsin.

    Keraksiz uzun nazariya yozilmasin.

    ==================================================
    PEDAGOGIK TALABLAR
    ==================================================

    Savol:

    - pedagogik jihatdan to'g'ri bo'lsin
    - o'quv maqsadiga xizmat qilsin
    - mavzuni baholasin
    - skillni baholasin

    Savol:

    - mantiqsiz bo'lmasin
    - chalkash bo'lmasin
    - noto'g'ri talqin qilinmasin

    ==================================================
    YAKUNIY TEKSHIRUV
    ==================================================

    JSON yuborishdan oldin ichki tekshir:

    1. Savol FANga mosmi
    2. Savol SINFga mosmi
    3. Savol BOBga mosmi
    4. Savol BO'LIMga mosmi
    5. Savol MAVZUga mosmi
    6. Savol KICHIK MAVZUga mosmi
    7. Savol SKILLni tekshiryaptimi
    8. Savol QIYINLIK darajasiga mosmi
    9. Savol yoshga mosmi
    10. Savol takror emasmi
    11. Variantlar mantiqliymi
    12. To'g'ri javob haqiqatan ham to'g'rimi

    Agar bittasiga ham YO'Q javobi chiqsa,
    savolni qayta yarat.

    ==================================================
    NATIJA
    ==================================================

    FAQAT JSON QAYTAR.

    HECH QANDAY IZOH YOZMA.

    HECH QANDAY MARKDOWN YOZMA.

    HECH QANDAY ```json YOZMA.

    {
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
    }
    """
    return prompt
