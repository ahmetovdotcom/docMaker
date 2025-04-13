from docxtpl import DocxTemplate



def fill_doc(temp_path, out_path, data):
    # Загружаем шаблон с помощью docxtpl
    doc = DocxTemplate(temp_path)
    # Передаем данные для замены в шаблон
    doc.render(data)
    # Сохраняем результат
    doc.save(out_path)
