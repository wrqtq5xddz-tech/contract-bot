# Анализатор договоров

Сервис анализа договоров на юридические риски с проверкой 214-ФЗ.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/deploy?repository=wrqtq5xddz-tech/contract-bot&branch=master&mainModule=app.py)

## Возможности

- Загрузка PDF, DOCX, TXT или вставка текста
- Анализ юридических рисков (7 категорий)
- Проверка соответствия 214-ФЗ
- Исправление рисков высокого уровня
- Экспорт справки в Word (.docx)

## Запуск локально

```bash
pip install -r requirements.txt
cp .env.example .env
# заполните .env своим ключом OpenRouter
streamlit run app.py
```

## Переменные окружения

```
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-sonnet-4-5
```
