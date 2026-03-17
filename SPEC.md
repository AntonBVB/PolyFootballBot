Нужно написать с нуля нового production-ready торгового бота для Polymarket CLOB под футбольную стратегию.

Цель:
создать чистого, устойчивого, тестируемого и готового к реальному запуску бота, который торгует только рынки исхода матча, входит только через BUY NO-token на команды, не торгует draw ни в каком виде, и корректно закрывает позиции с учётом новой логики входа.

Ключевая бизнес-логика:
- бот торгует только анти-исходы команд:
  - BUY NO on Team A
  - BUY NO on Team B
- бот никогда не торгует draw:
  - не BUY NO Draw
  - не BUY YES Draw
  - не SELL Draw
  - не использует draw в hedge
  - не использует draw в exit logic
- бот не торгует никакие дополнительные рынки:
  - Over/Under
  - O/U
  - Both Teams To Score / BTTS
  - Spread / Handicap
  - props
  - any other non-match-result markets

==================================================
1. СТЕК И ОБЩИЕ ТРЕБОВАНИЯ
==================================================

Использовать:
- Python 3.11+
- Docker
- docker compose
- sqlite для локального состояния
- requests или httpx для Gamma API
- py_clob_client для Polymarket CLOB
- typing
- dataclasses и/или pydantic
- logging
- unit tests для критичных частей

Нужен результат в виде:
- production-ready проекта
- понятной структуры файлов
- Dockerfile
- docker-compose.yml
- requirements.txt
- .env.example
- README.md
- автоматической инициализации sqlite схемы
- корректной поддержки dry-run и live режима

Требования к качеству:
- писать с нуля, а не патчить старую логику
- не переносить старую SELL-entry логику
- код должен быть модульным, читаемым, комментированным в критичных местах
- лучше пропустить сделку, чем создать неконсистентное состояние в БД
- бот должен быть безопасен к перезапуску контейнера

==================================================
2. ТОРГОВАЯ ВСЕЛЕННАЯ
==================================================

Бот должен поддерживать только рынки исхода матча и только в двух форматах:

A. Бинарные рынки победы команды:
- "Will Team A win on YYYY-MM-DD?"
- "Will Team B win on YYYY-MM-DD?"

B. 3-way markets формата:
- Team A
- Draw
- Team B

Что запрещено:
- бинарные рынки draw формата:
  - "Will Team A vs Team B end in a draw?"
- любые 3-way outcome с ролью DRAW
- любые O/U, BTTS, Spread и т.д.

Итого tradeable universe:
- BINARY_HOME_WIN
- BINARY_AWAY_WIN
- THREE_WAY_HOME
- THREE_WAY_AWAY

Всегда forbidden:
- BINARY_DRAW
- THREE_WAY_DRAW
- OTHER

==================================================
3. БИЗНЕС-ПРАВИЛО ПО DRAW
==================================================

Это жёсткое правило:
бот НИКОГДА не должен:
- анализировать draw как торговый кандидат
- создавать сигнал по draw
- открывать позицию по draw
- сопровождать draw позицию
- использовать draw в логике выхода
- использовать draw как хедж

Draw outcome может храниться в БД для полноты структуры рынка, но он должен быть полностью исключён из торгового pipeline.

==================================================
4. ПАРАМЕТРЫ СТРАТЕГИИ
==================================================

Сохранить все фильтры с текущими параметрами, кроме времени окна входа.

Использовать такие параметры по умолчанию:

- ENTRY_MIN = 0.73
- ENTRY_MAX = 0.83
- TAKE_PROFIT_DELTA = 0.05
- MAX_SPREAD = 0.03
- MIN_TOTAL_VOLUME = 20000
- BUY_COST_USD = 5
- MIN_AVAILABLE_USDC = 6
- OPEN_WINDOW_HOURS = 12

Сделать настраиваемыми также:
- FAST_MODE_BEFORE_START_MINUTES = 3
- PREMATCH_POLL_SECONDS = 60
- FAST_POLL_SECONDS = 15
- DISCOVERY_SECONDS = 3600
- RECONCILE_SECONDS = 600

