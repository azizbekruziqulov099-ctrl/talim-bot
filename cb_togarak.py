"""cb_student_tg.py"""
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

async def handle_stg(call, user_id, admin_state, user_state, temp_user, bot):
    d=call.data
    # ── O'QUVCHI TO'GARAK ──
    if call.data == "stg_join":
        await call.answer()
        user_state[user_id]="stg_join_id"
        await call.message.answer("🔑 To'garak ID raqamini yozing:\n(O'qituvchingizdan so'rang)")
        return True

    if call.data.startswith("stg_info:"):
        tgid=int(call.data[9:]); await call.answer()
        from togarak import get_student_togaraklar, get_baholar, get_tolov_status
        tgs={t["id"]:t for t in get_student_togaraklar(user_id)}
        t=tgs.get(tgid)
        if not t: await call.message.answer("❌ Topilmadi"); return True
        baholar=get_baholar(tgid,user_id)
        tolovlar=get_tolov_status(tgid,user_id)
        avg_baho=round(sum(b[0] for b in baholar)/len(baholar),1) if baholar else "—"
        last_tolov=tolovlar[0][1] if tolovlar else 0
        txt=(f"📚 {t['nomi']}\n"
             f"👨‍🏫 {t['teacher']}\n"
             f"📊 O'rtacha baho: {avg_baho}\n"
             f"💰 So'nggi to'lov: {last_tolov:,} so'm\n"
             f"📅 To'lov kuni: har oyning {t['oylik_sana']}-kuni")
        kb2=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Mavzular",    callback_data=f"stg_albomlar:{tgid}"),
             InlineKeyboardButton(text="📅 Jadval",      callback_data=f"stg_jadval:{tgid}:0")],
            [InlineKeyboardButton(text="📊 Baholarim",   callback_data=f"stg_baholar:{tgid}"),
             InlineKeyboardButton(text="🏆 Reyting",     callback_data=f"stg_reyting:{tgid}")],
            [InlineKeyboardButton(text="📝 Vazifalar",   callback_data=f"stg_hw:{tgid}"),
             InlineKeyboardButton(text="💬 Chat",        callback_data=f"stg_chat:{tgid}")],
            [InlineKeyboardButton(text="🚪 Chiqish",     callback_data=f"stg_leave_req:{tgid}")],
        ])
        await call.message.answer(txt, reply_markup=kb2)
        return True

    if call.data.startswith("stg_jadval:"):
        parts2=call.data[11:].split(":"); tgid=int(parts2[0]); week_off=int(parts2[1]) if len(parts2)>1 else 0
        await call.answer()
        from datetime import datetime, timedelta
        today=datetime.now().date()
        monday=today - timedelta(days=today.weekday()) + timedelta(weeks=week_off)
        KUNLAR=["Dushanba","Seshanba","Chorshanba","Payshanba","Juma","Shanba"]
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT kun_id,boshlanish FROM togarak_jadval WHERE togarak_id=%s",(tgid,))
        doimiy={r[0]:r[1] for r in cur2.fetchall()}
        cur2.execute("""SELECT dars_sana,dars_vaqt,topic_code,completed FROM togarak_reja
            WHERE togarak_id=%s AND dars_sana IS NOT NULL
            AND dars_sana BETWEEN %s AND %s ORDER BY dars_sana""",(tgid,monday,monday+timedelta(days=5)))
        darslar={}
        for r in cur2.fetchall():
            darslar.setdefault(str(r[0]),[]).append({"vaqt":r[1],"mavzu":r[2],"done":r[3]})
        cur2.close(); conn2.close()
        txt=f"📅 Dars jadvali\n{monday.strftime('%d.%m')} — {(monday+timedelta(days=5)).strftime('%d.%m.%Y')}\n{'━'*22}\n\n"
        for i in range(6):
            ks=monday+timedelta(days=i); ss=str(ks)
            is_today=ks==today; has_doimiy=i in doimiy
            pref="🔵" if is_today else ("🟢" if has_doimiy else "⚪")
            if ss in darslar:
                txt+=f"{pref} {KUNLAR[i]} {ks.strftime('%d.%m')}"
                if has_doimiy: txt+=f" 🕐{doimiy[i]}"
                txt+=":\n"
                for d in darslar[ss]:
                    m="✅ o'tildi" if d["done"] else "📗"
                    txt+=f"     {m} {(d['mavzu'] or '')[:26]}\n"
            elif has_doimiy:
                txt+=f"{pref} {KUNLAR[i]} {ks.strftime('%d.%m')} 🕐{doimiy[i]}\n"
            else:
                txt+=f"{pref} {KUNLAR[i]} {ks.strftime('%d.%m')}: —\n"
        txt+=f"\n🟢=dars kuni  📗=mavzu  ✅=o'tildi"
        rows2=[[
            InlineKeyboardButton(text="◀️ O'tgan",callback_data=f"stg_jadval:{tgid}:{week_off-1}"),
            InlineKeyboardButton(text="📆 Oylik",callback_data=f"stg_oylik:{tgid}:0"),
            InlineKeyboardButton(text="Keyingi ▶️",callback_data=f"stg_jadval:{tgid}:{week_off+1}"),
        ],[InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"stg_info:{tgid}")]]
        try: await call.message.edit_text(txt[:3500],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(txt[:3500],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("stg_oylik:"):
        parts2=call.data[10:].split(":"); tgid=int(parts2[0]); month_off=int(parts2[1]) if len(parts2)>1 else 0
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
        cur2.execute("SELECT kun_id FROM togarak_jadval WHERE togarak_id=%s",(tgid,))
        doimiy={r[0] for r in cur2.fetchall()}
        cur2.execute("""SELECT dars_sana,dars_vaqt,topic_code,completed FROM togarak_reja
            WHERE togarak_id=%s AND dars_sana BETWEEN %s AND %s ORDER BY dars_sana""",(tgid,first,last))
        darslar={}
        for r in cur2.fetchall(): darslar[str(r[0])]={"vaqt":r[1],"mavzu":r[2],"done":r[3]}
        cur2.close(); conn2.close()
        txt=f"📆 {OYLAR[mon-1]} {yr}\n{'━'*22}\n\nDu Se Ch Pa Ju Sh Ya\n"
        for week in calendar.monthcalendar(yr,mon):
            line=""
            for wd,day in enumerate(week):
                if day==0: line+="   "
                else:
                    dt=datetime(yr,mon,day).date(); ss=str(dt)
                    if ss in darslar: line+="✅ " if darslar[ss]["done"] else "📗 "
                    elif dt==today: line+="🔵 "
                    elif wd in doimiy: line+="🟢 "
                    else: line+=f"{day:2} "
            txt+=line+"\n"
        if darslar:
            txt+="\n📚 Darslar:\n"
            for ss in sorted(darslar):
                d=datetime.strptime(ss,"%Y-%m-%d").date()
                m="✅" if darslar[ss]["done"] else "📗"
                v=darslar[ss].get("vaqt") or ""
                txt+=f"{m} {d.day} {v}: {(darslar[ss]['mavzu'] or '')[:24]}\n"
        txt+=f"\n🟢=dars kuni  📗=mavzu  ✅=o'tildi"
        rows2=[[
            InlineKeyboardButton(text="◀️",callback_data=f"stg_oylik:{tgid}:{month_off-1}"),
            InlineKeyboardButton(text="📅 Haftalik",callback_data=f"stg_jadval:{tgid}:0"),
            InlineKeyboardButton(text="▶️",callback_data=f"stg_oylik:{tgid}:{month_off+1}"),
        ],[InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"stg_info:{tgid}")]]
        try: await call.message.edit_text(txt[:3500],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(txt[:3500],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True


    if call.data.startswith("stg_hw:"):
        rows2=[]
        for h in hws:
            status="✅" if h["javob"] else "⏳"
            rows2.append([InlineKeyboardButton(
                text=f"{status} {h['mavzu']} | {str(h['deadline'])[:10] if h['deadline'] else '-'}",
                callback_data=f"stg_hw_do:{h['id']}:{tgid}"
            )])
        await call.message.answer("📝 Uyga vazifalar:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("stg_hw_do:"):
        parts2=call.data.split(":"); hw_id,tgid=int(parts2[1]),int(parts2[2])
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT mavzu,topshiriq FROM homework WHERE id=%s",(hw_id,))
        hw=cur2.fetchone(); cur2.close(); conn2.close()
        if not hw: await call.message.answer("❌ Topilmadi"); return True
        admin_state[user_id]=f"hw_submit:{hw_id}:{tgid}"
        await call.message.answer(f"📝 {hw[0]}\n\n{hw[1]}\n\nJavobingizni yozing:")
        return True

    if call.data.startswith("stg_reyting:"):
        tgid=int(call.data[12:]); await call.answer()
        from features import get_reyting
        r=get_reyting(tgid)
        txt="🏆 Reyting\n"+"─"*20+"\n\n"
        medals=["🥇","🥈","🥉"]
        for i,st in enumerate(r):
            m=medals[i] if i<3 else f"{i+1}."
            me=" ← Siz" if st["uid"]==user_id else ""
            txt+=f"{m} {st['ism']}{me}\n  ⭐{st['baho']} | 📋{st['davomat']}%\n\n"
        await call.message.answer(txt[:2000])
        return True

    if call.data.startswith("stg_leave_req:"):
        tgid=int(call.data[14:]); await call.answer()
        from togarak import send_leave_request
        res=send_leave_request(tgid,user_id)
        if res["ok"]:
            try:
                await call.bot.send_message(
                    res["teacher_id"],
                    f"⚠️ Chiqish so'rovi!\n👤 {res['user_name']}\n📚 {res['tg_nomi']}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(text="✅ Ruxsat", callback_data=f"tg_leave_ok:{user_id}|{tgid}"),
                        InlineKeyboardButton(text="❌ Yo'q",   callback_data=f"tg_leave_no:{user_id}|{tgid}"),
                    ]])
                )
            except: pass
            await call.message.answer("✅ So'rov yuborildi! O'qituvchi javobini kuting.")
        return True

    if call.data.startswith("tg_leave_ok:"):
        parts2=call.data[12:].split("|"); uid2,tgid2=int(parts2[0]),int(parts2[1])
        await call.answer()
        from togarak import confirm_leave
        confirm_leave(tgid2,uid2)
        try: await call.bot.send_message(uid2,"✅ To'garakdan chiqishingizga ruxsat berildi.")
        except: pass
        await call.message.edit_text("✅ Tasdiqlandi.",reply_markup=None)
        return True

    if call.data.startswith("tg_leave_no:"):
        parts2=call.data[12:].split("|"); uid2=int(parts2[0])
        await call.answer()
        try: await call.bot.send_message(uid2,"❌ Chiqish so'rovingiz rad etildi.")
        except: pass
        await call.message.edit_text("❌ Rad etildi.",reply_markup=None)
        return True

    if call.data.startswith("stg_albomlar:"):
        tgid=int(call.data[13:]); await call.answer()
        from togarak import get_reja
        reja=get_reja(tgid)
        # To'garak fanini olish
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT fan FROM togaraklar WHERE id=%s",(tgid,))
        tg_fan=(cur2.fetchone() or [None])[0]
        if not reja and tg_fan:
            # Reja yo'q — to'garak fanidan mavzular
            cur2.execute("""SELECT DISTINCT ON (mavzu_code) mavzu_code, mavzu_name
                FROM dts_tree WHERE subject_name=%s
                AND is_deleted=FALSE AND mavzu_code IS NOT NULL
                ORDER BY mavzu_code""",(tg_fan,))
            barcha=cur2.fetchall(); cur2.close(); conn2.close()
            if not barcha:
                await call.message.answer(f"❌ '{tg_fan}' fanida mavzu topilmadi!"); return True
            ALBOM=10; total=len(barcha)
            ICONS=["📗","📘","📙","📕","📓"]
            rows2=[]
            for i in range(0,total,ALBOM):
                chunk=barcha[i:i+ALBOM]
                n=i//ALBOM+1
                icon=ICONS[min(n-1,len(ICONS)-1)]
                rows2.append([InlineKeyboardButton(
                    text=f"{icon} {n}-albom ({len(chunk)} ta mavzu)",
                    callback_data=f"stg_fan_albom:{tgid}:{i}"
                )])
            rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"stg_info:{tgid}")])
            try: await call.message.edit_text(f"📚 {tg_fan} — Mavzular ({total} ta):",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
            except: await call.message.answer(f"📚 {tg_fan} — Mavzular ({total} ta):",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
            return True
        cur2.close(); conn2.close()
        if not reja:
            await call.message.answer("📚 Reja mavjud emas! O'qituvchi reja qo'shishi kerak."); return True
        ALBOM=10; total=len(reja)
        ICONS=["📗","📘","📙","📕","📓"]
        rows2=[]
        for i in range(0,total,ALBOM):
            chunk=reja[i:i+ALBOM]
            done=sum(1 for r in chunk if r["completed"])
            n=i//ALBOM+1
            bar="█"*done+"░"*(len(chunk)-done)
            icon=ICONS[min(n-1,len(ICONS)-1)]
            rows2.append([InlineKeyboardButton(
                text=f"{icon} {n}-albom [{bar}] {done}/{len(chunk)}",
                callback_data=f"stg_albom_open:{tgid}:{i}"
            )])
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"stg_info:{tgid}")])
        rows2.append([InlineKeyboardButton(text="☑️ Mavzular tanlash (test)",callback_data=f"stg_select_mavzu:{tgid}:0")])
        try: await call.message.edit_text(f"📚 Barcha mavzular ({total} ta):",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(f"📚 Barcha mavzular ({total} ta):",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("stg_select_mavzu:"):
        # Ko'p mavzu tanlash → test
        parts2=call.data[17:].split(":"); tgid=int(parts2[0]); page=int(parts2[1]) if len(parts2)>1 else 0
        await call.answer()
        # Tanlangan mavzular session da
        sel_key=f"sel_mavzu:{user_id}:{tgid}"
        selected=set(temp_user.get(sel_key,[]))
        # Mavzularni olish
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT fan FROM togaraklar WHERE id=%s",(tgid,))
        fan=(cur2.fetchone() or [None])[0]
        if fan:
            cur2.execute("""SELECT DISTINCT ON (mavzu_code) mavzu_code, mavzu_name
                FROM dts_tree WHERE subject_name=%s AND is_deleted=FALSE
                AND mavzu_code IS NOT NULL ORDER BY mavzu_code""",(fan,))
        else:
            cur2.execute("""SELECT DISTINCT ON (mavzu_code) mavzu_code, mavzu_name
                FROM dts_tree WHERE is_deleted=FALSE AND mavzu_code IS NOT NULL
                ORDER BY mavzu_code LIMIT 100""")
        barcha=cur2.fetchall(); cur2.close(); conn2.close()
        PER=8; total=len(barcha)
        page_items=barcha[page*PER:(page+1)*PER]
        rows2=[]
        for m in page_items:
            mc=m[0]; mn=(m[1] or m[0])[:35]
            icon="☑️" if mc in selected else "🔲"
            rows2.append([InlineKeyboardButton(
                text=f"{icon} {mn}",
                callback_data=f"stg_toggle:{tgid}:{mc}:{page}"
            )])
        nav=[]
        if page>0: nav.append(InlineKeyboardButton(text="◀️",callback_data=f"stg_select_mavzu:{tgid}:{page-1}"))
        nav.append(InlineKeyboardButton(text=f"{page*PER+1}-{min((page+1)*PER,total)}/{total}",callback_data="noop"))
        if (page+1)*PER<total: nav.append(InlineKeyboardButton(text="▶️",callback_data=f"stg_select_mavzu:{tgid}:{page+1}"))
        if nav: rows2.append(nav)
        if selected:
            rows2.append([InlineKeyboardButton(text=f"🧪 Test boshlash ({len(selected)} mavzu)",callback_data=f"stg_multi_test:{tgid}")])
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"stg_albomlar:{tgid}")])
        txt=f"☑️ Mavzularni belgilang ({len(selected)} ta tanlandi):"
        try: await call.message.edit_text(txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("stg_toggle:"):
        parts2=call.data[11:].split(":"); tgid,mc,page=int(parts2[0]),parts2[1],int(parts2[2])
        await call.answer()
        sel_key=f"sel_mavzu:{user_id}:{tgid}"
        selected=set(temp_user.get(sel_key,[]))
        if mc in selected: selected.discard(mc)
        else: selected.add(mc)
        temp_user[sel_key]=list(selected)
        # Sahifani yangilash
        call2_data=f"stg_select_mavzu:{tgid}:{page}"
        # Inline update
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT fan FROM togaraklar WHERE id=%s",(tgid,))
        fan=(cur2.fetchone() or [None])[0]
        cur2.execute("""SELECT DISTINCT ON (mavzu_code) mavzu_code, mavzu_name
            FROM dts_tree WHERE subject_name=%s AND is_deleted=FALSE
            AND mavzu_code IS NOT NULL ORDER BY mavzu_code""",(fan,)) if fan else None
        barcha=cur2.fetchall() if fan else []; PER=8; total=len(barcha)
        page_items=barcha[page*PER:(page+1)*PER]; cur2.close(); conn2.close()
        rows2=[]
        for m in page_items:
            mc2=m[0]; mn=(m[1] or m[0])[:35]
            icon="☑️" if mc2 in selected else "🔲"
            rows2.append([InlineKeyboardButton(text=f"{icon} {mn}",callback_data=f"stg_toggle:{tgid}:{mc2}:{page}")])
        nav=[]
        if page>0: nav.append(InlineKeyboardButton(text="◀️",callback_data=f"stg_select_mavzu:{tgid}:{page-1}"))
        nav.append(InlineKeyboardButton(text=f"{page*PER+1}-{min((page+1)*PER,total)}/{total}",callback_data="noop"))
        if (page+1)*PER<total: nav.append(InlineKeyboardButton(text="▶️",callback_data=f"stg_select_mavzu:{tgid}:{page+1}"))
        if nav: rows2.append(nav)
        if selected: rows2.append([InlineKeyboardButton(text=f"🧪 Test boshlash ({len(selected)} mavzu)",callback_data=f"stg_multi_test:{tgid}")])
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"stg_albomlar:{tgid}")])
        try: await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: pass
        return True

    if call.data.startswith("stg_multi_test:"):
        tgid=int(call.data[15:]); await call.answer()
        sel_key=f"sel_mavzu:{user_id}:{tgid}"
        selected=list(temp_user.get(sel_key,[]))
        if not selected: await call.message.answer("❌ Mavzu tanlanmagan!"); return True
        temp_user.pop(sel_key,None)
        # Barcha tanlangan mavzulardan test
        conn2=_get_db_conn();cur2=conn2.cursor()
        codes_in="','".join(selected)
        cur2.execute(f"""SELECT topic_code FROM dts_tree
            WHERE mavzu_code IN ('{codes_in}') AND is_deleted=FALSE""")
        topic_codes=[r[0] for r in cur2.fetchall()]
        if not topic_codes: topic_codes=selected
        cur2.execute("""SELECT question,option_a,option_b,option_c,option_d,
            correct_answer,explanation,question_type,is_latex,image_url,audio_text,language,time_limit
            FROM generated_tests WHERE topic_code=ANY(%s) ORDER BY RANDOM() LIMIT 20""",(topic_codes,))
        tests=cur2.fetchall(); cur2.close(); conn2.close()
        if not tests: await call.message.answer("❌ Test topilmadi!"); return True
        await call.message.answer(f"🧪 {len(selected)} mavzudan {len(tests)} ta test boshlanmoqda...")
        from test_engine import start_test
        await start_test(user_id, tests, call.message)
        return True

    if call.data.startswith("stg_fan_albom:"):
        parts2=call.data[14:].split(":"); tgid,start=int(parts2[0]),int(parts2[1])
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT fan FROM togaraklar WHERE id=%s",(tgid,))
        tg_fan=(cur2.fetchone() or [None])[0]
        cur2.execute("""SELECT DISTINCT ON (mavzu_code) mavzu_code, mavzu_name,
            (SELECT COUNT(*) FROM generated_tests WHERE topic_code IN
                (SELECT topic_code FROM dts_tree WHERE mavzu_code=d.mavzu_code)) as cnt
            FROM dts_tree d WHERE subject_name=%s
            AND is_deleted=FALSE AND mavzu_code IS NOT NULL
            ORDER BY mavzu_code OFFSET %s LIMIT 10""",(tg_fan,start))
        mavzular=cur2.fetchall(); cur2.close(); conn2.close()
        albom_n=start//10+1
        rows2=[[InlineKeyboardButton(
            text=f"{'✅' if m[2]>0 else '📖'} {(m[1] or m[0])[:38]} ({m[2]})",
            callback_data=f"ts_mavzu:{m[0]}"
        )] for m in mavzular]
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"stg_albomlar:{tgid}")])
        await call.message.answer(f"📗 {albom_n}-albom:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("stg_free_albom:"):
        parts2=call.data[15:].split(":"); tgid,start=int(parts2[0]),int(parts2[1])
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("""SELECT DISTINCT d.mavzu_name, d.mavzu_code, COUNT(g.id)
            FROM generated_tests g JOIN dts_tree d ON d.topic_code=g.topic_code
            WHERE d.is_deleted=FALSE AND d.mavzu_code IS NOT NULL
            GROUP BY d.mavzu_name, d.mavzu_code ORDER BY d.mavzu_code LIMIT 50""")
        mavzular=cur2.fetchall()[start:start+10]; cur2.close(); conn2.close()
        rows2=[[InlineKeyboardButton(
            text=f"📖 {(m[0] or m[1])[:40]} ({m[2]} test)",
            callback_data=f"ts_mavzu:{m[1]}"
        )] for m in mavzular]
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"stg_albomlar:{tgid}")])
        albom_n=start//10+1
        await call.message.answer(f"📗 {albom_n}-albom:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("stg_albom_open:"):
        parts2=call.data[15:].split(":"); tgid,start=int(parts2[0]),int(parts2[1])
        await call.answer()
        from togarak import get_reja
        reja=get_reja(tgid)
        chunk=reja[start:start+10]
        albom_n=start//10+1
        rows2=[]
        for r in chunk:
            icon="✅" if r["completed"] else "📖"
            rows2.append([InlineKeyboardButton(
                text=f"{icon} {r['tartib']}. {r['code'][:40]}",
                callback_data=f"stg_mavzu_test:{tgid}:{r['code']}"
            )])
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"stg_albomlar:{tgid}")])
        try: await call.message.edit_text(f"📗 {albom_n}-albom mavzulari:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(f"📗 {albom_n}-albom mavzulari:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("stg_mavzu_test:"):
        parts2=call.data[15:].split(":"); tgid=int(parts2[0]); mavzu_name=":".join(parts2[1:])
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        # Mavzu_name bo'yicha barcha kichik mavzularning topic_code larini olish
        cur2.execute("""SELECT DISTINCT topic_code FROM dts_tree
            WHERE mavzu_name=%s AND is_deleted=FALSE AND topic_code IS NOT NULL""",
            (mavzu_name,))
        topic_codes=[r[0] for r in cur2.fetchall()]
        if not topic_codes:
            # Agar topilmasa mavzu_name ni topic_code sifatida ham qidir
            topic_codes=[mavzu_name]
        cur2.execute("SELECT COUNT(*) FROM generated_tests WHERE topic_code=ANY(%s)",(topic_codes,))
        cnt=(cur2.fetchone() or [0])[0]; cur2.close(); conn2.close()
        if cnt==0:
            await call.message.answer(f"❌ '{mavzu_name[:40]}' mavzusida test yo'q!\n\nBu mavzu uchun testlar hali import qilinmagan."); return True
        from storage import user_state as _us
        if not isinstance(_us.get(user_id),dict): _us[user_id]={}
        _us[user_id].update({
            "ts_topic": topic_codes[0],
            "ts_topic_codes": topic_codes,
            "ts_mavzu_name": mavzu_name,
            "ts_count": min(20,cnt), "ts_diff":"all",
            "ts_timed":True, "ts_write":False,
            "_ts_cnt_total":cnt
        })
        await call.message.answer(
            f"🧪 {mavzu_name[:50]}\n📊 Jami: {cnt} ta savol\n\nSozlamalar:",
            reply_markup=_mk_ts_kb(_us[user_id],cnt)
        )
        return True

    if call.data.startswith("stg_baholar:"):
        tgid=int(call.data[12:]); await call.answer()
        from togarak import get_baholar
        rows2=get_baholar(tgid,user_id)
        if not rows2: await call.message.answer("📊 Hali baho qo'yilmagan!"); return True
        txt="📊 Baholaringiz:\n\n"
        for b in rows2:
            txt+=f"⭐ {b[0]}/5 — {b[1] or '—'}\n"
        await call.message.answer(txt[:2000])
        return True

    if call.data.startswith("stg_tolovlar:"):
        tgid=int(call.data[13:]); await call.answer()
        from togarak import get_tolov_status
        rows2=get_tolov_status(tgid,user_id)
        if not rows2: await call.message.answer("💰 Hali to'lov ma'lumoti yo'q!"); return True
        txt="💰 To'lovlar tarixi:\n\n"
        for t2 in rows2:
            txt+=f"📅 {t2[0]}: {t2[1]:,} so'm\n"
        await call.message.answer(txt[:2000])
        return True

    if call.data.startswith("stg_chat:"):
        tgid=int(call.data[9:]); await call.answer()
        from togarak import get_guruh_xabarlar
        msgs=get_guruh_xabarlar(tgid,20)
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT a.user_id,u.full_name FROM togarak_azolar a JOIN users u ON u.user_id=a.user_id WHERE a.togarak_id=%s AND a.aktiv=TRUE",(tgid,))
        azolar=cur2.fetchall()
        cur2.execute("SELECT teacher_id,nomi FROM togaraklar WHERE id=%s",(tgid,))
        tg2=cur2.fetchone(); cur2.close(); conn2.close()
        txt=f"💬 Guruh chat\n{'─'*20}\n"
        if not msgs: txt+="(Hali xabarlar yo'q)\n"
        for m in msgs[-15:]:
            vaqt=str(m["vaqt"])[11:16] if m["vaqt"] else ""
            txt+=f"👤 {m['ism']} {vaqt}\n{m['matn']}\n\n"
        rows2=[
            [InlineKeyboardButton(text="✍️ Xabar yozish",callback_data=f"stg_chat_write:{tgid}"),
             InlineKeyboardButton(text="🔄",callback_data=f"stg_chat:{tgid}")]
        ]
        dm_row=[]
        for az in azolar:
            if az[0]==user_id: continue
            name=(az[1] or "?").split()[0]
            dm_row.append(InlineKeyboardButton(text=f"👤{name}",callback_data=f"stg_dm:{tgid}:{az[0]}:0"))
        if tg2 and tg2[0]!=user_id:
            conn2=_get_db_conn();cur2=conn2.cursor()
            cur2.execute("SELECT full_name FROM users WHERE user_id=%s",(tg2[0],))
            tn=((cur2.fetchone() or ["O'q"])[0] or "O'q").split()[0]; cur2.close(); conn2.close()
            dm_row.insert(0,InlineKeyboardButton(text=f"👨‍🏫{tn}",callback_data=f"stg_dm:{tgid}:{tg2[0]}:0"))
        if dm_row: rows2.append(dm_row[:4])
        rows2.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"stg_info:{tgid}")])
        try: await call.message.edit_text(txt[:3000],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(txt[:3000],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("stg_chat_write:"):
        tgid=int(call.data[15:]); await call.answer()
        admin_state[user_id]=f"tg_send_msg:{tgid}:all"
        await call.message.answer("✍️ Xabar yozing:",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor",callback_data=f"stg_chat:{tgid}")]]))
        return True

    if call.data.startswith("stg_dm:"):
        parts2=call.data[7:].split(":"); tgid,uid2,pg=int(parts2[0]),int(parts2[1]),int(parts2[2])
        await call.answer()
        from togarak import get_personal_messages
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT full_name FROM users WHERE user_id=%s",(uid2,))
        uname=(cur2.fetchone() or ["?"])[0]; cur2.close(); conn2.close()
        msgs=get_personal_messages(tgid,user_id,uid2,30)
        per=10; total=len(msgs); p=max(0,min(pg,(total-1)//per if total else 0))
        page_msgs=msgs[p*per:(p+1)*per]
        txt=f"💬 {uname}\n{'─'*20}\n"
        if not page_msgs: txt+="(Hali xabar yo'q)"
        for m in page_msgs:
            vaqt=str(m["vaqt"])[11:16] if m["vaqt"] else ""
            me=m["sender"]==user_id
            txt+=f"{'-> Siz' if me else '<- '+m['ism']} {vaqt}\n{m['matn']}\n\n"
        nav=[]
        if p>0: nav.append(InlineKeyboardButton(text="⬅️",callback_data=f"stg_dm:{tgid}:{uid2}:{p-1}"))
        if (p+1)*per<total: nav.append(InlineKeyboardButton(text="➡️",callback_data=f"stg_dm:{tgid}:{uid2}:{p+1}"))
        rows2=[]
        if nav: rows2.append(nav)
        rows2.append([InlineKeyboardButton(text="✍️ Xabar",callback_data=f"stg_dm_write:{tgid}:{uid2}"),InlineKeyboardButton(text="🔄",callback_data=f"stg_dm:{tgid}:{uid2}:{p}")])
        rows2.append([InlineKeyboardButton(text="⬅️ Chat",callback_data=f"stg_chat:{tgid}")])
        admin_state[user_id]=f"tg_send_pm:{tgid}:{uid2}"
        try: await call.message.edit_text(txt[:3000],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        except: await call.message.answer(txt[:3000],reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("stg_dm_write:"):
        parts2=call.data[13:].split(":"); tgid,uid2=int(parts2[0]),int(parts2[1])
        await call.answer()
        admin_state[user_id]=f"tg_send_pm:{tgid}:{uid2}"
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT full_name FROM users WHERE user_id=%s",(uid2,))
        uname=(cur2.fetchone() or ["?"])[0]; cur2.close(); conn2.close()
        await call.message.answer(f"✍️ {uname} ga:",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor",callback_data=f"stg_dm:{tgid}:{uid2}:0")]]))
        return True


    if call.data.startswith("stg_leave:"):
        tgid=int(call.data[10:]); await call.answer()
        from togarak import leave_togarak
        if leave_togarak(tgid,user_id):
            await call.message.answer("✅ To'garakdan chiqdingiz!")
        return True

    # ── OTA-ONA CALLBACKLAR ──

    return False
