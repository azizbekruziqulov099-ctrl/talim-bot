from topic_info import get_topic_info


def build_prompt(topic_code, difficulty, situation, question_type):

    info = get_topic_info(topic_code)

    if not info:
        return None

    grade, subject, bob, bolim, mavzu, kichik = info

    prompt = f"""
Siz tajribali test tuzuvchisiz.

Sinf: {grade}
Fan: {subject}

Bob: {bob}
Bo'lim: {bolim}
Mavzu: {mavzu}
Kichik mavzu: {kichik}

Qiyinlik: {difficulty}
Vaziyat: {situation}
Test turi: {question_type}

MUHIM:

1. Savol tili fan tilidan chiqib ketmasin.
2. Mavzudan chetga chiqma.
3. Mantiqsiz yoki mavzuga aloqasiz savol yaratma.
4. Avval yaratilgan savolni takrorlama.
5. Javob variantlari qisqa bo'lsin (2-5 so'z).
6. To'g'ri javobni option matni bilan qaytar:
   Masalan:
   "correct_answer":"40"

Test turi qat'iy:
- single_choice → 4 variant, 1 ta to'g'ri javob
- multiple_choice → 4 variant, 2 yoki undan ko'p to'g'ri javob
- true_false → To'g'ri/Noto'g'ri
- write_answer → variantsiz, o'quvchi yozadi
- image_question → image_prompt to'ldiriladi

Hayotiy darajalar:

0 = oddiy
1 = sodda hayotiy vaziyat
2 = o'rtacha hayotiy vaziyat
3 = murakkab hayotiy vaziyat
4 = ko'p bosqichli hayotiy vaziyat

Agar rasm kerak bo'lsa:
"is_latex": false
"image_prompt" ni to'ldir.

Agar formula bo'lsa:
"is_latex": true

Ovozli topshiriq kerak bo'lsa:
audio_text maydoniga o'qilishi kerak bo'lgan matnni yoz.

Faqat JSON qaytar.

{{
  "question_type":"",
  "is_latex":false,
  "image_prompt":"",
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
