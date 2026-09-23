# Telegram kirishi — Railway sozlamalari (REV60)

Rasmdagi `KABUTAR_AUTH_API_URL, KABUTAR_BOT_AUTH_SECRET` xabari **bot ishlayotgan jarayon** shu ikkala qiymatni yaroqli deb topmaganini bildiradi. API manzili bo‘sh yoki noto‘g‘ri formatda; maxfiy qiymat esa bo‘sh yoki 32 belgidan qisqa bo‘lishi mumkin. Variable backend xizmatida borligi botda ham borligini bildirmaydi.

## Aynan qayerga qo‘shiladi

Railway loyihasining `production` muhitida **Telegram bot ishlayotgan xizmatni** oching. Bu `python Talim.py` bilan ishga tushadigan xizmat. Uning `Variables` bo‘limiga quyidagi ikkita qiymatni qo‘shing.

Rasmingizdagi backend xizmatining nomi `talim_platformasi`; u shu Railway loyiha va muhitida bo‘lsa, quyidagi reference qiymatlarini ishlatish mumkin:

| Bot xizmatidagi Variable | Qiymat |
|---|---|
| `KABUTAR_AUTH_API_URL` | `https://${{talim_platformasi.RAILWAY_PUBLIC_DOMAIN}}` |
| `KABUTAR_BOT_AUTH_SECRET` | `${{talim_platformasi.KABUTAR_BOT_AUTH_SECRET}}` |

`RAILWAY_PUBLIC_DOMAIN` backendning `Settings → Networking` bo‘limida domen ulanganida taqdim etiladi. Agar reference topilmasa, birinchi qiymatga o‘sha bo‘limdagi **backendning haqiqiy HTTPS manzilini** yozing. Frontend sayti manzilini yoki oxiriga `/auth`, `/api`, `/docs` qo‘shilgan manzilni yozmang. Xizmatlar boshqa Railway loyiha yoki muhitida bo‘lsa, shu backend manzilini va uning bilan bir xil maxfiy qiymatni bot xizmatiga qo‘lda kiriting.

Backenddagi `KABUTAR_BOT_AUTH_SECRET` kamida **32 belgi** bo‘lsin. Reference botga aynan o‘sha qiymatni beradi. Bu foydalanuvchining kirish kodi ham, botning `BOT_TOKEN`i ham emas. Maxfiy qiymatni chatga yuborish talab qilinmaydi.

Keyin Railway’dagi kutilayotgan o‘zgarishlarni **Deploy** qiling. Yangi deployment `Active` bo‘lgach botda `/start` yuboring. Faqat Variables oynasida qator ko‘rinishi eski ishlayotgan jarayon yangi qiymatni olganini tasdiqlamaydi.

Botdagi mavjud `BOT_TOKEN` va `DATABASE_URL`ni saqlang. Backendda mavjud `KABUTAR_BOT_USERNAME` shu botni ko‘rsatsin. Sayt uchun `KABUTAR_SITE_URL=https://talimkabutar.uz`; qo‘shimcha domenlar bo‘lsa mavjud ruxsat ro‘yxatlari saqlanadi.

## Kutiladigan natija

`/start` → o‘z telefonini ulashish → o‘quvchi/talaba/o‘qituvchi/ota-ona tanlash → botdan olti xonali kod → saytda telefon va kodni kiritish. Eski Gmail hisobiga ulash uchun botdagi “Oldin Gmail bilan kirganman” tanlanadi, saytga qaytganda o‘sha Gmail orqali tasdiqlanadi. Hisoblar avtomatik birlashtirilmaydi.

Sozlama xatosi davom etsa, bot aytgan nomni **bot xizmatining yangi deploymentida** tekshiring. `401` chiqsa, bot va backenddagi maxfiy qiymatlar bir xil ekanini tekshiring; `404` bo‘lsa, backend manzili va o‘rnatilgan kirish versiyasi tekshiriladi. Kodni yangilash uchun `/sayt` ishlatiladi.

Railway’da Variablelar alohida xizmatga tegishli; boshqa xizmatning qiymati reference orqali ulanadi va o‘zgarishlar deploy bilan qo‘llanadi: [Railway rasmiy ko‘rsatmasi](https://docs.railway.com/variables).
