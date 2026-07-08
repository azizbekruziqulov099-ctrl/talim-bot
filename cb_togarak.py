"""cb_togarak.py"""
import psycopg2, asyncio, os
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from storage import user_state, admin_state, temp_user
DATABASE_URL = os.getenv("DATABASE_URL","")
def _get_db_conn():
    import psycopg2 as _p; return _p.connect(DATABASE_URL)
ADMINS = list(map(int, os.getenv("ADMINS","0").split(",")))
def render_text(t):
    if not t: return ""
    import re as _r
    t=str(t); t=_r.sub(r"\b(\d+)\.0\b",r"\1",t)
    t=_r.sub(r"\[en\](.*?)\[/en\]",r"_\1_",t,flags=_r.DOTALL)
    return t.strip()

async def handle_tg(call, user_id, admin_state, user_state, temp_user, bot):
    d=call.data
    # ══ TO'GARAK CALLBACKLAR ══
    if call.data == "tg_yangi":
        await call.answer()
        if user_id not in ADMINS:
            conn2=_get_db_conn();cur2=conn2.cursor()
            cur2.execute("SELECT COUNT(*) FROM togaraklar WHERE teacher_id=%s AND aktiv=TRUE",(user_id,))
            cnt2=(cur2.fetchone() or [0])[0]; cur2.close(); conn2.close()
            if cnt2 >= 1:
                await call.message.answer("❌ Siz allaqachon 1 ta to'garak ochgansiz!\n\nFaqat admin cheksiz to'garak ocha oladi."); return True
        user_state[user_id] = "tg_create_nomi"
        await call.message.answer("➕ Yangi to'garak\n\nTo'garak nomini yozing:")
        return True

    if call.data.startswith("tg_info:"):
        tgid=int(call.data[8:]); await call.answer()
        from togarak import get_togarak_azolar, get_teacher_togaraklar
        tgs = {t["id"]:t for t in get_teacher_togaraklar(user_id)}
        t = tgs.get(tgid)
        if not t: await call.message.answer("❌ Topilmadi"); return True
        azolar = get_togarak_azolar(tgid)
        # Parol yashirin — alohida ko'rish tugmasi
        txt = (f"📚 {t['nomi']}\n📖 Fan: {t['fan'] or '-'}\n"
               f"🆔 ID: {tgid}\n"
               f"👥 A'zolar: {len(azolar)}/{t['max'] or 25}\n"
               f"💰 Oylik: {t['oylik_summa'] or 0:,} so'm\n"
               f"📅 To'lov sanasi: har oyning {t['oylik_sana'] or 1}-kuni")
        conn3=_get_db_conn();cur3=conn3.cursor()
        cur3.execute("SELECT COUNT(*) FROM togarak_requests r JOIN togaraklar t ON t.id=r.togarak_id WHERE r.togarak_id=%s AND r.status='pending' AND t.teacher_id=%s",(tgid,user_id))
        pend_cnt=(cur3.fetchone() or [0])[0]; cur3.close(); conn3.close()
        pend_txt=f"📨 So'rovlar ({pend_cnt})" if pend_cnt else "📨 So'rovlar"
        kb2=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📅 Dars jadvali",callback_data=f"tg_reja:{tgid}:0")],
            [InlineKeyboardButton(text="👥 A'zolar",callback_data=f"tg_azolar:{tgid}"),
             InlineKeyboardButton(text="📋 Yoqlama",callback_data=f"tg_yoqlama:{tgid}")],
            [InlineKeyboardButton(text="📊 Statistika",callback_data=f"tg_stat:{tgid}"),
             InlineKeyboardButton(text=pend_txt,callback_data=f"tg_pending:{tgid}")],
            [InlineKeyboardButton(text="💬 Guruh chat",callback_data=f"tg_guruh_chat:{tgid}:0"),
             InlineKeyboardButton(text="📢 Xabar",callback_data=f"tg_msg_group:{tgid}")],
            [InlineKeyboardButton(text="⚙️ Sozlamalar",callback_data=f"tg_sozla:{tgid}"),
             InlineKeyboardButton(text="⬅️ Orqaga",callback_data="tg_back")],
        ])
        try: await call.message.edit_text(txt, reply_markup=kb2)
        except: await call.message.answer(txt, reply_markup=kb2)
        return True

    if call.data.startswith("tg_azolar:"):
        tgid=int(call.data[10:]); await call.answer()
        from togarak import get_togarak_azolar
        azolar = get_togarak_azolar(tgid)
        if not azolar:
            await call.message.answer("👥 Hali a'zo yo'q!"); return True
        txt = f"👥 A'zolar ({len(azolar)} ta):\n\n"
        rows2=[]
        for a in azolar:
            txt += f"• {a['ism']} — {a['sinf'] or '-'}\n"
            rows2.append([InlineKeyboardButton(
                text=f"❌ {a['ism'][:20]}",
                callback_data=f"tg_rm:{tgid}:{a['uid']}"
            )])
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"tg_info:{tgid}")])
        await call.message.answer(txt[:2000], reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_rm:"):
        parts2=call.data.split(":"); tgid,uid2=int(parts2[1]),int(parts2[2])
        await call.answer()
        from togarak import remove_azо, get_togarak_azolar
        if remove_azо(tgid,uid2,user_id):
            await call.answer("✅ O'chirildi",show_alert=True)
            # A'zolar ro'yhatini qayta ko'rsat
            azolar = get_togarak_azolar(tgid)
            txt = f"👥 A'zolar ({len(azolar)} ta):\n\n"
            rows2=[]
            for a in azolar:
                txt += f"• {a['ism']} — {a['sinf'] or '—'}\n"
                rows2.append([InlineKeyboardButton(text=f"❌ {a['ism'][:20]}",callback_data=f"tg_rm:{tgid}:{a['uid']}")])
            rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_info:{tgid}")])
            try: await call.message.edit_text(txt[:2000],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
            except: pass
        return True

    if (call.data.startswith("tg_yoqlama:") or call.data.startswith("tg_pick:")
        or call.data.startswith("tg_set:") or call.data.startswith("tg_kech:")
        or call.data.startswith("tg_kech_set:")):
        from togarak import save_yoqlama, get_yoqlama_bugun
        d=call.data

        # ═══ ISMNI BOSDI — tanlov oynasi ═══
        if d.startswith("tg_pick:"):
            p2=d[8:].split(":"); tgid=int(p2[0]); uid2=int(p2[1]); page=int(p2[2])
            await call.answer()
            conn2=_get_db_conn();cur2=conn2.cursor()
            cur2.execute("SELECT full_name FROM users WHERE user_id=%s",(uid2,))
            ism=(cur2.fetchone() or ["?"])[0]; cur2.close(); conn2.close()
            # Hozirgi holat
            hozir=None; izoh=None
            for a in get_yoqlama_bugun(tgid):
                if a["uid"]==uid2: hozir=a["holat"]; izoh=a.get("izoh"); break
            hs="✅ keldi" if hozir=="keldi" else ("🕐 "+(izoh or "kech") if hozir=="kech" else "❌ kelmadi")
            rows2=[
                [InlineKeyboardButton(text="✅ Keldi",callback_data=f"tg_set:{tgid}:{uid2}:keldi:{page}")],
                [InlineKeyboardButton(text="🕐 Kech qoldi",callback_data=f"tg_kech:{tgid}:{uid2}:{page}")],
                [InlineKeyboardButton(text="❌ Kelmadi",callback_data=f"tg_set:{tgid}:{uid2}:kelmadi:{page}")],
                [InlineKeyboardButton(text="⬅️ Ortga",callback_data=f"tg_yoqlama:{tgid}:{page}")],
            ]
            await call.message.edit_text(
                f"👤 <b>{ism}</b>\nHozir: {hs}\n\nHolatni tanlang:",
                parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
            return True

        elif d.startswith("tg_set:"):
            p2=d.split(":"); tgid=int(p2[1]); uid2=int(p2[2]); holat=p2[3]; page=int(p2[4])
            save_yoqlama(tgid,uid2,holat)
            await call.answer("✅ Keldi" if holat=="keldi" else "❌ Kelmadi")

        elif d.startswith("tg_kech_set:"):
            p2=d[12:].split(":"); tgid=int(p2[0]); uid2=int(p2[1]); dq=int(p2[2]); page=int(p2[3])
            if dq<60: izoh=f"{dq} daqiqa"
            elif dq==60: izoh="1 soat"
            else:
                s=dq//60; q=dq%60
                izoh=f"{s} soat" if q==0 else f"{s} soat {q} daqiqa"
            save_yoqlama(tgid,uid2,"kech",izoh)
            await call.answer(f"🕐 {izoh} kech")

        elif d.startswith("tg_kech:"):
            p2=d[8:].split(":"); tgid=int(p2[0]); uid2=int(p2[1]); page=int(p2[2])
            await call.answer()
            conn2=_get_db_conn();cur2=conn2.cursor()
            cur2.execute("SELECT full_name FROM users WHERE user_id=%s",(uid2,))
            ism=(cur2.fetchone() or ["?"])[0]; cur2.close(); conn2.close()
            daqiqalar=[5,10,15,20,30,45,60,90,120]
            rows2=[]; br=[]
            for dq in daqiqalar:
                if dq<60: lbl=f"{dq} daqiqa"
                elif dq==60: lbl="1 soat"
                else:
                    s=dq//60; q=dq%60
                    lbl=f"{s} soat" if q==0 else f"{s}s {q}daq"
                br.append(InlineKeyboardButton(text=lbl,callback_data=f"tg_kech_set:{tgid}:{uid2}:{dq}:{page}"))
                if len(br)==3: rows2.append(br); br=[]
            if br: rows2.append(br)
            rows2.append([InlineKeyboardButton(text="⬅️ Ortga",callback_data=f"tg_pick:{tgid}:{uid2}:{page}")])
            await call.message.edit_text(f"🕐 <b>{ism}</b> necha daqiqa kechikdi?",
                parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
            return True

        else:
            p2=d[11:].split(":"); tgid=int(p2[0]); page=int(p2[1]) if len(p2)>1 else 0
            await call.answer()
            # Birinchi kirish (sahifasiz) — bugun yo'qlama qilinganmi?
            if len(p2)==1:
                conn2=_get_db_conn();cur2=conn2.cursor()
                cur2.execute("SELECT COUNT(*) FROM togarak_yoqlama WHERE togarak_id=%s AND sana=CURRENT_DATE",(tgid,))
                bor=(cur2.fetchone() or [0])[0]; cur2.close(); conn2.close()
                if bor>0:
                    # Natijani ko'rsatamiz
                    from datetime import datetime
                    azolar=get_yoqlama_bugun(tgid)
                    bugun=datetime.now().strftime("%d.%m.%Y")
                    keldi=sum(1 for a in azolar if a["holat"]=="keldi")
                    kech=sum(1 for a in azolar if a["holat"]=="kech")
                    yoq=sum(1 for a in azolar if a["holat"]=="kelmadi")
                    txt=(f"📋 <b>Bugungi yo'qlama</b>\\n📅 {bugun}\\n"
                         f"━━━━━━━━━━━━━━━\\n"
                         f"✅ Keldi: {keldi}   🕐 Kech: {kech}   ❌ Yo'q: {yoq}\\n"
                         f"👥 Jami: {len(azolar)}\\n"
                         f"━━━━━━━━━━━━━━━\\n\\n")
                    for idx,a in enumerate(azolar):
                        h=a["holat"]
                        if h=="kelmadi": hs="❌ Kelmadi"
                        elif h=="kech": hs=f"🕐 {a.get('izoh') or 'kech'} kech"
                        else: hs="✅ Keldi"
                        txt+=f"<b>{idx+1}. {a['ism'][:26]}</b>\\n      {hs}\\n\\n"
                    rows2=[
                        [InlineKeyboardButton(text="✏️ O'zgartirish",callback_data=f"tg_yoqlama:{tgid}:0")],
                        [InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_info:{tgid}")],
                    ]
                    try: await call.message.edit_text(txt[:3800],parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
                    except: await call.message.answer(txt[:3800],parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
                    return True

        # ═══ RO'YXAT ═══
        azolar=get_yoqlama_bugun(tgid)
        if not azolar:
            await call.message.answer("👥 A'zo yo'q"); return True
        PER=10; total=len(azolar); max_page=(total-1)//PER; page=max(0,min(page,max_page))
        page_az=azolar[page*PER:(page+1)*PER]
        from datetime import datetime
        bugun=datetime.now().strftime("%d.%m.%Y")

        # Har o'quvchi = 1 tugma. Bosса tanlov chiqadi.
        rows2=[]
        for idx,a in enumerate(page_az):
            nom=page*PER+idx+1
            h=a["holat"]
            if h=="kelmadi": belgi="❌"
            elif h=="kech": belgi="🕐"
            else: belgi="✅"
            ism=a["ism"][:22]
            rows2.append([InlineKeyboardButton(
                text=f"{belgi} {nom}. {ism}",
                callback_data=f"tg_pick:{tgid}:{a['uid']}:{page}"
            )])

        if max_page>0:
            nav=[]
            if page>0: nav.append(InlineKeyboardButton(text="◀️",callback_data=f"tg_yoqlama:{tgid}:{page-1}"))
            nav.append(InlineKeyboardButton(text=f"{page+1}/{max_page+1}",callback_data="noop"))
            if page<max_page: nav.append(InlineKeyboardButton(text="▶️",callback_data=f"tg_yoqlama:{tgid}:{page+1}"))
            rows2.append(nav)
        rows2.append([InlineKeyboardButton(text="✔️ Tayyor — natijani ko'rish",callback_data=f"tg_yoq_natija:{tgid}")])

        kelmadi=[a for a in azolar if a["holat"]=="kelmadi"]
        kechlar=[a for a in azolar if a["holat"]=="kech"]
        keldi_soni=total-len(kelmadi)-len(kechlar)
        info=""
        if kelmadi:
            info+="\n❌ Kelmaganlar: "+", ".join(a['ism'].split()[0] for a in kelmadi)+"\n"
        if kechlar:
            info+="\n🕐 Kechikkanlar:\n"
            for a in kechlar: info+=f"   • {a['ism'].split()[0]}: {a.get('izoh') or 'kech'}\n"
        if not kelmadi and not kechlar:
            info="\n🎉 Hamma keldi!"

        txt=(f"📋 <b>Yoqlama · {bugun}</b>\n"
             f"━━━━━━━━━━━━━━━\n"
             f"✅ {keldi_soni}   🕐 {len(kechlar)}   ❌ {len(kelmadi)}   (jami {total})\n"
             f"{info}\n"
             f"👇 O'quvchini bosing → holatini o'zgartiring")

        try: await call.message.edit_text(txt,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except:
            try: await call.message.answer(txt,parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
            except: pass
        return True

    if call.data.startswith("tg_yoq_natija:"):
        tgid=int(call.data[14:]); await call.answer()
        from togarak import get_yoqlama_bugun
        from datetime import datetime
        azolar=get_yoqlama_bugun(tgid)
        bugun=datetime.now().strftime("%d.%m.%Y")
        keldi=sum(1 for a in azolar if a["holat"]=="keldi")
        kech=sum(1 for a in azolar if a["holat"]=="kech")
        yoq=sum(1 for a in azolar if a["holat"]=="kelmadi")
        total=len(azolar)
        txt=(f"📋 <b>Yo'qlama natijasi</b>\n"
             f"📅 {bugun}\n"
             f"━━━━━━━━━━━━━━━\n"
             f"✅ Keldi: {keldi}   🕐 Kech: {kech}   ❌ Yo'q: {yoq}\n"
             f"👥 Jami: {total} o'quvchi\n"
             f"━━━━━━━━━━━━━━━\n\n")
        for idx,a in enumerate(azolar):
            h=a["holat"]
            if h=="kelmadi": hs="❌ Kelmadi"
            elif h=="kech": hs=f"🕐 {a.get('izoh') or 'kech'} kech"
            else: hs="✅ Keldi"
            txt+=f"<b>{idx+1}. {a['ism'][:26]}</b>\n      {hs}\n\n"
        rows2=[
            [InlineKeyboardButton(text="✏️ O'zgartirish",callback_data=f"tg_yoqlama:{tgid}:0")],
            [InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_info:{tgid}")],
        ]
        try: await call.message.edit_text(txt[:3800],parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(txt[:3800],parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_stat:"):
        tgid=int(call.data[8:]); await call.answer()
        from togarak import get_yoqlama_statistika
        stat=get_yoqlama_statistika(tgid)
        if not stat: await call.message.answer("📊 Ma'lumot yo'q"); return True
        txt="📊 Yoqlama statistikasi:\n\n"
        for s2 in stat:
            total=s2["keldi"]+s2["kelmadi"]+s2["kech"]
            pct=round(s2["keldi"]*100/total) if total else 0
            txt+=f"👤 {s2['ism']} ({s2['sinf'] or '-'})\n"
            txt+=f"  ✅{s2['keldi']} ⏰{s2['kech']} ❌{s2['kelmadi']} | {pct}%\n\n"
        await call.message.answer(txt[:3000],reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⬅️",callback_data=f"tg_info:{tgid}")
        ]]))
        return True

    if call.data.startswith("tg_sozla:"):
        tgid=int(call.data[9:]); await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("""SELECT nomi,fan,oylik_summa,oylik_sana,
            (SELECT COUNT(*) FROM togarak_azolar WHERE togarak_id=%s AND aktiv=TRUE)
            FROM togaraklar WHERE id=%s AND teacher_id=%s""",(tgid,tgid,user_id))
        tg2=cur2.fetchone(); cur2.close(); conn2.close()
        if not tg2: await call.message.answer("❌ Ruxsat yo'q!"); return True
        txt=(f"⚙️ <b>To'garak sozlamalari</b>\n"
             f"─────────────\n"
             f"📚 {tg2[0]}\n"
             f"📖 Fan: {tg2[1] or '—'}\n"
             f"👥 A'zolar: {tg2[4]} ta\n"
             f"💰 Oylik: {tg2[2] or 0:,} so'm\n"
             f"📅 To'lov kuni: {tg2[3] or 1}\n")
        rows2=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Nomini o'zgartirish",callback_data=f"tg_edit_nomi:{tgid}"),
             InlineKeyboardButton(text="💰 Oylik summa",callback_data=f"tg_edit_summa:{tgid}")],
            [InlineKeyboardButton(text="📅 To'lov kunini o'zgartirish",callback_data=f"tg_edit_sana:{tgid}")],
            [InlineKeyboardButton(text="🔑 Parolni ko'r",callback_data=f"tg_show_parol:{tgid}"),
             InlineKeyboardButton(text="🔄 Parol almashtir",callback_data=f"tg_change_parol:{tgid}")],
            [InlineKeyboardButton(text="📊 To'lovlar hisoboti",callback_data=f"tg_tolovlar:{tgid}")],
            [InlineKeyboardButton(text="🗑 To'garakni o'chirish",callback_data=f"tg_del:{tgid}")],
            [InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_info:{tgid}")],
        ])
        try: await call.message.edit_text(txt,parse_mode="HTML",reply_markup=rows2)
        except: await call.message.answer(txt,parse_mode="HTML",reply_markup=rows2)
        return True

    if call.data.startswith("tg_edit_nomi:"):
        tgid=int(call.data[13:]); await call.answer()
        admin_state[user_id]=f"tg_set_nomi:{tgid}"
        await call.message.answer("✏️ Yangi to'garak nomini yozing:")
        return True

    if call.data.startswith("tg_edit_summa:"):
        tgid=int(call.data[14:]); await call.answer()
        admin_state[user_id]=f"tg_set_summa:{tgid}"
        await call.message.answer("💰 Oylik summani yozing (faqat raqam):\nMasalan: <code>150000</code>",parse_mode="HTML")
        return True

    if call.data.startswith("tg_edit_sana:"):
        tgid=int(call.data[13:]); await call.answer()
        rows2=[[InlineKeyboardButton(text=f"{d}",callback_data=f"tg_set_sana:{tgid}:{d}") for d in range(j,j+7) if d<=31] for j in range(1,29,7)]
        rows2.append([InlineKeyboardButton(text="⬅️",callback_data=f"tg_sozla:{tgid}")])
        await call.message.answer("📅 To'lov kunini tanlang (oyning nechanchi kuni):",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_set_sana:"):
        parts2=call.data[12:].split(":"); tgid,sana=int(parts2[0]),int(parts2[1])
        await call.answer(f"✅ {sana}-kun")
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("UPDATE togaraklar SET oylik_sana=%s WHERE id=%s AND teacher_id=%s",(sana,tgid,user_id))
        conn2.commit(); cur2.close(); conn2.close()
        await call.message.answer(f"✅ To'lov kuni: har oyning {sana}-kuni")
        return True

    if call.data.startswith("tg_show_parol:"):
        tgid=int(call.data[14:]); await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT parol FROM togaraklar WHERE id=%s AND teacher_id=%s",(tgid,user_id))
        row2=cur2.fetchone(); cur2.close(); conn2.close()
        if not row2: await call.message.answer("❌ Ruxsat yo'q!"); return True
        await call.message.answer(
            f"🔑 To'garak paroli:\n\n<code>{row2[0]}</code>\n\n"
            f"Bu xabar 30 soniyadan keyin o'chiriladi.",
            parse_mode="HTML"
        )
        return True

    if call.data.startswith("tg_change_parol:"):
        tgid=int(call.data[16:]); await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT id FROM togaraklar WHERE id=%s AND teacher_id=%s",(tgid,user_id))
        if not cur2.fetchone(): cur2.close(); conn2.close(); await call.message.answer("❌ Ruxsat yo'q!"); return True
        cur2.close(); conn2.close()
        admin_state[user_id]=f"tg_new_parol:{tgid}"
        await call.message.answer("🔑 Yangi parol yozing (kamida 4 belgi):")
        return True

    if call.data.startswith("tg_del:"):
        tgid=int(call.data[7:]); await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("""SELECT nomi,
            (SELECT COUNT(*) FROM togarak_azolar WHERE togarak_id=%s AND aktiv=TRUE)
            FROM togaraklar WHERE id=%s AND teacher_id=%s""",(tgid,tgid,user_id))
        r=cur2.fetchone(); cur2.close(); conn2.close()
        if not r: await call.message.answer("❌ Ruxsat yo'q!"); return True
        await call.message.answer(
            f"⚠️ <b>DIQQAT!</b>\n\n"
            f"📚 <b>{r[0]}</b> to'garagini o'chirmoqchimisiz?\n\n"
            f"❗️ Bu amal QAYTMAS:\n"
            f"• {r[1]} ta a'zo chiqarib yuboriladi\n"
            f"• Barcha baholar o'chadi\n"
            f"• Dars rejasi o'chadi\n"
            f"• Chat tarixi o'chadi\n\n"
            f"Rostdan o'chirasizmi?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Yo'q, bekor qilish",callback_data=f"tg_sozla:{tgid}")],
                [InlineKeyboardButton(text="🗑 Ha, o'chirish",callback_data=f"tg_del_confirm:{tgid}")],
            ])
        )
        return True

    if call.data.startswith("tg_del_confirm:"):
        tgid=int(call.data[15:]); await call.answer()
        user_state[user_id]=f"tg_del_parol:{tgid}"
        await call.message.answer(
            "🔑 Tasdiqlash uchun to'garak parolini yozing:\n\n"
            "(Noto'g'ri parol — o'chirilmaydi)"
        )
        return True

    if call.data == "tg_back":
        await call.answer()
        from togarak import get_teacher_togaraklar, togarak_list_kb
        tgs=get_teacher_togaraklar(user_id)
        kb2=togarak_list_kb(tgs,"tg")
        kb2.inline_keyboard.append([InlineKeyboardButton(text="➕ Yangi to'garak",callback_data="tg_yangi")])
        try: await call.message.edit_text(f"📚 Mening to'garaklarim ({len(tgs)} ta):",reply_markup=kb2)
        except: await call.message.answer(f"📚 Mening to'garaklarim ({len(tgs)} ta):",reply_markup=kb2)
        return True

    # ── TO'GARAK SO'ROVLAR ──
    if call.data.startswith("tg_req_approve:"):
        parts2=call.data[15:].split("|"); uid2,tgid2=int(parts2[0]),int(parts2[1])
        await call.answer()
        from togarak import join_togarak
        # O'qituvchi to'garakni boshqarishini tekshirish
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT id FROM togaraklar WHERE id=%s AND teacher_id=%s",(tgid2,user_id))
        if not cur2.fetchone():
            cur2.close();conn2.close()
            await call.message.edit_text("❌ Ruxsat yo'q!"); return True
        # Parolsiz qo'shish
        cur2.execute("SELECT COUNT(*) FROM togarak_azolar WHERE togarak_id=%s AND aktiv=TRUE",(tgid2,))
        cnt2=cur2.fetchone()[0]
        cur2.execute("SELECT max_talaba,nomi FROM togaraklar WHERE id=%s",(tgid2,))
        t2=cur2.fetchone()
        if cnt2 >= t2[0]:
            cur2.close();conn2.close()
            await call.message.edit_text(f"❌ To'garak to'ldi!"); return True
        try:
            cur2.execute("""
                INSERT INTO togarak_azolar(togarak_id,user_id,aktiv)
                VALUES(%s,%s,TRUE)
                ON CONFLICT(togarak_id,user_id) DO UPDATE SET aktiv=TRUE
            """,(tgid2,uid2))
            # So'rovni o'chiramiz (qayta ko'rinmasligi uchun)
            cur2.execute("DELETE FROM togarak_requests WHERE togarak_id=%s AND user_id=%s",(tgid2,uid2))
            conn2.commit()
        except Exception as e:
            print(f"approve insert: {e}")
            conn2.rollback()
        cur2.close();conn2.close()
        # O'quvchiga xabar
        try:
            await call.bot.send_message(uid2, f"✅ '{t2[1]}' to'garakka qabul qilindingiz!")
        except: pass
        await call.message.edit_text("✅ O'quvchi qabul qilindi!", reply_markup=None)
        return True

    if call.data.startswith("tg_req_reject:"):
        parts2=call.data[14:].split("|"); uid2,tgid2=int(parts2[0]),int(parts2[1])
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("DELETE FROM togarak_requests WHERE togarak_id=%s AND user_id=%s",(tgid2,uid2))
        conn2.commit(); cur2.close(); conn2.close()
        try:
            await call.bot.send_message(uid2, "❌ To'garakka qo'shilish so'rovingiz rad etildi.")
        except: pass
        await call.message.edit_text("❌ Rad etildi.", reply_markup=None)
        return True

    if call.data.startswith("tg_guruh_chat:"):
        parts2=call.data.split(":"); tgid=int(parts2[1])
        page=int(parts2[2]) if len(parts2)>2 else 0
        await call.answer()
        from togarak import get_guruh_xabarlar
        msgs=get_guruh_xabarlar(tgid, 30)
        # Pagination: 10 ta xabar ko'rsat
        per_page=10; total_p=(len(msgs)+per_page-1)//per_page
        page=max(0,min(page,total_p-1))
        page_msgs=msgs[page*per_page:(page+1)*per_page] if msgs else []
        txt=f"💬 Guruh chat [{page+1}/{max(1,total_p)}]\n{'─'*20}\n\n"
        if not page_msgs:
            txt+="(Hali xabarlar yo'q)"
        for m in page_msgs:
            vaqt=str(m["vaqt"])[11:16] if m["vaqt"] else ""
            txt+=f"👤 {m['ism']} {vaqt}:\n{m['matn']}\n\n"
        # Nav tugmalar
        nav=[]
        if page>0: nav.append(InlineKeyboardButton(text="⬅️",callback_data=f"tg_guruh_chat:{tgid}:{page-1}"))
        if page<total_p-1: nav.append(InlineKeyboardButton(text="➡️",callback_data=f"tg_guruh_chat:{tgid}:{page+1}"))
        rows2=[]
        if nav: rows2.append(nav)
        rows2.append([InlineKeyboardButton(text="✍️ Xabar yozish",callback_data=f"tg_msg_group:{tgid}")])
        rows2.append([InlineKeyboardButton(text="👤 Shaxsiy",callback_data=f"tg_azolar_msg:{tgid}"),
                      InlineKeyboardButton(text="🔄 Yangilash",callback_data=f"tg_guruh_chat:{tgid}:{page}")])
        try: await call.message.edit_text(txt[:3000], reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(txt[:3000], reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_azolar_msg:"):
        tgid=int(call.data[14:]); await call.answer()
        from togarak import get_togarak_azolar
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT teacher_id FROM togaraklar WHERE id=%s",(tgid,))
        t2=cur2.fetchone()
        cur2.execute("SELECT user_id FROM togarak_azolar WHERE togarak_id=%s AND aktiv=TRUE",(tgid,))
        member_ids=[r[0] for r in cur2.fetchall()]; cur2.close(); conn2.close()
        if user_id not in member_ids and (not t2 or t2[0]!=user_id):
            await call.message.answer("❌ Siz bu to'garak a'zosi emassiz!"); return True
        azolar=get_togarak_azolar(tgid)
        rows2=[]
        for a in azolar:
            if a["uid"]==user_id: continue
            rows2.append([InlineKeyboardButton(text=f"👤 {a['ism']} ({a['sinf'] or '-'})",callback_data=f"tg_pm:{tgid}:{a['uid']}:0")])
        if t2 and t2[0]!=user_id:
            conn2=_get_db_conn();cur2=conn2.cursor()
            cur2.execute("SELECT full_name FROM users WHERE user_id=%s",(t2[0],))
            tname=(cur2.fetchone() or ["O'qituvchi"])[0]; cur2.close(); conn2.close()
            rows2.insert(0,[InlineKeyboardButton(text=f"👨‍🏫 {tname}",callback_data=f"tg_pm:{tgid}:{t2[0]}:0")])
        if not rows2: await call.message.answer("👥 Boshqa a'zolar yo'q!"); return True
        await call.message.answer("👤 Kimga yozmoqchisiz?",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_pm:"):
        parts2=call.data.split(":"); tgid,uid2,page=int(parts2[1]),int(parts2[2]),int(parts2[3])
        await call.answer()
        from togarak import get_personal_messages
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT full_name FROM users WHERE user_id=%s",(uid2,))
        uname=(cur2.fetchone() or ["?"])[0]; cur2.close(); conn2.close()
        msgs=get_personal_messages(tgid,user_id,uid2,30)
        per_page=10; total_p=max(1,(len(msgs)+per_page-1)//per_page)
        page=max(0,min(page,total_p-1))
        page_msgs=msgs[page*per_page:(page+1)*per_page]
        txt=f"💬 {uname} bilan [{page+1}/{total_p}]\n" + "─"*20 + "\n\n"
        for m in page_msgs:
            me="Siz" if m["sender"]==user_id else m["ism"]
            vaqt=str(m["vaqt"])[11:16] if m["vaqt"] else ""
            txt+=f"{'➡️' if m['sender']==user_id else '⬅️'} {me} {vaqt}:\n{m['matn']}\n\n"
        if not page_msgs: txt+="(Hali xabar yo'q)"
        nav=[]
        if page>0: nav.append(InlineKeyboardButton(text="⬅️",callback_data=f"tg_pm:{tgid}:{uid2}:{page-1}"))
        if page<total_p-1: nav.append(InlineKeyboardButton(text="➡️",callback_data=f"tg_pm:{tgid}:{uid2}:{page+1}"))
        rows2=[]
        if nav: rows2.append(nav)
        rows2.append([InlineKeyboardButton(text="✍️ Xabar",callback_data=f"tg_pm_write:{tgid}:{uid2}"),
                      InlineKeyboardButton(text="🔄",callback_data=f"tg_pm:{tgid}:{uid2}:{page}")])
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_azolar_msg:{tgid}")])
        admin_state[user_id]=f"tg_send_pm:{tgid}:{uid2}"
        try: await call.message.edit_text(txt[:3000],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(txt[:3000],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_pm_write:"):
        parts2=call.data.split(":"); tgid,uid2=int(parts2[1]),int(parts2[2])
        await call.answer()
        admin_state[user_id]=f"tg_send_pm:{tgid}:{uid2}"
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT full_name FROM users WHERE user_id=%s",(uid2,))
        uname=(cur2.fetchone() or ["?"])[0]; cur2.close(); conn2.close()
        await call.message.answer(f"✍️ {uname} ga xabar yozing:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="❌ Bekor",callback_data=f"tg_pm:{tgid}:{uid2}:0")
            ]]))
        return True

    if call.data.startswith("tg_reja:"):
        parts2=call.data.split(":"); tgid=int(parts2[1])
        week_off=int(parts2[2]) if len(parts2)>2 else 0
        await call.answer()
        from datetime import datetime, timedelta
        today=datetime.now().date()
        monday=today - timedelta(days=today.weekday()) + timedelta(weeks=week_off)
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba"]
        KS=["Du","Se","Ch","Pa","Ju","Sh"]
        OY=["yanvar","fevral","mart","aprel","may","iyun","iyul","avgust","sentabr","oktabr","noyabr","dekabr"]
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT kun_id,boshlanish FROM togarak_jadval WHERE togarak_id=%s",(tgid,))
        doimiy={r[0]:r[1] for r in cur2.fetchall()}
        cur2.execute("""SELECT dars_sana,dars_vaqt,topic_code,completed FROM togarak_reja
            WHERE togarak_id=%s AND dars_sana IS NOT NULL
            AND dars_sana BETWEEN %s AND %s ORDER BY dars_sana""",
            (tgid,monday,monday+timedelta(days=5)))
        darslar={}
        for r in cur2.fetchall():
            darslar.setdefault(str(r[0]),[]).append({"vaqt":r[1],"mavzu":r[2],"done":r[3]})
        cur2.close(); conn2.close()

        # Sarlavha
        hafta_no = monday.isocalendar()[1]
        oxiri = monday+timedelta(days=5)
        if week_off==0: sarlavha="📅 Shu hafta"
        elif week_off==1: sarlavha="📅 Keyingi hafta"
        elif week_off==-1: sarlavha="📅 O'tgan hafta"
        else: sarlavha=f"📅 {hafta_no}-hafta"
        txt=f"{sarlavha}\n"
        txt+=f"{monday.day}–{oxiri.day} {OY[monday.month-1]}\n"
        txt+="╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n\n"

        kun_btns=[]
        for i in range(6):
            ks=monday+timedelta(days=i); ss=str(ks)
            is_today=ks==today
            has_doimiy=i in doimiy
            has_mavzu=ss in darslar

            # Kun sarlavhasi
            if is_today:
                bosh="▶️"
            elif has_mavzu or has_doimiy:
                bosh="🟩"
            else:
                bosh="⬜️"

            if has_mavzu:
                d=darslar[ss][0]
                done=d["done"]
                mavzu=(d["mavzu"] or "")[:24]
                vaqt=doimiy.get(i,d["vaqt"] or "")
                txt+=f"{bosh} <b>{KUNLAR[i]}</b> · {vaqt}\n"
                if done:
                    txt+=f"       ✅ {mavzu}\n\n"
                else:
                    txt+=f"       📗 {mavzu}\n\n"
                bt=f"✅{KS[i]}" if done else f"📗{KS[i]}"
            elif has_doimiy:
                txt+=f"{bosh} <b>{KUNLAR[i]}</b> · {doimiy[i]}\n"
                txt+=f"       ➕ mavzu qo'ying\n\n"
                bt=f"➕{KS[i]}"
            else:
                txt+=f"{bosh} {KUNLAR[i]} · dars yo'q\n\n"
                bt=f"{KS[i]}"
            kun_btns.append(InlineKeyboardButton(text=bt,callback_data=f"tg_kun:{tgid}:{ss}"))

        rows2=[kun_btns[:3],kun_btns[3:6]]
        rows2.append([
            InlineKeyboardButton(text="◀️",callback_data=f"tg_reja:{tgid}:{week_off-1}"),
            InlineKeyboardButton(text="📆 Oylik",callback_data=f"tg_oylik:{tgid}:0"),
            InlineKeyboardButton(text="▶️",callback_data=f"tg_reja:{tgid}:{week_off+1}"),
        ])
        rows2.append([
            InlineKeyboardButton(text="⚙️ Dars kunlari",callback_data=f"tg_jadval_set:{tgid}"),
            InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_info:{tgid}"),
        ])
        try: await call.message.edit_text(txt[:3500],parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(txt[:3500],parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True



    if call.data.startswith("tg_kun:"):
        parts2=call.data[7:].split(":"); tgid=int(parts2[0]); sana=parts2[1]
        await call.answer()
        from datetime import datetime
        from togarak import get_reja
        d=datetime.strptime(sana,"%Y-%m-%d").date()
        kun_id=d.weekday()
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba","Yakshanba"]
        # Bu kun doimiy jadvalda bormi?
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT boshlanish FROM togarak_jadval WHERE togarak_id=%s AND kun_id=%s",(tgid,kun_id))
        doimiy=cur2.fetchone()
        cur2.close(); conn2.close()
        if not doimiy:
            # Dars kuni belgilanmagan
            await call.message.answer(
                f"⚠️ {KUNLAR[kun_id]} kuni dars belgilanmagan!\n\n"
                f"Avval bu kunni doimiy jadvalga qo'shing.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"➕ {KUNLAR[kun_id]}ni dars kuni qilish",callback_data=f"tg_jadval_kun:{tgid}:{kun_id}")],
                    [InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_reja:{tgid}:0")],
                ])
            )
            return True
        # O'tilmagan, hali belgilanmagan mavzular
        reja=[r for r in get_reja(tgid) if not r["completed"] and not r.get("dars_sana")]
        if not reja:
            await call.message.answer("✅ Barcha mavzular belgilangan yoki o'tilgan!"); return True
        PER=10; total=len(reja)
        rows2=[]
        for i in range(0,min(total,PER)):
            r=reja[i]
            rows2.append([InlineKeyboardButton(
                text=f"📖 {r['code'][:40]}",
                callback_data=f"tg_kun_mavzu:{tgid}:{sana}:{r['id']}"
            )])
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_reja:{tgid}:0")])
        await call.message.answer(
            f"📅 {KUNLAR[kun_id]} {d.strftime('%d.%m.%Y')} 🕐{doimiy[0]}\n"
            f"Qaysi mavzu o'tiladi? ({total} ta qoldi)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2)
        )
        return True

    if call.data.startswith("tg_kun_mavzu:"):
        parts2=call.data[13:].split(":"); tgid=int(parts2[0]); sana=parts2[1]; reja_id=int(parts2[2])
        await call.answer()
        from datetime import datetime
        d=datetime.strptime(sana,"%Y-%m-%d").date()
        kun_id=d.weekday()
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba","Yakshanba"]
        # Doimiy jadvalda shu kun uchun vaqt bormi?
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT boshlanish FROM togarak_jadval WHERE togarak_id=%s AND kun_id=%s",(tgid,kun_id))
        doimiy=cur2.fetchone()
        if doimiy and doimiy[0]:
            # Avtomatik doimiy vaqt bilan belgilaymiz
            vaqt=doimiy[0]
            try:
                cur2.execute("UPDATE togarak_reja SET dars_sana=%s, dars_kuni=%s, dars_vaqt=%s WHERE id=%s",
                            (sana, KUNLAR[kun_id], vaqt, reja_id))
            except Exception:
                conn2.rollback()
                cur2.execute("UPDATE togarak_reja SET dars_sana=%s, dars_vaqt=%s WHERE id=%s",
                            (sana, vaqt, reja_id))
            conn2.commit(); cur2.close(); conn2.close()
            await call.message.answer(
                f"✅ {KUNLAR[kun_id]} {d.strftime('%d.%m')} — {vaqt}\n"
                f"Dars belgilandi! (doimiy vaqt)"
            )
        else:
            cur2.close(); conn2.close()
            # Vaqt so'raymiz
            admin_state[user_id]=f"tg_kun_vaqt:{tgid}:{sana}:{reja_id}"
            await call.message.answer(
                f"🕐 Dars vaqtini yozing:\nMasalan: <code>15:00</code>",
                parse_mode="HTML"
            )
        return True

    if call.data.startswith("tg_reja_albom:"):
        parts2=call.data[14:].split(":"); tgid,start=int(parts2[0]),int(parts2[1])
        await call.answer()
        from togarak import get_reja
        reja=get_reja(tgid); chunk=reja[start:start+10]; albom_n=start//10+1
        KS={"Dushanba":"Du","Seshanba":"Se","Chorshanba":"Ch","Payshanba":"Pa","Juma":"Ju","Shanba":"Sh"}
        rows2=[]
        for r in chunk:
            icon="✅" if r["completed"] else "📖"
            kun=KS.get(r.get("dars_kuni",""),""); vaqt=r.get("dars_vaqt","") or ""
            sana = (" " + kun + (" " + vaqt if vaqt else "")) if (kun or vaqt) else ""
            rows2.append([InlineKeyboardButton(text=f"{icon} {r['tartib']}. {r['code'][:30]}{sana}",callback_data=f"tg_reja_mavzu:{tgid}:{r['id']}")])
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_reja:{tgid}")])
        try: await call.message.edit_text(f"📗 {albom_n}-albom:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(f"📗 {albom_n}-albom:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_reja_mavzu:"):
        parts2=call.data[14:].split(":"); tgid,reja_id=int(parts2[0]),int(parts2[1])
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT topic_code,tartib,tur,dars_kuni,dars_vaqt,completed FROM togarak_reja WHERE id=%s",(reja_id,))
        r=cur2.fetchone(); cur2.close(); conn2.close()
        if not r: await call.message.answer("❌ Topilmadi"); return True
        holat="✅ O'tildi" if r[5] else "📖 O'tilmagan"
        txt=f"📌 {r[1]}-mavzu: {r[0]}\n📅 Kun: {r[3] or '—'} {r[4] or ''}\n🎯 Holat: {holat}"
        rows2=[[InlineKeyboardButton(text="📅 Kun/vaqt",callback_data=f"tg_reja_kun_set:{tgid}:{reja_id}"),InlineKeyboardButton(text="✅ O'tildi",callback_data=f"tg_mark_done:{tgid}:{r[0]}")],[InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_reja:{tgid}")]]
        await call.message.answer(txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True


    if call.data.startswith("tg_oylik:"):
        parts2=call.data[9:].split(":"); tgid=int(parts2[0]); month_off=int(parts2[1]) if len(parts2)>1 else 0
        await call.answer()
        from datetime import datetime
        import calendar
        today=datetime.now().date()
        mon=today.month+month_off; yr=today.year
        while mon>12: mon-=12; yr+=1
        while mon<1: mon+=12; yr-=1
        OYLAR=["Yanvar","Fevral","Mart","Aprel","May","Iyun","Iyul","Avgust","Sentabr","Oktabr","Noyabr","Dekabr"]
        conn2=_get_db_conn();cur2=conn2.cursor()
        first=datetime(yr,mon,1).date(); last_day=calendar.monthrange(yr,mon)[1]
        last=datetime(yr,mon,last_day).date()
        cur2.execute("SELECT kun_id,boshlanish FROM togarak_jadval WHERE togarak_id=%s",(tgid,))
        doimiy={r[0]:r[1] for r in cur2.fetchall()}
        cur2.execute("""SELECT dars_sana,dars_vaqt,topic_code,completed FROM togarak_reja
            WHERE togarak_id=%s AND dars_sana BETWEEN %s AND %s ORDER BY dars_sana""",(tgid,first,last))
        darslar={}
        for r in cur2.fetchall(): darslar[str(r[0])]={"vaqt":r[1],"mavzu":r[2],"done":r[3]}
        cur2.close(); conn2.close()

        txt=f"📆 <b>{OYLAR[mon-1]} {yr}</b>\n"
        txt+="╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
        txt+="Du Se Ch Pa Ju Sh Ya\n"
        for week in calendar.monthcalendar(yr,mon):
            line=""
            for wd,day in enumerate(week):
                if day==0: line+="·· "
                else:
                    dt=datetime(yr,mon,day).date(); ss=str(dt)
                    if ss in darslar:
                        line+="✅" if darslar[ss]["done"] else "📗"
                    elif dt==today: line+="🔴"
                    elif wd in doimiy: line+="🟩"
                    else: line+=f"{day:2}"
                    line+=" "
            txt+=line+"\n"

        txt+="\n🔴 bugun · 🟩 dars kuni\n📗 mavzu · ✅ o'tildi\n"

        if darslar:
            txt+="\n<b>📚 Darslar:</b>\n"
            for ss in sorted(darslar):
                d=datetime.strptime(ss,"%Y-%m-%d").date()
                m="✅" if darslar[ss]["done"] else "📗"
                v=darslar[ss].get("vaqt") or ""
                txt+=f"{m} <b>{d.day}</b> {v} · {(darslar[ss]['mavzu'] or '')[:22]}\n"

        rows2=[[
            InlineKeyboardButton(text="◀️",callback_data=f"tg_oylik:{tgid}:{month_off-1}"),
            InlineKeyboardButton(text="📅 Haftalik",callback_data=f"tg_reja:{tgid}:0"),
            InlineKeyboardButton(text="▶️",callback_data=f"tg_oylik:{tgid}:{month_off+1}"),
        ],[InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_info:{tgid}")]]
        try: await call.message.edit_text(txt[:3500],parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(txt[:3500],parse_mode="HTML",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True



    if call.data.startswith("tg_jadval_set:"):
        tgid=int(call.data[14:]); await call.answer()
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba"]
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT kun_id,boshlanish FROM togarak_jadval WHERE togarak_id=%s",(tgid,))
        mavjud={r[0]:r[1] for r in cur2.fetchall()}
        cur2.close(); conn2.close()
        txt="⚙️ Dars kunlarini sozlash\n"+"─"*20+"\n\n"
        txt+="Har hafta qaysi kunlari dars bo'ladi?\n\n"
        for i,k in enumerate(KUNLAR):
            txt+=(f"✅ {k}: 🕐 {mavjud[i]}\n" if i in mavjud else f"⚪ {k}: belgilanmagan\n")
        txt+="\n⬇️ Kun bosib vaqt belgilang:"
        rows2=[]
        for i,k in enumerate(KUNLAR):
            if i in mavjud:
                rows2.append([
                    InlineKeyboardButton(text=f"✅ {k} — {mavjud[i]}",callback_data=f"tg_jadval_kun:{tgid}:{i}"),
                    InlineKeyboardButton(text="🗑",callback_data=f"tg_jadval_del:{tgid}:{i}"),
                ])
            else:
                rows2.append([InlineKeyboardButton(text=f"⚪ {k} — vaqt qo'shish",callback_data=f"tg_jadval_kun:{tgid}:{i}")])
        rows2.append([InlineKeyboardButton(text="✅ Tayyor — jadvalga",callback_data=f"tg_reja:{tgid}:0")])
        try: await call.message.edit_text(txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_jadval_kun:"):
        parts2=call.data[14:].split(":"); tgid,kun_id=int(parts2[0]),int(parts2[1])
        await call.answer()
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba"]
        admin_state[user_id]=f"tg_jadval_vaqt:{tgid}:{kun_id}"
        await call.message.answer(
            f"🕐 <b>{KUNLAR[kun_id]}</b> kuni dars vaqti:\n\n"
            f"<code>15:00</code> → avto tugash 17:00 (+2 soat)\n"
            f"<code>15:00-16:30</code> → aniq tugash vaqti\n\n"
            f"✍️ Vaqtni yozing:",
            parse_mode="HTML"
        )
        return True

    if call.data.startswith("tg_jadval_del:"):
        parts2=call.data[14:].split(":"); tgid,kun_id=int(parts2[0]),int(parts2[1])
        await call.answer("O'chirildi")
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("DELETE FROM togarak_jadval WHERE togarak_id=%s AND kun_id=%s",(tgid,kun_id))
        conn2.commit(); cur2.close(); conn2.close()
        # Sozlash sahifasini qayta ochamiz — frozen call.data uchun yangi call yaratmaymiz
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba"]
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT kun_id,boshlanish FROM togarak_jadval WHERE togarak_id=%s",(tgid,))
        mavjud={r[0]:r[1] for r in cur2.fetchall()}
        cur2.close(); conn2.close()
        txt="⚙️ Dars kunlarini sozlash\n"+"─"*20+"\n\n"
        rows2=[]
        for i,k in enumerate(KUNLAR):
            bt=f"✅ {k} ({mavjud[i]})" if i in mavjud else f"⚪ {k}"
            rows2.append([
                InlineKeyboardButton(text=bt,callback_data=f"tg_jadval_kun:{tgid}:{i}"),
                InlineKeyboardButton(text="🗑" if i in mavjud else " ",callback_data=f"tg_jadval_del:{tgid}:{i}" if i in mavjud else "noop"),
            ])
        rows2.append([InlineKeyboardButton(text="⬅️ Jadvalga qaytish",callback_data=f"tg_reja:{tgid}:0")])
        try: await call.message.edit_text(txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: pass
        return True

    if call.data.startswith("tg_reja_jadval:"):
        # Eski jadval → yangi haftalik (frozen call.data ni o'zgartirmasdan)
        tgid=int(call.data[15:]); await call.answer()
        from datetime import datetime, timedelta
        today=datetime.now().date()
        monday=today - timedelta(days=today.weekday())
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba"]
        KS=["Du","Se","Ch","Pa","Ju","Sh"]
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("""SELECT dars_sana,dars_vaqt,topic_code,completed FROM togarak_reja
            WHERE togarak_id=%s AND dars_sana IS NOT NULL
            AND dars_sana BETWEEN %s AND %s ORDER BY dars_sana""",
            (tgid,monday,monday+timedelta(days=5)))
        darslar={}
        for r in cur2.fetchall():
            darslar.setdefault(str(r[0]),[]).append({"vaqt":r[1],"mavzu":r[2],"done":r[3]})
        cur2.close(); conn2.close()
        txt=f"📅 Haftalik jadval\n{monday.strftime('%d.%m')} — {(monday+timedelta(days=5)).strftime('%d.%m.%Y')}\n{'─'*20}\n\n"
        kun_btns=[]
        for i in range(6):
            ks=monday+timedelta(days=i); ss=str(ks)
            if ss in darslar:
                txt+=f"{'🔵' if ks==today else '📌'} {KUNLAR[i]} {ks.strftime('%d.%m')}:\n"
                for d in darslar[ss]:
                    m="✅" if d["done"] else "📖"
                    txt+=f"   {m} {d['vaqt'] or ''} {(d['mavzu'] or '')[:25]}\n"
                bt=f"{KS[i]} {ks.day} ●"
            else:
                txt+=f"{'🔵' if ks==today else '⚪'} {KUNLAR[i]} {ks.strftime('%d.%m')}: —\n"
                bt=f"{KS[i]} {ks.day}"
            kun_btns.append(InlineKeyboardButton(text=bt,callback_data=f"tg_kun:{tgid}:{ss}"))
        rows2=[kun_btns[:3],kun_btns[3:6]]
        rows2.append([
            InlineKeyboardButton(text="◀️ O'tgan",callback_data=f"tg_reja:{tgid}:-1"),
            InlineKeyboardButton(text="📆 Oylik",callback_data=f"tg_oylik:{tgid}:0"),
            InlineKeyboardButton(text="Keyingi ▶️",callback_data=f"tg_reja:{tgid}:1"),
        ])
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_info:{tgid}")])
        try: await call.message.edit_text(txt[:3000],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(txt[:3000],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_reja_kun_set:"):
        parts2=call.data[16:].split(":"); tgid=int(parts2[0])
        parts2=call.data[16:].split(":")
        tgid=int(parts2[0])
        reja_id=int(parts2[1]) if len(parts2)>1 and parts2[1].isdigit() else None
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba"]
        # Kun tanlatamiz
        rows2=[[InlineKeyboardButton(
            text=f"📅 {k}",
            callback_data=f"tg_reja_mavzu_kun:{tgid}:{reja_id}:{i}" if reja_id else f"tg_reja_kun_id:{tgid}:{i}"
        )] for i,k in enumerate(KUNLAR)]
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_reja:{tgid}")])
        await call.message.answer("📅 Qaysi kuni dars bo'ladi?",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_reja_kun_id:"):
        # Jadvaldan keldi — avval kun, keyin mavzu tanlash
        parts2=call.data[15:].split(":"); tgid,kun_id=int(parts2[0]),int(parts2[1])
        await call.answer()
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba"]
        from togarak import get_reja
        reja=get_reja(tgid)
        rows2=[[InlineKeyboardButton(
            text=f"📖 {r['tartib']}. {r['code'][:35]}",
            callback_data=f"tg_reja_mavzu_kun:{tgid}:{r['id']}:{kun_id}"
        )] for r in reja if not r["completed"]]
        if not rows2: await call.message.answer("✅ Barcha mavzular belgilangan!"); return True
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_reja_jadval:{tgid}")])
        await call.message.answer(f"📅 {KUNLAR[kun_id]} — qaysi mavzu?",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_reja_mavzu_kun:"):
        parts2=call.data[18:].split(":"); tgid,reja_id,kun_id=int(parts2[0]),int(parts2[1]),int(parts2[2])
        await call.answer()
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba"]
        admin_state[user_id]=f"tg_reja_vaqt_save:{tgid}:{reja_id}:{kun_id}"
        await call.message.answer(
            f"📅 {KUNLAR[kun_id]} — dars vaqtini yozing:\n"
            f"Masalan: <code>15:00</code>",
            parse_mode="HTML"
        )
        return True

    if call.data.startswith("tg_reja_today:"):
        tgid=int(call.data[14:]); await call.answer()
        from togarak import get_reja
        reja=[r for r in get_reja(tgid) if not r["completed"]]
        if not reja: await call.message.answer("✅ Barcha mavzular o'tilgan!"); return True
        # Jadvaldan bugungi vaqtni ham ko'rsat
        from datetime import datetime
        bugun_id=datetime.now().weekday()
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba","Yakshanba"]
        conn2=_get_db_conn();cur2=conn2.cursor()
        try:
            cur2.execute("SELECT boshlanish,tugash FROM togarak_jadval WHERE togarak_id=%s AND kun_id=%s",(tgid,bugun_id))
            j=cur2.fetchone()
        except: j=None
        cur2.close(); conn2.close()
        vaqt_txt=f"🕐 {j[0]}" + (f"–{j[1]}" if j and j[1] else "") if j else ""
        rows2=[]
        # 10 lik albomlar
        per=10; total=len(reja)
        for i,r in enumerate(reja[:10]):
            albom=f"[{i+1}/10]" if total>10 else f"[{i+1}/{total}]"
            rows2.append([InlineKeyboardButton(
                text=f"📖 {albom} {r['code'][:35]}",
                callback_data=f"tg_mark_done:{tgid}:{r['code']}"
            )])
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_reja:{tgid}")])
        txt=f"📅 {KUNLAR[bugun_id]} {vaqt_txt}\nBugungi darsni belgilang ({total} ta qoldi):"
        await call.message.answer(txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_mark_done:"):
        parts2=call.data[13:].split(":"); tgid=int(parts2[0]); code=parts2[1]
        await call.answer()
        from togarak import mark_dars_done
        mark_dars_done(tgid,code,user_id)
        await call.message.answer(f"✅ '{code}' dars o'tdi deb belgilandi!")
        call.data=f"tg_reja:{tgid}"; await handle_tg_reja(call,tgid,user_id)
        return True

    if call.data.startswith("tg_reja_add:"):
        tgid=int(call.data[12:]); await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("""SELECT DISTINCT grade FROM dts_tree
            WHERE grade IS NOT NULL AND is_deleted=FALSE
            AND NOT (grade ~ '^[0-9]+$' AND grade::int BETWEEN 1 AND 11)
            ORDER BY grade""")
        sinflar=cur2.fetchall(); cur2.close(); conn2.close()
        rows2=[[InlineKeyboardButton(text=f"🏫 {s[0]}",callback_data=f"tg_reja_sinf:{tgid}:{s[0]}")] for s in sinflar]
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_reja:{tgid}")])
        await call.message.answer("🏫 Sinf tanlang:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True


    if call.data.startswith("tg_reja_sinf_choose:"):
        tgid=int(call.data[20:]); await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("""SELECT DISTINCT grade FROM dts_tree
            WHERE grade IS NOT NULL AND is_deleted=FALSE
            AND NOT (grade ~ '^[0-9]+$' AND grade::int BETWEEN 1 AND 11)
            ORDER BY grade""")
        sinflar=cur2.fetchall(); cur2.close(); conn2.close()
        rows2=[[InlineKeyboardButton(text=f"🏫 {s[0]}",callback_data=f"tg_reja_sinf:{tgid}:{s[0]}")] for s in sinflar]
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_reja_add:{tgid}")])
        await call.message.answer("Sinf tanlang:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_reja_sinf:"):
        parts2=call.data[13:].split(":"); tgid=int(parts2[0]); sinf=parts2[1]
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT DISTINCT subject_name FROM dts_tree WHERE grade=%s AND is_deleted=FALSE ORDER BY subject_name",(sinf,))
        fanlar=cur2.fetchall(); cur2.close(); conn2.close()
        rows2=[[InlineKeyboardButton(text=f"📚 {f[0]}",callback_data=f"tg_reja_fan_add:{tgid}:{sinf}:{f[0]}")] for f in fanlar[:10]]
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_reja_add:{tgid}")])
        await call.message.answer(f"📚 Fan tanlang — barcha mavzular qo'shiladi:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_reja_fan_add:"):
        parts2=call.data[16:].split(":"); tgid=int(parts2[0]); sinf=parts2[1]; fan=parts2[2]
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        if sinf=="all":
            cur2.execute("""SELECT DISTINCT mavzu_name FROM dts_tree
                WHERE UPPER(subject_name)=UPPER(%s) AND is_deleted=FALSE
                AND mavzu_name IS NOT NULL ORDER BY mavzu_name""",(fan,))
        else:
            cur2.execute("""SELECT DISTINCT mavzu_name FROM dts_tree
                WHERE grade=%s AND UPPER(subject_name)=UPPER(%s) AND is_deleted=FALSE
                AND mavzu_name IS NOT NULL ORDER BY mavzu_name""",(sinf,fan))
        mavzular=cur2.fetchall()
        cur2.execute("DELETE FROM togarak_reja WHERE togarak_id=%s",(tgid,))
        for i,(name,) in enumerate(mavzular,1):
            cur2.execute("INSERT INTO togarak_reja(togarak_id,topic_code,tartib,tur) VALUES(%s,%s,%s,'dars')",(tgid,name,i))
        conn2.commit(); cur2.close(); conn2.close()
        await call.message.answer(f"✅ {fan} — {len(mavzular)} ta mavzu rejaga qo'shildi!")
        return True



    if call.data.startswith("tg_reja_fan:"):
        parts2=call.data[12:].split(":")
        tgid=int(parts2[0]); sinf=parts2[1]; fan=parts2[2]
        page=int(parts2[3]) if len(parts2)>3 else 0
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        if sinf=="all":
            cur2.execute("""SELECT DISTINCT ON (mavzu_code) mavzu_code, mavzu_name
                FROM dts_tree WHERE subject_name=%s
                AND is_deleted=FALSE AND mavzu_code IS NOT NULL
                ORDER BY mavzu_code""", (fan,))
        else:
            cur2.execute("""SELECT DISTINCT ON (mavzu_code) mavzu_code, mavzu_name
                FROM dts_tree WHERE grade=%s AND subject_name=%s
                AND is_deleted=FALSE AND mavzu_code IS NOT NULL
                ORDER BY mavzu_code""", (sinf,fan))
        barcha=cur2.fetchall(); cur2.close(); conn2.close()
        if not barcha:
            await call.message.answer("❌ Mavzu topilmadi!"); return True
        PER=10; total=len(barcha)
        page_items=barcha[page*PER:(page+1)*PER]
        rows2=[[InlineKeyboardButton(
            text=f"📌 {(m[1] or m[0])[:40]}",
            callback_data=f"tg_reja_add_topic:{tgid}:{m[0]}"
        )] for m in page_items]
        nav=[]
        if page>0: nav.append(InlineKeyboardButton(text="◀️",callback_data=f"tg_reja_fan:{tgid}:{sinf}:{fan}:{page-1}"))
        nav.append(InlineKeyboardButton(text=f"{page*PER+1}-{min((page+1)*PER,total)}/{total}",callback_data="noop"))
        if (page+1)*PER<total: nav.append(InlineKeyboardButton(text="▶️",callback_data=f"tg_reja_fan:{tgid}:{sinf}:{fan}:{page+1}"))
        if nav: rows2.append(nav)
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_reja_add:{tgid}")])
        try: await call.message.edit_text(f"📌 Mavzular ({total} ta):",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(f"📌 Mavzular ({total} ta):",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_reja_bob:"):
        parts2=call.data[12:].split(":"); tgid=int(parts2[0]); sinf=parts2[1]; fan=parts2[2]; bob=parts2[3]
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        # Faqat mavzu darajasi — DISTINCT mavzu_code bo'yicha
        cur2.execute("""SELECT DISTINCT ON (mavzu_code) mavzu_code, mavzu_name
            FROM dts_tree WHERE grade=%s AND subject=%s AND bo_lim LIKE %s
            AND is_deleted=FALSE AND mavzu_code IS NOT NULL
            ORDER BY mavzu_code LIMIT 20""",
            (sinf,fan,f"{bob}%"))
        mavzular=cur2.fetchall(); cur2.close(); conn2.close()
        if not mavzular:
            await call.message.answer("❌ Mavzu topilmadi!"); return True
        rows2=[[InlineKeyboardButton(
            text=f"📌 {m[1][:40] if m[1] else m[0]}",
            callback_data=f"tg_reja_add_topic:{tgid}:{m[0]}"
        )] for m in mavzular]
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_reja_add:{tgid}")])
        await call.message.answer("📌 Mavzuni tanlang:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_reja_add_topic:"):
        parts2=call.data[18:].split(":"); tgid=int(parts2[0]); code=parts2[1]
        await call.answer()
        # mavzu_code dan mavzu_name ni olish
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT mavzu_name FROM dts_tree WHERE mavzu_code=%s LIMIT 1",(code,))
        row2=cur2.fetchone(); cur2.close(); conn2.close()
        mavzu_name = row2[0] if row2 else code
        from togarak import add_to_reja
        add_to_reja(tgid, mavzu_name, "dars")
        await call.message.answer(f"✅ '{mavzu_name[:50]}' rejaga qo'shildi!")
        return True

    if call.data.startswith("tg_reja_manual:"):
        tgid=int(call.data[15:]); await call.answer()
        admin_state[user_id]=f"tg_reja_add_manual:{tgid}"
        await call.message.answer("Maxsus kun nomini yozing\n(Masalan: Imtihon, Laboratoriya, Sayohat):")
        return True

    if call.data.startswith("tg_hw:"):
        tgid=int(call.data[6:]); await call.answer()
        from features import get_homeworks
        hws=get_homeworks(tgid)
        rows2=[[InlineKeyboardButton(
            text=f"📝 {h['mavzu']} ({h['topshirildi']} ta topshirdi)",
            callback_data=f"tg_hw_view:{h['id']}"
        )] for h in hws]
        rows2.append([InlineKeyboardButton(text="➕ Yangi vazifa",callback_data=f"tg_hw_new:{tgid}")])
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"tg_info:{tgid}")])
        txt=f"📝 Uyga vazifalar ({len(hws)} ta aktiv)"
        try: await call.message.edit_text(txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("tg_hw_new:"):
        tgid=int(call.data[10:]); await call.answer()
        admin_state[user_id]=f"hw_new:{tgid}:mavzu"
        await call.message.answer("📝 Yangi vazifa\n\nVazifa mavzusini yozing:")
        return True

    if call.data.startswith("tg_hw_view:"):
        hw_id=int(call.data[11:]); await call.answer()
        from features import get_hw_submits
        subs=get_hw_submits(hw_id)
        txt=f"📝 Topshiriqlar ({len(subs)} ta):\n\n"
        for sb in subs:
            icon="✅" if sb["baho"] else "⏳"
            txt+=f"{icon} {sb['ism']}: {sb['javob'][:50]}\n"
        await call.message.answer(txt[:3000])
        return True

    if call.data.startswith("tg_reyting:"):
        tgid=int(call.data[11:]); await call.answer()
        from features import get_reyting
        r=get_reyting(tgid)
        txt="🏆 Reyting\n"+"─"*20+"\n\n"
        medals=["🥇","🥈","🥉"]
        for i,st in enumerate(r):
            m=medals[i] if i<3 else f"{i+1}."
            txt+=f"{m} {st['ism']} ({st['sinf'] or '-'})\n"
            txt+=f"  ⭐{st['baho']} | 📋{st['davomat']}% | 📝{st['hw']}\n\n"
        await call.message.answer(txt[:3000])
        return True

    if call.data.startswith("tg_hisobot:"):
        tgid=int(call.data[11:]); await call.answer()
        await call.message.answer("📊 Hisobot tayyorlanmoqda...")
        try:
            from features import generate_excel_report
            from aiogram.types import BufferedInputFile
            data=generate_excel_report(tgid)
            await call.message.answer_document(
                BufferedInputFile(data,"hisobot.xlsx"),
                caption="📊 To'garak hisoboti"
            )
        except Exception as e:
            await call.message.answer(f"❌ Hisobot xato: {e}")
        return True

    if call.data.startswith("tg_pending:"):
        tgid=int(call.data[11:]); await call.answer()
        from togarak import get_pending_requests
        reqs=[r for r in get_pending_requests(user_id) if r["tg_id"]==tgid]
        if not reqs:
            await call.message.answer("✅ Kutayotgan so'rovlar yo'q!"); return True
        for r in reqs:
            await call.message.answer(
                f"📨 So'rov #{r['id']}\n👤 {r['ism']} — {r['sinf'] or '-'}\n📚 {r['tg_nomi']}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✅ Qabul", callback_data=f"tg_req_approve:{r['uid']}|{r['tg_id']}"),
                    InlineKeyboardButton(text="❌ Rad",   callback_data=f"tg_req_reject:{r['uid']}|{r['tg_id']}"),
                ]])
            )
        return True

    if call.data.startswith("tg_msg_group:"):
        tgid=int(call.data[13:]); await call.answer()
        admin_state[user_id]=f"tg_send_msg:{tgid}:all"
        await call.message.answer(
            "📢 Guruhga xabar yozing:\n(Barcha a'zolarga yuboriladi)"
        )
        return True


    return False
