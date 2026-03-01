"""
generator.py - Secure random password generation.
Uses Python's `secrets` module (CSPRNG) instead of `random`.
"""

import secrets
import string


LOWERCASE = string.ascii_lowercase
UPPERCASE = string.ascii_uppercase
DIGITS = string.digits
SYMBOLS = "!@#$%^&*()-_=+[]{}|;:,.<>?"


def generate_password(
    length: int = 20,
    use_lowercase: bool = True,
    use_uppercase: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    exclude_ambiguous: bool = False,
) -> str:
    """
    Generate a cryptographically secure random password.

    Parameters
    ----------
    length          : total character count (8–128)
    use_lowercase   : include a–z
    use_uppercase   : include A–Z
    use_digits      : include 0–9
    use_symbols     : include special characters
    exclude_ambiguous: remove characters that look similar (0/O, l/1/I)

    Raises ValueError if no character sets are selected or length < 8.
    """
    if length < 8:
        raise ValueError("Password length must be at least 8 characters.")
    if length > 128:
        raise ValueError("Password length must not exceed 128 characters.")

    pool = ""
    required_chars = []

    if use_lowercase:
        chars = LOWERCASE
        if exclude_ambiguous:
            chars = chars.replace("l", "").replace("o", "")
        pool += chars
        required_chars.append(secrets.choice(chars))

    if use_uppercase:
        chars = UPPERCASE
        if exclude_ambiguous:
            chars = chars.replace("I", "").replace("O", "")
        pool += chars
        required_chars.append(secrets.choice(chars))

    if use_digits:
        chars = DIGITS
        if exclude_ambiguous:
            chars = chars.replace("0", "").replace("1", "")
        pool += chars
        required_chars.append(secrets.choice(chars))

    if use_symbols:
        pool += SYMBOLS
        required_chars.append(secrets.choice(SYMBOLS))

    if not pool:
        raise ValueError("At least one character set must be selected.")

    # Fill remaining slots from the full pool
    remaining = length - len(required_chars)
    password_chars = required_chars + [secrets.choice(pool) for _ in range(remaining)]

    # Shuffle to avoid predictable positions for required chars
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def estimate_entropy(password: str) -> float:
    """
    Return a rough Shannon-entropy estimate (bits) for *password*.
    Useful for displaying password strength.
    """
    pool_size = 0
    has_lower = any(c in LOWERCASE for c in password)
    has_upper = any(c in UPPERCASE for c in password)
    has_digit = any(c in DIGITS for c in password)
    has_symbol = any(c in SYMBOLS for c in password)

    if has_lower:
        pool_size += 26
    if has_upper:
        pool_size += 26
    if has_digit:
        pool_size += 10
    if has_symbol:
        pool_size += len(SYMBOLS)

    if pool_size == 0:
        return 0.0
    import math
    return len(password) * math.log2(pool_size)


def strength_label(entropy: float) -> tuple[str, str]:
    """Return (label, colour) based on entropy bits."""
    if entropy < 40:
        return "Weak", "#e74c3c"
    elif entropy < 60:
        return "Fair", "#e67e22"
    elif entropy < 80:
        return "Good", "#f1c40f"
    elif entropy < 100:
        return "Strong", "#2ecc71"
    else:
        return "Very Strong", "#27ae60"
