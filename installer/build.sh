#!/bin/bash
# Build the setup programs into build/setup/, each with the game build for its platform
# inside it (export the game first, see README):
#   VrouvesSetup-windows-x64.exe, VrouvesSetup-linux-x64, VrouvesSetup-macos-{x64,arm64}.zip
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(dirname "$HERE")
OUT="$ROOT/build/setup"
PY="$ROOT/.venv/bin/python"
mkdir -p "$OUT" "$HERE/payload"

zip_files() {   # zip_files OUT.zip FILE... : the files at the root of the zip
    "$PY" - "$@" <<'EOF'
import os, sys, zipfile
out, files = sys.argv[1], sys.argv[2:]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for f in files:
        info = zipfile.ZipInfo.from_file(f, os.path.basename(f))
        info.compress_type = zipfile.ZIP_DEFLATED
        with open(f, "rb") as src:
            z.writestr(info, src.read(), compresslevel=9)
EOF
}

publish() {     # publish RID PAYLOAD: first without the game, as the uninstaller, then with it
    dotnet publish "$HERE/VrouvesSetup.csproj" -c Release -r "$1" -p:Payload=none \
        -o "$HERE/bin/uninstaller/$1" --nologo -v quiet
    local un="$HERE/bin/uninstaller/$1/VrouvesSetup"
    [ -f "$un.exe" ] && un="$un.exe"
    cp "$un" "$HERE/payload/uninstall-$1.bin"
    dotnet publish "$HERE/VrouvesSetup.csproj" -c Release -r "$1" -p:Payload="$2" \
        -p:Uninstaller="$HERE/payload/uninstall-$1.bin" -o "$HERE/bin/publish/$1" --nologo -v quiet
}

echo "== windows-x64"
zip_files "$HERE/payload/win.zip" "$ROOT/build/windows/LetsGoForVrouves.exe"
publish win-x64 "$HERE/payload/win.zip"
cp "$HERE/bin/publish/win-x64/VrouvesSetup.exe" "$OUT/VrouvesSetup-windows-x64.exe"

echo "== linux-x64"
zip_files "$HERE/payload/linux.zip" "$ROOT/build/linux/LetsGoForVrouves.x86_64"
publish linux-x64 "$HERE/payload/linux.zip"
cp "$HERE/bin/publish/linux-x64/VrouvesSetup" "$OUT/VrouvesSetup-linux-x64"
chmod +x "$OUT/VrouvesSetup-linux-x64"

# macOS: the game's own export is already a zip of the .app; the setup goes in an .app too
"$PY" -c "
from PIL import Image
Image.open('$ROOT/art/icon_1024.png').save('$HERE/payload/setup.icns')"
for arch in x64 arm64; do
    echo "== macos-$arch"
    publish "osx-$arch" "$ROOT/build/macos/LetsGoForVrouves.zip"
    APP="$HERE/bin/mac-$arch/Let's Go For Vrouves Setup.app"
    rm -rf "$HERE/bin/mac-$arch"
    mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
    cp "$HERE/bin/publish/osx-$arch/VrouvesSetup" "$APP/Contents/MacOS/"
    chmod +x "$APP/Contents/MacOS/VrouvesSetup"
    cp "$HERE/payload/setup.icns" "$APP/Contents/Resources/setup.icns"
    cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Let's Go For Vrouves Setup</string>
  <key>CFBundleDisplayName</key><string>Let's Go For Vrouves Setup</string>
  <key>CFBundleIdentifier</key><string>com.revive8bit.vrouves.setup</string>
  <key>CFBundleVersion</key><string>1.0.0</string>
  <key>CFBundleShortVersionString</key><string>1.0.0</string>
  <key>CFBundleExecutable</key><string>VrouvesSetup</string>
  <key>CFBundleIconFile</key><string>setup.icns</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
EOF
    # a zip that keeps the executable bit, so the .app runs after unzipping
    (cd "$HERE/bin/mac-$arch" && rm -f "$OUT/VrouvesSetup-macos-$arch.zip" && \
        "$PY" - "$OUT/VrouvesSetup-macos-$arch.zip" <<'EOF'
import os, sys, zipfile
out = sys.argv[1]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for base, dirs, files in os.walk("."):
        for f in files:
            p = os.path.join(base, f)
            z.write(p, os.path.relpath(p, "."))
EOF
    )
done
ls -la "$OUT"