Нужен .env.example со всеми параметрами.

==================================================
5. ГЛАВНАЯ ЛОГИКА ВХОДА
==================================================

Новая торговая логика:

- вход НЕ через SELL YES
- вход НЕ через покупку YES-token команды
- вход только через BUY NO-token конкретного outcome команды

То есть:
- если outcome = Team A и он tradeable, вход = BUY NO on Team A
- если outcome = Team B и он tradeable, вход = BUY NO on Team B
- если outcome = Draw, вход запрещён всегда

Важное следствие:
весь жизненный цикл позиции должен быть консистентным:
- BUY NO -> hold -> SELL NO

==================================================
6. DISCOVERY И НОРМАЛИЗАЦИЯ РЫНКОВ
==================================================

Бот должен регулярно обновлять рынки через Gamma API.

Требования:
1. Загружать футбольные события и рынки
2. Сохранять события, рынки, outcomes в sqlite
3. Отбирать только рынки:
   - с enable_orderbook = true
   - с валидным event start_time
   - внутри окна OPEN_WINDOW_HOURS
   - только match result markets
4. Полностью исключать:
   - O/U
   - BTTS
   - Spread
   - props
   - любые не-исходные рынки
5. Для 3-way markets:
   - корректно нормализовать outcome roles:
     - HOME
     - DRAW
     - AWAY
   - DRAW всегда non-tradeable

Нужны отдельные функции:

- classify_market_type(...) -> enum
- classify_outcome_role(...) -> enum
- is_tradeable_match_result_market(market) -> bool
- is_tradeable_outcome(market_type, outcome_role) -> bool

Ожидаемые enum:
- BINARY_HOME_WIN
- BINARY_AWAY_WIN
- BINARY_DRAW
- THREE_WAY_HOME
- THREE_WAY_DRAW
- THREE_WAY_AWAY
- OTHER

Правила tradeable outcome:
- HOME -> True
- AWAY -> True
- DRAW -> False

==================================================
7. РАБОТА С TOKEN IDS
==================================================

Нужна надёжная логика получения token_ids.

Требования:
- Gamma API может возвращать clobTokenIds как JSON-string или как массив
- нужно поддержать оба формата
- для бинарных рынков:
  - корректно получать yes_token_id и no_token_id для нужного outcome
- для 3-way markets:
  - корректно получать token_id каждого outcome
  - потом строить логику BUY NO для конкретного outcome

Нужна отдельная функция, которая для выбранного tradeable outcome возвращает всё нужное для торговли:
- resolve_tradeable_outcome_tokens(...)
или аналогичная структура

Важно:
архитектура должна явно разделять:
- market_id
- outcome_name
- outcome_role
- yes_token_id / outcome_token_id
- no_token_id, если применимо для данного механизма

Если для выбранного формата рынка есть технические ограничения CLOB-клиента и BUY NO требует особой интерпретации token semantics, это должно быть реализовано явно и задокументировано в коде.

Сделать кэш token ids.

==================================================
8. РАБОТА СО СТАКАНОМ
==================================================

Одна из критичных прошлых ошибок:
нельзя брать первый элемент bids/asks как лучший bid/ask.

Нужно:
- best_bid = max(price по bids)
- best_ask = min(price по asks)
- не предполагать, что массивы уже отсортированы

Нужна собственная внутренняя структура, например:
- AssetBookTop(best_bid, best_ask)

Важно:
в стратегии не должно быть путаницы между yes/no naming внутри py_clob_client и реальным смыслом торгуемого актива.
Нужны комментарии в коде, объясняющие:
- как интерпретируется стакан для торгуемого outcome
- как считается цена входа в BUY NO
- как считается цена выхода SELL NO

==================================================
9. ПАЙПЛАЙН ВХОДА
==================================================

Вход должен работать по outcome-level, не только по market-level.

Для каждого tradeable outcome:

