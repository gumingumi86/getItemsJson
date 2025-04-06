import os
import zipfile
import json
import io
from PIL import Image

VANILLA_JAR = "1.20.1.jar"  # 省略可能（modsのみでも可）
MODS_DIR = "mods"
OUTPUT_DIR = "output"
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")

os.makedirs(IMAGE_DIR, exist_ok=True)

item_data = []
skipped_count = 0  # スキップした件数をカウント

# 除外条件（内部アイテム・非表示アイテムなど）
excluded_keywords = [
    "empty_armor_slot", "empty_slot", "debug_", "barrier",
    "structure_void", "jigsaw", "bundle"
]

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
    global skipped_count
    print(f"Processing {jar_path}")
    with zipfile.ZipFile(jar_path, "r") as z:
        modids = set(
            x.split("/")[1] for x in z.namelist()
            if x.startswith("assets/") and len(x.split("/")) > 2
        )

        for modid in modids:
            en = load_lang(z, f"assets/{modid}/lang/en_us.json")
            jp = load_lang(z, f"assets/{modid}/lang/ja_jp.json")

            for file in z.namelist():
                if file.startswith(f"assets/{modid}/textures/item/") and file.endswith(".png"):
                    item_name = os.path.basename(file).replace(".png", "")
                    translation_key = f"item.{modid}.{item_name}"

                    en_name = en.get(translation_key, item_name)
                    jp_name = jp.get(translation_key, en_name)

                    item_id = f"{modid}:{item_name}"
                    is_untranslated = (
                        en_name == item_name and
                        jp_name == item_name and
                        "_" in item_name
                    )

                    if (
                        any(keyword in item_id for keyword in excluded_keywords) or
                        is_untranslated
                    ):
                        skipped_count += 1
                        continue

                    try:
                        img_data = z.read(file)
                        img_path = save_image(img_data, f"{modid}_{item_name}")

                        item_data.append({
                            "id": item_id,
                            "en": en_name,
                            "jp": jp_name,
                            "image": img_path
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

print(f"\n✅ Done. Exported {len(item_data)} items to {OUTPUT_DIR}/items.json")
print(f"🚫 Skipped {skipped_count} items due to exclusion rules.")
