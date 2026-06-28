import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from database import (
    init_db, add_teacher, get_teachers, get_teacher, delete_teacher,
    add_student, get_student, get_all_students, get_all_student_ids,
    count_students, add_admin, is_admin
)

TOKEN = os.getenv("BOT_TOKEN", "8970750284:AAFKq9kwvQ5gp-A9fbgXp200VONB7hX_p9E")
SUPER_ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # O'zingizni ID ni .env ga kiriting

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

SUBJECTS = ["Ingliz tili", "Rus tili", "Matematika", "Fizika", "Kimyo", "Biologiya", "Tarix", "IT/Dasturlash", "Boshqa"]
LEVELS = ["Beginner (A1)", "Elementary (A2)", "Pre-Intermediate (B1)", "Intermediate (B2)", "Upper-Intermediate (C1)", "Advanced (C2)"]
LANG_SUBJECTS = ["Ingliz tili", "Rus tili"]

# ============================================================
# STATES
# ============================================================
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

# ============================================================
# KEYBOARDS
# ============================================================
def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📝 Ro'yxatdan o'tish")],
        [KeyboardButton(text="ℹ️ Mening ma'lumotlarim")],
        [KeyboardButton(text="📞 Admin bilan bog'lanish")],
    ], resize_keyboard=True)

def admin_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="👥 O'quvchilar ro'yxati"), KeyboardButton(text="📢 Xabar yuborish")],
        [KeyboardButton(text="👨‍🏫 O'qituvchi qo'shish"), KeyboardButton(text="🗑 O'qituvchi o'chirish")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🏠 Asosiy menyu")],
    ], resize_keyboard=True)

def subjects_kb():
    buttons = [[KeyboardButton(text=s)] for s in SUBJECTS]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def levels_kb():
    buttons = [[KeyboardButton(text=l)] for l in LEVELS]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

async def teachers_kb(subject):
    teachers = await get_teachers()
    filtered = [t for t in teachers if t[2] == subject or subject not in LANG_SUBJECTS]
    if not filtered:
        filtered = teachers
    buttons = [[KeyboardButton(text=f"👨‍🏫 {t[1]} — {t[2]}")] for t in filtered]
    buttons.append([KeyboardButton(text="⏭ O'qituvchi keyinroq tanlanadi")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True), filtered

# ============================================================
# /start
# ============================================================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    if uid == SUPER_ADMIN_ID or await is_admin(uid):
        await message.answer("👋 Xush kelibsiz, Admin!", reply_markup=admin_menu())
    else:
        await message.answer(
            "🎓 <b>Edmonds School O'quv Markazi</b> botiga xush kelibsiz!\n\n"
            "Quyidagi tugmalardan birini tanlang:",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )

# ============================================================
# REGISTRATION
# ============================================================
@dp.message(F.text == "📝 Ro'yxatdan o'tish")
async def start_register(message: Message, state: FSMContext):
    existing = await get_student(message.from_user.id)
    if existing:
        await message.answer("✅ Siz allaqachon ro'yxatdan o'tgansiz!\n\n«ℹ️ Mening ma'lumotlarim» tugmasini bosing.", reply_markup=main_menu())
        return
    await state.set_state(Register.full_name)
    await message.answer("✏️ Ism va familyangizni kiriting:\n(Masalan: Aliyev Jasur)", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))

