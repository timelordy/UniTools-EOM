#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to analyze character encodings in family names
"""

# Paste the exact family name from Revit here:
family_name = "TSL_LD_т_СТ_в_IP20_Вкл_1P_1кл"

print("Family name analysis:")
print(f"String: {family_name}")
print(f"\nCharacter breakdown:")

for i, char in enumerate(family_name):
    print(f"  [{i:2d}] '{char}' -> U+{ord(char):04X} ({ord(char)}) - {char.encode('unicode-escape').decode('ascii')}")

print("\n" + "="*60)
print("Full hex representation:")
print(family_name.encode('utf-8').hex())
