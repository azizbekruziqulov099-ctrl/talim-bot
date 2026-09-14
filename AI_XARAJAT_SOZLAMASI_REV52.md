# OpenAI va Together xarajatini boshqarish

Botdagi OpenAI GPT, OpenAI rasm yaratish (DALL-E/GPT Image) va Together
chaqiruvlari endi odatda **o‘chirilgan**. `OPENAI_API_KEY` yoki
`TOGETHER_API_KEY` borligining o‘zi ularni ishga tushirmaydi.

Railway **BOT** xizmati → Variables:

```dotenv
ALLOW_PAID_AI=false
```

Bu sozlama bo‘lmasa ham `false` hisoblanadi. Bepul xizmatlardan foydalanish
niyatingiz uchun uni `false` holida qoldiring. `true` qilish pullik
OpenAI/Together so‘rovlariga ruxsat beradi; bu yangilash uni yoqmaydi.

Gemini yoki rasm provayderi javob bermasa, pullik OpenAI/Together zaxirasi
chaqirilmaydi. Formula o‘qishda mahalliy qoidalar ishlaydi. Faqat OpenAI bilan
ishlaydigan test generatori tushunarli xabar beradi; Word/Excel shablonini
qo‘lda to‘ldirish ishlashda davom etadi.

Saytdagi PPT yordamchisi uchun Groq/GPT-OSS integratsiyasi alohida **BACKEND**
xizmatida turadi: `PRESENTATION_AI_ENABLED`, `GROQ_API_KEY`. Gemini yoki
OpenAI kaliti Groq kalitining o‘rniga ishlamaydi. Kalitlarni kodga yoki
frontendga yozmang.

`ALLOW_PAID_AI` faqat botning OpenAI/Together chaqiruvlarini boshqaradi.
Gemini, Cloudflare, boshqa xizmatlar va Railway o‘z kvotasi hamda hisob
tarifiga ega. Shu sabab bu sozlama butun bot mutlaqo bepul ishlashini
kafolatlamaydi. Boshqa xizmatlar bu yangilashda o‘zgartirilmagan.

Tekshiruv: `python -m unittest discover -s tests -p 'test_paid_ai_policy.py' -v`
— 17 ta offline test. Kalit bor, lekin ruxsat yo‘q holatida tarmoq
chaqirilmasligi, aniq ruxsat bilan oldingi interfeys ishlashi va qo‘lda
shablon olish saqlanishi tekshirildi. Jonli AI chaqiruvi yuborilmadi.
