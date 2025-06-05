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


def normalize_text(text: str, lower: bool = True) -> str:
    """Удаляет пробелы, переносы строк и лишние символы для нормализации текста."""
    if lower == True:
        return re.sub(r'[\s«»"“”\n\t]+', '', text.lower())
    else:
        return re.sub(r'[\s«»"“”\n\t]+', '', text)

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
        r"((?:Общая сумма кредита / валюта|Сумма кредитного лимита):.*?)(?=ЗАЛОГИ)", 
        full_text, 
        flags=re.DOTALL
    )

    # Ищем контракт, связанный с компанией
    for chunk in contract_chunks:
        # Ищем компанию в тексте блока
        if find_company_in_contract(chunk, company_name):
            # Если компания найдена, создаем словарь с данными контракта
            contract = {
                'Номер договора': extract_field(
                    r"Номердоговора:\s*(.*?)\s*(?:Датаначаласрокадействиядоговора|СОСТОЯНИЕ)", 
                    normalize_text(chunk, False)
                ),
                'Дата начала': extract_field(r'Дата начала[^0-9]*(\d{2}\.\d{2}\.\d{4})', chunk),
                'Дата окончания': extract_field(r'Дата окончания[^0-9]*(\d{2}\.\d{2}\.\d{4})', chunk),
                'Общая сумма кредита': safe_numeric_string(extract_field(r"(?:Общая сумма кредита / валюта|Сумма кредитного лимита):\s*([^\n]+)", chunk)),
                'Сумма просроченных взносов': safe_numeric_string(extract_field(r"Сумма просроченных взносов:\s*([^\n]+)", chunk)),
                'Непогашенная сумма по кредиту': safe_numeric_string(extract_field(r"(?:Непогашенная сумма по кредиту|Использованная сумма \(подлежащая погашению\)):\s*([^\n]+)", chunk)),
                'ИИН': iin
            }

            return contract  # Возвращаем первый найденный контракт

    return None  # Если не найдено ни одного совпадения

                #'Номер договора': extract_field(r"номердоговора:\s*(.*?)\s*датаначаласрокадействиядоговора:", chunk),


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



