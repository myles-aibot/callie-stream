import sys
import os

print("🧠 sys.path:")
for p in sys.path:
    print(" -", p)

print("\n📂 Current working directory:", os.getcwd())

print("\n📁 Directory contents:")
for root, dirs, files in os.walk("."):
    print(f"\n{root}")
    for name in dirs:
        print(f"  [D] {name}")
    for name in files:
        print(f"  [F] {name}")
