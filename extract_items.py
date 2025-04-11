import os
import zipfile
import json
import io
from PIL import Image

VANILLA_JAR = "1.20.1.jar"  # 省略可能（modsのみでも可）
MODS_DIR = "mods"
OUTPUT_DIR = ""
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")

os.makedirs(IMAGE_DIR, exist_ok=True)

item_data = []

def load_lang(z, path):
    try:
        with z.open(path) as f:
            content = f.read().decode("utf-8")
            return json.loads(content)
    except (KeyError, json.JSONDecodeError):
        return {}

def save_image(img_bytes, name):
    image = Image.open(io.BytesIO(img_bytes))
    path = os.path.join(IMAGE_DIR, f"{name}.png")
    image.save(path)
    return path.replace("\\", "/")

def process_jar(jar_path, source_name):
    print(f"Processing {jar_path}")
    seen_ids = set()
    with zipfile.ZipFile(jar_path, "r") as z:
        modids = set(
            x.split("/")[1] for x in z.namelist()
            if x.startswith("assets/") and len(x.split("/")) > 2
        )

        for modid in modids:
            en = load_lang(z, f"assets/{modid}/lang/en_us.json")
            jp = load_lang(z, f"assets/{modid}/lang/ja_jp.json")

            for file in z.namelist():
                if not (file.startswith(f"assets/{modid}/textures/item/") or file.startswith(f"assets/{modid}/textures/block/")):
                    continue
                if not file.endswith(".png"):
                    continue

                category = "block" if "/block/" in file else "item"
                item_name = os.path.basename(file).replace(".png", "")
                item_id = f"{modid}:{item_name}"
                translation_key = f"{category}.{modid}.{item_name}"

                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                en_name = en.get(translation_key, item_name)
                jp_name = jp.get(translation_key, en_name)

                excluded_keywords = [
                    "empty_armor_slot", "empty_slot", "debug_", "barrier",
                    "structure_void", "jigsaw", "bundle"
                ]

                is_untranslated = (
                    en_name == item_name and
                    jp_name == item_name and
                    "_" in item_name
                )

                if (
                    any(keyword in item_id for keyword in excluded_keywords) or
                    is_untranslated
                ):
                    continue

                try:
                    img_data = z.read(file)
                    img_path = save_image(img_data, f"{modid}_{item_name}")

                    item_data.append({
                        "id": item_id,
                        "en": en_name,
                        "jp": jp_name,
                        "image": img_path,
                        "category": category,
                        "mod": modid
                    })
                except Exception as e:
                    print(f"Failed to process image for {file}: {e}")

# 1. Vanilla jar（任意）
if os.path.exists(VANILLA_JAR):
    process_jar(VANILLA_JAR, "minecraft")

# 2. Mod jarすべて
for file in os.listdir(MODS_DIR):
    if file.endswith(".jar"):
        process_jar(os.path.join(MODS_DIR, file), file)

# 3. JSON出力
with open(os.path.join(OUTPUT_DIR, "items.json"), "w", encoding="utf-8") as f:
    json.dump(item_data, f, ensure_ascii=False, indent=2)

print(f"\nDone. Exported {len(item_data)} items to {OUTPUT_DIR}/items.json")
