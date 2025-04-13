import fitz 
import re

def safe_numeric_string(value):
    """Проверяет, является ли строка числом. Если нет — возвращает '0'."""
    if not value:
        return "0"
    # Удаляем пробелы и валюту вроде KZT
    cleaned = re.sub(r'[^\d.,-]', '', value.replace(' ', ''))
    try:
        float(cleaned.replace(',', '.'))  # Проверяем возможность преобразования
        return value
    except ValueError:
        return "0"

def normalize_text(text: str) -> str:
    """Удаляет пробелы, переносы строк и лишние символы для нормализации текста."""
    return re.sub(r'[\s«»"“”\n\t]+', '', text.lower())

def extract_field(pattern, text):
    """Извлекает первое совпадение по заданному регулярному выражению."""
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None

def find_company_in_contract(text, company_name):
    """Ищет компанию в контракте с возможными пробелами и переносами строк между словами."""
    # Нормализуем название компании
    normalized_target = normalize_text(company_name)
    
    # Проверка на наличие компании в тексте без пробелов и переносов строк
    if normalized_target in normalize_text(text):
        return True  # Компания найдена
    return False  # Компания не найдена

def parse_contract_data_from_pdf(filepath: str, company_name: str):
    doc = fitz.open(filepath)  # Открываем PDF-документ
    full_text = ""
    first_page = doc[0]
    text = first_page.get_text()
    
    # Извлечение ИИН из текста первой страницы
    iin_match = re.search(r"ИИН:\s*(\d{12})", text.replace("\n", "").replace(" ", ""))
    iin = iin_match.group(1) if iin_match else None

    in_active_block = False

    # Проходим по всем страницам PDF
    for page in doc:
        text = page.get_text()
        
        # Находим начало блока с действующими договорами
        if "ДЕЙСТВУЮЩИЕ ДОГОВОРА" in text:
            in_active_block = True
        
        if in_active_block:
            full_text += text + "\n"  # Собираем текст для анализа
        
        # Закрытие блока с договорами
        if "ЗАВЕРШЕННЫЕ ДОГОВОРА" in text and in_active_block:
            break

    doc.close()  # Закрываем документ

    # Разделяем текст на блоки по регулярному выражению
    contract_chunks = re.findall(
        r"(Общая сумма кредита / валюта:.*?)(?=ЗАЛОГИ)", 
        full_text, 
        flags=re.DOTALL
    )

    # Ищем контракт, связанный с компанией
    for chunk in contract_chunks:
        # Ищем компанию в тексте блока
        if find_company_in_contract(chunk, company_name):
            # Если компания найдена, создаем словарь с данными контракта
            contract = {
                'Номер договора': extract_field(r"Номер договора:\s*(\S+)", chunk),
                'Дата начала': extract_field(r'Дата начала[^0-9]*(\d{2}\.\d{2}\.\d{4})', chunk),
                'Дата окончания': extract_field(r'Дата окончания[^0-9]*(\d{2}\.\d{2}\.\d{4})', chunk),
                'Общая сумма кредита': safe_numeric_string(extract_field(r"Общая сумма кредита / валюта:\s*([^\n]+)", chunk)),
                'Сумма просроченных взносов': safe_numeric_string(extract_field(r"Сумма просроченных взносов:\s*([^\n]+)", chunk)),
                'Непогашенная сумма по кредиту': safe_numeric_string(extract_field(r"Непогашенная сумма по кредиту:\s*([^\n]+)", chunk)),
                'ИИН': iin
            }

            return contract  # Возвращаем первый найденный контракт

    return None  # Если не найдено ни одного совпадения



def parse_active_total(filepath: str):

    doc = fitz.open(filepath) 
    first_page = doc[0]
    text = first_page.get_text()


    match_no_overdue = re.search(r"(\d+)\s*Действующие договоры без просрочки\*", text)
    match_with_overdue = re.search(r"(\d+)\s*Действующие договоры с просрочкой\*", text)
    
    active_without_overdue = int(match_no_overdue.group(1)) if match_no_overdue else 0
    active_with_overdue = int(match_with_overdue.group(1)) if match_with_overdue else 0
    
    active_total = active_without_overdue + active_with_overdue

    return active_total




