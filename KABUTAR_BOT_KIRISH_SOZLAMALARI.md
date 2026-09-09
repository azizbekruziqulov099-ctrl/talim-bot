# Kabutar bot orqali saytga kirish — REV31

Almashtiriladigan fayllar: `Talim.py`, `cb_kabinet.py`.
Yangi fayl: `kabutar_web_auth.py`.
Tekshiruv: `python -m unittest discover -s tests -p 'test_kabutar_web_auth.py' -v`.

## Bot servisidagi Railway Variables

| Nomi | Qiymati |
|---|---|
| `KABUTAR_AUTH_API_URL` | Sayt backendining HTTPS manzili, masalan `https://sizning-backendingiz.up.railway.app`. Oxirida `/auth` yoki boshqa yo'l yozilmaydi. |
| `KABUTAR_BOT_AUTH_SECRET` | Backenddagi shu nomli qiymat bilan bir xil, tasodifiy kamida 32 belgili xizmat siri. Bot tokenining o'zi emas. |
| `KABUTAR_SITE_URL` | `https://talimkabutar.uz` |
| `DATABASE_URL` | Hozir bot foydalanayotgan PostgreSQL ulanishi; yangi hisob bazasi ochish shart emas. |

Mavjud bot tokeni o'zgartirilmaydi. Sirni GitHubga yoki frontend kodiga qo'ymang.
Backendda `KABUTAR_BOT_USERNAME` haqiqiy bot nomiga (`@`siz) sozlanadi.

## Ish tartibi

1. Sayt bir martalik, brauzerga bog'langan, 5 daqiqalik so'rov yaratadi.
2. `/start kb_...` havolasi botga olib keladi. Bot va saytda bir xil olti raqam ko'rinadi.
3. Foydalanuvchi belgilarni solishtirib, Telegramning o'z kontaktini ulashish tugmasini bosadi.
4. Faqat haqiqiy yuboruvchi IDsi bilan mos keladigan, uzatilmagan kontakt qabul qilinadi.
5. Foydalanuvchi «Ha, shu brauzerda kiraman»ni bosadi.
6. Bot backendga xizmat siri bilan tasdiq yuboradi. Sessiyani faqat boshlang'ich brauzer oladi.
7. Botda tanlangan bola yoki boshqa virtual profil telefon egasining identifikatori sifatida yuborilmaydi.

Bu SMS xizmati emas. Telegram bot foydalanuvchining o'zi botni ochganidan keyin ishlaydi.
Google orqali ochilgan hisobga Telegramni biriktirish foydalanuvchi o'sha hisobga kirgan holda boshlanadi.
Hisoblar avtomatik ko'chirilmaydi yoki birlashtirilmaydi; ziddiyat bo'lsa so'rov rad etiladi.

## Chiqish, uzilish va qayta urinish

Brauzer sessiyasi, chiqish va qayta kirish sayt backendida boshqariladi.
Bot holati PostgreSQLdagi `kabutar_bot_login_state`da qisqa muddat saqlanadi; bot qayta ishga tushsa so'rov yo'qolmaydi.
Jadval birinchi tegishli so'rovda avtomatik yaratiladi. Yakunlangan/bekor qilingan holat o'chiriladi; muddati o'tgan qatorlar keyingi so'rovlarda tozalanadi.
Ikki marta tugma bosilishi bir xil tasdiqni parallel yubormaydi. Server javobi kechiksa foydalanuvchidan sayt oynasini tekshirish so'raladi.

Bot va sayt yangi versiyalari birga o'rnatiladi. Faqat botni yangilash sayt kirishini o'zidan-o'zi ishga tushirmaydi.

## Tekshiruv chegarasi

Mahalliy testlar Telegram/API/PostgreSQL o'rnida boshqariladigan test obyektlari bilan ishlaydi.
Haqiqiy Telegram akkaunti, Railway servis sirlari va jonli ma'lumotlar bazasida kirish/chiqish sinovi bu muhitda bajarilmagan.
