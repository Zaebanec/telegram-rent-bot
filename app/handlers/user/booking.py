from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery, InputMediaPhoto

from app.services.property_service import get_property_with_media_and_owner
from app.services.review_service import get_reviews_summary 
from app.keyboards.inline_keyboards import get_property_card_keyboard

router = Router()

@router.callback_query(F.data.startswith(("view_photos:", "view_media:")))
async def view_media(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    property_id = int(callback.data.split(":")[1])

    prop, photo_files, video_file = await get_property_with_media_and_owner(property_id)

    if not prop:
        await callback.message.answer("Объект не найден.")
        return

    media_to_show = []
    if video_file and callback.data.startswith("view_media:"):
        await bot.send_video_note(chat_id=callback.from_user.id, video_note=video_file)
        media_to_show = photo_files
    elif callback.data.startswith("view_photos:") and len(photo_files) > 1:
        media_to_show = photo_files[1:]

    if media_to_show:
        if len(media_to_show) > 1:
            media_group = [InputMediaPhoto(media=file_id) for file_id in media_to_show]
            await bot.send_media_group(chat_id=callback.from_user.id, media=media_group)
        elif len(media_to_show) == 1:
            await bot.send_photo(chat_id=callback.from_user.id, photo=media_to_show[0])
    elif not video_file:
         await callback.message.answer("Больше фотографий нет.")

    _, reviews_count = await get_reviews_summary(prop.id)

    await callback.message.answer(
        text="Выберите дальнейшее действие:",
        reply_markup=get_property_card_keyboard(
            property_id=prop.id,
            photos_count=len(photo_files),
            has_video=bool(video_file),
            reviews_count=reviews_count
        )
    )