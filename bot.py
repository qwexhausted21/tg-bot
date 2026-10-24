import asyncio
import csv
import io
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    BufferedInputFile,
)
from dotenv import load_dotenv

from database import (
    init_db,
    add_lead,
    get_leads_count,
    get_last_leads,
    get_all_leads,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Отмена")]],
    resize_keyboard=True,
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📋 Последние 5 заявок")],
        [KeyboardButton(text="📤 Выгрузить в CSV")],
    ],
    resize_keyboard=True,
)


class Form(StatesGroup):
    name = State()
    phone = State()
    comment = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        "Это бот для приёма заявок. Ответь на 3 вопроса — и заявка уйдёт администратору.\n\n"
        "Как тебя зовут?",
        reply_markup=cancel_kb,
    )
    await state.set_state(Form.name)


@dp.message(Form.name, F.text == "Отмена")
@dp.message(Form.phone, F.text == "Отмена")
@dp.message(Form.comment, F.text == "Отмена")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Отменено. Напиши /start, чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(Form.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Отлично! Теперь номер телефона:")
    await state.set_state(Form.phone)


@dp.message(Form.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await message.answer("И последнее — короткий комментарий к заявке:")
    await state.set_state(Form.comment)


@dp.message(Form.comment)
async def process_comment(message: Message, state: FSMContext):
    await state.update_data(comment=message.text.strip())
    data = await state.get_data()
    await state.clear()

    lead_id = add_lead(
        user_id=message.from_user.id,
        username=message.from_user.username,
        name=data["name"],
        phone=data["phone"],
        comment=data["comment"],
    )

    await message.answer(
        "Спасибо! Заявка принята и сохранена. Напиши /start для новой.",
        reply_markup=ReplyKeyboardRemove(),
    )

    text_for_admin = (
        f"🔔 <b>Новая заявка #{lead_id}</b>\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"💬 Комментарий: {data['comment']}\n"
        f"🆔 От: @{message.from_user.username or 'без username'} (ID: {message.from_user.id})"
    )
    try:
        await bot.send_message(ADMIN_ID, text_for_admin, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление админу: {e}")


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав доступа к админ-панели.")
        return
    await message.answer(
        "🔧 Админ-панель\nВыберите действие:",
        reply_markup=admin_kb,
    )


@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    count = get_leads_count()
    await message.answer(f"📊 Всего заявок в базе: <b>{count}</b>", parse_mode="HTML")


@dp.message(F.text == "📋 Последние 5 заявок")
async def admin_last_leads(message: Message):
    if not is_admin(message.from_user.id):
        return
    leads = get_last_leads(limit=5)
    if not leads:
        await message.answer("Заявок пока нет.")
        return

    lines = ["📋 <b>Последние 5 заявок:</b>\n"]
    for lead in leads:
        lines.append(
            f"#{lead['id']} | {lead['name']} | {lead['phone']}\n"
            f"   Комментарий: {lead['comment'] or '—'}\n"
            f"   Дата: {lead['date_added']}\n"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(F.text == "📤 Выгрузить в CSV")
async def admin_export_csv(message: Message):
    if not is_admin(message.from_user.id):
        return
    leads = get_all_leads()
    if not leads:
        await message.answer("Заявок пока нет для выгрузки.")
        return

    output = io.BytesIO()
    wrapper = io.TextIOWrapper(output, encoding="utf-8")
    writer = csv.writer(wrapper)
    writer.writerow(["ID", "User ID", "Username", "Имя", "Телефон", "Комментарий", "Дата"])
    for lead in leads:
        writer.writerow([
            lead["id"],
            lead["user_id"],
            lead["username"] or "",
            lead["name"],
            lead["phone"],
            lead["comment"] or "",
            lead["date_added"],
        ])
    wrapper.flush()
    output.seek(0)

    await message.answer_document(
        document=BufferedInputFile(
            output.getvalue(),
            filename="leads.csv",
        ),
        caption=f"📤 Все заявки ({len(leads)} шт.)",
    )


async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())