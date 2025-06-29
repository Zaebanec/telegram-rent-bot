from datetime import datetime
from sqlalchemy import (BigInteger, Boolean, Column, DateTime, ForeignKey,
                        Integer, String, Text, func, Date)
from sqlalchemy.orm import relationship, Mapped
from .base import Base

# Общая функция для временных меток, чтобы избежать повторений
def now_on_update_now():
    return {
        'server_default': func.now(),
        'onupdate': func.now(),
        'nullable': False
    }

class User(Base):
    __tablename__ = 'users'
    telegram_id = Column(BigInteger, primary_key=True)
    username = Column(String(32), unique=True, nullable=True)
    first_name = Column(String(64), nullable=False)
    role = Column(String(20), default='user', nullable=False)
    
    # --- ИЗМЕНЕНИЯ ЗДЕСЬ ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, **now_on_update_now())

    bookings = relationship('Booking', back_populates='user')
    properties = relationship('Property', back_populates='owner')
    reviews = relationship('Review', back_populates='user')

    __table_args__ = {'schema': 'public'}


class Property(Base):
    __tablename__ = 'properties'
    id = Column(Integer, primary_key=True)
    owner_id = Column(BigInteger, ForeignKey('public.users.telegram_id'), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    address = Column(String(255), nullable=False)
    
    # --- ИЗМЕНЕНИЯ ЗДЕСЬ: Добавляем индексы ---
    district = Column(String(50), nullable=False, index=True)
    price_per_night = Column(Integer, nullable=False, index=True) 
    
    rooms = Column(Integer, nullable=False)
    max_guests = Column(Integer, default=1, nullable=False)
    property_type = Column(String(50), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # --- ИЗМЕНЕНИЯ ЗДЕСЬ: Добавляем временные метки ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, **now_on_update_now())

    owner = relationship('User', back_populates='properties')
    media = relationship('PropertyMedia', back_populates='property', cascade="all, delete-orphan")
    bookings = relationship('Booking', back_populates='property', cascade="all, delete-orphan")
    reviews = relationship('Review', back_populates='property', cascade="all, delete-orphan")
    unavailable_dates = relationship('UnavailableDate', back_populates='property', cascade="all, delete-orphan")
    price_rules = relationship('PriceRule', back_populates='property', cascade="all, delete-orphan")

    __table_args__ = {'schema': 'public'}


class PropertyMedia(Base):
    __tablename__ = 'property_media'
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey('public.properties.id'), nullable=False)
    file_id = Column(String(255), nullable=False)
    media_type = Column(String(10), nullable=False)
    
    # --- ИЗМЕНЕНИЯ ЗДЕСЬ ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    property = relationship('Property', back_populates='media')
    __table_args__ = {'schema': 'public'}


class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey('public.properties.id'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('public.users.telegram_id'), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String(20), default='pending', nullable=False)

    # --- ИЗМЕНЕНИЯ ЗДЕСЬ ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, **now_on_update_now())

    user = relationship('User', back_populates='bookings')
    property = relationship('Property', back_populates='bookings')
    review = relationship('Review', back_populates='booking', uselist=False, cascade="all, delete-orphan")

    __table_args__ = {'schema': 'public'}


class Review(Base):
    __tablename__ = 'reviews'
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey('public.properties.id'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('public.users.telegram_id'), nullable=False)
    booking_id = Column(Integer, ForeignKey('public.bookings.id'), unique=True, nullable=False)
    rating = Column(Integer, nullable=False)
    text = Column(Text, nullable=True)
    
    # --- ИЗМЕНЕНИЯ ЗДЕСЬ ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, **now_on_update_now())

    property = relationship('Property', back_populates='reviews')
    user = relationship('User', back_populates='reviews')
    booking = relationship('Booking', back_populates='review')
    
    __table_args__ = {'schema': 'public'}


class UnavailableDate(Base):
    __tablename__ = 'unavailable_dates'
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey('public.properties.id'), nullable=False)
    date = Column(Date, nullable=False)
    comment = Column(String(100), nullable=True)

    # --- ИЗМЕНЕНИЯ ЗДЕСЬ ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    property = relationship('Property', back_populates='unavailable_dates')

    __table_args__ = {'schema': 'public'}


class PriceRule(Base):
    __tablename__ = 'price_rules'
    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey('public.properties.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    price = Column(Integer, nullable=False)

    # --- ИЗМЕНЕНИЯ ЗДЕСЬ ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    property = relationship('Property', back_populates='price_rules')
    __table_args__ = {'schema': 'public'}