# import fitz  # PyMuPDF
# import re

# def parse_contract_data_from_pdf(filepath, company_name):
#     doc = fitz.open(filepath)
#     block_1 = ""
#     block_2 = ""

#     start_block_1_found = False
#     start_block_2_found = False
#     stop_found = False

#     for page in doc:
#         blocks = page.get_text("blocks")
#         for block in blocks:
#             block_text = block[4]

#             # Первый блок
#             if "ИНФОРМАЦИЯ ИЗ ДОПОЛНИТЕЛЬНЫХ ИСТОЧНИКОВ ГОСУДАРСТВЕННЫХ БАЗ ДАННЫХ" in block_text:
#                 start_block_1_found = True
#                 block_1 += block_text + "\n"
#                 break
#             if not start_block_1_found:
#                 block_1 += block_text + "\n"

#             # Второй блок
#             if "ДЕЙСТВУЮЩИЕ ДОГОВОРА" in block_text:
#                 start_block_2_found = True
#             if start_block_2_found:
#                 block_2 += block_text + "\n"
#             if "ЗАВЕРШЕННЫЕ ДОГОВОРЫ" in block_text and start_block_2_found:
#                 stop_found = True
#                 break

#         if stop_found:
#             break
#     doc.close()

#     # --- Обработка block_1 ---
#     pattern_main = r'''(?ix)
#         (''' + re.escape(company_name) + r''')       # Название компании
#         .*?
#         (\d{2}\.\d{2}\.\d{4})                         # Первая дата
#         \s*(\d[\d\s.]*kzt)                            # Сумма по договору
#         \s*(\d[\d\s.]*kzt)                            # Платеж
#         \s*(\d[\d\s.]*kzt)                            # Остаток
#         .*?
#         (\d{2}\.\d{2}\.\d{4})                         # Вторая дата
#     '''
#     match = re.search(pattern_main, block_1, re.DOTALL)
#     iin_match = re.search(r'\b\d{12}\b', block_1)

#     result = {}

#     if match:
#         result.update({
#             'Компания': match.group(1).strip(),
#             'Дата начала договора': match.group(2).strip(),
#             'Сумма по договору': match.group(3).strip(),
#             'Сумма периодического платежа': match.group(4).strip(),
#             'Непогашенная сумма': match.group(5).strip(),
#             'Дата окончания договора': match.group(6).strip(),
#             'ИИН': iin_match.group(0) if iin_match else None
#         })
#     else:
#         result['Ошибка'] = '❌ Данные из block_1 не найдены'

#     # --- Обработка block_2 ---
#     def extract_contract_details(block_2):
#         parts = re.split(r'(?i)вид финансирования', block_2)
#         for part in parts:
#             if company_name.lower() in part.lower():
#                 lower_part = part.lower()
#                 if 'залоги' in lower_part:
#                     part = part[:lower_part.find('залоги')]
#                 flat_text = part.replace('\n', ' ').replace('\r', ' ')
#                 number_match = re.search(r'Номер договора:\s*([A-ZА-Я0-9\-]+)', flat_text)
#                 start_date_match = re.search(r'Дата начала[^0-9]*(\d{2}\.\d{2}\.\d{4})', flat_text)
#                 end_date_match = re.search(r'Дата окончания[^0-9]*(\d{2}\.\d{2}\.\d{4})', flat_text)
#                 return {
#                     'Номер договора': number_match.group(1) if number_match else None,
#                     'Дата начала': start_date_match.group(1) if start_date_match else None,
#                     'Дата окончания': end_date_match.group(1) if end_date_match else None
#                 }
#         return None

#     block2_data = extract_contract_details(block_2)
#     if block2_data:
#         result.update(block2_data)
#     else:
#         result['block_2'] = '❌ Данные не найдены или компания не указана'

#     return result