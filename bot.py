Y
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
 
from database import (
    init_db, add_teacher, get_teachers, get_teacher, delete_teacher,
    add_student, get_student, get_all_students, get_all_student_ids,
    count_students, add_admin, is_admin
)
 
TOKEN = os.getenv("BOT_TOKEN", "")
SUPER_ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
 
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
 
SUBJECTS = ["Ingliz tili", "Rus tili", "Matematika", "Fizika", "Kimyo", "Biologiya", "Tarix", "IT/Dasturlash", "Boshqa"]
LEVELS = ["Beginner (A1)", "Elementary (A2)", "Pre-Intermediate (B1)", "Intermediate (B2)", "Upper-Intermediate (C1)", "Advanced (C2)"]
LANG_SUBJECTS = ["Ingliz tili", "Rus tili"]
 
class Register(StatesGroup):
    full_name = State()
    age_or_class = State()
    subject = State()
    level = State()
    teacher = State()
 
class AdminStates(StatesGroup):
    broadcast = State()
    add_teacher_name = State()
    add_teacher_subject = State()
    add_teacher_levels = State()
    delete_teacher = State()
 
class ContactAdmin(StatesGroup):
    message = State()
 
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📝 Ro'yxatdan o'tish"))
    kb.add(KeyboardButton("ℹ️ Mening ma'lumotlarim"))
    kb.add(KeyboardButton("📞 Admin bilan bog'lanish"))
    return kb
 
def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("👥 O'quvchilar ro'yxati"), KeyboardButton("📢 Xabar yuborish"))
    kb.row(KeyboardButton("👨‍🏫 O'qituvchi qo'shish"), KeyboardButton("🗑 O'qituvchi o'chirish"))
    kb.row(KeyboardButton("📊 Statistika"), KeyboardButton("🏠 Asosiy menyu"))
    return kb
 
def cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Bekor qilish"))
    return kb
 
def subjects_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for s in SUBJECTS:
        kb.add(KeyboardButton(s))
    return kb
 
def levels_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for lv in LEVELS:
        kb.add(KeyboardButton(lv))
    return kb
 
async def teachers_kb(subject):
    teachers = await get_teachers()
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for t in teachers:
        kb.add(KeyboardButton("👨‍🏫 " + t[1] + " — " + t[2]))
    kb.add(KeyboardButton("⏭ O'qituvchi keyinroq tanlanadi"))
    return kb, teachers
 
