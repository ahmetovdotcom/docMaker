import fitz
import re

def safe_numeric_string(value):
    if not value:
        return "0"
    cleaned = re.sub(r'[^\d.,-]', '', value.replace(' ', ''))
    try:
        float(cleaned.replace(',', '.'))
        return value
    except ValueError:
        return "0"

def normalize_text(text: str) -> str:
    """Удаляет пробелы и переносы, сохраняет регистр."""
    return re.sub(r'[\s\n\r\t\u200B\uFEFF]+', '', text)

def normalize_text_for_find_company(text: str) -> str:
    """Удаляет пробелы и делает всё строчными — для поиска названия компании."""
    return re.sub(r'[\s\n\r\t\u200B\uFEFF]+', '', text).lower()

def extract_field(pattern, text):
    match = re.search(pattern, text, flags=re.DOTALL)
    return match.group(1).strip() if match else None

def extract_global_field(pattern, text):
    match = re.search(pattern, text, flags=re.DOTALL)
    return match.group(1).strip() if match else None

def find_company_in_contract(text, company_name):
    normalized_target = normalize_text_for_find_company(company_name)
    return normalized_target in normalize_text_for_find_company(text)

def parse_old_ru_contract_data_from_pdf(filepath: str, company_name: str):
    doc = fitz.open(filepath)
    full_text = ""
    all_text = ""
    

    # Сканируем страницы с активными договорами
    in_active_block = False
    for page in doc:
        page_text = page.get_text()
        all_text += page_text
        if "Действующие договора" in page_text:
            in_active_block = True
        if in_active_block:
            full_text += page_text + "\n"
        if "Завершенные договора" in page_text and in_active_block:
            break

    doc.close()

    # Глобальный текст без пробелов и переносов
    global_text_clean = normalize_text(all_text)

    # Глобальные поля
    iin = extract_global_field(r"Индивидуальныйидентификационныйномер\(ИИН\).*?(\d{12})", global_text_clean)


    # Договора
    cleaned_text = normalize_text(full_text)
    contract_chunks = re.findall(r"(Видфинансирования:.*?Дополнительнаяинформация)", cleaned_text, flags=re.DOTALL)


    cleaned_text = normalize_text(full_text)

    # Разбиваем на блоки договоров
    contract_chunks = re.findall(r"(Видфинансирования:.*?Дополнительнаяинформация)", cleaned_text, flags=re.DOTALL)

    for chunk in contract_chunks:
        
        if find_company_in_contract(chunk, company_name):
            return {
                'ИИН': iin,
                'Номер договора': extract_field(r"Номердоговора[:№]?\s*(.*?)\s*(?:Датазаявки|Состояние[:№]?)", chunk),
                'Дата начала': extract_field(r"Датаначаласрокадействиядоговора[:№]?\s*(\d{2}\.\d{2}\.\d{4})", chunk),
                'Дата окончания': extract_field(r"Датаокончаниясрокадействиядоговора[:№]?\s*(\d{2}\.\d{2}\.\d{4})", chunk),
                'Общая сумма кредита': safe_numeric_string(
                    extract_field(r"Общаясуммакредита.?валюта[:№]?\s*([\d.,]+KZT)", chunk)
                ),
                'Сумма просроченных взносов': safe_numeric_string(
                    extract_field(r"Суммапериодическогоплатежа[:№]?\s*([\d.,]+KZT)", chunk)
                ),
                'Непогашенная сумма по кредиту': safe_numeric_string(
                    extract_field(r"Непогашеннаясуммапокредиту[:№]?\s*([\d.,]+KZT)", chunk)
                ),
            }

    return None


def parse_old_ru_total_contracts(filepath: str) -> int:
    doc = fitz.open(filepath)
    all_text = ""
    
    # Собираем текст со всех страниц
    for page in doc:
        all_text += page.get_text()

    doc.close()

    # Удаляем пробелы, переносы строк и т.д., чтобы искать подряд
    normalized = re.sub(r'[\s\n\r\t\u200B\uFEFF]+', '', all_text)

    # Ищем первое вхождение Заёмщик + число перед скобкой
    match = re.search(r"Заёмщик\s*([0-9]+)\s*\(", normalized)
    return int(match.group(1)) if match else 0