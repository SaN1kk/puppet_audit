# Выгрузка PuppetDB в CSV

Скрипты выгружают характеристики серверов и параметры служб из API PuppetDB.
Используется проверенная схема: GET на `/pdb/query/v4`, PQL в параметре `query`
и Basic Auth, как в `curl -G -u username --data-urlencode 'query=...'`.

## Настройка

Достаточно Python 3.7+ с поддержкой HTTPS и доступа к API.
Устанавливать пакеты не нужно: `pip`, `sudo` и интернет для установки не требуются.

Заполните `.env` рядом со скриптами. Если файла нет, скопируйте `.env.example`:

```dotenv
PUPPET_API=https://puppetdb-api.dh.xx.xx/pdb/query/v4
# Для Basic Auth раскомментируйте обе строки:
# PUPPET_USER=username
# PUPPET_PASSWORD="password"
```

Переменные окружения имеют приоритет над `.env`. Файл `.env` исключён из Git.
Для Basic Auth заполните обе переменные: `PUPPET_USER` и `PUPPET_PASSWORD`.
Поддерживаются строки `KEY=value`, комментарии с `#` и значения в одинарных или двойных кавычках.
Пароли с пробелами или `#` заключайте в кавычки. Подстановка `${VAR}` не выполняется.

Проверка доступа с теми же адресом и логином (пароль curl запросит отдельно):

```bash
curl -i -G -u username \
  --data-urlencode 'query=inventory[facts.dmi] { certname = "vm-test.9.dh.xx.xx" }' \
  'https://puppetdb-api.dh.xx.xx/pdb/query/v4'
```

Ожидаемый ответ — HTTP 200 и JSON-массив. Скрипт запрашивает все facts,
необходимые для CSV, и отдельно ресурсы Service.

## Один хост

```bash
python3 export_host.py vm-test-1 -o host.csv
```

## Группа хостов

В `hosts.txt` укажите точные `certname` из PuppetDB, по одному на строку:

```text
vm-test-1
vm-test-2
vm-test-3
```

```bash
python3 export_hosts.py hosts.txt -o summary.csv
```

Один хост — одна строка CSV. Пустые строки, комментарии с `#` и повторы пропускаются.
Ошибки записываются в колонку `error`, остальные хосты продолжают обрабатываться.
При наличии ошибок код завершения — `1`. Оба скрипта должны находиться рядом.
На Windows вместо `python3` используйте `python`.

CSV сохраняется в UTF-8 с BOM; словари и списки записываются как JSON.
Facts отражают последний сбор данных (`facts_timestamp`), а параметры служб — желаемую конфигурацию Puppet.
