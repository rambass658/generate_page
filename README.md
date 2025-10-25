# generate_page

Скрипт собирает информацию с сайта https://toinbe.ru/ и формирует HTML-страницу с данными об организации.

Включено:
- извлечение названия, описания, адреса, телефонов, email и логотипа (по возможности);
- попытка определить шрифт, подключённый на сайте, и подбор пяти альтернативных шрифтов;
- выпадающий список для переключения шрифтов и образцы текста;
- сохранение результата в папке output/.

Требования
- Python 3.8+
- pip

Установка и запуск (Windows PowerShell)
1. Откройте PowerShell и перейдите в папку проекта:
   cd C:\путь\к\проекту

2. Создайте виртуальное окружение:
   py -3 -m venv venv

3. Активируйте окружение:
   .\venv\Scripts\Activate.ps1
   Если появится ошибка про выполнение скриптов, выполните:
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   затем повторите активацию.

4. Установите зависимости:
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt

5. Запустите скрипт:
   python generate_page.py

6. Откройте результат в браузере:
   start .\output\index.html

Альтернативы
- Без активации venv можно использовать прямой путь к интерпретатору:
  .\venv\Scripts\python.exe -m pip install -r requirements.txt
  .\venv\Scripts\python.exe generate_page.py

- Быстрая проверка без venv (не рекомендуется для постоянного использования):
  py -3 -m pip install requests beautifulsoup4
  py -3 generate_page.py

Структура
- generate_page.py — основной скрипт.
- requirements.txt — зависимости.
- output/ — создаётся автоматически: index.html, styles.css, assets/ (логотип, шрифты).

Лицензия
Свободное использование и модификация для учебных целей.
```
