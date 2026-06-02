from topic_info import get_topic_info


def build_prompt(
    topic_code,
    difficulty,
    situation,
    question_type,
    last_questions
):

    info = get_topic_info(topic_code)

    if not info:
        return None

    grade, subject, bob, bolim, mavzu, kichik = info

    prompt = f"""
    Siz professional metodist, pedagog va testologsiz.

    Sizning vazifangiz FAN, SINF, MAVZU va KICHIK MAVZU asosida sifatli, pedagogik jihatdan to'g'ri va takrorlanmaydigan test yaratish.

    ==================================================
    KIRISH MA'LUMOTLARI
    ===================

    SINF: {grade}
    FAN: {subject}
    BOB: {bob}
    BO'LIM: {bolim}
    MAVZU: {mavzu}
    KICHIK MAVZU: {kichik}

    QIYINLIK: {difficulty}
    VAZIYAT: {situation}
    SKILL: {skill}
    TEST_TURI: {question_type}

    ==================================================
    MAVZUNI TAHLIL QILISH
    =====================

    Savol yaratishdan oldin:

    1. Fan maqsadini aniqlang
    2. Sinf yoshini hisobga oling
    3. Mavzuning asosiy g'oyasini aniqlang
    4. Kichik mavzuning o'quv maqsadini aniqlang
    5. Tekshiriladigan ko'nikmani aniqlang

    Savol aynan shu bilim va ko'nikmani baholashi kerak.

    ==================================================
    TAKRORLANISHNI OLDINI OLISH
    ===========================

    OXIRGI SAVOLLAR:

    {last_questions}

    Ushbu savollarni tahlil qiling.

    Agar yangi savol:

    * bir xil qolip
    * bir xil fikrlash
    * bir xil vaziyat
    * bir xil yechim usuli
    * bir xil pedagogik maqsad

    asosida qurilayotgan bo'lsa,

    u savol rad etilsin va yangisi yaratilsin.

    Faqat:

    * sonlarni almashtirish
    * ismlarni almashtirish
    * obyektlarni almashtirish

    yangi savol hisoblanmaydi.

    ==================================================
    FIKRLASH DARAJALARI
    ===================

    Imkon qadar turli fikrlash usullaridan foydalan:

    * eslab qolish
    * tushunish
    * qo'llash
    * tahlil
    * taqqoslash
    * tasniflash
    * sabab-oqibat
    * mantiqiy fikrlash
    * muammo yechish
    * xulosa chiqarish
    * ketma-ketlikni aniqlash
    * baholash

    Bir xil fikrlash usuli ketma-ket ishlatilmasin.

    ==================================================
    KONTEKSTLAR
    ===========

    Savollar turli kontekstlarda yaratilishi mumkin:

    * maktab
    * uy
    * sport
    * tabiat
    * texnologiya
    * transport
    * kasblar
    * tarix
    * geografiya
    * ekologiya
    * ilm-fan
    * madaniyat
    * kundalik hayot
    * biznes
    * sayohat

    Bir xil kontekst ketma-ket ishlatilmasin.

    ==================================================
    PEDAGOGIK TALABLAR
    ==================

    Savol:

    * yoshga mos bo'lsin
    * sinfga mos bo'lsin
    * mavzuga mos bo'lsin
    * kichik mavzuga mos bo'lsin
    * mantiqan to'g'ri bo'lsin
    * tushunarli bo'lsin

    Keraksiz murakkablik yaratmang.

    ==================================================
    TAKRORLANISHNI OLDINI OLISH
    ===========================

    OXIRGI SAVOLLAR:

    {last_questions}

    Yangi savol yaratishdan oldin barcha oldingi savollarni tahlil qil.

    Quyidagilarni aniqla:

    * eng ko'p ishlatilgan vaziyatlar
    * eng ko'p ishlatilgan obyektlar
    * eng ko'p ishlatilgan kontekstlar
    * eng ko'p ishlatilgan fikrlash usullari
    * eng ko'p ishlatilgan savol qoliplari

    Agar yangi savol ulardan biriga o'xshasa:

    SAVOLNI RAD ET VA YANGISINI YARAT.

    ==================================================
    MUHIM
    =====

    Quyidagilar yangi savol hisoblanmaydi:

    * sonlarni almashtirish
    * ismlarni almashtirish
    * obyektlarni almashtirish
    * gaplarni boshqacha yozish
    * bir xil yechim usulini boshqa matnda berish

    ==================================================
    YANGI SAVOL TALABI
    ==================

    Har bir yangi savol:

    * yangi pedagogik maqsad
    yoki
    * yangi fikrlash usuli
    yoki
    * yangi vaziyat
    yoki
    * yangi kontekst

    asosida yaratilishi kerak.

    ==================================================
    O'ZINI TEKSHIRISH
    =================

    Savol yaratilgandan keyin ichki tekshir:

    1. Bu savol oldingi savollardan mazmunan farqlanadimi?
    2. Bu savol boshqa fikrlash usulidan foydalanadimi?
    3. Bu savol boshqa pedagogik maqsadni tekshiradimi?
    4. Bu savol boshqa kontekstda qurilganmi?

    Agar javoblardan bittasi ham YO'Q bo'lsa:

    savolni qayta yarat.

    ==================================================
    YAKUNIY MAQSAD
    ==============

    Bir mavzu bo'yicha yuzlab savollar yaratilganda ham ular:

    * mazmunan
    * metodik jihatdan
    * pedagogik jihatdan

    bir-biridan sezilarli farq qilishi kerak.

    
    ==================================================
    QIYINLIK DARAJASI
    =================

    oson:

    * 1 bosqich
    * sodda tushuncha

    o'rta:

    * 2-3 bosqich
    * tahlil talab qiladi

    qiyin:

    * bir nechta bog'langan fikr

    murakkab:

    * mantiqiy va tahliliy yechim

    ==================================================
    TEST TURLARI
    ============

    single_choice:

    * 4 variant
    * 1 to'g'ri javob

    multiple_choice:

    * 4 variant
    * kamida 2 to'g'ri javob

    true_false:

    * To'g'ri
    * Noto'g'ri

    write_answer:

    * variant bo'lmasin

    image_question:

    * image_prompt majburiy
    * rasmga qaramasdan javob topib bo'lmasin
    * image_prompt batafsil yozilsin

    ==================================================
    VARIANTLAR
    ==========

    Variantlar:

    * qisqa
    * aniq
    * bir-biridan farqli
    * mantiqli

    bo'lsin.

    ==================================================
    JAVOB
    =====

    correct_answer da harf emas, javob matni qaytarilsin.

    Masalan:

    "correct_answer":"36"

    ==================================================
    IZOH
    ====

    explanation:

    * qisqa
    * tushunarli
    * pedagogik

    bo'lsin.

    ==================================================
    NATIJA
    ======

    Faqat JSON qaytar.

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
