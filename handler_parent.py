"""handler_parent.py — Ota-ona handlerlari"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from shared import *

router = Router()

@router.message(F.text == "👶 Farzandim")
async def parent_farzandim(message: Message):
    user_id = message.from_user.id
    conn2=_get_db_conn();cur2=conn2.cursor()
    cur2.execute("""SELECT u.user_id,u.full_name,u.class FROM parent_child p
        JOIN users u ON u.user_id=p.child_id WHERE p.parent_id=%s""",(user_id,))
    bolalar=cur2.fetchall(); cur2.close(); conn2.close()
    rows2=[[InlineKeyboardButton(
        text=f"👶 {b[1]} ({b[2] or '-'})",
        callback_data=f"parent_child:{b[0]}"
    )] for b in bolalar]
    rows2.append([InlineKeyboardButton(text="➕ Farzand ulash",callback_data="parent_link")])
    txt=f"👶 Farzandlarim ({len(bolalar)} ta):" if bolalar else "👶 Hali farzand ulanmagan.\n\nFarzandingiz bot ID sini oling va ulang."
    await message.answer(txt,reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))

@router.message(F.text == "📊 Nazorat")
async def parent_nazorat(message: Message):
    user_id = message.from_user.id
    conn2=_get_db_conn();cur2=conn2.cursor()
    cur2.execute("""SELECT u.user_id,u.full_name FROM parent_child p
        JOIN users u ON u.user_id=p.child_id WHERE p.parent_id=%s""",(user_id,))
    bolalar=cur2.fetchall(); cur2.close(); conn2.close()
    if not bolalar: await message.answer("👶 Avval farzand ulang!"); return
    rows2=[[InlineKeyboardButton(text=f"📊 {b[1]}",callback_data=f"parent_progress:{b[0]}")] for b in bolalar]
    await message.answer("📊 Qaysi farzandni ko'rmoqchisiz?",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))

@router.message(F.text == "📋 Yoqlama")
async def parent_yoqlama_btn(message: Message):
    user_id = message.from_user.id
    conn2=_get_db_conn();cur2=conn2.cursor()
    cur2.execute("""SELECT u.user_id,u.full_name FROM parent_child p
        JOIN users u ON u.user_id=p.child_id WHERE p.parent_id=%s""",(user_id,))
    bolalar=cur2.fetchall(); cur2.close(); conn2.close()
    if not bolalar: await message.answer("👶 Avval farzand ulang!"); return
    rows2=[[InlineKeyboardButton(text=f"📋 {b[1]}",callback_data=f"parent_yoqlama:{b[0]}")] for b in bolalar]
    await message.answer("📋 Qaysi farzandning yoqlamasini ko'rmoqchisiz?",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))

@router.message(F.text == "⭐ Baholar")
async def parent_baholar_btn(message: Message):
    user_id = message.from_user.id
    conn2=_get_db_conn();cur2=conn2.cursor()
    cur2.execute("""SELECT u.user_id,u.full_name FROM parent_child p
        JOIN users u ON u.user_id=p.child_id WHERE p.parent_id=%s""",(user_id,))
    bolalar=cur2.fetchall(); cur2.close(); conn2.close()
    if not bolalar: await message.answer("👶 Avval farzand ulang!"); return
    rows2=[[InlineKeyboardButton(text=f"⭐ {b[1]}",callback_data=f"parent_baho:{b[0]}")] for b in bolalar]
    await message.answer("⭐ Qaysi farzandning baholarini ko'rmoqchisiz?",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))

@router.message(F.text == "📝 Uy imtihoni")
async def parent_imtihon_btn(message: Message):
    user_id = message.from_user.id
    conn2=_get_db_conn();cur2=conn2.cursor()
    cur2.execute("""SELECT u.user_id,u.full_name,u.class FROM parent_child p
        JOIN users u ON u.user_id=p.child_id WHERE p.parent_id=%s""",(user_id,))
    bolalar=cur2.fetchall(); cur2.close(); conn2.close()
    if not bolalar: await message.answer("👶 Avval farzand ulang!"); return
    rows2=[[InlineKeyboardButton(text=f"📝 {b[1]} ({b[2]})",callback_data=f"parent_imtihon:{b[0]}")] for b in bolalar]
    await message.answer("📝 Kim uchun test yaratmoqchisiz?",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))

@router.message(F.text == "💬 O'qituvchi")
async def parent_oqituvchi_btn(message: Message):
    user_id = message.from_user.id
    conn2=_get_db_conn();cur2=conn2.cursor()
    cur2.execute("""SELECT DISTINCT tg.teacher_id, u.full_name, tg.nomi
        FROM parent_child p
        JOIN togarak_azolar a ON a.user_id=p.child_id
        JOIN togaraklar tg ON tg.id=a.togarak_id AND tg.aktiv=TRUE
        JOIN users u ON u.user_id=tg.teacher_id
        WHERE p.parent_id=%s""",(user_id,))
    oqituvchilar=cur2.fetchall(); cur2.close(); conn2.close()
    if not oqituvchilar:
        await message.answer("👨‍🏫 Farzandingiz hali hech qaysi to'garakda yo'q."); return
    rows2=[[InlineKeyboardButton(text=f"👨‍🏫 {o[1]} ({o[2]})",callback_data=f"parent_msg_teacher:{o[0]}")] for o in oqituvchilar]
    await message.answer("👨‍🏫 Qaysi o'qituvchiga murojaat?",reply_markup=InlineKeyboardMarkup(inline_keyboard=rows2))
