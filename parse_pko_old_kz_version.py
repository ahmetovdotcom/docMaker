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

def parse_pko_old_kz_version(filepath: str, company_name: str):
    doc = fitz.open(filepath)  # Открываем PDF-документ
    full_text = ""
    first_page = doc[0]
    text = first_page.get_text()
    
    # Извлечение ИИН из текста первой страницы
    iin_match = re.search(r"ЖСН:\s*(\d{12})", text.replace("\n", "").replace(" ", ""))
    iin = iin_match.group(1) if iin_match else None

    in_active_block = False

    # Проходим по всем страницам PDF
    for page in doc:
        text = page.get_text()
        
        # Находим начало блока с действующими договорами
        if "ҚОЛДАНЫСТАҒЫ ШАРТТАР БОЙЫНША ТОЛЫҚ АҚПАРАТ" in text:
            in_active_block = True
        
        if in_active_block:
            full_text += text + "\n"  # Собираем текст для анализа
        
        # Закрытие блока с договорами
        if "АЯҚТАЛҒАН ШАРТТАР" in text and in_active_block:
            break

    doc.close()  # Закрываем документ


    # Разделяем текст на блоки по регулярному выражению
    contract_chunks = re.findall(
        r"(Міндеттеме.*?)(?=Мерзімін ұзартулар күні)", 
        full_text, 
        flags=re.DOTALL
    )

    # Ищем контракт, связанный с компанией
    for chunk in contract_chunks:
        # Ищем компанию в тексте блока
        if find_company_in_contract(chunk, company_name):
            # Если компания найдена, создаем словарь с данными контракта
            contract = {
                'Номер договора': extract_field(r"Шартнөмірі:\s*(.*?)\s*Кредиткеөтінімберукүні:", normalize_text(chunk, False)),
                'Дата начала': extract_field(r'Келісімшарттың қолданылу мерзімінің басталу күні[^0-9]*(\d{2}\.\d{2}\.\d{4})', chunk),
                'Дата окончания': extract_field(r'Келісімшарттың қолданылу мерзімінің аяқталу күні[^0-9]*(\d{2}\.\d{2}\.\d{4})', chunk),
                'Общая сумма кредита': safe_numeric_string(extract_field(r"Ай сайынғы төлем сомасы / валюта:\s*([^\n]+)", chunk)),
                'Сумма просроченных взносов': safe_numeric_string(extract_field(r"Мерзімі өткен жарналар сомасы /валюта:\s*([^\n]+)", chunk)),
                'Непогашенная сумма по кредиту': safe_numeric_string(extract_field(r"Алдағы төлемдер сомасы/валюта\s*([^\n]+)", chunk)),
                'ИИН': iin
            }

            return contract  # Возвращаем первый найденный контракт

    return None  # Если не найдено ни одного совпадения

                #'Номер договора': extract_field(r"номердоговора:\s*(.*?)\s*датаначаласрокадействиядоговора:", chunk),


def parse_old_kz_total_contracts(filepath: str):
    doc = fitz.open(filepath)
    full_text = ""

    for page in doc:
        full_text += page.get_text()

    doc.close()

    # Удаляем переносы и лишние пробелы для удобства поиска
    cleaned_text = re.sub(r'[\n\r\t]+', ' ', full_text)

    # Ищем число в скобках после фразы "Қолданыстағы міндеттемелер"
    match = re.search(r"Қолданыстағы\s+міндеттемелер\s*\((\d+)\)", cleaned_text, flags=re.IGNORECASE)

    if match:
        return int(match.group(1))
    
    return 0  # если не найдено


