from topic_info import get_topic_info


def build_prompt(topic_code, difficulty, situation):

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

Test turi quyidagilardan biri bo'lsin:

1. single_choice
   - 4 ta variant
   - 1 ta to'g'ri javob

2. multiple_choice
   - 4 ta variant
   - 2 yoki undan ko'p to'g'ri javob

3. write_answer
   - variantlarsiz
   - o'quvchi javobni o'zi yozadi

4. image_question
   - savol uchun rasm kerak bo'lsa
   - image_prompt maydonini to'ldir

5. true_false
   - To'g'ri / Noto'g'ri

Agar matematik formula kerak bo'lsa:
"is_latex": true

Agar rasm kerak bo'lsa:
"question_type": "image_question"

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
