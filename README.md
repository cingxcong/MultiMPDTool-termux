# 🎬 MultiMPDTool

A **Textual-based GUI and CLI tool** for downloading and decrypting MPD (DASH) streams using `mp4decrypt` and Widevine DRM.  
**Optimized for Termux** on Android.

---

## ✨ Features

- 🔓 Download & decrypt MPD streams or decrypt **existing video/audio** files.
- 📝 Input:
  - MPD URL
  - License URL
  - PSSH
  - Headers (JSON)
  - Decryption keys
  - Output file name
- 📋 Clipboard support (Paste URLs easily).
- 🔎 Test MPD URL availability.
- 🕘 Save & load MPD history.
- 🗂 Export output as ZIP.
- 🌙 Dark Mode toggle (`d` key).
- 💻 Command-line interface for automation.

---

## 📦 Prerequisites

- ✅ **Termux** installed on Android.
- ✅ Widevine CDM file in `.wvd` format (containing device credentials).
- ✅ `mp4decrypt` binary (installed via script below).
- ✅ Python 3.11+ and other dependencies.

---

## 🛠 Installation

```bash
# Install required packages
pkg install python git ffmpeg clang cmake make termux-api -y

# Clone the MultiMPDTool repository
git clone https://github.com/cingxcong/MultiMPDTool-termux.git

# Change directory
cd MultiMPDTool-termux

# Install Python dependencies
pip install -r requirements.txt

# Make mp4decrypt installer executable
chmod +x install_mp4decrypt.sh

# Run the installer for mp4decrypt
./install_mp4decrypt.sh

# Create CDM folder and copy your .wvd file
mkdir CDM
cp /path/to/your/cdm/*.wvd CDM/

# Run the Textual GUI tool
python3 gui_multimpdtool.py
