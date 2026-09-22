# Kabutar bot orqali saytga kirish — REV53

Bot kabinetidagi **«Kabutar saytiga kirish»** tugmasi yoki `/sayt` buyrug'i saytning Telegram kirish oynasini ochadi. `/kabutar` ham ishlaydi.
Eski xabarlardagi «Saytga ulanish kodi» va «Saytdan ulash» tugmalari ham shu yangi yo'lni ko'rsatadi. Eski kod orqali hisoblarni ko'chirish qayta yoqilmagan.

Almashtiriladigan fayllar: `Talim.py`, `kabutar_web_auth.py`, ushbu yo'riqnoma va `tests/test_kabutar_web_auth.py`.
Tekshiruv: `python -m unittest discover -s tests -p 'test_kabutar_web_auth.py' -v`.

## Bot servisidagi Railway Variables

| Nomi | Qiymati |
|---|---|
| `KABUTAR_AUTH_API_URL` | Sayt backendining HTTPS manzili, masalan `https://sizning-backendingiz.up.railway.app`. Oxirida `/auth` yoki boshqa yo'l yozilmaydi. |
| `KABUTAR_BOT_AUTH_SECRET` | Backenddagi shu nomli qiymat bilan bir xil, tasodifiy kamida 32 belgili xizmat siri. Bot tokenining o'zi emas. |
| `KABUTAR_SITE_URL` | `https://talimkabutar.uz` — foydalanuvchi kiradigan sayt manzili. Backenddagi ruxsat etilgan frontend manzillari orasida ham bo'lsin. |
| `KABUTAR_SITE_URLS` | Ixtiyoriy qo'shimcha frontend manzillari. Masalan `https://www.talimkabutar.uz,https://sizning-frontendingiz.up.railway.app`. Faqat o'zingiz boshqaradigan, backend `FRONTEND_URLS` ro'yxatida ham bor aniq HTTPS manzillarni yozing. `*`, yo'l va oxirgi vergul bo'lmasin. |
| `DATABASE_URL` | Hozir bot foydalanayotgan PostgreSQL ulanishi; yangi hisob bazasi ochish shart emas. |

Mavjud bot tokeni o'zgartirilmaydi. Sirni GitHubga yoki frontend kodiga qo'ymang.
Backendda `KABUTAR_BOT_USERNAME` haqiqiy bot nomiga (`@`siz) sozlanadi.
Backenddagi `FRONTEND_URL=https://talimkabutar.uz` va `FRONTEND_URLS` ichida shu manzil bo'lsin. `FRONTEND_URLS` bir nechta manzilni vergul bilan ajratib oladi; `https://www.talimkabutar.uz` boshqa origin hisoblanadi.
Bot uchun `KABUTAR_AUTH_API_URL` frontend saytga emas, **backend servisiga** qarashi kerak. Bot va backenddagi `KABUTAR_BOT_AUTH_SECRET` bir xil bo'lishi shart; Gemini/Groq kaliti bundan boshqa narsa.
`KABUTAR_SITE_URLS` bo'sh bo'lsa, bot faqat `KABUTAR_SITE_URL`ni qabul qiladi. `www` bilan kirish ishlashi uchun `https://www.talimkabutar.uz`ni qo'shimcha ro'yxatga aniq kiriting. Tugmalar har doim asosiy `KABUTAR_SITE_URL`ni ochadi.

REV53 backend yangi so'rovda kirishni boshlagan, ruxsat etilgan sayt manzilini saqlaydi. Shu sabab eski Railway manzili bilan yangi domen aralashib ketishi oldi olinadi. Bot begona sayt manzilini baribir rad etadi.

## Ish tartibi