1. Проверить, что outcome_role != DRAW
2. Проверить, что market_type входит в:
   - BINARY_HOME_WIN
   - BINARY_AWAY_WIN
   - THREE_WAY_HOME
   - THREE_WAY_AWAY
3. Проверить окно времени:
   - event start_time > now
   - event start_time <= now + OPEN_WINDOW_HOURS
4. Проверить:
   - enable_orderbook = true
   - total_volume > MIN_TOTAL_VOLUME
5. Получить token ids нужного outcome
6. Получить стакан нужного outcome
7. Рассчитать:
   - best_bid
   - best_ask
   - spread = best_ask - best_bid
8. Проверить:
   - ENTRY_MIN <= entry_price <= ENTRY_MAX
   - spread <= MAX_SPREAD
9. Проверить отсутствие:
   - открытого entry ордера по этому outcome
   - открытой позиции по этому outcome
10. Проверить баланс:
   - available_usdc >= MIN_AVAILABLE_USDC
11. Рассчитать размер:
   - shares = round_down(BUY_COST_USD / entry_price, 0.01)
12. Выставить LIMIT BUY для NO-логики на выбранный outcome
13. Сохранить ордер и затем позицию после подтверждения / fill

Важно:
уникальность должна быть на уровне outcome, а не только market_id.
Например:
- market_id + outcome_role
или
- market_id + outcome_token_id

Это нужно, чтобы 3-way market не блокировал HOME и AWAY друг друга неверным образом, но DRAW всегда оставался запрещённым.

==================================================
10. ЛОГИКА ВЫХОДА ИЗ ПОЗИЦИИ
==================================================

Ключевое требование:
логика выхода должна соответствовать новой логике входа.

Если вход = BUY NO на outcome,
то выход = SELL того же самого NO-token того же outcome.

Никаких инверсий через YES-token.
Никаких legacy-фрагментов SELL-entry / BUY-exit.

Нужны два сценария выхода.

A. TAKE PROFIT
--------------
Если позиция открыта:
- регулярно получать стакан по тому же outcome/token
- вычислять текущий best_bid для выхода
- если best_bid >= entry_price + TAKE_PROFIT_DELTA:
  - выставить LIMIT SELL
  - side = SELL
  - token_id = токен открытой позиции
  - price = round_down(best_bid, tick_size)
  - size = текущий объём позиции

B. PROTECTIVE EXIT
------------------
Так как стратегия прематчевая, нужна логика защитного выхода:
- если матч стартовал
или
- если рынок ушёл в live / in-play
а позиция всё ещё открыта и TP не сработал,
бот должен пытаться закрыть позицию через SELL того же outcome/token

Требования к protective exit:
- price = лучший доступный best_bid
- несколько повторных попыток при временных ошибках
- если стакан пустой, позиция должна перейти в EXIT_PENDING
- логика должна быть прозрачной и безопасной

Draw никогда не участвует ни в одной ветке выхода.

==================================================
11. ЛОГИКА ПОЗИЦИЙ
==================================================

После успешного входа должна открываться позиция по конкретному tradeable outcome.

Позиция должна хранить:
- market_id
- token_id
- outcome_name
- outcome_role
- market_format
- shares
- entry_price
- status
- timestamps

Если ордер частично заполнен:
- это должно отражаться в БД
- позиция должна учитывать фактический fill
- нельзя считать request size как filled size без проверки

==================================================
12. СОСТОЯНИЕ, SQLITE И RECONCILE
==================================================

Одна из прошлых проблем:
локальная sqlite могла содержать OPEN-ордера, которых уже нет на бирже.

Новый бот должен уметь синхронизировать локальное состояние с реальным состоянием CLOB.

Нужны таблицы:
- events
- markets
- outcomes
- orders
- positions
- возможно system_logs / task_runs / fills

Минимальные поля:

events:
- event_id
- league_name
- home_team
- away_team
- start_time
- raw_json
- created_at
- updated_at

markets:
- market_id
- event_id
- question
- slug
- market_type
- market_format
- total_volume
- tick_size
- neg_risk
- enable_orderbook
- raw_json
- created_at
- updated_at

