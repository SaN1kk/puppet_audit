# Выгрузка PuppetDB в CSV

Скрипты выгружают характеристики серверов и параметры служб из PuppetDB через nginx.
Адрес `PUPPET_API` должен вести на API PuppetDB `/pdb/query/v4`.

## Настройка

Установите Python 3.9+ и зависимости. Команды ниже — для PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Заполните `.env` рядом со скриптами. Если файла нет, скопируйте `.env.example`:

```dotenv
PUPPET_API=https://puppetboard.example.ru/pdb/query/v4
# Для Basic Auth раскомментируйте обе строки:
# PUPPET_USER=username
# PUPPET_PASSWORD="password"
```

Переменные окружения имеют приоритет над `.env`. Файл `.env` исключён из Git.

## Один хост

```powershell
.\.venv\Scripts\python.exe export_host.py vm-test-1 -o host.csv
```

## Группа хостов

В `hosts.txt` укажите точные `certname` из PuppetDB, по одному на строку:

```text
vm-test-1
vm-test-2
vm-test-3
```

```powershell
.\.venv\Scripts\python.exe export_hosts.py hosts.txt -o summary.csv
```

Один хост — одна строка CSV. Пустые строки, комментарии с `#` и повторы пропускаются.
Ошибки записываются в колонку `error`, остальные хосты продолжают обрабатываться.
При наличии ошибок код завершения — `1`. Оба скрипта должны находиться рядом.

CSV сохраняется в UTF-8 с BOM; словари и списки записываются как JSON.
Facts отражают последний сбор данных (`facts_timestamp`), а параметры служб — желаемую конфигурацию Puppet.
