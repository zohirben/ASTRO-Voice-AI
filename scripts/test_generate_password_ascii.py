import asyncio
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.generate_password import generate_password

async def main():
    print("\n=== Test 1: charset='ascii', enforce_classes=True, length=20 ===")
    pwd1 = await generate_password(None, length=20, charset="ascii", enforce_classes=True, save=False)
    print(f"Generated: {pwd1}")
    if pwd1.startswith("Error:"):
        print("❌ FAILED: Returned error")
        raise SystemExit(1)
    if len(pwd1) != 20:
        print(f"❌ FAILED: Expected length 20, got {len(pwd1)}")
        raise SystemExit(2)
    # Verify it only has ASCII letters and digits (no symbols)
    if not all(c.isalnum() for c in pwd1):
        print(f"❌ FAILED: Expected only alphanumeric (ASCII), but got symbols: {pwd1}")
        raise SystemExit(3)
    print("✅ PASSED: ASCII charset with enforce_classes works")

    print("\n=== Test 2: charset='upper,digits', enforce_classes=True, length=16 ===")
    pwd2 = await generate_password(None, length=16, charset="upper,digits", enforce_classes=True, save=False)
    print(f"Generated: {pwd2}")
    if pwd2.startswith("Error:"):
        print("❌ FAILED: Returned error")
        raise SystemExit(4)
    if len(pwd2) != 16:
        print(f"❌ FAILED: Expected length 16, got {len(pwd2)}")
        raise SystemExit(5)
    # Verify it has uppercase and digits only
    if not all(c.isupper() or c.isdigit() for c in pwd2):
        print(f"❌ FAILED: Expected only uppercase and digits: {pwd2}")
        raise SystemExit(6)
    # Verify at least one from each class
    if not any(c.isupper() for c in pwd2):
        print(f"❌ FAILED: No uppercase letters when enforce_classes=True: {pwd2}")
        raise SystemExit(7)
    if not any(c.isdigit() for c in pwd2):
        print(f"❌ FAILED: No digits when enforce_classes=True: {pwd2}")
        raise SystemExit(8)
    print("✅ PASSED: upper,digits with enforce_classes works")

    print("\n=== Test 3: Empty charset (default: all), length=20, save=True ===")
    pwd3 = await generate_password(None, length=20, save=True)
    print(f"Generated: {pwd3}")
    if pwd3.startswith("Error:"):
        print("❌ FAILED: Returned error")
        raise SystemExit(9)
    if len(pwd3) != 20:
        print(f"❌ FAILED: Expected length 20, got {len(pwd3)}")
        raise SystemExit(10)
    file_path = project_root / "generated_passwords.txt"
    if not file_path.exists():
        print("❌ FAILED: generated_passwords.txt not found")
        raise SystemExit(11)
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    if not lines or pwd3 not in lines[-1]:
        print(f"❌ FAILED: Password not saved correctly")
        raise SystemExit(12)
    print("✅ PASSED: Default charset with save works")

    print("\n🎉 All tests PASSED!")

if __name__ == '__main__':
    asyncio.run(main())
