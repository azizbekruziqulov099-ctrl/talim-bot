"""cb_kabinet.py"""
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

def _create_new_account(telegram_id, name, rol_uz, sinf_txt):
    """Yangi akkaunt yaratish — ishonchli."""
    conn=_get_db_conn();cur=conn.cursor()
    try:
        # Yangi index
        cur.execute("SELECT COALESCE(MAX(account_index),-1)+1 FROM user_accounts WHERE telegram_id=%s",(telegram_id,))
        new_idx=cur.fetchone()[0]
        print(f"[new_acc] telegram={telegram_id} name={name} rol={rol_uz} idx={new_idx}")
        # Barchasini nofaol
        cur.execute("UPDATE user_accounts SET is_active=FALSE WHERE telegram_id=%s",(telegram_id,))
        # Yangi qo'shish
        cur.execute("""INSERT INTO user_accounts(telegram_id,account_index,full_name,role,class,is_active)
            VALUES(%s,%s,%s,%s,%s,TRUE)""",(telegram_id,new_idx,name,rol_uz,sinf_txt))
        # users ni yangilaymiz (aktiv akkaunt)
        # users yangilash (ON CONFLICT ishlamaydi — UPDATE keyin INSERT)
        cur.execute("UPDATE users SET full_name=%s,role=%s,class=%s WHERE user_id=%s",
                    (name,rol_uz,sinf_txt,telegram_id))
        if cur.rowcount==0:
            cur.execute("INSERT INTO users(user_id,full_name,role,class) VALUES(%s,%s,%s,%s)",
                        (telegram_id,name,rol_uz,sinf_txt))
        conn.commit()
        print(f"[new_acc] ✅ saqlandi idx={new_idx}")
        ok=True
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"[new_acc] ❌ {e}")
        conn.rollback(); ok=False
    cur.close();conn.close()
    return ok

