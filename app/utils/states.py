from aiogram.fsm.state import State, StatesGroup

class AddProperty(StatesGroup):
    title = State()
    description = State()
    region = State()
    district = State()
    address = State()
    rooms = State()
    price_per_night = State()
    max_guests = State()
    property_type = State()
    photos = State()
    video_note = State()
    
class SearchProperties(StatesGroup):
    region = State()
    district = State()
    price = State()
    guests = State()

class EditProperty(StatesGroup):
    choosing_field = State()
    editing_title = State()
    editing_description = State()
    editing_address = State()
    editing_region = State()
    editing_district = State()
    editing_rooms = State()
    editing_price = State()
    editing_guests = State()
    editing_type = State()
    managing_media = State()
    adding_photos = State()
    managing_availability = State() # Новое состояние

class LeaveReview(StatesGroup):
    waiting_for_rating = State()
    waiting_for_comment = State()

class BookingFlow(StatesGroup):
    choosing_checkin_date = State()
    choosing_checkout_date = State()