import datetime
import glob
import os
import uuid
import argparse
import sys
import json
import requests
import xmltodict
import yt_dlp
from pywidevine import Cdm, PSSH, Device
import ffmpeg

class color:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class style:
    INFO = '[' + color.GREEN + 'INFO' + color.END + '] '
    WARN = '[' + color.YELLOW + 'WARN' + color.END + '] '
    ERROR = '[' + color.RED + 'EROR' + color.END + '] '

def format_seconds(seconds: int) -> str:
    m, seconds = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f'{int(h)}h {int(m)}m {int(seconds)}s'

def getPSSH(mpd_url: str) -> str | None:
    pssh = None
    try:
        r = requests.get(url=mpd_url)
        r.raise_for_status()
        xml = xmltodict.parse(r.text)
        mpd = json.loads(json.dumps(xml))
        periods = mpd['MPD']['Period']
        if isinstance(periods, list):
            for period in periods:
                if isinstance(period['AdaptationSet'], list):
                    for ad_set in period['AdaptationSet']:
                        if ad_set['@mimeType'] == 'video/mp4':
                            try:
                                for t in ad_set['ContentProtection']:
                                    if t['@schemeIdUri'].lower() == "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed":
                                        pssh = t["cenc:pssh"]
                            except Exception:
                                pass
                else:
                    if period['AdaptationSet']['@mimeType'] == 'video/mp4':
                        try:
                            for t in period['AdaptationSet']['ContentProtection']:
                                if t['@schemeIdUri'].lower() == "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed":
                                    pssh = t["cenc:pssh"]
                        except Exception:
                            pass
        else:
            for ad_set in periods['AdaptationSet']:
                if ad_set['@mimeType'] == 'video/mp4':
                    try:
                        for t in ad_set['ContentProtection']:
                            if t['@schemeIdUri'].lower() == "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed":
                                pssh = t["cenc:pssh"]
                    except Exception:
                        pass
    except Exception:
        return None
    return pssh

def getKeys(pssh: str, lic_url: str, headers: dict = None) -> list | None:
    files = glob.glob('CDM/*.wvd')
    if not files:
        print(style.ERROR + "No .wvd files found in CDM/ directory.")
        return None

    device = Device.load(files[0])
    cdm = Cdm.from_device(device)
    session_id = cdm.open()
    challenge = cdm.get_license_challenge(session_id, PSSH(pssh))

    response = requests.post(url=lic_url, data=challenge, headers=headers or {})
    if not 200 <= response.status_code <= 299:
        print(style.ERROR + f"Unable to obtain decryption keys, got error code {response.status_code}: \n{response.text}")
        return None

    try:
        cdm.parse_license(session_id, response.content)
    except Exception as e:
        print(style.ERROR + f"Unable to parse license: {e}")
        return None

    keys = list(
        map(
            lambda key: f"{key.kid.hex}:{key.key.hex()}",
            filter(
                lambda key: key.type == 'CONTENT',
                cdm.get_keys(session_id)
            )
        )
    )
    cdm.close(session_id)
    return keys if keys else None

