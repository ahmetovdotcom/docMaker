import re
import asyncio
import json
import os
import calendar
from datetime import datetime
from num2words import num2words
from config import BOT_TOKEN
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from docling_qa import ask_ai_from_pdf
from docling_qa2 import ask_ai_from_pdf2
from docx_replacer import fill_doc
from parse_pko_new_version import parse_contract_data_from_pdf, parse_active_total
from datetime import datetime
import unicodedata





bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class FileInfo(StatesGroup):
    user_text = State()
    file_path = State()
    reason = State()
    MFO = State()
    mfo = State()
    attached_documents = State()

class BatchProcess(StatesGroup):
    file_path = State()
    user_text = State()
    mfo_list = State()
    reason = State()
    attached_documents = State()
    

def clean(name: str) -> str:
    # Убираем невидимые символы Unicode (все категории "Cf" — форматирующие)
    name = ''.join(ch for ch in name if unicodedata.category(ch) != 'Cf')
    # Удаляем обычные пробелы, табы, неразрывные пробелы
    return re.sub(r"[ \t\u00A0]+", "", name).strip().lower()


def get_current_date_str():
    return datetime.now().strftime("%d.%m.%Y")


def get_term_by_amount(amount_str):
    # Удаляем все пробелы и валюты, только цифры
    digits_only = ''.join(filter(str.isdigit, amount_str))
    
    if not digits_only:
        return "❌ Некорректная сумма"

    amount = int(digits_only)

    if amount < 100_000:
        return "от 3 до 6 месяцев"
    elif amount < 150_000:
        return "от 6 до 12 месяцев"
    else:
        return "от 12 до 24 месяцев"