@dp.message_handler(commands=["start"], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.finish()
    uid = message.from_user.id
    if uid == SUPER_ADMIN_ID or await is_admin(uid):
        await message.answer("👋 Xush kelibsiz, Admin!", reply_markup=admin_menu())
    else:
        await message.answer(
            "🎓 <b>Edmonds School O'quv Markazi</b> botiga xush kelibsiz!\n\nQuyidagi tugmalardan birini tanlang:",
            reply_markup=main_menu(), parse_mode="HTML"
        )
 
@dp.message_handler(lambda m: m.text == "📝 Ro'yxatdan o'tish")
async def start_register(message: types.Message):
    existing = await get_student(message.from_user.id)
    if existing:
        await message.answer("✅ Siz allaqachon ro'yxatdan o'tgansiz!", reply_markup=main_menu())
        return
    await Register.full_name.set()
    await message.answer("✏️ Ism va familyangizni kiriting:", reply_markup=cancel_kb())
 
@dp.message_handler(state=Register.full_name)
async def reg_name(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    await state.update_data(full_name=message.text)
    await Register.age_or_class.set()
    await message.answer("📚 Yoshingiz yoki sinfingizni kiriting:\n(Masalan: 15 yosh yoki 9-sinf)")
 
@dp.message_handler(state=Register.age_or_class)
async def reg_age(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    await state.update_data(age_or_class=message.text)
    await Register.subject.set()
    await message.answer("📖 Qaysi fanni o'rganmoqchisiz?", reply_markup=subjects_kb())
 
@dp.message_handler(state=Register.subject)
async def reg_subject(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    if message.text not in SUBJECTS:
        await message.answer("Iltimos, tugmadan tanlang!")
        return
    await state.update_data(subject=message.text)
    if message.text in LANG_SUBJECTS:
        await Register.level.set()
        await message.answer("🎯 Darajangizni tanlang:", reply_markup=levels_kb())
    else:
        await state.update_data(level="—")
        kb, _ = await teachers_kb(message.text)
        await Register.teacher.set()
        await message.answer("👨‍🏫 O'qituvchini tanlang:", reply_markup=kb)
 
@dp.message_handler(state=Register.level)
async def reg_level(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    if message.text not in LEVELS:
        await message.answer("Iltimos, tugmadan tanlang!")
        return
    await state.update_data(level=message.text)
    data = await state.get_data()
    kb, _ = await teachers_kb(data["subject"])
    await Register.teacher.set()
    await message.answer("👨‍🏫 O'qituvchini tanlang:", reply_markup=kb)
 
@dp.message_handler(state=Register.teacher)
async def reg_teacher(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    data = await state.get_data()
    teacher_id = None
    if message.text != "⏭ O'qituvchi keyinroq tanlanadi":
        teachers = await get_teachers()
        for t in teachers:
            btn_text = "👨‍🏫 " + t[1] + " — " + t[2]
            if btn_text == message.text:
                teacher_id = t[0]
                break
        if teacher_id is None:
            await message.answer("Iltimos, tugmadan tanlang!")
            return
    await add_student(message.from_user.id, data["full_name"], data["age_or_class"], data["subject"], data["level"], teacher_id)
    await state.finish()
    teacher_info = "Keyinroq tanlanadi"
    if teacher_id:
        t = await get_teacher(teacher_id)
        teacher_info = t[1] if t else "—"
    full_name = data["full_name"]
    subject = data["subject"]
    level = data["level"]
    await message.answer(
        "✅ <b>Ro'yxatdan muvaffaqiyatli o'tdingiz!</b>\n\n"
        "👤 Ism: " + full_name + "\n"
        "📚 Fan: " + subject + "\n"
        "🎯 Daraja: " + level + "\n"
        "👨‍🏫 O'qituvchi: " + teacher_info + "\n\n"
        "Tez orada siz bilan bog'lanamiz! 📞",
        reply_markup=main_menu(), parse_mode="HTML"
    )
    if SUPER_ADMIN_ID:
        try:
            username = message.from_user.username or "—"
            uid = message.from_user.id
            await bot.send_message(SUPER_ADMIN_ID,
                "🆕 <b>Yangi o'quvchi!</b>\n\n"
                "👤 " + full_name + "\n"
                "📱 @" + username + "\n"
                "🆔 " + str(uid) + "\n"
                "📚 " + subject + " | " + level + "\n"
                "👨‍🏫 " + teacher_info,
                parse_mode="HTML")
        except:
            pass
 
@dp.message_handler(lambda m: m.text == "ℹ️ Mening ma'lumotlarim")
async def my_info(message: types.Message):
    student = await get_student(message.from_user.id)
    if not student:
        await message.answer("Siz hali ro'yxatdan o'tmagansiz.")
        return
    _, _, full_name, age_or_class, subject, level, teacher_id, created_at = student
    teacher_name = "—"
    if teacher_id:
        t = await get_teacher(teacher_id)
        teacher_name = t[1] if t else "—"
    await message.answer(
        "👤 <b>Sizning ma'lumotlaringiz:</b>\n\n"
        "📛 Ism: " + full_name + "\n"
        "🎓 Sinf/Yosh: " + age_or_class + "\n"
        "📚 Fan: " + subject + "\n"
        "🎯 Daraja: " + level + "\n"
        "👨‍🏫 O'qituvchi: " + teacher_name + "\n"
        "📅 Sana: " + str(created_at)[:10],
        parse_mode="HTML"
    )
 
@dp.message_handler(lambda m: m.text == "📞 Admin bilan bog'lanish")
async def contact_admin(message: types.Message):
    await ContactAdmin.message.set()
    await message.answer("✍️ Xabaringizni yozing:", reply_markup=cancel_kb())
 
@dp.message_handler(state=ContactAdmin.message)
async def send_to_admin(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    await state.finish()
    if SUPER_ADMIN_ID:
        try:
            username = message.from_user.username or "—"
            await bot.send_message(SUPER_ADMIN_ID,
                "📩 <b>Murojaat:</b>\n\n"
                "👤 " + message.from_user.full_name + "\n"
                "🆔 " + str(message.from_user.id) + "\n"
                "@" + username + "\n\n"
                "💬 " + message.text,
                parse_mode="HTML")
        except:
            pass
    await message.answer("✅ Xabaringiz adminga yuborildi!", reply_markup=main_menu())
 
@dp.message_handler(lambda m: m.text == "🏠 Asosiy menyu")
async def back_main(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Asosiy menyu:", reply_markup=main_menu())
 
@dp.message_handler(lambda m: m.text == "📊 Statistika")
async def stats(message: types.Message):
    if not (message.from_user.id == SUPER_ADMIN_ID or await is_admin(message.from_user.id)):
        return
    count = await count_students()
    teachers = await get_teachers()
    await message.answer(
        "📊 <b>Statistika:</b>\n\n"
        "👥 O'quvchilar: " + str(count) + "\n"
        "👨‍🏫 O'qituvchilar: " + str(len(teachers)),
        parse_mode="HTML"
    )
 
@dp.message_handler(lambda m: m.text == "👥 O'quvchilar ro'yxati")
async def students_list(message: types.Message):
    if not (message.from_user.id == SUPER_ADMIN_ID or await is_admin(message.from_user.id)):
        return
    students = await get_all_students()
    if not students:
        await message.answer("Hali o'quvchi yo'q.")
        return
    text = "👥 <b>O'quvchilar:</b>\n\n"
    for i, s in enumerate(students, 1):
        t_name = s[4] or "—"
        text += str(i) + ". " + s[0] + " | " + s[1] + " | " + s[2] + " | " + s[3] + " | 👨‍🏫" + t_name + "\n"
    for i in range(0, len(text), 4000):
        await message.answer(text[i:i+4000], parse_mode="HTML")
 
@dp.message_handler(lambda m: m.text == "📢 Xabar yuborish")
async def broadcast_start(message: types.Message):
    if not (message.from_user.id == SUPER_ADMIN_ID or await is_admin(message.from_user.id)):
        return
    await AdminStates.broadcast.set()
    await message.answer("✍️ Barcha o'quvchilarga yuboriladigan xabarni yozing:", reply_markup=cancel_kb())
 
@dp.message_handler(state=AdminStates.broadcast)
async def do_broadcast(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return
    await state.finish()
    ids = await get_all_student_ids()
    sent = 0
    for uid in ids:
        try:
            await bot.send_message(uid, "📢 <b>Edmonds School:</b>\n\n" + message.text, parse_mode="HTML")
            sent += 1
        except:
            pass
    await message.answer("✅ " + str(sent) + " ta o'quvchiga yuborildi.", reply_markup=admin_menu())
 
@dp.message_handler(lambda m: m.text == "👨‍🏫 O'qituvchi qo'shish")
async def add_teacher_start(message: types.Message):
    if not (message.from_user.id == SUPER_ADMIN_ID or await is_admin(message.from_user.id)):
        return
    await AdminStates.add_teacher_name.set()
    await message.answer("👨‍🏫 O'qituvchi ismini kiriting:", reply_markup=cancel_kb())
 
@dp.message_handler(state=AdminStates.add_teacher_name)
async def add_teacher_name_h(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return
    await state.update_data(t_name=message.text)
    await AdminStates.add_teacher_subject.set()
    await message.answer("📚 Fanini tanlang:", reply_markup=subjects_kb())
 
@dp.message_handler(state=AdminStates.add_teacher_subject)
async def add_teacher_subj_h(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return
    if message.text not in SUBJECTS:
        await message.answer("Iltimos, tugmadan tanlang!")
        return
    await state.update_data(t_subject=message.text)
    if message.text in LANG_SUBJECTS:
        await AdminStates.add_teacher_levels.set()
        await message.answer("🎯 Qaysi darajalarni o'qitadi?\n(Masalan: Beginner, Intermediate yoki Barchasi)", reply_markup=cancel_kb())
    else:
        data = await state.get_data()
        await add_teacher(data["t_name"], data["t_subject"], "Barchasi")
        await state.finish()
        await message.answer("✅ O'qituvchi qo'shildi: " + data["t_name"] + " — " + data["t_subject"], reply_markup=admin_menu())
 
@dp.message_handler(state=AdminStates.add_teacher_levels)
async def add_teacher_lvl_h(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return
    data = await state.get_data()
    await add_teacher(data["t_name"], data["t_subject"], message.text)
    await state.finish()
    await message.answer("✅ O'qituvchi qo'shildi: " + data["t_name"] + " — " + data["t_subject"], reply_markup=admin_menu())
 
@dp.message_handler(lambda m: m.text == "🗑 O'qituvchi o'chirish")
async def delete_teacher_start(message: types.Message):
    if not (message.from_user.id == SUPER_ADMIN_ID or await is_admin(message.from_user.id)):
        return
    teachers = await get_teachers()
    if not teachers:
        await message.answer("O'qituvchilar yo'q.")
        return
    text = "🗑 O'chirish uchun ID yozing:\n\n"
    for t in teachers:
        text += "ID: " + str(t[0]) + " — " + t[1] + " (" + t[2] + ")\n"
    await AdminStates.delete_teacher.set()
    await message.answer(text, reply_markup=cancel_kb())
 
@dp.message_handler(state=AdminStates.delete_teacher)
async def do_delete_teacher(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.finish()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return
    try:
        await delete_teacher(int(message.text))
        await state.finish()
        await message.answer("✅ O'qituvchi o'chirildi.", reply_markup=admin_menu())
    except:
        await message.answer("To'g'ri ID kiriting.")
 
@dp.message_handler(commands=["addadmin"])
async def cmd_add_admin(message: types.Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Foydalanish: /addadmin <id>")
        return
    try:
        await add_admin(int(parts[1]))
        await message.answer("✅ Admin qo'shildi.")
    except:
        await message.answer("Xato.")
 
async def on_startup(dp):
    await init_db()
    if SUPER_ADMIN_ID:
        await add_admin(SUPER_ADMIN_ID)
 
if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
 
