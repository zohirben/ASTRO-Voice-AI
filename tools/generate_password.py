from livekit.agents import function_tool, RunContext
import secrets
import string
import logging
from pathlib import Path
from datetime import datetime


@function_tool()
async def generate_password(
    context: RunContext,  # type: ignore
    length: int = 16,
    charset: str = "",
    enforce_classes: bool = False,
    save: bool = True,
) -> str:
    """
    Generate a secure random password using the `secrets` module.
    
    The LLM calls this when the user asks to generate, create, or make a password.
    Supports custom length, character sets, and optional enforcement of character classes.

    Args:
        context: RunContext for session access (used for logging)
        length: Desired password length (must be > 0, default 16)
        charset: Either a comma-separated list of named classes or a literal string of characters.
                 Named classes: upper, lower, digits, symbols, ascii (upper+lower+digits), all (default: all)
                 Examples: "upper,digits" or "lower,symbols" or "ascii" or literal chars like "abc123!@#"
                 If empty (default), all classes (upper+lower+digits+symbols) are used.
        enforce_classes: If True and named classes are used, ensure at least one character
                         from each selected class appears in the password.
        save: If True (default) append the generated password with a timestamp to
              a plaintext file `generated_passwords.txt` in the project root.    Returns:
        The generated password on success, or a string starting with "Error:" on failure.

    Security note:
        This tool writes generated passwords in plain text if `save=True`. Plain-text storage
        is insecure. Use with awareness. This file is created at the repository root and is
        not encrypted.
    """
    try:
        if length <= 0:
            return "Error: length must be a positive integer"

        # Named classes we recognize
        named = {
            "upper": string.ascii_uppercase,
            "lower": string.ascii_lowercase,
            "digits": string.digits,
            "symbols": string.punctuation,
            "ascii": string.ascii_letters + string.digits,  # upper+lower+digits (no symbols)
            "all": string.ascii_letters + string.digits + string.punctuation,
        }

        # If charset is provided and looks like a comma-separated list of named classes,
        # use those; otherwise, if charset is provided treat it as a literal alphabet.
        selected_pools: dict[str, str] = {}
        if charset:
            parts = [p.strip().lower() for p in charset.split(",") if p.strip()]
            if parts and all(p in named for p in parts):
                for p in parts:
                    selected_pools[p] = named[p]
            else:
                # Treat charset as literal set of characters
                pool = "".join(sorted(set(charset)))
                if not pool:
                    return "Error: provided charset resulted in empty character set"
                # Simple generation (can't enforce classes for literal charsets)
                pwd = "".join(secrets.choice(pool) for _ in range(length))
                if save:
                    path = Path(__file__).resolve().parents[1] / "generated_passwords.txt"
                    with open(path, "a", encoding="utf-8") as f:
                        f.write(f"{datetime.utcnow().isoformat()}Z\tlength={length}\tcharset={repr(charset)}\tpassword={pwd}\n")
                    logging.info(f"✅ Password saved to generated_passwords.txt")
                return pwd
        else:
            # default: all classes (upper+lower+digits+symbols)
            selected_pools = {
                "upper": named["upper"],
                "lower": named["lower"],
                "digits": named["digits"],
                "symbols": named["symbols"],
            }

        # Build the available characters pool
        available_chars = "".join({c for pool in selected_pools.values() for c in pool})
        if not available_chars:
            return "Error: no characters available for password generation"

        pwd_chars: list[str] = []
        if enforce_classes:
            # ensure at least one character from each selected class
            required_pools = [p for p in selected_pools.values() if p]
            if length < len(required_pools):
                return f"Error: length {length} too small to include {len(required_pools)} required character classes"
            for pool in required_pools:
                pwd_chars.append(secrets.choice(pool))

            # fill the rest
            for _ in range(length - len(pwd_chars)):
                pwd_chars.append(secrets.choice(available_chars))
        else:
            for _ in range(length):
                pwd_chars.append(secrets.choice(available_chars))

        # Shuffle to avoid predictable placement of required chars
        secrets.SystemRandom().shuffle(pwd_chars)
        pwd = "".join(pwd_chars)

        if save:
            path = Path(__file__).resolve().parents[1] / "generated_passwords.txt"
            try:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"{datetime.utcnow().isoformat()}Z\tlength={length}\tenforce_classes={enforce_classes}\tcharset={','.join(selected_pools.keys())}\tpassword={pwd}\n")
                logging.info(f"✅ Password saved to generated_passwords.txt")
            except Exception:
                # don't fail generation if file write fails; just log
                logging.exception("generate_password: failed to write password to file")

        return pwd
    except Exception:
        logging.exception("generate_password: unexpected error")
        return "Error: failed to generate password"
