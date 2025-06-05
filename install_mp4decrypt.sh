#!/data/data/com.termux/files/usr/bin/bash

echo "[*] Updating packages..."
pkg update -y && pkg upgrade -y

echo "[*] Installing build tools..."
pkg install -y git cmake clang make || {
    echo "[!] Failed to install build tools."
    exit 1
}

echo "[*] Checking for existing mp4decrypt..."
TARGET_DIR="${OLDPWD:-$(pwd)}"
if [ -f "$TARGET_DIR/mp4decrypt" ] && "$TARGET_DIR/mp4decrypt" --version &>/dev/null; then
    echo "[✅] mp4decrypt already installed and functional in $TARGET_DIR"
    exit 0
fi

echo "[*] Cloning Bento4..."
cd $HOME
git clone https://github.com/axiomatic-systems/Bento4.git || {
    echo "[!] Failed to clone Bento4."
    exit 1
}

echo "[*] Building mp4decrypt..."
cd Bento4
mkdir -p build && cd build
cmake .. && make -j$(nproc) || {
    echo "[!] mp4decrypt build failed."
    exit 1
}

if [ ! -f mp4decrypt ]; then
    echo "[!] mp4decrypt build failed."
    exit 1
fi

echo "[*] Moving mp4decrypt to $TARGET_DIR"
cp mp4decrypt "$TARGET_DIR/"
chmod +x "$TARGET_DIR/mp4decrypt"

echo "[✅] mp4decrypt successfully installed to $TARGET_DIR"
"$TARGET_DIR/mp4decrypt" --version
