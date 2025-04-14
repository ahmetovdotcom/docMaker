from aiogram.types import ReplyKeyboardMarkup, KeyboardButton



select_file_version = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Новая версия(рус)")],
    [KeyboardButton(text="Старая версия(рус)"), KeyboardButton(text="Старая версия(каз)")]
],                  resize_keyboard=True,
                    
)

