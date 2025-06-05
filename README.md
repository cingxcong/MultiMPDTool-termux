# MultiMPDTool

A Textual-based GUI and command-line tool for decrypting MPD streams using `mp4decrypt` and Widevine DRM. Designed for use in Termux on Android.

## Features
- Download and decrypt MPD streams or decrypt local video/audio files.
- Input MPD URL, License URL, PSSH, keys, headers (JSON), and output name via GUI.
- Test MPD URL accessibility.
- Paste URLs from clipboard.
- Save and load MPD history.
- Export decrypted files to a ZIP archive.
- Dark mode toggle (`d` key).
- Command-line interface for scripting.

## Prerequisites
- **Termux** installed on an Android device.
- Widevine CDM files (`device_client_id_blob` and `device_private_key`).
- `mp4decrypt` binary (installed via `install_mp4decrypt.sh`).

## Installation

1. **Install Termux dependencies**:
   ```bash
   pkg install python git ffmpeg clang cmake make -y
   pip install -r requirements.txt