# Функция для загрузки данных из файла JSON
def load_companies_db():
    try:
        with open("companies_db.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print("Файл companies_db.json не найден.")
        return []
    except json.JSONDecodeError:
        print("Ошибка при разборе JSON.")
        return []

def normalize_string(s):
    return re.sub(r'\s+', '', s).lower()  # удаляет ВСЕ пробельные символы и приводит к нижнему регистру

def find_company_by_trade_name(trade_name):
    normalized_trade_name = normalize_string(trade_name)
    companies_data = load_companies_db()
    for company in companies_data:
        if normalize_string(company["trade_name"]) == normalized_trade_name:
            return company
    return None

def pluralize(value, one, few, many):
    # Функция для склонения слова в зависимости от числа
    if 11 <= value % 100 <= 14:
        return many
    elif value % 10 == 1:
        return one
    elif 2 <= value % 10 <= 4:
        return few
    else:
        return many

def calculate_date_diff(start_date_str, end_date_str):
    start_date = datetime.strptime(start_date_str, "%d.%m.%Y")
    end_date = datetime.strptime(end_date_str, "%d.%m.%Y")
    
    if end_date < start_date:
        return "❌ Конечная дата раньше начальной"

    years = end_date.year - start_date.year
    months = end_date.month - start_date.month
    days = end_date.day - start_date.day

    if days < 0:
        months -= 1
        prev_month = end_date.month - 1 if end_date.month > 1 else 12
        prev_year = end_date.year if end_date.month > 1 else end_date.year - 1
        days_in_prev_month = calendar.monthrange(prev_year, prev_month)[1]
        days += days_in_prev_month

    if months < 0:
        years -= 1
        months += 12

    result = []
    if years > 0:
        result.append(f"{years} {pluralize(years, 'год', 'года', 'лет')}")
    if months > 0:
        result.append(f"{months} {pluralize(months, 'месяц', 'месяца', 'месяцев')}")
    if days > 0:
        result.append(f"{days} {pluralize(days, 'день', 'дня', 'дней')}")

    return " и ".join(result) if result else "менее дня"





@dp.message(Command("batch"))
async def cmd_batch(message: Message, state: FSMContext):
    await state.set_state(BatchProcess.file_path)
    await message.answer("📄 Пожалуйста, сначала отправьте PDF-файл с описанием. (Жирный клиент)")

@dp.message(BatchProcess.file_path)
async def handle_pdf_with_text(message: Message, state: FSMContext):
    document = message.document

    if document.mime_type != "application/pdf":
        await message.answer("❌ Пожалуйста, отправьте PDF-файл.")
        return

    if not message.caption or not message.caption.strip():
        await message.answer("❗ Пожалуйста, добавьте описание к PDF-файлу.")
        return

    file_path = f"temp/{message.from_user.id}_{document.file_name}"
    file = await bot.get_file(document.file_id)
    await bot.download_file(file.file_path, destination=file_path)

    await state.update_data(user_text=message.caption.strip(), file_path=file_path)
    await state.set_state(BatchProcess.mfo_list)
    await message.answer("📋 Введите список торговых названий, каждое с новой строки:")

@dp.message(BatchProcess.mfo_list)
async def handle_mfo_list(message: Message, state: FSMContext):
    raw_mfos = message.text.splitlines()
    mfo_names = [clean(name) for name in raw_mfos if clean(name)]

    await state.update_data(mfo_names=mfo_names)
    await state.set_state(BatchProcess.reason)
    data = await state.get_data()

    await message.answer("📄 Пожалуйста, напишите причину. Пример:")
    await message.answer(f"""В настоящее время мое финансовое положение очень затруднительное в связи с нехваткой денежных средств. Также имею высокую долговую нагрузку ввиду наличия {parse_active_total(data["file_path"])} действующих договоров в микрофинансовых организациях, а также банках второго уровня, это видно по Персональному Кредитному Отчету. Являюсь получателем АСП.""")

@dp.message(BatchProcess.reason)
async def handle_reason(message: Message, state: FSMContext):
    await state.update_data(reason=message.text)
    await state.set_state(BatchProcess.attached_documents)
    await message.answer("📄 Пожалуйста, напишите Прилагаемые документы. Пример:")
    await message.answer("""
1)	ПКО - Персональный Кредитный Отчет
2)	Удостоверение личности
3)	Справка ЕНПФ
4)	Выписка
5)	Свидетельство о рождении
6)	Справка о соц. отчислениях
""")

@dp.message(BatchProcess.attached_documents)
async def handle_attached_documents(message: Message, state: FSMContext):
    await state.update_data(attached_documents=message.text)
    data = await state.get_data()
    await state.clear()

    file_path = data["file_path"]
    user_text = data["user_text"]
    mfo_names = data["mfo_names"]
    reason = data["reason"]
    attached_documents = data["attached_documents"]

    status_msg = await message.answer("🔍 Обрабатываю...")

    # try:

    response = ask_ai_from_pdf2(file_path, user_text)
    user_data = json.loads(response)

    for mfo_name in mfo_names:
        company = find_company_by_trade_name(mfo_name)
        if not company:
            await message.answer(f"⚠️ Не найдено в Базе данных: {mfo_name}")
            continue

        result = parse_contract_data_from_pdf(file_path, company_name=company["search_field"])
        if not result:
            await message.answer(f"❌ Контракт не найден в пко для: {mfo_name}")
            continue

        credit_total = re.sub(r'\s*KZT$', '', result["Общая сумма кредита"])
        credit_total_no_cents = re.sub(r'\.\d+$', '', credit_total)
        credit_total_int = int(credit_total_no_cents.replace(" ", ""))
        credit_total_words = num2words(credit_total_int, lang='ru')
        result["Общая сумма кредита"] = f"{credit_total_no_cents} ({credit_total_words})"

        credit_str = re.sub(r'\s*KZT$', '', result["Непогашенная сумма по кредиту"])
        overdue_str = re.sub(r'\s*KZT$', '', result["Сумма просроченных взносов"])
        credit_val = float(credit_str.replace(" ", ""))
        overdue_val = float(overdue_str.replace(" ", ""))
        chosen_str = credit_str if credit_val >= overdue_val else overdue_str
        chosen_str_no_cents = re.sub(r'\.\d+$', '', chosen_str)
        chosen_int = int(chosen_str_no_cents.replace(" ", ""))
        chosen_words = num2words(chosen_int, lang='ru')

        result["Непогашенная сумма по кредиту"] = f"{chosen_str_no_cents} ({chosen_words})"
        result["Сумма просроченных взносов"] = re.sub(r'\.\d+$', '', overdue_str)

        date_diff = calculate_date_diff(result["Дата начала"], result["Дата окончания"])

        replacements = {
            "fullName": user_data["fullName"],
            "IIN": result["ИИН"],
            "address": user_data["address"],
            "phone": user_data["phone"],
            "email": user_data["email"],
            "receiver": company["details"]["to"],
            "mfoAddress": company["details"]["address"],
            "bin": company["details"]["bin"],
            "mfoEmail": company["details"]["email"],
            "contract_number": result["Номер договора"],
            "contract_start_date": result["Дата начала"],
            "contract_amount": result["Общая сумма кредита"],
            "outstanding_amount": result["Непогашенная сумма по кредиту"],
            "shortName": user_data["shortName"],
            "date_diff": date_diff,
            "reason": reason,
            "attached_documents": attached_documents,
            "date_now": get_current_date_str(),
            "term": get_term_by_amount(result["Непогашенная сумма по кредиту"])
        }

        doc_name = result.get("ИИН", "") + "_" + mfo_name + ".docx"
        doc_path = f"temp/{doc_name}"
        filename = mfo_name + " " + "заявление на реестр" + " " + user_data["shortName"] + ".docx"

        fill_doc("template.docx", doc_path, replacements)

        result_file = FSInputFile(doc_path, filename=filename)
        await message.answer_document(result_file, caption=f"✅ Документ для: {mfo_name}")
    await message.answer("✅ Готово!")
    

    await status_msg.delete()
    # except Exception as e:
    #     await status_msg.edit_text(f"⚠️ Ошибка при обработке данных: {e}")
























# ---------------------------------------------------------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("👋 Добро пожаловать! Пришлите PDF-файл с описанием (в подписи).")


@dp.message(F.document)
async def handle_pdf_with_text(message: Message, state: FSMContext):
    document = message.document

    if document.mime_type != "application/pdf":
        await message.answer("❌ Пожалуйста, отправьте PDF-файл.")
        return

    if not message.caption or not message.caption.strip():
        await message.answer("❗ Пожалуйста, добавьте описание к PDF-файлу.")
        return

    user_text = message.caption.strip()
    file_path = f"temp/{message.from_user.id}{document.file_name}"
    file = await bot.get_file(document.file_id)
    try:
        await bot.download_file(file.file_path, destination=file_path)
        await state.update_data(user_text=user_text, file_path=file_path)
        await state.set_state(FileInfo.MFO)
        await message.answer("📄 Пожалуйста, введите торговое название компании.")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при загрузке файла: {e}")
        return
    
@dp.message(FileInfo.MFO)
async def handle_mfo(message: Message, state: FSMContext):
    # Ищем компанию в базе
    company = find_company_by_trade_name(message.text)
    if company is None:
        await message.answer("⚠️ Компания с таким торговым названием не найдена в базе.")
        await state.clear()
        return
    # Если компания найдена, продолжаем обработку
    await state.update_data(MFO=company)
    await state.update_data(mfo=message.text)
    await state.set_state(FileInfo.reason)
    data = await state.get_data()

    await message.answer("📄 Пожалуйста, напишите причину. Пример:")
    await message.answer(f"""В настоящее время мое финансовое положение очень затруднительное в связи с нехваткой денежных средств. Также имею высокую долговую нагрузку ввиду наличия {parse_active_total(data["file_path"])} действующих договоров в микрофинансовых организациях, а также банках второго уровня, это видно по Персональному Кредитному Отчету. Являюсь получателем АСП.""")


@dp.message(FileInfo.reason)
async def handle_reason(message: Message, state: FSMContext):
    await state.update_data(reason=message.text)
    await state.set_state(FileInfo.attached_documents)
    await message.answer("📄 Пожалуйста, напишите Прилагаемые документы. Пример:")
    await message.answer("""
1)	ПКО - Персональный Кредитный Отчет
2)	Удостоверение личности
3)	Справка ЕНПФ
4)	Выписка
5)	Свидетельство о рождении
6)	Справка о соц. отчислениях
""")
    

@dp.message(FileInfo.attached_documents)
async def handle_attached_documents(message: Message, state: FSMContext):
    await state.update_data(attached_documents=message.text)
    data = await state.get_data()
    await state.clear()

    status_msg = await message.answer("📥 Загружаю PDF-файл...")

    file_path = data["file_path"]
    user_text = data["user_text"]
    mfo = data["MFO"]

    try:
        await status_msg.edit_text("🔍 Ищу контракт в PDF-файле...")
        result = parse_contract_data_from_pdf(file_path, company_name=mfo["search_field"])

        if result is None:
            await status_msg.edit_text(f"❌ Не удалось найти контракт для компании: {mfo['details']['to']}")
            return



        await status_msg.edit_text("📄 Анализирую пользовательский ввод...")
        response = ask_ai_from_pdf2(file_path, user_text)
        user_data = json.loads(response)

        await status_msg.edit_text("💰 Обрабатываю сумму кредита...")
        credit_total = re.sub(r'\s*KZT$', '', result["Общая сумма кредита"])
        credit_total_no_cents = re.sub(r'\.\d+$', '', credit_total)
        credit_total_int = int(credit_total_no_cents.replace(" ", ""))
        credit_total_words = num2words(credit_total_int, lang='ru')
        result["Общая сумма кредита"] = f"{credit_total_no_cents} ({credit_total_words})"

        credit_str = re.sub(r'\s*KZT$', '', result["Непогашенная сумма по кредиту"])
        overdue_str = re.sub(r'\s*KZT$', '', result["Сумма просроченных взносов"])

        credit_val = float(credit_str.replace(" ", ""))
        overdue_val = float(overdue_str.replace(" ", ""))
        chosen_str = credit_str if credit_val >= overdue_val else overdue_str
        chosen_str_no_cents = re.sub(r'\.\d+$', '', chosen_str)
        chosen_int = int(chosen_str_no_cents.replace(" ", ""))
        chosen_words = num2words(chosen_int, lang='ru')

        result["Непогашенная сумма по кредиту"] = f"{chosen_str_no_cents} ({chosen_words})"
        result["Сумма просроченных взносов"] = re.sub(r'\.\d+$', '', overdue_str)

        await status_msg.edit_text("📆 Рассчитываю срок кредита...")
        date_diff = calculate_date_diff(result["Дата начала"], result["Дата окончания"])

        replacements = {
            "fullName": user_data["fullName"],
            "IIN": result["ИИН"],
            "address": user_data["address"],
            "phone": user_data["phone"],
            "email": user_data["email"],
            "receiver": mfo["details"]["to"],
            "mfoAddress": mfo["details"]["address"],
            "bin": mfo["details"]["bin"],
            "mfoEmail": mfo["details"]["email"],
            "contract_number": result["Номер договора"],
            "contract_start_date": result["Дата начала"],
            "contract_amount": result["Общая сумма кредита"],
            "outstanding_amount": result["Непогашенная сумма по кредиту"],
            "shortName": user_data["shortName"],
            "date_diff": date_diff,
            "reason": data["reason"],
            "attached_documents": data["attached_documents"],
            "date_now": get_current_date_str(),
            "term": get_term_by_amount(result["Непогашенная сумма по кредиту"])
        }

        await status_msg.edit_text("📝 Генерирую документ...")
        docName = result.get("ИИН", "") + ".docx"
        doc_path = f"temp/{docName}"
        fill_doc("template.docx", doc_path, replacements)

        await status_msg.edit_text("📤 Отправляю итоговый документ...")
        filename = data["MFO"]["trade_name"] + " " + "заявление на реестр" + " " + user_data["shortName"] + ".docx"
        result_file = FSInputFile(doc_path, filename=filename)
        await message.answer_document(result_file, caption="✅ Ваш документ готов!")
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"⚠️ Ошибка при обработке данных: {e}")













    
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())