outcomes:
- outcome_id
- market_id
- outcome_name
- outcome_role (HOME / AWAY / DRAW)
- token_id
- no_token_id если применимо
- is_tradeable
- raw_json
- created_at
- updated_at

orders:
- order_id
- market_id
- token_id
- outcome_name
- outcome_role
- market_format
- kind (ENTRY / TP / EXIT / PROTECTIVE_EXIT)
- side (BUY / SELL)
- price
- size
- filled_size
- status (OPEN / FILLED / CANCELED / REJECTED / EXPIRED / UNKNOWN)
- dry_run
- created_at
- updated_at
- exchange_payload_json
- error_message

positions:
- position_id
- market_id
- token_id
- outcome_name
- outcome_role
- market_format
- shares
- entry_price
- status (OPEN / CLOSING / CLOSED / EXIT_PENDING)
- opened_at
- closed_at
- live_detected_at
- notes

Нужен reconcile task:
- пройти по локальным OPEN ордерам
- запросить фактическое состояние на бирже
- обновить локальные статусы
- очистить stale/open мусор
- не допускать, чтобы старые dry-run или stale live записи блокировали новый вход

Нужно либо:
- полностью разделить dry-run и live данные
или
- явно маркировать их и никогда не позволять dry-run OPEN записям блокировать live стратегию

==================================================
13. БАЛАНС И ALLOWANCE
==================================================

В прошлой реализации была проблема:
нельзя вызывать balance allowance без explicit params.

Нужна надёжная функция:
- available_usdc()

Требования:
- использовать BalanceAllowanceParams
- передавать asset_type = COLLATERAL
- передавать signature_type
- при необходимости funder
- корректно обрабатывать разные форматы ответа:
  - available
  - balance
  - data.available
  - data.balance
- если баланс приходит в микроединицах, корректно переводить в USDC
- покрыть unit tests

==================================================
14. ИНИЦИАЛИЗАЦИЯ CLOB CLIENT
==================================================

Нужно корректно инициализировать Polymarket CLOB client:
- PRIVATE_KEY
- FUNDER
- SIGNATURE_TYPE
- host = https://clob.polymarket.com

Требования:
- корректно derive/create API creds
- поддержка signature_type = 2
- валидация env на старте
- безопасное логирование без утечки секретов
- понятные ошибки, если funder / signature_type / creds заданы неправильно

==================================================
15. DRY-RUN И LIVE MODE
==================================================

Нужен полноценный dry-run режим.

В dry-run:
- реальные ордера не отправляются
- но проходит весь pipeline
- логируется, какой ордер был бы отправлен
- dry-run не должен создавать фантомные OPEN-ордера, которые потом блокируют live

В live:
- ордера реально отправляются
- exchange response логируется и сохраняется в БД
- ошибки API сохраняются в БД и логах

Нужна чёткая защита от смешивания dry-run и live состояния.

==================================================
16. ОБРАБОТКА ОШИБОК
==================================================

Явно обработать:
- пустой стакан
- некорректный token_id
- Gamma API errors
- network errors
- timeouts
- 400 not enough balance / allowance
- 403 access restricted
- local sqlite stale OPEN orders
- database locked
- duplicated orders
- partial fills
- exchange / local state mismatch

Нужны безопасные retry только там, где они оправданы.

==================================================
17. ЛОГИРОВАНИЕ
==================================================

Нужны понятные структурные события, например:
- DISCOVERY_OK
- DISCOVERY_FAILED
- TOKEN_ID_LOOKUP_FAILED
- BOOK_FETCH_FAILED
- BUY_NO_ENTRY
- ENTRY_REJECTED
- TP_PLACED
- TP_REJECTED
- PROTECTIVE_EXIT_PLACED
- PROTECTIVE_EXIT_REJECTED
- RECONCILE_UPDATED
- BALANCE_FETCH_FAILED
- MARKET_SKIPPED_NON_TRADEABLE
- MARKET_SKIPPED_DRAW
- OUTCOME_SKIPPED_DRAW
- DRY_RUN_ORDER_SIMULATED

