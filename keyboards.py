from aiogram.types import ReplyKeyboardMarkup, KeyboardButton



select_file_version = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Новая версия(рус)"), KeyboardButton(text="Старая версия(рус)")],
    [KeyboardButton(text="Зеленая версия(рус)"), KeyboardButton(text="Зеленая версия(каз)")]
],                  resize_keyboard=True,
                    
)