class Main:
    def __init__(self):
        self.video_file = None
        self.audio_file = None
        self.current_media_type = 'Video'

    def log(self, data: dict):
        done = data.get('status') == 'finished'
        name = data.get('filename')
        size, progress = 0, 0
        if (size_estimate := data.get('total_bytes_estimate')) and (size_downloaded := data.get('downloaded_bytes')):
            if size_estimate:
                size = int(size_estimate / 1000000)
                if size_downloaded:
                    progress = int(size_downloaded / size_estimate * 100)

        eta = 'N/A'
        if eta_data := data.get('eta'):
            eta = format_seconds(eta_data)

        frags = f"{data.get('fragment_index', '?')}/{data.get('fragment_count', '?')}"
        speed = int(data.get('speed', 0) / 1000) if data.get('speed') else 0

        if progress <= 25:
            percent = f'{color.RED}{round(progress) + 1}%{color.END}'
        elif 25 < progress <= 75:
            percent = f'{color.YELLOW}{round(progress) + 1}%{color.END}'
        elif progress > 75:
            percent = f'{color.GREEN}{round(progress) + 1}%{color.END}'
        else:
            percent = color.RED + '??.?%' + color.END

        progress_message = (
            f'{style.INFO}Progress ({self.current_media_type}): {percent} (ETA: {eta}, Frags: {frags}, {speed} KB/s, {size} MB)'
        )

        if name:
            if self.current_media_type == 'Video':
                self.video_file = name
            elif self.current_media_type == 'Audio':
                self.audio_file = name

        if done:
            print()
            if progress == 0:
                progress_message = ''
                self.current_media_type = 'Audio'

        print('\r' + progress_message, end="")

    def run(self, mpd_url: str = None, license_url: str = None, pssh: str = None, keys: list = None, headers: dict = None, output_name: str = None):
        if not os.path.exists("mp4decrypt"):
            print(style.ERROR + "mp4decrypt not found in current directory.")
            sys.exit(-1)

        if not mpd_url and not (self.video_file and self.audio_file):
            print(style.ERROR + "No MPD URL or media files provided.")
            sys.exit(-1)

        process_id = str(uuid.uuid4())
        output = output_name or (process_id + f'.{datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")}.mkv')

        if mpd_url:
            print(style.INFO + 'Downloading .mpd file ...')
            ydl_opts = {
                'allow_unplayable_formats': True,
                'noprogress': True,
                'quiet': True,
                'fixup': 'never',
                'format': 'bv,ba',
                'no_warnings': True,
                'outtmpl': {'default': process_id + '.f%(format_id)s.%(ext)s'},
                'progress_hooks': [self.log],
                'http_headers': headers or {}
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download(mpd_url)
            except Exception as e:
                print(style.ERROR + f"Unable to download .mpd file: {e}")
                sys.exit(-1)
            print(style.INFO + "Download successful.")

        if not keys:
            if not pssh:
                pssh = getPSSH(mpd_url) if mpd_url else None
                if not pssh:
                    print(style.ERROR + "No PSSH found or provided.")
                    sys.exit(-1)
            if not license_url:
                print(style.ERROR + "No license URL provided.")
                sys.exit(-1)
            keys = getKeys(pssh, license_url, headers)
            if not keys:
                print(style.ERROR + "Unable to extract key(s).")
                sys.exit(-1)

        print(style.INFO + "Decrypting ...")
        for media in (self.video_file, self.audio_file):
            if not media:
                continue
            media_type = 'video' if media == self.video_file else 'audio'
            extension = os.path.splitext(media)[-1]
            output_file = f'{process_id}.{media_type}.{extension}'

            command = ['mp4decrypt'] + sum([['--key', k] for k in keys], []) + [media, output_file]
            process = Popen(command, stdout=PIPE, stderr=PIPE)
            _, stderr = process.communicate()

            if errors := stderr.decode('utf-8'):
                print(style.ERROR + f"Failed decrypting {media}: {errors}")
                sys.exit(-1)

            print(style.INFO + f"Successfully decrypted {media}.")
            if media_type == 'video':
                self.video_file = output_file
            else:
                self.audio_file = output_file
            if os.path.exists(media):
                os.remove(media)

        if self.video_file and self.audio_file:
            print(style.INFO + "Muxing ...")
            video = ffmpeg.input(self.video_file)
            audio = ffmpeg.input(self.audio_file)
            stream = ffmpeg.output(video, audio, output, vcodec='copy', acodec='copy')
            stream = ffmpeg.overwrite_output(stream)
            try:
                ffmpeg.run(stream, quiet=True)
            except Exception as e:
                print(style.ERROR + f"Muxing failed: {e}")
                sys.exit(-1)
            if os.path.exists(self.video_file):
                os.remove(self.video_file)
            if os.path.exists(self.audio_file):
                os.remove(self.audio_file)
            print(style.INFO + f"Output file => {output}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="MultiMPDTool: Decrypt MPD streams or local media files.")
    parser.add_argument("mpd_url", nargs="?", help="MPD URL to download and decrypt")
    parser.add_argument("--license", help="License URL for Widevine key extraction")
    parser.add_argument("--pssh", help="PSSH for Widevine decryption")
    parser.add_argument("--keys", nargs="*", help="Decryption keys (KID:KEY format)")
    parser.add_argument("--headers", help="Headers for license request (JSON string)")
    parser.add_argument("--output", help="Output file name (without extension)")
    args = parser.parse_args()

    try:
        headers = json.loads(args.headers) if args.headers else {}
    except json.JSONDecodeError:
        print(style.ERROR + "Invalid headers JSON format.")
        sys.exit(-1)

    main = Main()
    main.run(
        mpd_url=args.mpd_url,
        license_url=args.license,
        pssh=args.pssh,
        keys=args.keys,
        headers=headers,
        output_name=args.output
    )