Логи должны помогать быстро понять:
- почему рынок отброшен
- почему outcome отброшен
- почему ордер не поставился
- почему позиция не закрылась

==================================================
18. SCHEDULER / TASKS
==================================================

Нужны отдельные циклы / задачи:
1. discovery task
2. prematch entry scan task
3. fast scan task перед матчем
4. live/tp/protective-exit monitor
5. reconcile task

Требования:
- каждая задача логирует старт и ошибки
- падение одной задачи не должно убивать весь процесс
- защита от overlap
- защита от database lock
- единый main loop / scheduler

==================================================
19. ТЕСТЫ
==================================================

Обязательно добавить unit tests хотя бы на:

A. Классификацию рынка:
- "Will ACF Fiorentina win on 2026-03-16?" -> tradeable
- "Will US Cremonese win on 2026-03-16?" -> tradeable
- "Will US Cremonese vs. ACF Fiorentina end in a draw?" -> not tradeable
- "US Cremonese vs. ACF Fiorentina: O/U 2.5" -> not tradeable
- "US Cremonese vs. ACF Fiorentina: Both Teams to Score" -> not tradeable
- "Spread: ACF Fiorentina (-1.5)" -> not tradeable

B. 3-way outcomes:
- Team A outcome -> tradeable
- Team B outcome -> tradeable
- Draw outcome -> not tradeable

C. Orderbook extraction:
- best bid = max(bids)
- best ask = min(asks)

D. Balance parsing:
- разные форматы ответа allowance

E. Dry-run:
- dry-run не создаёт блокирующие OPEN записи

F. Position lifecycle:
- BUY NO -> SELL NO
- protective exit использует тот же outcome/token
- draw никогда не участвует в позиции и выходе

==================================================
20. README И ДОКУМЕНТАЦИЯ
==================================================

README должен содержать:
- как настроить .env
- как запустить dry-run
- как перевести в live
- какие рынки торгуются
- почему draw запрещён
- как проверить sqlite
- как работает reconcile
- как работает BUY NO / SELL NO lifecycle

==================================================
21. ОСОБЫЕ ТРЕБОВАНИЯ К АРХИТЕКТУРЕ
==================================================

Внутри кода добавить комментарии в критичных местах:
- почему draw запрещён
- как интерпретируется матчевый outcome
- как устроен вход через BUY NO
- почему выход только SELL того же outcome/token
- как работает уникальность на уровне outcome
- как предотвращается stale state в sqlite
- как предотвращается mixing dry-run/live

Если в каком-то месте логика неоднозначна, выбирать решение, которое минимизирует риск ложного входа и ложного состояния.

==================================================
22. ЧТО НУЖНО ОТВЕТИТЬ
==================================================

Сначала:
1. предложи структуру проекта
2. кратко объясни архитектуру
3. перечисли ключевые технические решения по:
   - BUY NO entry
   - SELL NO exit
   - исключению draw
   - поддержке 3-way markets
   - фильтрации только match-result markets
   - reconcile local state with exchange
   - balance / allowance
   - корректному best bid / best ask extraction

Затем:
4. выдай полный код всех файлов проекта

Финальный код должен быть готов к запуску на сервере в dry-run и live режиме.

==================================================
23. ACCEPTANCE CRITERIA
==================================================

Проект считается принятым только если выполнены все пункты ниже.

--------------------------------------------------
A. АРХИТЕКТУРА И СБОРКА
--------------------------------------------------

AC-A1
Проект собирается без ручных правок:
- docker compose up -d --build проходит успешно
- контейнер стартует без syntax error
- приложение не падает на старте

AC-A2
Есть все обязательные файлы:
- Dockerfile
- docker-compose.yml
- requirements.txt
- .env.example
- README.md
- init schema / auto-init sqlite
- исходный код проекта
- tests

AC-A3
Код написан с нуля как новая реализация, а не как набор ad-hoc патчей поверх старой SELL-entry логики.

--------------------------------------------------
B. КОНФИГУРАЦИЯ
--------------------------------------------------

