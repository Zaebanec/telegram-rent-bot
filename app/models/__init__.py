# Этот файл собирает все модели из папки models
# Чтобы SQLAlchemy и Alembic могли их легко найти.

from .base import Base
from .models import User, Property, PropertyMedia, Booking