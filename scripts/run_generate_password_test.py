import asyncio
from pathlib import Path
import sys

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.generate_password import generate_password

async def main():
    print("Running generate_password test...")
    pwd = await generate_password(None, length=20, save=True)
    print("Generated:", pwd)
    if not isinstance(pwd, str) or pwd.startswith("Error:"):
        print("Test FAILED: tool returned error or non-string")
        raise SystemExit(2)
    if len(pwd) != 20:
        print(f"Test FAILED: expected length 20 but got {len(pwd)}")
        raise SystemExit(3)

    # Verify file exists in project root
    file_path = project_root / "generated_passwords.txt"
    if not file_path.exists():
        print("Test FAILED: generated_passwords.txt not found")
        raise SystemExit(4)

    # Check last line contains the password
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    if not lines:
        print("Test FAILED: generated_passwords.txt is empty")
        raise SystemExit(5)
    last = lines[-1]
    if pwd in last:
        print("Test PASSED: password saved to generated_passwords.txt")
        print("Last line:", last)
        raise SystemExit(0)
    else:
        print("Test FAILED: password not found in last line")
        print("Last line:", last)
        raise SystemExit(6)

if __name__ == '__main__':
    asyncio.run(main())
