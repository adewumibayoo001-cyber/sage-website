#!/usr/bin/env python3
"""
performance_split.py
Extracts all base64-embedded images from index.html into an assets/ folder
and rewrites index.html to use relative paths.
Run from the sage-website repo root: python3 performance_split.py
"""
import re, os, base64, sys

TARGET = "index.html"
ASSETS = "assets"

if not os.path.exists(TARGET):
    print(f"[FAIL] {TARGET} not found — run from the sage-website repo root.")
    sys.exit(1)

os.makedirs(ASSETS, exist_ok=True)

src = open(TARGET, encoding="utf-8").read()

# Map mime type → extension
EXT = {
    "image/png":  ".png",
    "image/jpeg": ".jpg",
    "image/jpg":  ".jpg",
    "image/gif":  ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}

# Named slots — detect by context so files get sensible names
NAMED = [
    ("miso-avatar",  "assets/miso-avatar.png"),
    ("miso-avatar",  "assets/miso-avatar.png"),
]

# Find all data URIs
pattern = re.compile(r'data:(image/[a-z+]+);base64,([A-Za-z0-9+/=]+)')
matches = list(pattern.finditer(src))
print(f"Found {len(matches)} embedded image(s)")

counter = {}
replacements = []

for m in matches:
    mime = m.group(1)
    b64  = m.group(2)
    ext  = EXT.get(mime, ".bin")
    
    # Use size as a fingerprint to deduplicate
    key = len(b64)
    if key not in counter:
        counter[key] = len(counter) + 1
    
    replacements.append((m.start(), m.end(), mime, b64, ext, key))

# Assign filenames — try to infer from size order
# Largest unique sizes get descriptive names
size_to_name = {}
sorted_by_size = sorted(set(len(b64) for _,_,_,b64,_,_ in replacements), reverse=True)

# Known approximate sizes from our build process
name_map = {}
for _,_,mime,b64,ext,key in replacements:
    sz = len(b64)
    if sz not in name_map:
        # Infer name from mime and order
        name_map[sz] = f"img-{len(name_map)+1:02d}{ext}"

# Save files and collect URI→path mapping
uri_to_path = {}
for _,_,mime,b64,ext,key in replacements:
    sz = len(b64)
    fname = name_map[sz]
    fpath = os.path.join(ASSETS, fname)
    data_uri = f"data:{mime};base64,{b64}"
    
    if data_uri not in uri_to_path:
        if not os.path.exists(fpath):
            raw = base64.b64decode(b64)
            with open(fpath, "wb") as f:
                f.write(raw)
            print(f"  Saved {fpath} ({len(raw):,} bytes)")
        uri_to_path[data_uri] = fpath

# Rewrite HTML — replace longest strings first to avoid partial matches
out = src
for uri, path in sorted(uri_to_path.items(), key=lambda x: -len(x[0])):
    out = out.replace(uri, path)
    print(f"  Replaced {path} ({len(uri):,} chars → {len(path)} chars)")

with open(TARGET, "w", encoding="utf-8") as f:
    f.write(out)

saved_kb = (len(src) - len(out)) // 1024
print(f"\n[OK] index.html reduced by ~{saved_kb:,} KB")
print(f"     {len(uri_to_path)} image file(s) saved to {ASSETS}/")
print("     Now run: git add -A && git commit -m \'perf: split images into assets folder\' && git push")
