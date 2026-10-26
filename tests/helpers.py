def valid_payload(**overrides) -> dict:
    payload = {
        "national_code": "0013542419",
        "name": "علی رضایی",
        "birth_date": "1995-03-21",
        "phone_number": "09123456789",
        "address": "تهران، خیابان آزادی، پلاک ۱۰",
        "postal_code": "1593656789",
    }
    payload.update(overrides)
    return payload
