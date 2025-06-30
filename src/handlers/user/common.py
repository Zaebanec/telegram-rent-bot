from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove

from src.services.user_service import add_user
from src.keyboards.inline_keyboards import get_main_menu

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # При старте на всякий случай сбрасываем состояние
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        
    await message.answer("Загрузка...", reply_markup=ReplyKeyboardRemove())
    await add_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    await message.answer(
        "Добро пожаловать в 'Гид по Калининграду'!",
        reply_markup=get_main_menu()
    )

# --- НАШ НОВЫЙ ОБРАБОТЧИК ---
@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "<b>Добро пожаловать в Справку!</b>\n\n"
        "Я бот для поиска и аренды жилья в Калининградской области.\n\n"
        "<b>Основные команды:</b>\n"
        "/start - перезапуск бота и вызов главного меню.\n"
        "/help - вызов этого сообщения.\n"
        "/cancel - отмена любого текущего диалога (добавления, поиска и т.д.).\n\n"
        "<b>Для Владельцев (и Администраторов):</b>\n"
        "/myproperties - посмотреть список ваших объектов и управлять ими.\n"
        "/addproperty - запустить диалог добавления нового объекта."
    )
    await message.answer(help_text)


@router.callback_query(F.data == "main_menu:about")
async def about_service(callback: CallbackQuery):
    await callback.message.answer(
        "Этот бот создан, чтобы помочь вам легко найти и арендовать "
        "лучшее жилье в Калининградской области."
    )
    await callback.answer()