AC-B1
Все параметры читаются из .env и валидируются на старте.

AC-B2
Параметры стратегии по умолчанию:
- ENTRY_MIN = 0.73
- ENTRY_MAX = 0.83
- TAKE_PROFIT_DELTA = 0.05
- MAX_SPREAD = 0.03
- MIN_TOTAL_VOLUME = 20000
- BUY_COST_USD = 5
- MIN_AVAILABLE_USDC = 6
- OPEN_WINDOW_HOURS = 12

AC-B3
Неверный или неполный .env не приводит к молчаливой деградации — бот падает с понятной ошибкой конфигурации.

--------------------------------------------------
C. ТОРГОВАЯ ВСЕЛЕННАЯ
--------------------------------------------------

AC-C1
Бот торгует только match-result markets.

AC-C2
Бот поддерживает:
- бинарные рынки победы Team A
- бинарные рынки победы Team B
- 3-way markets формата Team A / Draw / Team B

AC-C3
Бот полностью исключает:
- бинарные draw markets
- draw outcome внутри 3-way markets
- O/U
- BTTS
- Spread
- props
- любые дополнительные рынки

AC-C4
Draw не должен попадать:
- в eligible candidates
- в сигналы
- в открытые позиции
- в exit logic
- в order placement

--------------------------------------------------
D. ЛОГИКА ВХОДА
--------------------------------------------------

AC-D1
Вход реализован только через BUY NO на команду.

AC-D2
Нигде в entry logic не используется legacy-модель:
- SELL YES как способ входа
- BUY YES вместо BUY NO

AC-D3
Для tradeable outcome бот проверяет:
- временное окно
- объём
- цену входа
- спред
- отсутствие открытого entry/position
- доступный баланс

AC-D4
Цена входа корректно интерпретируется под BUY NO модель.

AC-D5
Размер позиции считается как:
- shares = round_down(BUY_COST_USD / entry_price, 0.01)

AC-D6
В 3-way markets бот может торговать только HOME/AWAY outcome и никогда DRAW.

--------------------------------------------------
E. ЛОГИКА ВЫХОДА
--------------------------------------------------

AC-E1
Если позиция открыта через BUY NO, выход реализован только через SELL того же NO-token.

AC-E2
TP логика считает условие выхода как:
- current_best_bid >= entry_price + TAKE_PROFIT_DELTA

AC-E3
Есть protective exit при старте матча или live/in-play.

AC-E4
Protective exit работает по тому же outcome/token.

AC-E5
Draw не участвует в выходе.

--------------------------------------------------
F. TOKEN IDS И OUTCOMES
--------------------------------------------------

AC-F1
Бот корректно парсит clobTokenIds как:
- JSON-string
- list/array

AC-F2
Для tradeable outcome бот умеет корректно определить token ids.

AC-F3
Для 3-way market outcome роли корректно нормализуются:
- HOME
- DRAW
- AWAY

AC-F4
Есть явная функция определения tradeable / non-tradeable outcome.

--------------------------------------------------
G. ORDERBOOK
--------------------------------------------------

AC-G1
Лучший bid определяется как максимум по bids.

AC-G2
Лучший ask определяется как минимум по asks.

AC-G3
Код не предполагает, что bids/asks уже отсортированы.

AC-G4
Внутри стратегии нет путаницы между внутренними именами yes/no клиента и реальным смыслом торгуемого outcome/token.

--------------------------------------------------
H. SQLITE И СОСТОЯНИЕ
--------------------------------------------------

AC-H1
Есть таблицы:
- events
- markets
- outcomes
- orders
- positions

AC-H2
В orders и positions хранится outcome-level информация:
- market_id
- token_id
- outcome_name
- outcome_role
- market_format

AC-H3
Уникальность входа реализована на уровне outcome, а не только market_id.

AC-H4
Dry-run записи не блокируют live входы.

AC-H5
Stale OPEN ордера могут быть корректно reconciled и не ломают стратегию.

--------------------------------------------------
I. RECONCILE
--------------------------------------------------

