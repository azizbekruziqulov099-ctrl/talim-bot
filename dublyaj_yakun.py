"""REV96: dublyajni yakunlash (ovoz yaratish → videoga ulash → yuborish) — Excel va AI tarjima yo'llari uchun umumiy."""
import asyncio
import os
import shutil

from aiogram.types import FSInputFile


async def yakunla(message, xabar, ctx, segmentlar_tarjima, db_mod, manba_izoh="sizning tarjimangiz"):
    """True — video yuborildi. Xato bo'lsa xabar matnida ko'rsatiladi."""
    papka = ctx["papka"]
    maqsad_til = ctx.get("maqsad_til", "en")
    jins = ctx.get("jins", "ayol")

    async def holat(matn):
        try:
            await xabar.edit_text(matn, parse_mode="HTML")
        except Exception:
            pass

    await holat(f"⏳ 2/3 — {db_mod.til_nomi(maqsad_til)} ovoz yaratilmoqda...\n<i>Har gap o'z vaqtiga moslanmoqda</i>")
    til = db_mod.TILLAR.get(maqsad_til, (None, None, None))
    ovoz = til[2] if jins == "ogil" else til[1]
    yangi_audio, xato = await db_mod.segmentlardan_ovoz_yigindisi(
        segmentlar_tarjima, ovoz, papka, ctx["jami_uzunlik"], dvigatel="edge",
        tezlik_moljal=ctx.get("tezlik_moljal", 1.0), asl_audio_yol=ctx.get("audio_yol"))
    if not yangi_audio:
        await holat(f"❌ Ovoz yaratilmadi:\n<code>{xato}</code>")
        return False
    await holat("⏳ 3/3 — Videoga ulanmoqda...")
    yakuniy = os.path.join(papka, "yakuniy.mp4")
    ok, xato = await asyncio.to_thread(db_mod.videoga_ulash, ctx["video_yol"], yangi_audio, yakuniy)
    if not ok:
        await holat(f"❌ Videoga ulanmadi:\n<code>{xato}</code>")
        return False
    matn = " ".join(s[2] for s in segmentlar_tarjima)
    try:
        await message.answer_video(FSInputFile(yakuniy),
                                   caption=f"🌐 {db_mod.til_nomi(maqsad_til)} tilida dublyaj qilindi\n"
                                           f"⏱ Har gap o'z vaqtida — {manba_izoh}\n\n📝 {matn[:200]}")
        try:
            await xabar.delete()
        except Exception:
            pass
        return True
    except Exception as e:
        await holat(f"❌ Yuborishda xato: {e}")
        return False
    finally:
        shutil.rmtree(papka, ignore_errors=True)
