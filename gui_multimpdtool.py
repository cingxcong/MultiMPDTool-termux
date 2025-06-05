from textual.app import App, ComposeResult
from textual.widgets import Input, Label, Button, Static, Header, Footer, Select
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
import asyncio
import os
import subprocess
import datetime
import re
import json
from typing import List

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

HISTORY_FILE = "mpd_history.log"
CDM_DIR = "CDM"

def load_history() -> List[str]:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        print(f"Error loading history: {e}")
        return []

def append_to_history(entry: str) -> None:
    if not entry:
        return
    try:
        with open(HISTORY_FILE, "a") as f:
            f.write(entry + "\n")
    except Exception as e:
        print(f"Error appending to history: {e}")

def is_valid_url(url: str) -> bool:
    regex = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(regex, url))

def is_valid_json(json_str: str) -> bool:
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False

def check_requirements() -> tuple[bool, str]:
    if not os.path.isfile("mp4decrypt"):
        return False, "❌ mp4decrypt not found. Run install_mp4decrypt.sh first."
    if not os.path.isdir(CDM_DIR) or not any(os.listdir(CDM_DIR)):
        return False, f"❌ No CDM files found in {CDM_DIR}/."
    return True, ""

class DecryptorApp(App):
    CSS_PATH = "style.css"
    TITLE = "MultiMPDTool GUI"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    mpd_url = reactive("")
    license_url = reactive("")
    pssh = reactive("")
    keys = reactive("")
    headers = reactive("")
    output = reactive("")
    status = reactive("")

    def compose(self) -> ComposeResult:
        req_ok, req_message = check_requirements()
        if not req_ok:
            self.status = req_message

        yield Header()
        with Vertical():
            yield Label("📺 MPD URL:")
            self.mpd_input = Input(placeholder="Enter MPD URL here...")
            yield self.mpd_input

            yield Label("🔐 License URL:")
            self.license_input = Input(placeholder="Enter License URL here...")
            yield self.license_input

            yield Label("📦 PSSH:")
            self.pssh_input = Input(placeholder="Enter PSSH here...")
            yield self.pssh_input

            yield Label("🗝️ Keys (optional, one per line):")
            self.keys_input = Input(placeholder="Enter decryption keys (KID:KEY format)...")
            yield self.keys_input

            yield Label("🌐 Headers (optional, JSON format):")
            self.headers_input = Input(placeholder='Enter headers as JSON (e.g., {"Authorization": "Bearer token"})...')
            yield self.headers_input

            yield Label("💾 Output Name (optional, no extension):")
            self.output_input = Input(placeholder="Enter output file name...")
            yield self.output_input

            yield Label("🕘 History:")
            history = load_history()
            options = [("None", "")] + [(h, h) for h in history]
            self.history_select = Select(options, prompt="Select a previous MPD URL")
            yield self.history_select

            with Horizontal():
                yield Button("📋 Paste Clipboard", id="paste_clip")
                yield Button("🧪 Test MPD", id="test_mpd")
                yield Button("🚀 Run Decrypt", id="run")
                yield Button("📤 Export ZIP", id="export_zip")

            yield Static(self.status, id="status", classes="status")

        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run":
            self.mpd_url = self.mpd_input.value.strip()
            self.license_url = self.license_input.value.strip()
            self.pssh = self.pssh_input.value.strip()
            self.keys = self.keys_input.value.strip()
            self.headers = self.headers_input.value.strip()
            self.output = self.output_input.value.strip()

            if not self.mpd_url:
                self.set_status("⚠️ MPD URL is required!")
                return
            if not is_valid_url(self.mpd_url):
                self.set_status("⚠️ Invalid MPD URL format!")
                return
            if self.license_url and not is_valid_url(self.license_url):
                self.set_status("⚠️ Invalid License URL format!")
                return
            if self.headers and not is_valid_json(self.headers):
                self.set_status("⚠️ Invalid headers JSON format!")
                return

            req_ok, req_message = check_requirements()
            if not req_ok:
                self.set_status(req_message)
                return

            append_to_history(self.mpd_url)
            self.history_select.options = [("None", "")] + [(h, h) for h in load_history()]

            self.set_status("Running decryption...")
            cmd = ["python3", "multimpdtool.py", self.mpd_url]
            if self.license_url:
                cmd.extend(["--license", self.license_url])
            if self.pssh:
                cmd.extend(["--pssh", self.pssh])
            if self.keys:
                keys = self.keys.splitlines()
                cmd.extend(["--keys"] + [k.strip() for k in keys if k.strip()])
            if self.headers:
                cmd.extend(["--headers", self.headers])
            if self.output:
                cmd.extend(["--output", self.output])

            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                if process.returncode == 0:
                    self.set_status("✅ Decryption complete: " + (self.output or "default output") + ".mkv")
                else:
                    self.set_status(f"❌ Decryption failed: {stderr.decode()}")
            except Exception as e:
                self.set_status(f"❌ Error running decryption: {e}")

        elif event.button.id == "test_mpd":
            url = self.mpd_input.value.strip()
            if not url:
                self.set_status("⚠️ MPD URL is empty!")
                return
            if not is_valid_url(url):
                self.set_status("⚠️ Invalid MPD URL format!")
                return
            if not aiohttp:
                self.set_status("❌ 'aiohttp' library not installed!")
                return

            self.set_status("🔍 Testing MPD...")
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            self.set_status("✅ MPD is reachable.")
                        else:
                            self.set_status(f"❌ MPD returned {response.status}")
            except Exception as e:
                self.set_status(f"❌ Error testing MPD: {e}")

        elif event.button.id == "paste_clip":
            if not pyperclip:
                self.set_status("❌ 'pyperclip' library not installed!")
                return
            try:
                value = pyperclip.paste()
                self.mpd_input.value = value
                self.set_status("📋 MPD URL pasted from clipboard.")
            except Exception as e:
                self.set_status(f"❌ Clipboard error: {e}")

        elif event.button.id == "export_zip":
            try:
                output = f"output_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.makedirs(output, exist_ok=True)
                files_moved = False
                for f in os.listdir():
                    if f.endswith((".mp4", ".mkv", ".key", ".log")):
                        os.rename(f, os.path.join(output, f))
                        files_moved = True
                if not files_moved:
                    self.set_status("⚠️ No files found to export!")
                    return
                process = await asyncio.create_subprocess_exec(
                    "zip", "-r", f"{output}.zip", output,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                if process.returncode == 0:
                    self.set_status(f"✅ Output exported to {output}.zip")
                else:
                    self.set_status(f"❌ Export failed: {stderr.decode()}")
            except Exception as e:
                self.set_status(f"❌ Export error: {e}")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value:
            self.mpd_input.value = event.value
            self.set_status("📜 MPD loaded from history.")

    def set_status(self, message: str) -> None:
        status_widget = self.query_one("#status", Static)
        status_widget.update(message)

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

if __name__ == "__main__":
    app = DecryptorApp()
    app.run()