AC-I1
Есть отдельный reconcile task.

AC-I2
Reconcile умеет:
- проверять реальные статусы ордеров
- обновлять sqlite
- убирать stale OPEN состояния
- корректно обрабатывать fill / cancel / reject

AC-I3
После reconcile локальное состояние не должно расходиться с биржей настолько, чтобы блокировать новые валидные входы.

--------------------------------------------------
J. BALANCE / ALLOWANCE
--------------------------------------------------

AC-J1
available_usdc() использует explicit params.

AC-J2
Передаётся asset_type.

AC-J3
Передаётся signature_type.

AC-J4
При необходимости передаётся funder.

AC-J5
Баланс корректно нормализуется до USDC.

AC-J6
Ошибки allowance логируются.

--------------------------------------------------
K. DRY-RUN / LIVE
--------------------------------------------------

AC-K1
Dry-run не шлёт реальные ордера.

AC-K2
Dry-run логирует simulated order.

AC-K3
Dry-run не создаёт блокирующее состояние.

AC-K4
Live реально шлёт ордера.

AC-K5
Live сохраняет exchange payload.

--------------------------------------------------
L. ОБРАБОТКА ОШИБОК
--------------------------------------------------

AC-L1
Обработаны:
- empty book
- token lookup failure
- gamma timeout
- network errors
- 400 balance / allowance
- 403 restricted
- sqlite lock
- stale local state
- partial fills
- duplicate entries

AC-L2
Одна упавшая задача не убивает весь бот.

AC-L3
Ошибки логируются структурно и понятно.

--------------------------------------------------
M. ТЕСТЫ
--------------------------------------------------

AC-M1
Есть unit tests на классификацию рынков.

AC-M2
Есть unit tests на 3-way outcome filtering.

AC-M3
Есть unit tests на best bid / best ask extraction.

AC-M4
Есть unit tests на balance parsing.

AC-M5
Есть unit tests на lifecycle позиции:
- BUY NO -> SELL NO

AC-M6
Есть unit tests, подтверждающие:
- draw всегда non-tradeable

--------------------------------------------------
N. README
--------------------------------------------------

AC-N1
README объясняет:
- как настроить .env
- как запустить dry-run
- как включить live
- какие рынки торгуются
- почему draw запрещён
- как проверить sqlite
- как работает reconcile
- как работает BUY NO / SELL NO lifecycle

--------------------------------------------------
O. ГОТОВНОСТЬ К ПРОДАКШЕНУ
--------------------------------------------------

AC-O1
Бот после рестарта контейнера продолжает работу корректно.

AC-O2
Бот не дублирует входы после рестарта.

AC-O3
Бот не оставляет систему в неконсистентном состоянии после сетевой ошибки.

AC-O4
В логах можно понять:
- почему рынок пропущен
- почему outcome пропущен
- почему entry не поставился
- почему exit не поставился

==================================================
24. CHECKLIST ПРИЁМКИ
==================================================

[ ] Проект собирается через docker compose up -d --build
[ ] Контейнер стартует без traceback
[ ] Есть Dockerfile, docker-compose.yml, requirements.txt, README.md, .env.example
[ ] Есть auto-init sqlite схемы
[ ] Есть tests

----------------------------------------
1. Конфиг
----------------------------------------
[ ] ENTRY_MIN = 0.73
[ ] ENTRY_MAX = 0.83
[ ] TAKE_PROFIT_DELTA = 0.05
[ ] MAX_SPREAD = 0.03
[ ] MIN_TOTAL_VOLUME = 20000
[ ] BUY_COST_USD = 5
[ ] MIN_AVAILABLE_USDC = 6
[ ] OPEN_WINDOW_HOURS = 12

----------------------------------------
2. Торговая вселенная
----------------------------------------
[ ] Бот торгует только match-result markets
[ ] Бот поддерживает binary Team A win
[ ] Бот поддерживает binary Team B win
[ ] Бот поддерживает 3-way Team A / Draw / Team B
[ ] Draw полностью исключён
[ ] O/U исключён
[ ] BTTS исключён
[ ] Spread исключён
[ ] Props исключены

