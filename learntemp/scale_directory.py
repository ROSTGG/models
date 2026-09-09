import os
import sys

# ======== НАСТРОЙКИ ========
FREECAD_PATH = r"C:\Users\zerox\AppData\Local\Programs\FreeCAD 1.1\bin"

INPUT_FOLDER = r"C:\Users\zerox\Documents\iss"
OUTPUT_FOLDER = os.path.join(INPUT_FOLDER, "scaled")

SCALE = 1.5
# ============================

sys.path.append(FREECAD_PATH)

import FreeCAD as App
import Part

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

matrix = App.Matrix()
matrix.scale(SCALE, SCALE, SCALE)

files = [
    f for f in os.listdir(INPUT_FOLDER)
    if f.lower().endswith((".step", ".stp"))
]

print(f"Найдено {len(files)} STEP файлов")

for file in files:
    src = os.path.join(INPUT_FOLDER, file)
    dst = os.path.join(OUTPUT_FOLDER, file)

    try:
        print(f"Обработка {file}")

        shape = Part.Shape()
        shape.read(src)

        scaled = shape.transformGeometry(matrix)

        scaled.exportStep(dst)

        print("OK")

    except Exception as e:
        print(f"Ошибка: {e}")

print("Готово!")