@dp.message(Register.full_name)
async def reg_name(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    await state.update_data(full_name=message.text)
    await state.set_state(Register.age_or_class)
    await message.answer("📚 Yoshingiz yoki sinfingizni kiriting:\n(Masalan: 15 yosh yoki 9-sinf)")

@dp.message(Register.age_or_class)
async def reg_age(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    await state.update_data(age_or_class=message.text)
    await state.set_state(Register.subject)
    await message.answer("📖 Qaysi fanni o'rganmoqchisiz?", reply_markup=subjects_kb())

@dp.message(Register.subject)
async def reg_subject(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    if message.text not in SUBJECTS:
        await message.answer("Iltimos, tugmadan tanlang!")
        return
    await state.update_data(subject=message.text)

    if message.text in LANG_SUBJECTS:
        await state.set_state(Register.level)
        await message.answer("🎯 Darajangizni tanlang:", reply_markup=levels_kb())
    else:
        await state.update_data(level="—")
        kb, filtered = await teachers_kb(message.text)
        await state.update_data(teacher_list=[t[0] for t in filtered])
        await state.set_state(Register.teacher)
        await message.answer("👨‍🏫 O'qituvchini tanlang:", reply_markup=kb)

@dp.message(Register.level)
async def reg_level(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    if message.text not in LEVELS:
        await message.answer("Iltimos, tugmadan tanlang!")
        return
    await state.update_data(level=message.text)
    data = await state.get_data()
    kb, filtered = await teachers_kb(data["subject"])
    await state.update_data(teacher_list=[t[0] for t in filtered])
    await state.set_state(Register.teacher)
    await message.answer("👨‍🏫 O'qituvchini tanlang:", reply_markup=kb)

@dp.message(Register.teacher)
async def reg_teacher(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return

    data = await state.get_data()
    teacher_id = None

    if message.text != "⏭ O'qituvchi keyinroq tanlanadi":
        teachers = await get_teachers()
        for t in teachers:
            if f"👨‍🏫 {t[1]} — {t[2]}" == message.text:
                teacher_id = t[0]
                break
        if teacher_id is None:
            await message.answer("Iltimos, tugmadan tanlang!")
            return

    await add_student(
        message.from_user.id,
        data["full_name"],
        data["age_or_class"],
        data["subject"],
        data["level"],
        teacher_id
    )
    await state.clear()

    teacher_info = "Keyinroq tanlanadi"
    if teacher_id:
        t = await get_teacher(teacher_id)
        teacher_info = t[1] if t else "—"

    await message.answer(
        f"✅ <b>Ro'yxatdan muvaffaqiyatli o'tdingiz!</b>\n\n"
        f"👤 Ism: {data['full_name']}\n"
        f"📚 Fan: {data['subject']}\n"
        f"🎯 Daraja: {data['level']}\n"
        f"👨‍🏫 O'qituvchi: {teacher_info}\n\n"
        f"Tez orada siz bilan bog'lanamiz! 📞",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

    # Adminga xabar
    if SUPER_ADMIN_ID:
        try:
            await bot.send_message(
                SUPER_ADMIN_ID,
                f"🆕 <b>Yangi o'quvchi!</b>\n\n"
                f"👤 {data['full_name']}\n"
                f"📱 @{message.from_user.username or 'username yo\'q'}\n"
                f"🆔 {message.from_user.id}\n"
                f"📚 {data['subject']} | {data['level']}\n"
                f"👨‍🏫 {teacher_info}",
                parse_mode="HTML"
            )
        except:
            pass

# ============================================================
# MY INFO
# ============================================================
@dp.message(F.text == "ℹ️ Mening ma'lumotlarim")
async def my_info(message: Message):
    student = await get_student(message.from_user.id)
    if not student:
        await message.answer("Siz hali ro'yxatdan o'tmagansiz.\n«📝 Ro'yxatdan o'tish» tugmasini bosing.")
        return
    _, _, full_name, age_or_class, subject, level, teacher_id, created_at = student
    teacher_name = "—"
    if teacher_id:
        t = await get_teacher(teacher_id)
        teacher_name = t[1] if t else "—"
    await message.answer(
        f"👤 <b>Sizning ma'lumotlaringiz:</b>\n\n"
        f"📛 Ism: {full_name}\n"
        f"🎓 Sinf/Yosh: {age_or_class}\n"
        f"📚 Fan: {subject}\n"
        f"🎯 Daraja: {level}\n"
        f"👨‍🏫 O'qituvchi: {teacher_name}\n"
        f"📅 Ro'yxatdan o'tgan: {str(created_at)[:10]}",
        parse_mode="HTML"
    )

# ============================================================
# CONTACT ADMIN
# ============================================================
@dp.message(F.text == "📞 Admin bilan bog'lanish")
async def contact_admin(message: Message, state: FSMContext):
    await state.set_state(ContactAdmin.message)
    await message.answer("✍️ Xabaringizni yozing, admin ko'rib chiqadi:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))

@dp.message(ContactAdmin.message)
async def send_to_admin(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    await state.clear()
    if SUPER_ADMIN_ID:
        try:
            await bot.send_message(
                SUPER_ADMIN_ID,
                f"📩 <b>Foydalanuvchi murojati:</b>\n\n"
                f"👤 {message.from_user.full_name}\n"
                f"🆔 {message.from_user.id}\n"
                f"@{message.from_user.username or '—'}\n\n"
                f"💬 {message.text}",
                parse_mode="HTML"
            )
        except:
            pass
    await message.answer("✅ Xabaringiz adminga yuborildi! Tez orada javob beramiz.", reply_markup=main_menu())

# ============================================================
# ADMIN PANEL
# ============================================================
@dp.message(F.text == "🏠 Asosiy menyu")
async def back_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyu:", reply_markup=main_menu())

@dp.message(F.text == "📊 Statistika")
async def stats(message: Message):
    if not (message.from_user.id == SUPER_ADMIN_ID or await is_admin(message.from_user.id)):
        return
    count = await count_students()
    teachers = await get_teachers()
    await message.answer(
        f"📊 <b>Statistika:</b>\n\n"
        f"👥 Jami o'quvchilar: {count}\n"
        f"👨‍🏫 Jami o'qituvchilar: {len(teachers)}",
        parse_mode="HTML"
    )

@dp.message(F.text == "👥 O'quvchilar ro'yxati")
async def students_list(message: Message):
    if not (message.from_user.id == SUPER_ADMIN_ID or await is_admin(message.from_user.id)):
        return
    students = await get_all_students()
    if not students:
        await message.answer("Hali o'quvchi yo'q.")
        return
    text = "👥 <b>O'quvchilar ro'yxati:</b>\n\n"
    for i, s in enumerate(students, 1):
        text += f"{i}. {s[0]} | {s[1]} | {s[2]} | {s[3]} | 👨‍🏫{s[4] or '—'}\n"
    # Telegram limit 4096
    for i in range(0, len(text), 4000):
        await message.answer(text[i:i+4000], parse_mode="HTML")

# ---- BROADCAST ----
@dp.message(F.text == "📢 Xabar yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    if not (message.from_user.id == SUPER_ADMIN_ID or await is_admin(message.from_user.id)):
        return
    await state.set_state(AdminStates.broadcast)
    await message.answer("✍️ Barcha o'quvchilarga yuboriladigan xabarni yozing:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))

@dp.message(AdminStates.broadcast)
async def do_broadcast(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return
    await state.clear()
    ids = await get_all_student_ids()
    sent = 0
    for uid in ids:
        try:
            await bot.send_message(uid, f"📢 <b>Edmonds School:</b>\n\n{message.text}", parse_mode="HTML")
            sent += 1
        except:
            pass
    await message.answer(f"✅ Xabar {sent} ta o'quvchiga yuborildi.", reply_markup=admin_menu())

# ---- ADD TEACHER ----
@dp.message(F.text == "👨‍🏫 O'qituvchi qo'shish")
async def add_teacher_start(message: Message, state: FSMContext):
    if not (message.from_user.id == SUPER_ADMIN_ID or await is_admin(message.from_user.id)):
        return
    await state.set_state(AdminStates.add_teacher_name)
    await message.answer("👨‍🏫 O'qituvchi ismini kiriting:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))

@dp.message(AdminStates.add_teacher_name)
async def add_teacher_name(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return
    await state.update_data(t_name=message.text)
    await state.set_state(AdminStates.add_teacher_subject)
    await message.answer("📚 O'qituvchi fanini tanlang:", reply_markup=subjects_kb())

@dp.message(AdminStates.add_teacher_subject)
async def add_teacher_subj(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return
    if message.text not in SUBJECTS:
        await message.answer("Iltimos, tugmadan tanlang!")
        return
    await state.update_data(t_subject=message.text)
    await state.set_state(AdminStates.add_teacher_levels)
    if message.text in LANG_SUBJECTS:
        await message.answer("🎯 O'qituvchi qaysi darajalarni o'qitadi?\n(Masalan: Beginner, Intermediate yoki Barchasi)")
    else:
        await state.update_data(t_levels="Barchasi")
        data = await state.get_data()
        await add_teacher(data["t_name"], data["t_subject"], "Barchasi")
        await state.clear()
        await message.answer(f"✅ O'qituvchi qo'shildi: {data['t_name']} — {data['t_subject']}", reply_markup=admin_menu())

@dp.message(AdminStates.add_teacher_levels)
async def add_teacher_lvl(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return
    data = await state.get_data()
    await add_teacher(data["t_name"], data["t_subject"], message.text)
    await state.clear()
    await message.answer(f"✅ O'qituvchi qo'shildi: {data['t_name']} — {data['t_subject']}", reply_markup=admin_menu())

# ---- DELETE TEACHER ----
@dp.message(F.text == "🗑 O'qituvchi o'chirish")
async def delete_teacher_start(message: Message, state: FSMContext):
    if not (message.from_user.id == SUPER_ADMIN_ID or await is_admin(message.from_user.id)):
        return
    teachers = await get_teachers()
    if not teachers:
        await message.answer("O'qituvchilar yo'q.")
        return
    text = "🗑 O'chirish uchun o'qituvchi ID sini yozing:\n\n"
    for t in teachers:
        text += f"ID: {t[0]} — {t[1]} ({t[2]})\n"
    await state.set_state(AdminStates.delete_teacher)
    await message.answer(text, reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))

@dp.message(AdminStates.delete_teacher)
async def do_delete_teacher(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return
    try:
        tid = int(message.text)
        await delete_teacher(tid)
        await state.clear()
        await message.answer("✅ O'qituvchi o'chirildi.", reply_markup=admin_menu())
    except:
        await message.answer("Iltimos, to'g'ri ID kiriting.")

# ---- SET ADMIN (faqat super admin) ----
@dp.message(Command("addadmin"))
async def cmd_add_admin(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Foydalanish: /addadmin <telegram_id>")
        return
    try:
        new_admin_id = int(parts[1])
        await add_admin(new_admin_id)
        await message.answer(f"✅ {new_admin_id} admin qilindi.")
    except:
        await message.answer("Xato ID.")

# ============================================================
# MAIN
# ============================================================
async def main():
    await init_db()
    # Super admini avtomatik qo'shish
    if SUPER_ADMIN_ID:
        await add_admin(SUPER_ADMIN_ID)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
