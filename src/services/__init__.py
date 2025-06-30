# Этот файл делает функции из разных сервисных модулей
# доступными на уровне всего пакета app.services.

from .availability_service import get_manual_blocks, toggle_manual_availability
from .booking_service import create_booking, get_booked_dates_for_property, get_booking_with_details, update_booking_status
from .media_service import add_photos_to_property, add_video_note_to_property, delete_one_media_item
from .pricing_service import get_price_for_date, add_price_rule, get_property_with_price_rules
from .property_service import (
    add_property, 
    get_all_properties, 
    get_property_with_media_and_owner,
    set_property_verified,
    get_properties_by_owner,
    toggle_property_activity,
    delete_property,
    update_property_field,
    get_owner_properties_summary
)
from .review_service import add_review, get_latest_reviews, get_reviews_summary
from .user_service import add_user, get_user, set_user_role