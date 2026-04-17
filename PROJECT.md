# StatBet Bot — Полное описание проекта

> **Дисклеймер:** Бот предоставляет аналитическую информацию на основе математических моделей
> и **не является** инвестиционной рекомендацией или призывом к совершению ставок.
> Все решения пользователь принимает самостоятельно и несёт полную ответственность за них.
> Использование стратегий хеджирования может нарушать правила букмекерских контор.

---

## Содержание

1. [Назначение проекта](#1-назначение-проекта)
2. [Функциональность](#2-функциональность)
3. [Архитектура](#3-архитектура)
4. [Структура файлов](#4-структура-файлов)
5. [Компоненты системы](#5-компоненты-системы)
6. [База данных](#6-база-данных)
7. [Конфигурация](#7-конфигурация)
8. [Математические модели](#8-математические-модели)
9. [API команд бота](#9-api-команд-бота)
10. [Запуск и развёртывание](#10-запуск-и-развёртывание)
11. [Тестирование](#11-тестирование)
12. [Зависимости](#12-зависимости)
13. [Дорожная карта](#13-дорожная-карта)

---

## 1. Назначение проекта

**StatBet Bot** — Telegram-бот для спортивной аналитики и бумажного (виртуального) трейдинга
на основе машинного обучения.

### Цели

- Предоставлять вероятностные оценки исходов матчей на базе ML-моделей (XGBoost, Bivariate Poisson)
- Рассчитывать стратегии хеджирования ставок (Full Hedge, Partial Hedge, Lock Profit)
- Отслеживать изменения вероятностей в реальном времени (Live Tracker)
- Давать пользователям возможность тестировать стратегии без реальных денег (Paper Trading)
- Объяснять решения модели через факторный анализ (SHAP-значения)

### Целевая аудитория

Аналитики и энтузиасты спортивной статистики, желающие изучать математические модели
оценки вероятностей без реального риска.

---

## 2. Функциональность

### Реализовано

| Команда | Описание | Статус |
|---------|----------|--------|
| `/start` | Регистрация пользователя, приветствие, дисклеймер | ✅ |
| `/matches` | Список ближайших матчей с вероятностями | ✅ (placeholder) |
| `/analyze` | Детальный анализ матча с SHAP-факторами | ✅ (placeholder) |
| `/calc_hedge` | Интерактивный калькулятор хеджирования | ✅ |
| `/track` | Подписка на live-обновления матча | 🔧 В разработке |
| `/untrack` | Отписка от live-обновлений | 🔧 В разработке |
| `/status` | Статус системы | 🔧 В разработке |
| `/paper` | Виртуальный портфель | 🔧 В разработке |
| `/stats` | Статистика качества модели | 🔧 В разработке |

### Калькулятор хеджирования (`/calc_hedge`)

Полностью рабочий диалоговый FSM-калькулятор. Пользователь вводит:
1. Сумму условной позиции
2. Коэффициент основной ставки
3. Коэффициент противоположного исхода
4. Желаемый процент покрытия (0–100%)

Бот рассчитывает три стратегии и проверяет наличие арбитражной ситуации.

---

## 3. Архитектура

### Общая схема

```
Telegram API
     │
     ▼
 Aiogram 3.x (Bot + Dispatcher)
     │
     ├── Handlers (команды и FSM)
     │       │
     │       ├── Services (бизнес-логика)
     │       │       ├── HedgeService
     │       │       └── PredictionService
     │       │               │
     │       │               └── Models (HedgeCalculator, PredictionModel)
     │       │
     │       └── Utils (validators, formatters)
     │
     ├── Database (asyncpg pool + redis)
     │       ├── PostgreSQL — пользователи, матчи, ставки, предсказания
     │       └── Redis — кеш, сессии, live-данные
     │
     └── Config (pydantic-settings, .env)
```

### Принципы проектирования

- **Разделение ответственности** — handlers не содержат бизнес-логику
- **Единственный источник правды** — математика только в `HedgeCalculator`, `HedgeService` делегирует
- **Dependency Injection** — `Database` передаётся в handlers через `Dispatcher.workflow_data`
- **Fail-fast конфигурация** — невалидный `.env` останавливает запуск с понятным сообщением
- **Graceful shutdown** — при SIGINT/SIGTERM закрываются пул БД и сессия бота

---

## 4. Структура файлов

```
BKbot/
├── src/
│   └── statbet_bot/
│       ├── __init__.py               # Пакет
│       ├── bot.py                    # Точка входа, запуск polling, graceful shutdown
│       ├── config.py                 # Конфигурация (Pydantic BaseSettings)
│       ├── database.py               # Класс Database (asyncpg + redis)
│       ├── models.py                 # HedgeCalculator, HedgeInput, PredictionModel
│       │
│       ├── handlers/
│       │   ├── __init__.py           # register_handlers(dp)
│       │   ├── start.py              # /start — регистрация пользователя
│       │   ├── matches.py            # /matches — список матчей
│       │   ├── analyze.py            # /analyze — анализ матча
│       │   ├── calc_hedge.py         # /calc_hedge — FSM калькулятор хеджа
│       │   └── other.py              # /track, /untrack, /status, /paper, /stats
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── hedge.py              # HedgeService + HedgeResult dataclass
│       │   └── prediction.py         # PredictionService + PredictionResult dataclass
│       │
│       └── utils/
│           ├── __init__.py
│           ├── validators.py         # validate_stake, validate_odds, validate_percent
│           └── formatters.py         # format_probability, format_currency, format_odds
│
├── tests/
│   ├── __init__.py
│   └── test_models.py                # 44 теста: HedgeCalculator, HedgeService, HedgeInput, Validators
│
├── models/                           # Директория для сохранённых ML-моделей (пусто)
├── data/                             # Директория для датасетов (пусто)
│
├── .env                              # Переменные окружения (не в git)
├── .env.example                      # Пример конфигурации
├── docker-compose.yml                # PostgreSQL 15 + Redis 7
├── Dockerfile                        # Python 3.11-slim, poetry install
├── pyproject.toml                    # Poetry зависимости + pytest конфиг
├── requirements.txt                  # Production зависимости (pip)
├── requirements-dev.txt              # Dev/test зависимости (pip)
├── README.md                         # Краткое описание для GitHub
└── PROJECT.md                        # Этот файл
```

---

## 5. Компоненты системы

### `bot.py` — Точка входа

Управляет жизненным циклом приложения:

```
запуск → Config.load() → Bot() → Database.init() → dp["db"] = db
       → register_handlers(dp) → dp.start_polling(bot)
остановка → Database.close() → bot.session.close()
```

Обрабатывает сигналы `SIGINT` и `SIGTERM`. При любой ошибке на старте
выходит с кодом `1` и печатает стек в лог.

---

### `config.py` — Конфигурация

Использует `pydantic-settings.BaseSettings`. Автоматически читает `.env` файл.

| Переменная | Тип | Обязательна | Описание |
|------------|-----|:-----------:|---------|
| `TELEGRAM_TOKEN` | `str` | ✅ | Токен бота от @BotFather |
| `DATABASE_URL` | `str` | — | PostgreSQL URL (default: localhost) |
| `REDIS_URL` | `str` | — | Redis URL (default: localhost:6379) |
| `API_FOOTBALL_KEY` | `str \| None` | — | Ключ API-Football для данных о матчах |
| `ODDS_API_KEY` | `str \| None` | — | Ключ The Odds API для коэффициентов |

**Валидаторы:**
- `TELEGRAM_TOKEN` — минимум 10 символов, не может быть плейсхолдером (`your_token_here`, `changeme`)
- `DATABASE_URL` — должен начинаться с `postgresql://` или `postgres://`

---

### `database.py` — Слой данных

Класс `Database` инкапсулирует два соединения:

| Компонент | Библиотека | Назначение |
|-----------|-----------|-----------|
| PostgreSQL | `asyncpg` | Основное хранилище (пул соединений) |
| Redis | `redis.asyncio` | Кеширование, сессии, live-данные |

Методы:
- `init()` — создаёт пул, подключает Redis, создаёт таблицы и индексы
- `close()` — корректно закрывает все соединения
- `_create_tables()` — идемпотентное создание схемы (`IF NOT EXISTS`)

---

### `services/hedge.py` — Сервис хеджирования

**`HedgeService`** — валидирует входные данные и делегирует математику в `HedgeCalculator`.

Метод `calculate(stake, k_main, k_hedge, percent)` возвращает `HedgeResult`:

| Поле | Тип | Описание |
|------|-----|---------|
| `full_hedge` | `float \| None` | Сумма для полного хеджа |
| `partial_hedge` | `float \| None` | Сумма для частичного хеджа |
| `lock_profit` | `float \| None` | Сумма для фиксации прибыли |
| `is_arbitrage` | `bool` | Обнаружена арбитражная ситуация |
| `guaranteed_profit` | `float \| None` | Гарантированная прибыль при арбитраже |
| `error` | `str \| None` | Сообщение об ошибке валидации |

Границы валидации `HedgeService` (совпадают с `HedgeCalculator`):

| Параметр | Условие |
|----------|---------|
| `stake` | `> 0` и `<= 1 000 000` |
| `k_main` | `> 1.0` и `<= 100.0` |
| `k_hedge` | `> 1.0` и `<= 100.0` |
| `percent` | `>= 0` и `<= 100` |

---

### `services/prediction.py` — Сервис предсказаний

**`PredictionService`** оборачивает `PredictionModel` и возвращает `PredictionResult`:

| Поле | Описание |
|------|---------|
| `tb_25` | Вероятность тотала больше 2.5 |
| `tm_25` | Вероятность тотала меньше 2.5 |
| `factors` | Список SHAP-факторов с вкладом в % |
| `confidence` | Уровень уверенности модели |
| `error` | Ошибка, если модель недоступна |

> ⚠️ Текущая реализация `PredictionModel.predict()` — placeholder с фиксированными значениями.
> Реальное обучение и инференс — в дорожной карте.

---

### `utils/validators.py` — Валидаторы

Все функции возвращают `Tuple[bool, Optional[float], Optional[str]]` — `(is_valid, value, error_message)`.

| Функция | Что проверяет |
|---------|--------------|
| `validate_stake(value)` | Число > 0, не `NaN`/`Inf`, ≤ 1 000 000, ≥ 0.01 |
| `validate_odds(value)` | Число > 1.0, не `NaN`/`Inf`, ≤ 100.0 |
| `validate_percent(value)` | Число от 0 до 100 включительно, не `NaN`/`Inf` |

---

### `utils/formatters.py` — Форматирование

| Функция | Пример вывода |
|---------|--------------|
| `format_probability(0.67)` | `67% █████████████░░░░░░░` |
| `format_currency(1234.5)` | `1,234.50 у.е.` |
| `format_percentage(12.5)` | `12.5%` |
| `format_odds(2.35)` | `2.35` |

---

## 6. База данных

### Схема PostgreSQL

```sql
-- Пользователи бота
CREATE TABLE users (
    id               SERIAL PRIMARY KEY,
    telegram_id      BIGINT UNIQUE NOT NULL,
    username         TEXT,
    virtual_balance  DECIMAL DEFAULT 10000.0,   -- Виртуальный баланс (у.е.)
    created_at       TIMESTAMP DEFAULT NOW()
);

-- Матчи
CREATE TABLE matches (
    id          SERIAL PRIMARY KEY,
    home_team   TEXT NOT NULL,
    away_team   TEXT NOT NULL,
    league      TEXT,
    match_date  TIMESTAMP,
    status      TEXT DEFAULT 'scheduled'         -- scheduled | live | finished
);

-- Предсказания модели
CREATE TABLE predictions (
    id           SERIAL PRIMARY KEY,
    match_id     INT REFERENCES matches(id),
    outcome      TEXT,                           -- TB_2.5 | TM_2.5 | W1 | X | W2
    probability  DECIMAL,
    created_at   TIMESTAMP DEFAULT NOW()
);

-- Виртуальные ставки (Paper Trading)
CREATE TABLE virtual_bets (
    id          SERIAL PRIMARY KEY,
    user_id     INT REFERENCES users(id),
    match_id    INT REFERENCES matches(id),
    outcome     TEXT,
    amount      DECIMAL,
    odds        DECIMAL,
    result      TEXT DEFAULT 'pending',          -- pending | win | loss
    created_at  TIMESTAMP DEFAULT NOW()
);
```

### Индексы

| Индекс | Таблица | Поле | Назначение |
|--------|---------|------|-----------|
| `idx_users_telegram_id` | `users` | `telegram_id` | Быстрый поиск пользователя при каждом запросе |
| `idx_matches_date` | `matches` | `match_date` | Сортировка и фильтр по дате |
| `idx_predictions_match` | `predictions` | `match_id` | JOIN с таблицей матчей |
| `idx_bets_user` | `virtual_bets` | `user_id` | История ставок пользователя |

### Redis

Используется для (планируется):
- Кеширования коэффициентов и вероятностей
- Хранения live-данных матчей
- Управления подписками на live-обновления

---

## 7. Конфигурация

### Файл `.env`

```ini
# Обязательно
TELEGRAM_TOKEN=your_real_token_here

# База данных (значения по умолчанию для docker-compose)
DATABASE_URL=postgresql://user:password@localhost/statbet
REDIS_URL=redis://localhost:6379

# Опционально — внешние API
API_FOOTBALL_KEY=your_api_football_key
ODDS_API_KEY=your_odds_api_key
```

### Docker Compose

| Сервис | Образ | Порт | Данные |
|--------|-------|------|--------|
| `db` | `postgres:15` | `5432` | Volume `postgres_data` |
| `redis` | `redis:7-alpine` | `6379` | In-memory |

---

## 8. Математические модели

### Стратегии хеджирования

Все формулы реализованы в `HedgeCalculator` (`src/statbet_bot/models.py`).

#### Full Hedge — Полное хеджирование

Рассчитывает ставку, которая полностью покрывает потенциальную прибыль от основной ставки.

```
hedge_stake = stake × (k_main − 1) / (k_hedge − 1)
```

**Пример:** stake=100, k_main=2.0, k_hedge=1.8
```
hedge_stake = 100 × (2.0 − 1) / (1.8 − 1) = 100 / 0.8 = 125.0
```

#### Partial Hedge — Частичное хеджирование

Покрывает заданный процент потенциальной прибыли.

```
hedge_stake = stake × (k_main − 1) × (percent / 100) / (k_hedge − 1)
```

**Пример:** stake=100, k_main=2.0, k_hedge=1.8, percent=50%
```
hedge_stake = 100 × 1.0 × 0.5 / 0.8 = 62.5
```

#### Lock Profit — Фиксация прибыли

Уравнивает выплаты при любом исходе — фиксирует одинаковую сумму.

```
hedge_stake = stake × k_main / k_hedge
```

**Пример:** stake=100, k_main=2.0, k_hedge=1.8
```
hedge_stake = 100 × 2.0 / 1.8 ≈ 111.11
```

#### Определение арбитража

Арбитраж существует, когда сумма подразумеваемых вероятностей меньше 1:

```
1/k_main + 1/k_hedge < 1  →  арбитраж обнаружен
```

### ML-модель предсказаний (Planned)

Планируемый стек:

| Компонент | Технология | Назначение |
|-----------|-----------|-----------|
| Основная модель | XGBoost | Предсказание вероятностей исходов |
| Голевая модель | Bivariate Poisson | Моделирование счёта матча |
| Объяснимость | SHAP | Декомпозиция факторов вклада |
| Метрики качества | Brier Score, ROI | Оценка калиброванности модели |

---

## 9. API команд бота

### `/start`
**Описание:** Регистрация пользователя в системе.

**Логика:**
1. Проверяет наличие `telegram_id` в таблице `users`
2. Если отсутствует — создаёт запись с балансом 10 000 у.е.
3. Отображает приветствие, дисклеймер и список команд

---

### `/calc_hedge` — FSM диалог

**Описание:** Интерактивный калькулятор хеджирования.

**Состояния FSM (`HedgeStates`):**

```
START
  │
  ▼
waiting_for_stake   ← validate_stake()
  │
  ▼
waiting_for_k_main  ← validate_odds()
  │
  ▼
waiting_for_k_hedge ← validate_odds()
  │
  ▼
waiting_for_percent ← validate_percent()
  │
  ▼
HedgeService.calculate() → вывод результата → state.clear()
```

**Валидация на каждом шаге:**
- Некорректный ввод → сообщение об ошибке, состояние не меняется
- Пользователь остаётся в том же состоянии до корректного ввода

**Пример вывода:**
```
📊 РАСЧЕТ ХЕДЖА

Параметры:
• Сумма позиции: 100.0
• Кэф позиции: 2.0
• Кэф хеджа: 1.8
• Покрытие: 50%

Результаты:
• Full Hedge: 125.00
• Partial Hedge (50%): 62.50
• Lock Profit: 111.11

⚠️ Не является инвестиционной рекомендацией.
```

---

### `/analyze`
**Описание:** Вероятностный анализ матча с SHAP-факторами.

**Пример вывода:**
```
📊 ВЕРОЯТНОСТНАЯ ОЦЕНКА МОДЕЛИ

🔮 Исходы:
• ТБ 2.5: 67% ████████████░░░░░░
• ТМ 2.5: 33% ██████░░░░░░░░░░░░

📈 Рыночная оценка (Implied Probability):
• ТБ 2.5: ~51% (кэф 1.95)
• ТМ 2.5: ~48% (кэф 2.10)

🔍 Ключевые факторы (SHAP):
• xG последних 5 матчей: +12%
• Домашнее поле: +8%
• Травма форварда: -5%
```

---

## 10. Запуск и развёртывание

### Локальный запуск (Poetry)

```bash
# 1. Установить зависимости
poetry install

# 2. Создать .env файл
cp .env.example .env
# Заполнить TELEGRAM_TOKEN и другие переменные

# 3. Запустить базы данных
docker-compose up -d

# 4. Запустить бота
python -m statbet_bot.bot
```

### Локальный запуск (pip)

```bash
pip install -r requirements.txt
docker-compose up -d
python -m statbet_bot.bot
```

### Запуск через Docker

```bash
# Собрать образ
docker build -t statbet-bot .

# Запустить (базы данных должны быть запущены)
docker run --env-file .env --network host statbet-bot
```

### Переменные окружения для production

```ini
TELEGRAM_TOKEN=<реальный токен>
DATABASE_URL=postgresql://user:password@db_host:5432/statbet
REDIS_URL=redis://redis_host:6379
```

---

## 11. Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С подробным выводом
pytest -v

# Конкретный класс
pytest tests/test_models.py::TestHedgeService -v

# С покрытием (требует pytest-cov)
pytest --cov=statbet_bot --cov-report=term-missing
```

### Покрытие тестами

| Класс | Тестов | Что покрыто |
|-------|:------:|------------|
| `TestHedgeCalculator` | 12 | Все три формулы, граничные значения, невалидные входы |
| `TestHedgeService` | 8 | Валидация, делегирование, арбитраж, граничные значения |
| `TestHedgeInput` | 7 | Pydantic-валидация полей модели |
| `TestValidators` | 17 | `stake`, `odds`, `percent` — все граничные случаи |
| **Итого** | **44** | |

### Конфигурация pytest (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
asyncio_mode = "auto"
```

---

## 12. Зависимости

### Production (`requirements.txt`)

| Пакет | Версия | Назначение |
|-------|--------|-----------|
| `aiogram` | 3.17.0 | Telegram Bot framework (async) |
| `pydantic` | 2.10.0 | Валидация данных и моделей |
| `pydantic-settings` | 2.7.0 | Загрузка конфигурации из `.env` |
| `asyncpg` | 0.30.0 | Async PostgreSQL клиент |
| `redis` | 5.2.1 | Async Redis клиент |
| `psycopg2-binary` | 2.9.10 | PostgreSQL драйвер (sync, для миграций) |
| `pandas` | 2.2.3 | Обработка данных |
| `xgboost` | 2.1.3 | ML-модель градиентного бустинга |
| `scikit-learn` | 1.5.2 | Утилиты ML (split, metrics) |
| `shap` | 0.46.0 | Объяснимость предсказаний |

### Dev (`requirements-dev.txt`)

| Пакет | Версия | Назначение |
|-------|--------|-----------|
| `pytest` | 8.3.0 | Тестовый фреймворк |
| `pytest-asyncio` | 0.24.0 | Поддержка async-тестов |
| `black` | 24.10.0 | Форматирование кода |
| `flake8` | 7.1.0 | Линтер |

---

## 13. Дорожная карта

### v0.2 — Реальные данные

- [ ] Интеграция с API-Football (получение матчей)
- [ ] Интеграция с The Odds API (получение коэффициентов)
- [ ] Реализация `/matches` с реальными данными
- [ ] Реализация `/analyze <id>` с парсингом ID матча

### v0.3 — ML-модель

- [ ] Сбор и подготовка датасета (исторические матчи + xG)
- [ ] Обучение XGBoost-модели на реальных данных
- [ ] Калибровка вероятностей (Platt Scaling / Isotonic Regression)
- [ ] Bivariate Poisson для моделирования счёта
- [ ] Интеграция SHAP для объяснения факторов
- [ ] Сохранение и загрузка модели из директории `models/`

### v0.4 — Live Tracker

- [ ] Реализация `/track <id>` — подписка через Redis pub/sub
- [ ] Фоновый воркер для обновления live-вероятностей
- [ ] Push-уведомления при значимых изменениях (порог > 5%)
- [ ] Реализация `/untrack`

### v0.5 — Paper Trading

- [ ] Реализация `/paper` — отображение виртуального портфеля
- [ ] Размещение виртуальных ставок (`/bet <id> <исход> <сумма>`)
- [ ] Автоматическое закрытие ставок по результатам матчей
- [ ] Реализация `/stats` — Brier Score, ROI, история ставок

### v1.0 — Production-ready

- [ ] Миграции БД через Alembic
- [ ] Rate limiting для пользователей
- [ ] Мониторинг (Prometheus + Grafana)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Полное покрытие тестами (> 80%)
- [ ] Документация API (mkdocs)
