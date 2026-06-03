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

    VAZIFA:
    FAN, SINF, MAVZU va KICHIK MAVZU asosida sifatli, pedagogik jihatdan to'g'ri va takrorlanmaydigan test yarating.

    KIRISH MA'LUMOTLARI

    SINF: {grade}
    FAN: {subject}
    BOB: {bob}
    BO'LIM: {bolim}
    MAVZU: {mavzu}
    KICHIK MAVZU: {kichik}

    QIYINLIK: {difficulty}
    VAZIYAT: {situation}
    TEST_TURI: {question_type}

    ==================================================
    TAHLIL KETMA-KETLIGI

    Savol yaratishdan oldin:

    1. FANni tahlil qil
    2. MAVZUni tahlil qil
    3. KICHIK MAVZUni tahlil qil
    4. SINF va YOSHni tahlil qil
    5. QIYINLIK va HAYOTIYLIK darajasini tahlil qil

    Shundan keyingina savol yarat.

    ==================================================
    YOSHGA MOSLASHUV

    1-sinf:

    - juda qisqa
    - 2-8 so'z
    - 1 amal yoki 1 fikr

    2-sinf:

    - 3-12 so'z
    - 1-2 qadam

    3-4 sinf:

    - qisqa
    - sodda hayotiy vaziyat

    5-6 sinf:

    - tushunish va taqqoslash

    7-8 sinf:

    - tahliliy fikrlash

    9-sinf:

    - sabab-oqibat

    10-sinf:

    - murakkab bog'lanishlar

    11-sinf:

    - tanqidiy fikrlash
    - real hayot bilan integratsiya

    ==================================================
    FAN USTUVOR

    Savol faqat FAN doirasida bo'lsin.

    Agar FAN matematika bo'lsa:
    faqat matematik ko'nikmalar tekshirilsin.

    Agar FAN tarix bo'lsa:
    faqat tarixiy bilim va tahlil tekshirilsin.

    Agar FAN biologiya bo'lsa:
    faqat biologik bilimlar tekshirilsin.

    Agar FAN ingliz tili bo'lsa:
    faqat ingliz tili ko'nikmalari tekshirilsin.

    Boshqa fan bilimini talab qilma.

    ==================================================
    TAKRORLANISHNI OLDINI OLISH

    OXIRGI SAVOLLAR:

    {last_questions}

    Ularni tahlil qil.

    Quyidagilar YANGI SAVOL hisoblanmaydi:

    - sonlarni almashtirish
    - ismlarni almashtirish
    - obyektlarni almashtirish
    - gapni boshqacha yozish

    Masalan:

    6+25=?

    6 va 25 ni qo'shing

    6 ta olma va 25 ta olma

    6 ta qalam va 25 ta qalam

    Bularning barchasi bir xil savol hisoblanadi.

    Agar yechim usuli bir xil bo'lsa,
    savol ham bir xil hisoblanadi.

    ==================================================
    YANGI SAVOL TALABI

    Har yangi savolda kamida bittasi o'zgarsin:

    - fikrlash usuli
    - pedagogik maqsad
    - kontekst
    - yechim strategiyasi

    ==================================================
    O'ZINI TEKSHIRISH

    Savol yaratilgach tekshir:

    1. Mavzuga mosmi?
    2. Kichik mavzuga mosmi?
    3. Yoshga mosmi?
    4. Oldingi savollarga mazmunan o'xshaydimi?

    Agar bittasiga ham YO'Q javobi chiqsa,
    savolni qayta yarat.

    ==================================================
    TEST TURLARI

    single_choice:

    - 4 variant
    - 1 to'g'ri javob

    multiple_choice:

    - 4 variant
    - kamida 2 to'g'ri javob

    true_false:

    - To'g'ri / Noto'g'ri

    write_answer:

    - variantsiz

    image_question:

    - image_prompt majburiy
    - rasmga qaramasdan javob topib bo'lmasin

    ==================================================
    JAVOB FORMATI

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