1. Saytda «Telegram orqali kirish» bosiladi. Besh daqiqalik brauzer so‘rovi va bot havolasi ochiladi.
2. «Telegram botini ochish» bosiladi, botda Start orqali davom etiladi.
3. Foydalanuvchi o‘z telefon raqamini Telegram kontakt tugmasi bilan ulashadi.
4. Botda O‘quvchi, Talaba, O‘qituvchi yoki Ota-ona tanlanadi. Mavjud tasdiqlangan profil roli o‘zboshimchalik bilan almashtirilmaydi.
5. Bot saytga kirish uchun alohida 6 xonali bir martalik kod beradi.
6. Foydalanuvchi kirishni boshlagan brauzerga qaytadi va «Botdan olingan kod» maydoniga kodni yozadi.
7. To‘g‘ri kod va brauzer siri tekshirilgach, hisob shu rolda ochiladi. Besh xato urinishdan so‘ng yangi so‘rov kerak.
8. Profil → Telegramni ulash amali mavjud hisobni saqlaydigan avvalgi tasdiqlash tartibidan foydalanadi.

Saytdagi «So‘rov belgisi» kirish kodi emas. Kirish kodini faqat bot yuboradi.

Bu SMS xizmati emas. Telegram bot foydalanuvchining o'zi botni ochganidan keyin ishlaydi.
Google orqali ochilgan hisobga Telegramni biriktirish foydalanuvchi o'sha hisobga kirgan holda boshlanadi.
Hisoblar avtomatik ko'chirilmaydi yoki birlashtirilmaydi; ziddiyat bo'lsa so'rov rad etiladi.

Administrator bergan **muassasa paroli** bu Telegram tekshiruv belgisi emas. Avval saytga o'z hisobingiz bilan kirasiz, keyin sayt ichida «Muassasaga qo'shilish» bo'limida administrator bergan kod/parolni kiritasiz.

## Chiqish, uzilish va qayta urinish

Brauzer sessiyasi, chiqish va qayta kirish sayt backendida boshqariladi.
Bot holati PostgreSQLdagi `kabutar_bot_login_state`da qisqa muddat saqlanadi; bot qayta ishga tushsa so'rov yo'qolmaydi.
Jadval birinchi tegishli so'rovda avtomatik yaratiladi. Bir necha nusxa bir vaqtda ishga tushsa, PostgreSQL qulfidan foydalaniladi. Yakunlangan/bekor qilingan holat o'chiriladi; muddati o'tgan qatorlar keyingi so'rovlarda tozalanadi.
Ikki marta tugma bosilishi bir xil tasdiqni parallel yubormaydi. Server javobi kechiksa foydalanuvchidan sayt oynasini tekshirish so'raladi.

Bot va sayt yangi versiyalari birga o'rnatiladi. Faqat botni yangilash sayt kirishini o'zidan-o'zi ishga tushirmaydi.

## Sozlama yetishmasa

Bot ishga tushayotganda logda `Kabutar web login configuration needs checking:` yozuvi bilan faqat tekshirilishi kerak bo'lgan Variable nomlari chiqadi. Maxfiy qiymatlar logga yozilmaydi. Foydalanuvchiga ham bot orqali kirish hali sozlanmagani aniq ko'rsatiladi.

- `401`: bot va backend xizmat sirlari mos emas.
- `403`: so'rov/brauzer yoki sayt manzili mos emas; ikkala servisdagi domenni tekshiring.
- `404`: backend manzili yoki yangi auth fayllari tekshirilsin.
- `410`: 5 daqiqa o'tgan yoki so'rov bekor qilingan; saytda yangidan boshlang.
- `503`: backend/baza vaqtincha ishlamayapti yoki kirish sozlanmagan.

Bu kodlar taxminiy umumiy yo'nalish beradi; logdagi xabarga qarab tekshiring. Hech kimga Telegram akkauntingizning SMS kodini yubormang — Kabutar bunday kodni so'ramaydi.

## Tekshiruv chegarasi

Mahalliy testlar Telegram/API/PostgreSQL o'rnida boshqariladigan test obyektlari bilan ishlaydi.
Haqiqiy Telegram akkaunti, Railway servis sirlari va jonli ma'lumotlar bazasida kirish/chiqish sinovi bu muhitda bajarilmagan.