async def handle_kb(call, user_id, admin_state, user_state, temp_user, bot):
    d=call.data
    if call.data == "parent_link":
        await call.answer()
        user_state[user_id]="parent_link_id"
        await call.message.answer(
            "👶 Farzandingizning Telegram ID sini yozing.\n\n"
            "Farzandingiz botda /id yozsin — ID ni ko'radi."
        )
        return True

    if call.data.startswith("parent_child:"):
        child_id=int(call.data[13:]); await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT full_name,class FROM users WHERE user_id=%s",(child_id,))
        child=cur2.fetchone(); cur2.close(); conn2.close()
        if not child: await call.message.answer("❌ Topilmadi"); return True
        rows2=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Rivojlanish",callback_data=f"parent_progress:{child_id}"),
             InlineKeyboardButton(text="📋 Yoqlama",callback_data=f"parent_yoqlama:{child_id}")],
            [InlineKeyboardButton(text="⭐ Baholar",callback_data=f"parent_baho:{child_id}"),
             InlineKeyboardButton(text="📝 Test ber",callback_data=f"parent_imtihon:{child_id}")],
        ])
        await call.message.answer(
            f"👶 {child[0]} ({child[1] or '-'})",
            reply_markup=rows2
        )
        return True

    if call.data.startswith("parent_progress:"):
        child_id=int(call.data[16:]); await call.answer()
        from togarak import get_student_togaraklar, get_student_progress, get_togarak_progress
        tgs=get_student_togaraklar(child_id)
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT full_name,class FROM users WHERE user_id=%s",(child_id,))
        child=cur2.fetchone(); cur2.close(); conn2.close()
        txt=f"📊 {child[0] if child else '?'} rivojlanishi\n{'─'*20}\n\n"
        if not tgs: txt+="Hali to'garakka a'zo emas."
        for t in tgs:
            prog=get_togarak_progress(t["id"])
            sp=get_student_progress(t["id"],child_id)
            txt+=f"📚 {t['nomi']}\n"
            txt+=f"  📖 O'tildi: {prog['pct']}%\n"
            txt+=f"  📋 Davomat: {sp['yoqlama_pct']}%\n"
            txt+=f"  ⭐ Baho: {sp['avg_baho']}\n\n"
        await call.message.answer(txt[:3000])
        return True

    if call.data.startswith("parent_yoqlama:"):
        child_id=int(call.data[15:]); await call.answer()
        from togarak import get_student_togaraklar
        tgs=get_student_togaraklar(child_id)
        txt="📋 Yoqlama\n"+"─"*20+"\n\n"
        for t in tgs:
            conn2=_get_db_conn();cur2=conn2.cursor()
            cur2.execute("""SELECT sana,holat FROM togarak_yoqlama
                WHERE togarak_id=%s AND user_id=%s ORDER BY sana DESC LIMIT 10""",
                (t["id"],child_id))
            rows2=cur2.fetchall(); cur2.close(); conn2.close()
            txt+=f"📚 {t['nomi']}:\n"
            for y in rows2:
                icon="✅" if y[1]=="keldi" else ("⏰" if y[1]=="kech" else "❌")
                txt+=f"  {icon} {str(y[0])[:10]}\n"
            txt+="\n"
        await call.message.answer(txt[:3000])
        return True

    if call.data.startswith("parent_baho:"):
        child_id=int(call.data[12:]); await call.answer()
        from togarak import get_student_togaraklar, get_baholar
        tgs=get_student_togaraklar(child_id)
        txt="⭐ Baholar\n"+"─"*20+"\n\n"
        for t in tgs:
            baholar=get_baholar(t["id"],child_id)
            txt+=f"📚 {t['nomi']}:\n"
            for b in baholar[:5]:
                txt+=f"  ⭐{b[0]}/5 — {b[1] or ''}\n"
            txt+="\n"
        await call.message.answer(txt[:3000])
        return True

    if call.data.startswith("parent_imtihon:"):
        child_id=int(call.data[15:]); await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT class FROM users WHERE user_id=%s",(child_id,))
        cls=(cur2.fetchone() or [None])[0]
        sinf=str(cls or "").replace("-sinf","").strip()
        cur2.execute("""SELECT topic_code,mavzu FROM dts_tree
            WHERE sinf=%s AND NOT is_deleted ORDER BY RANDOM() LIMIT 10""",(sinf,))
        topics=cur2.fetchall(); cur2.close(); conn2.close()
        if not topics:
            await call.message.answer("❌ Mavzular topilmadi. Sinf belgilanmagan bo'lishi mumkin."); return True
        rows2=[[InlineKeyboardButton(
            text=f"📌 {t[1][:40]}",callback_data=f"parent_test:{child_id}:{t[0]}"
        )] for t in topics]
        await call.message.answer("📝 Qaysi mavzudan test bermoqchisiz?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("parent_test:"):
        parts2=call.data[12:].split(":"); child_id=int(parts2[0]); tcode=parts2[1]
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("""SELECT question,option_a,option_b,option_c,option_d,
            correct_answer,explanation,question_type,is_latex,image_url,audio_text,language,time_limit
            FROM generated_tests WHERE topic_code=%s ORDER BY RANDOM() LIMIT 10""",(tcode,))
        tests=cur2.fetchall(); cur2.close(); conn2.close()
        if not tests:
            await call.message.answer("❌ Bu mavzuda testlar yo'q!"); return True
        # Farzandga test yuborish
        try:
            await call.bot.send_message(child_id,
                f"📝 Ota-onangiz sizga test yubordi!\nMavzu: {tcode}")
            from test_engine import start_test
            await start_test(child_id, tests, call.message)
            await call.message.answer("✅ Test farzandingizga yuborildi!")
        except Exception as e:
            await call.message.answer(f"❌ Xato: {e}")
        return True

    if call.data.startswith("parent_msg_teacher:"):
        teacher_id=int(call.data[19:]); await call.answer()
        admin_state[user_id]=f"parent_send_msg:{teacher_id}"
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT full_name FROM users WHERE user_id=%s",(teacher_id,))
        tname=(cur2.fetchone() or ["O'qituvchi"])[0]; cur2.close(); conn2.close()
        await call.message.answer(f"✍️ {tname} ga xabar yozing:")
        return True

    # ── KABINET CALLBACKLAR ──
    if call.data == "kb_change_name":
        await call.answer()
        user_state[user_id]="change_name"
        await call.message.answer("✏️ Yangi ismingizni yozing:")
        return True

    if call.data == "kb_change_role":
        await call.answer()
        rows2=[
            [InlineKeyboardButton(text="🧒 O'quvchi",callback_data="kb_set_role:student")],
            [InlineKeyboardButton(text="👨‍🏫 O'qituvchi",callback_data="kb_set_role:teacher")],
            [InlineKeyboardButton(text="👨‍👩‍👧 Ota-ona",callback_data="kb_set_role:parent")],
        ]
        await call.message.answer("🎭 Yangi rolni tanlang:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("kb_set_role:"):
        rol=call.data[12:]; await call.answer()
        rol_uz={"student":"O'quvchi","teacher":"O'qituvchi","parent":"Ota-ona"}.get(rol,rol)
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("UPDATE users SET role=%s WHERE user_id=%s",(rol_uz,user_id))
        cur2.execute("UPDATE user_accounts SET role=%s WHERE telegram_id=%s AND is_active=TRUE",(rol_uz,user_id))
        conn2.commit();cur2.close();conn2.close()
        from keyboards import get_main_keyboard
        await call.message.answer(f"✅ Rol o'zgartirildi: {rol_uz}",reply_markup=get_main_keyboard(rol_uz))
        return True

    if call.data == "kb_new_acc":
        await call.answer()
        # Yangi akkaunt — ism so'raymiz
        user_state[user_id] = "nacc_name"
        await call.message.answer(
            "➕ <b>Yangi akkaunt</b>\n\nYangi akkaunt uchun F.I.Sh yozing:\nMasalan: Aliyev Ali",
            parse_mode="HTML"
        )
        return True

    if call.data.startswith("nacc_rol:"):
        # Yangi akkaunt — rol tanlandi, DARHOL saqlaymiz
        parts2=call.data[9:].split("|")
        rol=parts2[0]; name=parts2[1] if len(parts2)>1 else "Foydalanuvchi"
        await call.answer()
        rol_uz={"student":"O'quvchi","teacher":"O'qituvchi","parent":"Ota-ona"}.get(rol,rol)
        if rol=="student":
            # Sinf so'raymiz
            user_state[user_id]=f"nacc_sinf|{name}"
            rows2=[[InlineKeyboardButton(text=f"{i}-sinf",callback_data=f"nacc_save:{name}|{i}") for i in range(j,j+4) if i<=11] for j in range(1,12,4)]
            await call.message.edit_text(f"🧒 {name}\n\nSinfni tanlang:",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        else:
            # Darhol saqlaymiz
            ok=_create_new_account(user_id,name,rol_uz,"")
            user_state.pop(user_id,None)
            from keyboards import get_main_keyboard
            if ok:
                await call.message.answer(f"✅ Yangi akkaunt yaratildi!\n👤 {name}\n🎭 {rol_uz}",reply_markup=get_main_keyboard(rol_uz))
            else:
                await call.message.answer("❌ Xatolik. Qayta urinib ko'ring.")
        return True

    if call.data.startswith("nacc_save:"):
        # O'quvchi — sinf tanlandi, saqlaymiz
        parts2=call.data[10:].split("|")
        name=parts2[0]; sinf=parts2[1]
        await call.answer()
        ok=_create_new_account(user_id,name,"O'quvchi",f"{sinf}-sinf")
        user_state.pop(user_id,None)
        from keyboards import get_main_keyboard
        if ok:
            await call.message.answer(f"✅ Yangi akkaunt yaratildi!\n👤 {name}\n🎭 O'quvchi {sinf}-sinf",reply_markup=get_main_keyboard("O'quvchi"))
        else:
            await call.message.answer("❌ Xatolik. Qayta urinib ko'ring.")
        return True

    if call.data == "kb_switch_acc":
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("""
            SELECT id, account_index, full_name, role, class, is_active
            FROM user_accounts WHERE telegram_id=%s
            ORDER BY account_index
        """, (user_id,))
        accs = cur2.fetchall(); cur2.close(); conn2.close()
        if not accs:
            await call.message.answer("❌ Akkaunt topilmadi"); return True
        rows2=[]
        for a in accs:
            aktiv = a[5]  # is_active
            sinf = f" {a[4]}" if a[4] else ""
            rol_uz = a[3] or "—"
            belgi = "✅" if aktiv else "👤"
            rows2.append([InlineKeyboardButton(
                text=f"{belgi} {a[2] or '—'} — {rol_uz}{sinf}",
                callback_data=f"kb_activate:{a[0]}"
            )])
        rows2.append([InlineKeyboardButton(text="➕ Yangi akkaunt",callback_data="kb_new_acc")])
        await call.message.answer(
            f"🔄 <b>Akkauntlaringiz</b> ({len(accs)} ta)\nAlmashtirish uchun tanlang:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2)
        )
        return True

    if call.data.startswith("kb_activate:"):
        acc_id2=int(call.data[12:]); await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("UPDATE user_accounts SET is_active=FALSE WHERE telegram_id=%s",(user_id,))
        cur2.execute("""
            UPDATE user_accounts SET is_active=TRUE WHERE id=%s
            RETURNING full_name, role, class
        """, (acc_id2,))
        row2=cur2.fetchone()
        if row2:
            cur2.execute("UPDATE users SET full_name=%s, role=%s, class=%s WHERE user_id=%s",
                        (row2[0],row2[1],row2[2],user_id))
        conn2.commit();cur2.close();conn2.close()
        from keyboards import get_main_keyboard
        sinf=f" {row2[2]}" if row2 and row2[2] else ""
        await call.message.answer(
            f"✅ Akkaunt almashtirildi!\n👤 {row2[0] if row2 else ''}\n🎭 {row2[1] if row2 else ''}{sinf}",
            reply_markup=get_main_keyboard(row2[1] if row2 else "")
        )
        return True

    if call.data == "ai_stop":
        await call.answer()
        user_state.pop(user_id, None)
        await call.message.answer("✅ AI yordamchi o'chirildi.")
        return True

    if call.data == "kb_togaraklar":
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("SELECT role FROM users WHERE user_id=%s",(user_id,))
        role2=str((cur2.fetchone() or [""])[0]); cur2.close(); conn2.close()
        from togarak import get_teacher_togaraklar, get_student_togaraklar
        if "qituvchi" in role2:
            tgs = get_teacher_togaraklar(user_id)
            rows2=[[InlineKeyboardButton(text=f"📚 {t['nomi']} ({t['azolar']}/{t['max']})",callback_data=f"tg_info:{t['id']}")] for t in tgs]
            rows2.append([InlineKeyboardButton(text="➕ Yangi to'garak", callback_data="tg_yangi")])
            await call.message.answer(f"📚 Mening to'garaklarim ({len(tgs)} ta):", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        else:
            tgs = get_student_togaraklar(user_id)
            rows2=[[InlineKeyboardButton(text=f"📚 {t['nomi']}",callback_data=f"stg_info:{t['id']}")] for t in tgs]
            rows2.append([InlineKeyboardButton(text="🔍 To'garak izlash", callback_data="stg_join")])
            await call.message.answer(f"📚 To'garaklar ({len(tgs)} ta):", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        return True

    if call.data.startswith("kb_change:"):
        field = call.data[10:]; await call.answer()
        prompts = {
            "name":   "✏️ Yangi ismingizni yozing (F.I.Sh):",
            "role":   None,
            "class":  None,
            "bdate":  "🎂 Tug'ilgan sanangizni yozing (KK.OO.YYYY):",
            "school": "🏛 Maktab nomini yozing:",
        }
        if field == "role":
            await call.message.answer("🎭 Yangi rolni tanlang:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🧒 O'quvchi",   callback_data="kb_set_role:O'quvchi")],
                    [InlineKeyboardButton(text="👨‍🏫 O'qituvchi", callback_data="kb_set_role:O'qituvchi")],
                    [InlineKeyboardButton(text="👨‍👩‍👧 Ota-ona",    callback_data="kb_set_role:Ota-ona")],
                ]))
        elif field == "class":
            rows2=[[InlineKeyboardButton(text=f"{i}-sinf",callback_data=f"kb_set_class:{i}") for i in range(j,j+4)] for j in range(1,12,4)]
            await call.message.answer("🏫 Sinfni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
        else:
            user_state[user_id] = f"kb_change_{field}"
            await call.message.answer(prompts[field])
        return True

    if call.data.startswith("kb_set_role:"):
        rol = call.data[12:]; await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("UPDATE users SET role=%s WHERE user_id=%s",(rol,user_id))
        try:
            cur2.execute("UPDATE user_accounts SET role=%s WHERE telegram_id=%s AND is_active=TRUE",(rol,user_id))
        except: pass
        conn2.commit();cur2.close();conn2.close()
        from keyboards import get_main_keyboard
        await call.message.answer(f"✅ Rol o'zgartirildi: {rol}", reply_markup=get_main_keyboard(rol))
        return True

    if call.data.startswith("kb_set_class:"):
        cls = call.data[13:]; await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("UPDATE users SET class=%s WHERE user_id=%s",(f"{cls}-sinf",user_id))
        conn2.commit();cur2.close();conn2.close()
        await call.message.answer(f"✅ Sinf o'zgartirildi: {cls}-sinf")
        return True

    if call.data == "kb_rereg":
        await call.answer()
        from register import start_registration
        await start_registration(call.message)
        return True

    if call.data == "kb_delete":
        await call.answer()
        await call.message.answer(
            "⚠️ Profilni o'chirishni tasdiqlaysizmi?\n\nBarcha ma'lumotlar o'chadi!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ Ha, o'chir", callback_data="kb_delete_confirm"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data="kb_delete_cancel"),
            ]])
        )
        return True

    if call.data == "kb_delete_confirm":
        await call.answer()
        conn2=_get_db_conn();cur2=conn2.cursor()
        cur2.execute("DELETE FROM users WHERE user_id=%s",(user_id,))
        conn2.commit();cur2.close();conn2.close()
        user_state.pop(user_id,None); temp_user.pop(user_id,None)
        from aiogram.types import ReplyKeyboardRemove
        await call.message.answer("✅ Profil o'chirildi. Qayta kirish uchun /start bosing", reply_markup=ReplyKeyboardRemove())
        return True

    if call.data == "kb_delete_cancel":
        await call.answer("❌ Bekor qilindi"); return True

    if call.data.startswith("reg_quick:"):
        await call.answer()
        user_id2 = call.from_user.id
        temp_user[user_id2] = {"quick": True}
        # Rol tanlash
        await call.message.edit_text(
            "⚡ Tez kirish\n\nRolni tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🧒 O'quvchi",   callback_data="rq_rol:student")],
                [InlineKeyboardButton(text="👨‍🏫 O'qituvchi", callback_data="rq_rol:teacher")],
                [InlineKeyboardButton(text="👨‍👩‍👧 Ota-ona",    callback_data="rq_rol:parent")],
            ])
        )
        return True

    if call.data.startswith("rq_rol:"):
        rol = call.data[7:]; await call.answer()
        user_id2 = call.from_user.id
        print(f"[rq_rol] user={user_id2} rol={rol}")
        if user_id2 not in temp_user or not isinstance(temp_user.get(user_id2),dict):
            temp_user[user_id2] = {}
        temp_user[user_id2]["role"] = rol
        user_state[user_id2] = f"rq_name:{rol}"
        print(f"[rq_rol] user_state set to rq_name:{rol}")
        rol_uz = {"student":"O'quvchi","teacher":"O'qituvchi","parent":"Ota-ona"}.get(rol,rol)
        try:
            await call.message.edit_text(f"⚡ {rol_uz}\n\nF.I.Sh yozing:\nMasalan: Aliyev Ali Aliyevich")
        except Exception:
            await call.message.answer(f"⚡ {rol_uz}\n\nF.I.Sh yozing:\nMasalan: Aliyev Ali Aliyevich")
        return True

    if call.data.startswith("reg_full:"):
        await call.answer()
        # To'liq ro'yxat — avvalgi oqim
        from register import _ik, ROLES
        user_id2 = call.from_user.id
        temp_user[user_id2] = {}
        user_state[user_id2] = "reg_wait_inline"
        await call.message.edit_text("📋 Ro'yxatdan o'tish\n\nRolni tanlang:", reply_markup=_ik(ROLES,"role",cols=1))
        return True

    if call.data.startswith("rq_sinf:"):
        # Sinf tanlash — to'liq saqlash (mustaqil)
        sinf = call.data[8:]; await call.answer()
        user_id2 = call.from_user.id
        data = temp_user.get(user_id2, {}) if isinstance(temp_user.get(user_id2),dict) else {}
        name = data.get("full_name","Foydalanuvchi")
        rol = data.get("role","student")
        sinf_txt = f"{sinf}-sinf"
        rol_uz = {"student":"O'quvchi","teacher":"O'qituvchi","parent":"Ota-ona"}.get(rol,rol)
        conn2=_get_db_conn();cur2=conn2.cursor()
        try:
            cur2.execute("UPDATE users SET full_name=%s,role=%s,class=%s WHERE user_id=%s",
                        (name,rol_uz,sinf_txt,user_id2))
            if cur2.rowcount==0:
                cur2.execute("INSERT INTO users(user_id,full_name,role,class) VALUES(%s,%s,%s,%s)",
                            (user_id2,name,rol_uz,sinf_txt))
            cur2.execute("SELECT MAX(account_index) FROM user_accounts WHERE telegram_id=%s",(user_id2,))
            max_idx=(cur2.fetchone() or [None])[0]
            new_idx = 0 if max_idx is None else max_idx+1
            cur2.execute("UPDATE user_accounts SET is_active=FALSE WHERE telegram_id=%s",(user_id2,))
            cur2.execute("""
                INSERT INTO user_accounts(telegram_id,account_index,full_name,role,class,is_active)
                VALUES(%s,%s,%s,%s,%s,TRUE)
                ON CONFLICT(telegram_id,account_index) DO UPDATE
                SET full_name=EXCLUDED.full_name,role=EXCLUDED.role,class=EXCLUDED.class,is_active=TRUE
            """, (user_id2, new_idx, name, rol_uz, sinf_txt))
            conn2.commit()
        except Exception as e:
            print(f"rq_sinf save: {e}"); conn2.rollback()
        cur2.close();conn2.close()
        temp_user.pop(user_id2,None); user_state.pop(user_id2,None)
        from keyboards import get_main_keyboard
        await call.message.answer(
            f"✅ Xush kelibsiz, {name}!\n🎯 {rol_uz} {sinf_txt}",
            reply_markup=get_main_keyboard(rol_uz)
        )
        return True

    if call.data.startswith("reg:"):
        from register import reg_callback
        await reg_callback(call)
        return True

    if call.data.startswith("reg_yr:"):
        from register import reg_year_callback
        await reg_year_callback(call)
        return True

    if call.data == "speak_question":

        await speak_question(
            call.from_user.id,
            call.message
        )

        return True

    if call.data == "speak_a":

        await speak_a(
            call.from_user.id,
            call.message
        )

        return True

    if call.data == "speak_b":

        await speak_b(
            call.from_user.id,
            call.message
        )
        return True

    if call.data == "speak_c":

        await speak_c(
            call.from_user.id,
            call.message
        )
        return True

    if call.data == "speak_d":

        await speak_d(
            call.from_user.id,
            call.message
        )
        return True

    if call.data == "cancel_import":
        await state.clear()
        admin_state.pop(user_id, None)
        await call.message.edit_text("❌ Import bekor qilindi")
        await call.message.answer("🏠 Bosh menyu", reply_markup=get_main_keyboard("Admin"))
        return True

    if call.data.startswith("resume_lesson:"):
        from lesson_engine import build_lesson_data, show_main_step, LESSON_COLS
        await call.answer()
        tc  = call.data.split(":")[1]
        uid = call.from_user.id
        # lesson_progress dan step olish
        try:
            _conn = _get_db_conn(); _cur = _conn.cursor()
            _cur.execute("SELECT current_step FROM lesson_progress WHERE user_id=%s AND topic_code=%s", (uid, tc))
            _row = _cur.fetchone()
            _step = _row[0] if _row else 0
            _cur.execute("SELECT * FROM teacher_lessons WHERE topic_code=%s", (tc,))
            _lesson = _cur.fetchone()
            _cur.execute("SELECT grade, subject_name, mavzu_name FROM dts_tree WHERE topic_code=%s LIMIT 1", (tc,))
            _t = _cur.fetchone()
            _cur.execute("SELECT full_name, gender FROM users WHERE user_id=%s", (uid,))
            _u = _cur.fetchone()
            _cur.close(); _conn.close()
        except Exception as _e:
            await call.message.answer(f"❌ Xato: {_e}"); return True
        if not _lesson:
            await call.message.answer("❌ Dars topilmadi"); return True
        _main, _simple = build_lesson_data(_lesson)
        lesson_state[uid] = {
            "topic_code": tc, "main_parts": _main, "simple_parts": _simple,
            "main_step": _step, "simple_step": 0, "mode": "main",
            "total": len(_main),
            "full_name": _u[0] if _u else "O'quvchi",
            "fan": _t[1] if _t else "", "mavzu": _t[2] if _t else tc,
            "gender": _u[1] if _u else "",
            "lesson_msg_id": None, "lesson_has_photo": False, "voice_msg_id": None,
        }
        user_state[uid] = "in_lesson"
        await call.message.answer(f"▶️ {_step+1}-qadamdan davom etilmoqda...")
        await show_main_step(uid, call.message.chat.id)
        return True

    if call.data.startswith("restart_lesson:"):
        await call.answer()
        tc = call.data.split(":")[1]
        try:
            _conn = _get_db_conn(); _cur = _conn.cursor()
            _cur.execute("DELETE FROM lesson_progress WHERE user_id=%s", (call.from_user.id,))
            _conn.commit(); _cur.close(); _conn.close()
        except: pass
        await open_teacher_lesson(call.message, topic_code=tc, _user_id=call.from_user.id)
        return True

    if call.data == "lesson_prev":
        from lesson_engine import lesson_prev
        await call.answer()
        await lesson_prev(call.from_user.id, call.message.chat.id)
        return True

    if call.data == "lesson_next":
        from lesson_engine import lesson_next
        await call.answer()
        await lesson_next(call.from_user.id, call.message.chat.id)
        return True

    if call.data == "speak_all":
        from test_engine import speak_all_question
        await call.answer()
        await speak_all_question(call.from_user.id)
        return True

    if call.data == "test_skip":
        from test_engine import test_skip
        await call.answer()
        await test_skip(call.from_user.id)
        return True

    if call.data == "lesson_speak":
        from lesson_engine import lesson_speak
        await call.answer()
        await lesson_speak(call.from_user.id, call.message.chat.id)
        return True

    if call.data == "lesson_help":
        from lesson_engine import lesson_help_open
        await call.answer()
        await lesson_help_open(call.from_user.id, call.message.chat.id)
        return True

    if call.data == "lesson_help_next":
        from lesson_engine import lesson_help_next
        await call.answer()
        await lesson_help_next(call.from_user.id, call.message.chat.id)
        return True

    if call.data == "lesson_help_prev":
        from lesson_engine import lesson_help_prev
        await call.answer()
        await lesson_help_prev(call.from_user.id, call.message.chat.id)
        return True

    if call.data == "lesson_help_close":
        from lesson_engine import lesson_help_close
        await call.answer()
        await lesson_help_close(call.from_user.id, call.message.chat.id)
        return True

    if call.data == "lesson_exit":
        from lesson_engine import lesson_exit
        await call.answer()
        await lesson_exit(call.from_user.id, call.message.chat.id)
        return True

    if call.data == "lesson_finish_confirm":
        from lesson_engine import lesson_finish_and_test
        from storage import lesson_state as _ls
        await call.answer()
        tc = (_ls.get(call.from_user.id) or {}).get("topic_code", "")
        await lesson_finish_and_test(call.from_user.id, call.message.chat.id, tc)
        return True

    if call.data in ("tset_start_quick", "tset_start_force"):
        from datetime import datetime
        now        = datetime.now()
        hour       = now.hour
        weekday    = now.weekday()
        is_night   = hour >= 22 or hour < 6
        is_weekend = weekday >= 5
        forced     = call.data == "tset_start_force"

        if is_night and not forced:
            await call.answer("🌙 Tun vaqti! Uxlash sog'liq uchun muhim.", show_alert=True)
            return True

        if is_weekend and not forced:
            await call.answer()
            await call.message.answer(
                "🏖 Bugun dam olish kuni!\n\nBaribir test ishlaysizmi?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✅ Ha, test", callback_data="tset_start_force"),
                    InlineKeyboardButton(text="🎮 Yo'q, dam olaman", callback_data="go_rest"),
                ]])
            )
            return True

        await call.answer()
        conn2 = _get_db_conn()
        cur2  = conn2.cursor()
        cur2.execute("SELECT class FROM users WHERE user_id=%s", (user_id,))
        row = cur2.fetchone()
        grade = row[0] if row else "5"
        cur2.execute("""
            SELECT question, option_a, option_b, option_c, option_d,
                   correct_answer, explanation, question_type, is_latex,
                   image_url, audio_text, language, time_limit
            FROM generated_tests
            WHERE topic_code IN (
                SELECT topic_code FROM dts_tree WHERE grade=%s AND is_deleted=FALSE
            )
            AND question IS NOT NULL AND option_a IS NOT NULL
            ORDER BY RANDOM() LIMIT 20
        """, (grade,))
        tests = cur2.fetchall()
        cur2.close(); conn2.close()
        if not tests:
            await call.answer("❌ Testlar topilmadi!", show_alert=True)
            return True
        await start_test(user_id, tests, call.message)
        return True

    if call.data == "test_next_from_result":
        await call.answer()
        from test_engine import test_sessions, next_question
        session = test_sessions.get(call.from_user.id)
        if not session:
            await call.answer("❌ Test tugagan", show_alert=True)
            return True
        await next_question(call.from_user.id, call.message)
        return True

    if call.data == "noop_timer":
        await call.answer("⏱ Vaqt ketmoqda...")
        return True

    if call.data == "test_settings":
        await call.answer()
        from storage import user_state as us
        if not isinstance(us.get(user_id), dict):
            us[user_id] = {}
        # O'quvchi sinfi
        try:
            _cn = _get_db_conn(); _cc = _cn.cursor()
            _cc.execute("SELECT class FROM users WHERE user_id=%s", (user_id,))
            _gr = _cc.fetchone()
            _my_g = str(_gr[0]) if _gr and _gr[0] else "1"
            _cc.close(); _cn.close()
        except: _my_g = "1"

        us[user_id]["test_settings"] = {
            "count": 20, "diff": "all",
            "timed": True, "images": True,
            "write": False, "grades": [_my_g]
        }

        # Barcha mavjud sinflar
        try:
            _cn = _get_db_conn(); _cc = _cn.cursor()
            _cc.execute("""SELECT grade FROM (SELECT DISTINCT grade FROM dts_tree WHERE is_deleted=FALSE) _g
                ORDER BY CASE WHEN grade ~ '^[0-9]+$' THEN grade::int ELSE 9999 END, grade""")
            _all_gr = [r[0] for r in _cc.fetchall()]
            _cc.close(); _cn.close()
        except: _all_gr = [_my_g]

        def _mk_settings_kb(s2, all_gr):
            def c(cond): return "✅ " if cond else ""
            cnt   = s2["count"]
            diff  = s2["diff"]
            timed = s2["timed"]
            write = s2.get("write", False)
            sel_gr = s2.get("grades", [])
            rows = []
            # Sinf tanlash
            grade_row = []
            for _g in all_gr:
                lbl = f"{_g}-sinf" if str(_g).isdigit() else str(_g)
                grade_row.append(InlineKeyboardButton(
                    text=f"{c(str(_g) in [str(x) for x in sel_gr])}{lbl}",
                    callback_data=f"tset_grade_{_g}"
                ))
                if len(grade_row) == 3:
                    rows.append(grade_row); grade_row = []
            if grade_row: rows.append(grade_row)
            rows.append([
                InlineKeyboardButton(text=f"{c(cnt==20)}20 ta", callback_data="tset_count_20"),
                InlineKeyboardButton(text=f"{c(cnt==40)}40 ta", callback_data="tset_count_40"),
                InlineKeyboardButton(text=f"{c(cnt==60)}60 ta", callback_data="tset_count_60"),
            ])
            rows.append([
                InlineKeyboardButton(text=f"{c(diff=='oson')}🟢 Oson",   callback_data="tset_diff_oson"),
                InlineKeyboardButton(text=f"{c(diff=='orta')}🟡 O'rta",  callback_data="tset_diff_orta"),
                InlineKeyboardButton(text=f"{c(diff=='qiyin')}🔴 Qiyin", callback_data="tset_diff_qiyin"),
                InlineKeyboardButton(text=f"{c(diff=='all')}🌈 Aralash",  callback_data="tset_diff_all"),
            ])
            rows.append([
                InlineKeyboardButton(text=f"{c(timed)}⏱ Vaqtli",   callback_data="tset_time_on"),
                InlineKeyboardButton(text=f"{c(not timed)}∞ Vaqtsiz", callback_data="tset_time_off"),
            ])
            rows.append([
                InlineKeyboardButton(text=f"{c(write)}✍️ Yozuvli ham", callback_data="tset_write_on"),
                InlineKeyboardButton(text=f"{c(not write)}🔘 Faqat tugmali", callback_data="tset_write_off"),
            ])
            rows.append([InlineKeyboardButton(text="▶️ Boshlash", callback_data="tset_start")])
            return InlineKeyboardMarkup(inline_keyboard=rows)

        us[user_id]["_all_grades"] = _all_gr
        await call.message.answer(
            "⚙️ Test sozlamalari:\n\nSinf, son, qiyinlik va turni tanlang:",
            reply_markup=_mk_settings_kb(us[user_id]["test_settings"], _all_gr)
        )
        return True

    if call.data.startswith("tset_"):
        from storage import user_state as us
        if not isinstance(us.get(user_id), dict):
            us[user_id] = {}
        if "test_settings" not in us[user_id]:
            us[user_id]["test_settings"] = {
                "count": 20, "diff": "all",
                "timed": True, "images": True, "write": False
            }

        s = us[user_id]["test_settings"]

        if call.data.startswith("tset_grade_"):
            grade_val = call.data.replace("tset_grade_", "")
            sel = s.get("grades", [])
            sel_str = [str(x) for x in sel]
            if str(grade_val) in sel_str:
                if len(sel) > 1:  # Kamida 1 ta qolsin
                    s["grades"] = [x for x in sel if str(x) != str(grade_val)]
            else:
                s["grades"] = sel + [grade_val]
            await call.answer(f"✅ {grade_val}")
        elif call.data.startswith("tset_count_"):
            s["count"] = int(call.data.replace("tset_count_", ""))
            await call.answer(f"✅ {s['count']} ta savol")
        elif call.data.startswith("tset_diff_"):
            s["diff"] = call.data.replace("tset_diff_", "")
            diff_names = {"oson": "Oson 🟢", "orta": "O'rta 🟡", "qiyin": "Qiyin 🔴", "all": "Aralash 🌈"}
            await call.answer(f"✅ {diff_names.get(s['diff'], s['diff'])}")
        elif call.data == "tset_time_on":
            s["timed"] = True
            await call.answer("✅ Vaqtli")
        elif call.data == "tset_time_off":
            s["timed"] = False
            await call.answer("✅ Vaqtsiz")
        elif call.data == "tset_img_on":
            s["images"] = True
            await call.answer("✅ Rasmli")
        elif call.data == "tset_img_off":
            s["images"] = False
            await call.answer("✅ Rasmsiz")
        elif call.data == "tset_write_on":
            s["write"] = True
            await call.answer("✅ Yozuvli savollar ham")
        elif call.data == "tset_write_off":
            s["write"] = False
            await call.answer("✅ Faqat tugmali savollar")

        # Klaviaturani yangilash
        if not call.data == "tset_start":
            from storage import user_state as _us2
            _all_gr2 = _us2.get(user_id, {}).get("_all_grades", []) if isinstance(_us2.get(user_id), dict) else []

            def _mk_kb2(s2, all_gr):
                def c(cond): return "✅ " if cond else ""
                cnt   = s2["count"]; diff  = s2["diff"]
                timed = s2["timed"]; write = s2.get("write", False)
                sel_gr = [str(x) for x in s2.get("grades", [])]
                rows = []
                grade_row = []
                for _g in all_gr:
                    lbl = f"{_g}-sinf" if str(_g).isdigit() else str(_g)
                    grade_row.append(InlineKeyboardButton(
                        text=f"{c(str(_g) in sel_gr)}{lbl}",
                        callback_data=f"tset_grade_{_g}"
                    ))
                    if len(grade_row) == 3:
                        rows.append(grade_row); grade_row = []
                if grade_row: rows.append(grade_row)
                rows.append([
                    InlineKeyboardButton(text=f"{c(cnt==20)}20 ta", callback_data="tset_count_20"),
                    InlineKeyboardButton(text=f"{c(cnt==40)}40 ta", callback_data="tset_count_40"),
                    InlineKeyboardButton(text=f"{c(cnt==60)}60 ta", callback_data="tset_count_60"),
                ])
                rows.append([
                    InlineKeyboardButton(text=f"{c(diff=='oson')}🟢 Oson",   callback_data="tset_diff_oson"),
                    InlineKeyboardButton(text=f"{c(diff=='orta')}🟡 O'rta",  callback_data="tset_diff_orta"),
                    InlineKeyboardButton(text=f"{c(diff=='qiyin')}🔴 Qiyin", callback_data="tset_diff_qiyin"),
                    InlineKeyboardButton(text=f"{c(diff=='all')}🌈 Aralash",  callback_data="tset_diff_all"),
                ])
                rows.append([
                    InlineKeyboardButton(text=f"{c(timed)}⏱ Vaqtli",     callback_data="tset_time_on"),
                    InlineKeyboardButton(text=f"{c(not timed)}∞ Vaqtsiz", callback_data="tset_time_off"),
                ])
                rows.append([
                    InlineKeyboardButton(text=f"{c(write)}✍️ Yozuvli ham",   callback_data="tset_write_on"),
                    InlineKeyboardButton(text=f"{c(not write)}🔘 Faqat tugmali", callback_data="tset_write_off"),
                ])
                rows.append([InlineKeyboardButton(text="▶️ Boshlash", callback_data="tset_start")])
                return InlineKeyboardMarkup(inline_keyboard=rows)

            new_kb = _mk_kb2(s, _all_gr2)
            try:
                await call.message.edit_reply_markup(reply_markup=new_kb)
            except Exception:
                pass
            return True
        elif call.data == "tset_start":
            # Test boshlash — tanlangan sinflardan
            conn2 = _get_db_conn()
            cur2  = conn2.cursor()

            sel_grades = s.get("grades", [])
            if not sel_grades:
                cur2.execute("SELECT class FROM users WHERE user_id=%s", (user_id,))
                row = cur2.fetchone()
                sel_grades = [row[0] if row else "1"]

            diff_filter = "" if s["diff"] == "all" else f"AND difficulty='{s['diff']}'"
            type_filter = "" if s.get("write") else "AND question_type != 'write_answer'"

            grade_placeholders = ",".join(["%s"] * len(sel_grades))
            cur2.execute(f"""
                SELECT question, option_a, option_b, option_c, option_d,
                       correct_answer, explanation, question_type, is_latex,
                       image_url, audio_text, language, time_limit
                FROM generated_tests
                WHERE topic_code IN (
                    SELECT topic_code FROM dts_tree
                    WHERE grade IN ({grade_placeholders}) AND is_deleted=FALSE
                )
                AND question IS NOT NULL
                {diff_filter}
                {type_filter}
                ORDER BY RANDOM()
                LIMIT %s
            """, (*sel_grades, s["count"]))
            tests = cur2.fetchall()
            cur2.close(); conn2.close()

            if not tests:
                await call.answer("❌ Testlar topilmadi!", show_alert=True)
                return

            # Vaqtsiz bo'lsa time_limit = 0
            if not s["timed"]:
                tests = [(*t[:12], 0) for t in tests]

            await call.answer()
            await start_test(user_id, tests, call.message)
        return True

    elif True:  # test_sessions tekshiruvi test_engine da
        await call.answer(
            "♻️ Bot yangilangan. Qayta boshlang.",
            show_alert=True
        )
        return True


    return False
