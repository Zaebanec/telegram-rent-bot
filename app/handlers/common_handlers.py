from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

router = Router()

@router.message(Command("cancel"), StateFilter("*"))
@router.message(F.text.casefold() == "отмена", StateFilter("*"))
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """
    Универсальный обработчик для отмены любого состояния FSM.
    Работает по команде /cancel или слову "отмена".
    """
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            text="Нет активных действий для отмены.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    await state.clear()
    await message.answer(
        text="Действие отменено.",
        reply_markup=ReplyKeyboardRemove()
    )