----------------------------------------
3. Логика входа
----------------------------------------
[ ] Entry = BUY NO only
[ ] Нет SELL YES legacy entry
[ ] Нет BUY YES entry
[ ] Проверяется объём
[ ] Проверяется спред
[ ] Проверяется диапазон цены
[ ] Проверяется отсутствие открытого entry
[ ] Проверяется отсутствие позиции
[ ] Проверяется баланс
[ ] В 3-way tradeable только HOME/AWAY
[ ] DRAW never tradeable

----------------------------------------
4. Логика выхода
----------------------------------------
[ ] Exit = SELL same NO token
[ ] TP работает от entry_price + TAKE_PROFIT_DELTA
[ ] Есть protective exit
[ ] Protective exit работает по тому же outcome/token
[ ] Draw не участвует в выходе

----------------------------------------
5. Token ids и outcomes
----------------------------------------
[ ] clobTokenIds парсятся и как string, и как array
[ ] Есть outcome normalization
[ ] Есть outcome_role = HOME / AWAY / DRAW
[ ] Есть is_tradeable_outcome()
[ ] DRAW всегда False

----------------------------------------
6. Orderbook
----------------------------------------
[ ] best bid = max(bids)
[ ] best ask = min(asks)
[ ] Нет логики "берём первый элемент массива"
[ ] Семантика токена документирована комментариями

----------------------------------------
7. SQLite и reconcile
----------------------------------------
[ ] Есть events
[ ] Есть markets
[ ] Есть outcomes
[ ] Есть orders
[ ] Есть positions
[ ] В orders есть outcome_name / outcome_role / market_format
[ ] В positions есть outcome_name / outcome_role / market_format
[ ] Есть reconcile task
[ ] Reconcile обновляет stale OPEN
[ ] dry-run OPEN не блокируют live
[ ] Повторный старт не дублирует входы

----------------------------------------
8. Balance / allowance
----------------------------------------
[ ] available_usdc() использует explicit params
[ ] Передаётся asset_type
[ ] Передаётся signature_type
[ ] При необходимости передаётся funder
[ ] Баланс нормализуется до USDC
[ ] Ошибки allowance логируются

----------------------------------------
9. Dry-run / Live
----------------------------------------
[ ] Dry-run не шлёт реальные ордера
[ ] Dry-run логирует simulated order
[ ] Dry-run не создаёт блокирующее состояние
[ ] Live реально шлёт ордера
[ ] Live сохраняет exchange payload

----------------------------------------
10. Логи
----------------------------------------
[ ] Есть DISCOVERY_OK / DISCOVERY_FAILED
[ ] Есть BUY_NO_ENTRY
[ ] Есть ENTRY_REJECTED
[ ] Есть TP_PLACED / TP_REJECTED
[ ] Есть PROTECTIVE_EXIT_PLACED / PROTECTIVE_EXIT_REJECTED
[ ] Есть RECONCILE_UPDATED
[ ] Есть MARKET_SKIPPED_DRAW / OUTCOME_SKIPPED_DRAW
[ ] По логам понятно, почему рынок пропущен

----------------------------------------
11. Тесты
----------------------------------------
[ ] Тесты на классификацию binary markets
[ ] Тесты на 3-way HOME/AWAY/DRAW
[ ] Тесты на исключение O/U, BTTS, Spread
[ ] Тесты на best bid / best ask
[ ] Тесты на balance parsing
[ ] Тесты на BUY NO -> SELL NO lifecycle
[ ] Тесты на то, что draw никогда не торгуется

----------------------------------------
12. Финальная проверка
----------------------------------------
[ ] Dry-run запуск проходит без ошибок
[ ] Live-конфиг валидируется
[ ] Код не содержит следов старой SELL-entry архитектуры
[ ] Код готов к реальному запуску на сервере

Твоя работа считается завершённой только если результат удовлетворяет всем Acceptance Criteria и всем пунктам Checklist выше.
