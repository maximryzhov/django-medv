import logging
import os

def load_env(path):
    """
    Мини-парсер для .env файла
    Поддерживаются:
    - одинарные и двойные кавычки
    - многострочные значения
    - символы \n и \r
    - пустые строки и комментарии
    """
    if not path.exists():
        logging.warning(".env файл не найден")
        return

    lines = iter(path.read_text(encoding="utf-8").splitlines())
    for raw_line in lines:
        line = raw_line.strip()

        # Комментарий игнорируется
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if value.startswith(("\"", "'")):
            quote = value[0]
            while not value.endswith(quote):
                try:
                    value += "\n" + next(lines)
                except StopIteration:
                    raise ValueError(f"Отсутствует закрывающая кавычка: {line}")
            if value.endswith(quote):
                value = value[1:-1]
            if quote == "\"":
                value = value.replace("\\n", "\n").replace("\\r", "\r")
        else:
            value = value.split(" #", 1)[0].strip()

        os.environ.setdefault(key, value)