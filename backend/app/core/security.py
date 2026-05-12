"""Security utilities placeholder — JWT / password hashing to be added."""


def verify_api_key(provided: str, expected: str) -> bool:
    import secrets
    return secrets.compare_digest(provided, expected)
