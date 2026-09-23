import os
import cloudinary
import cloudinary.uploader
from pathlib import Path

# Cloudinary membaca CLOUDINARY_URL dari environment variable
cloudinary.config(secure=True)

MEDIA_ROOT = Path("media")

if not MEDIA_ROOT.exists():
    print("Folder media tidak ditemukan!")
    exit()

files = [
    file for file in MEDIA_ROOT.rglob("*")
    if file.is_file()
]

print(f"Ditemukan {len(files)} file.")

for file in files:
    relative_path = file.relative_to(MEDIA_ROOT)
    public_id = str(relative_path.with_suffix("")).replace("\\", "/")

    print(f"Uploading: {file}")

    try:
        result = cloudinary.uploader.upload(
            str(file),
            public_id=public_id,
            resource_type="image",
            overwrite=True,
        )

        print(f"SUCCESS: {result['secure_url']}")

    except Exception as e:
        print(f"ERROR: {file}")
        print(e)

print("SELESAI!")