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

4 variantli test yarating.

Faqat JSON qaytaring.
"""

    return prompt
