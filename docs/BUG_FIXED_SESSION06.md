# BUG_FIXED_SESSION06.md

- سرویس و اعضای تیم: S1-ACC (مدیریت مشتری و حساب) | مسیح مهدوی نیا/محمدرضا رضویان/ ایلیا حبیبیان فرد
- مخزن تمرین: [[لینک مخزن LabBank-S1-Session06](https://github.com/AUT-SE1/LabBank-S1-Session06)]

## رفتار اشتباه و علت اصلی

بعد از ۵ بار ورود ناموفق پشت سر هم حساب قفل میشد، ولی مدت قفل حدود ۱۵ ثانیه بود، در حالی که طبق نیازمندی باید ۱۵ دقیقه باشد. مقدار `retry_after_seconds` و سرآیند `Retry-After` هم حدود ۱۵ برمی‌گشت و باعث میشد کاربر خیلی زودتر از موعد دوباره بتواند وارد شود.

مراحل بازتولید: ثبت یک کاربر، ۵ بار login با رمز اشتباه، و بعد login دوباره (با رمز درست) که ۴۲۹ برمیگرداند. نتیجه‌ی واقعی: `retry_after_seconds` حدود ۱۵. نتیجه‌ی مورد انتظار: حدود ۹۰۰.

علت اصلی: در تابع `register_failed_attempt` (فایل `app/routers/auth.py`) مقدار `LOCK_MINUTES` (برابر ۱۵) به پارامتر `seconds` تابع `timedelta` داده شده بود (`timedelta(seconds=LOCK_MINUTES)`) و واحد اشتباه باعث میشد `locked_until` فقط ۱۵ ثانیه بعد تنظیم شود.


## اصلاح انجام شده

- خط مشکل‌دار به `timedelta(minutes=LOCK_MINUTES)` تغییر کرد.
- ریفکتور (بدون تغییر رفتار بیرونی): بلوک تکراری بررسی ACTIVE بودن کاربر (که در `login` و `refresh` کپی شده بود) به تابع `ensure_user_is_active` منتقل شد و پیام پیش‌فرض هم در ثابت `DEFAULT_INACTIVE_MESSAGE` قرار گرفت.

## تست‌ها و نتیجه اجرا

- تست پیش از اصلاح: `test_lock_lasts_15_minutes` (تست جدید در `tests/test_login_lockout.py`) روی نسخه‌ی باگ‌دار fail شد:
```
[(.venv) masih.m@Masihs-MacBook-Air LabBank-S1-Session06 % python -m pytest tests/test_login_lockout.py::test_lock_lasts_15_minutes -q

F                                                                                                                             [100%]
============================================================= FAILURES ==============================================================
____________________________________________________ test_lock_lasts_15_minutes _____________________________________________________

client = <starlette.testclient.TestClient object at 0x10c93e810>

    def test_lock_lasts_15_minutes(client):
        register_user(client)
        fail_login(client, 5)
    
        response = login(client)  # still locked, even with the correct password
        assert response.status_code == 429
        retry_after = response.json()["retry_after_seconds"]
>       assert 14 * 60 < retry_after <= 15 * 60  # about 15 minutes, not 15 seconds
E       assert (14 * 60) < 15

tests/test_login_lockout.py:61: AssertionError
------------------------------------------------------- Captured stderr call --------------------------------------------------------
{"level": "INFO", "time": "2026-11-13T08:55:09.380941+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b3e-7a31-a7f1-80865af120ed", "method": "POST", "path": "/api/v1/users", "status": 201}
HTTP Request: POST http://testserver/api/v1/users "HTTP/1.1 201 Created"
{"level": "INFO", "time": "2026-11-13T08:55:09.385214+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b46-7164-b23a-f47fa520e5b8", "method": "POST", "path": "/api/v1/auth/login", "status": 401}
HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 401 Unauthorized"
{"level": "INFO", "time": "2026-11-13T08:55:09.387890+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b4a-7f1f-9424-88360ec85558", "method": "POST", "path": "/api/v1/auth/login", "status": 401}
HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 401 Unauthorized"
{"level": "INFO", "time": "2026-11-13T08:55:09.390525+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b4c-79b0-82ed-63054c84d690", "method": "POST", "path": "/api/v1/auth/login", "status": 401}
HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 401 Unauthorized"
{"level": "INFO", "time": "2026-11-13T08:55:09.392955+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b4f-757c-95c5-4a17b52ebc3d", "method": "POST", "path": "/api/v1/auth/login", "status": 401}
HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 401 Unauthorized"
{"level": "INFO", "time": "2026-11-13T08:55:09.395928+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b51-79ae-ba1f-00b50a2cb695", "method": "POST", "path": "/api/v1/auth/login", "status": 401}
HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 401 Unauthorized"
{"level": "INFO", "time": "2026-11-13T08:55:09.397181+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b54-7a63-ad5e-6337afc4a56d", "method": "POST", "path": "/api/v1/auth/login", "status": 429}
HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 429 Too Many Requests"
--------------------------------------------------------- Captured log call ---------------------------------------------------------
INFO     labbank:middleware.py:19 {"level": "INFO", "time": "2026-11-13T08:55:09.380941+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b3e-7a31-a7f1-80865af120ed", "method": "POST", "path": "/api/v1/users", "status": 201}
INFO     httpx:_client.py:1025 HTTP Request: POST http://testserver/api/v1/users "HTTP/1.1 201 Created"
INFO     labbank:middleware.py:19 {"level": "INFO", "time": "2026-11-13T08:55:09.385214+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b46-7164-b23a-f47fa520e5b8", "method": "POST", "path": "/api/v1/auth/login", "status": 401}
INFO     httpx:_client.py:1025 HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 401 Unauthorized"
INFO     labbank:middleware.py:19 {"level": "INFO", "time": "2026-11-13T08:55:09.387890+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b4a-7f1f-9424-88360ec85558", "method": "POST", "path": "/api/v1/auth/login", "status": 401}
INFO     httpx:_client.py:1025 HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 401 Unauthorized"
INFO     labbank:middleware.py:19 {"level": "INFO", "time": "2026-11-13T08:55:09.390525+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b4c-79b0-82ed-63054c84d690", "method": "POST", "path": "/api/v1/auth/login", "status": 401}
INFO     httpx:_client.py:1025 HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 401 Unauthorized"
INFO     labbank:middleware.py:19 {"level": "INFO", "time": "2026-11-13T08:55:09.392955+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b4f-757c-95c5-4a17b52ebc3d", "method": "POST", "path": "/api/v1/auth/login", "status": 401}
INFO     httpx:_client.py:1025 HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 401 Unauthorized"
INFO     labbank:middleware.py:19 {"level": "INFO", "time": "2026-11-13T08:55:09.395928+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b51-79ae-ba1f-00b50a2cb695", "method": "POST", "path": "/api/v1/auth/login", "status": 401}
INFO     httpx:_client.py:1025 HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 401 Unauthorized"
INFO     labbank:middleware.py:19 {"level": "INFO", "time": "2026-11-13T08:55:09.397181+00:00", "service": "S1-ACC", "correlation_id": "01a1d41e-2b54-7a63-ad5e-6337afc4a56d", "method": "POST", "path": "/api/v1/auth/login", "status": 429}
INFO     httpx:_client.py:1025 HTTP Request: POST http://testserver/api/v1/auth/login "HTTP/1.1 429 Too Many Requests"
========================================================= warnings summary ==========================================================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /Users/masih.m/Temp/temp/LabBank-S1-Session06/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================================================== short test summary info ======================================================
FAILED tests/test_login_lockout.py::test_lock_lasts_15_minutes - assert (14 * 60) < 15
1 failed, 1 warning in 0.05s
(.venv) masih.m@Masihs-MacBook-Air LabBank-S1-Session06 % ]
```
- تست پس از اصلاح: همان تست pass شد:
```
[(.venv) masih.m@Masihs-MacBook-Air LabBank-S1-Session06 % python -m pytest tests/test_login_lockout.py::test_lock_lasts_15_minutes -q
.                                                                                                            [100%]
================================================= warnings summary =================================================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /Users/masih.m/Temp/temp/LabBank-S1-Session06/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 1 warning in 0.03s
(.venv) masih.m@Masihs-MacBook-Air LabBank-S1-Session06 % ]
```
- نتیجه کل تست‌ها: `python -m pytest -q` → [103] passed، بدون failure و regression.

## فایل‌های تغییر یافته

- `app/routers/auth.py` (رفع باگ و ریفکتور)
- `tests/test_login_lockout.py` (تست رگرسیون جدید)

## نتیجه نهایی

باگ قفل ورود رفع شد و حالا قفل بعد از ۵ تلاش ناموفق ۱۵ دقیقه طول می‌کشد و `retry_after_seconds` و `Retry-After` مقدار درست را اعلام می‌کنند. تست رگرسیون قبل از اصلاح fail و بعد از آن pass شد و تست‌های قبلی هم همچنان pass هستند.