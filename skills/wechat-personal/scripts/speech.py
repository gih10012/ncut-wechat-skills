"""Generate a private, normalized PCM WAV for either client's call-play command."""
import argparse
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import wave


PACKAGE = 'edge-tts==7.2.8'
MAX_CHARS = 1200
MAX_SECONDS = 300


class SpeechError(ValueError):
    pass


def pcm_info(path):
    if path.stat().st_size > MAX_SECONDS * 32000 + 4096:
        raise SpeechError('SPEECH_AUDIO_TOO_LARGE')
    try:
        with wave.open(str(path), 'rb') as stream:
            if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate(),
                    stream.getcomptype()) != (1, 2, 16000, 'NONE'):
                raise SpeechError('SPEECH_PCM_FORMAT_REQUIRED')
            frames = stream.getnframes()
            duration = frames / 16000
            if not .1 <= duration <= MAX_SECONDS:
                raise SpeechError('SPEECH_DURATION_OUT_OF_RANGE')
            raw = stream.readframes(frames)
    except (wave.Error, EOFError) as exc:
        raise SpeechError('SPEECH_INVALID_WAV') from exc
    if len(raw) != frames * 2:
        raise SpeechError('SPEECH_TRUNCATED_WAV')
    samples = array('h', raw)
    if sys.byteorder != 'little':
        samples.byteswap()
    peak = max(abs(sample) for sample in samples)
    if not peak:
        raise SpeechError('SPEECH_EMPTY_AUDIO')
    peak_dbfs = 20 * math.log10(peak / 32768)
    if peak_dbfs > -5.5:
        raise SpeechError('SPEECH_PEAK_TOO_HIGH')
    rms = math.sqrt(sum(sample * sample for sample in samples) / frames)
    return {
        'sample_rate': 16000, 'channels': 1, 'sample_width_bytes': 2,
        'duration_seconds': duration, 'peak_dbfs': round(peak_dbfs, 3),
        'rms_dbfs': round(20 * math.log10(rms / 32768), 3),
        'clipped_samples': sum(abs(sample) >= 32767 for sample in samples),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def run_stage(command, timeout, failure):
    try:
        completed = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise SpeechError(failure + '_TIMEOUT') from exc
    # Provider diagnostics can contain submitted text or URLs. Return only the
    # failed stage, and never publish an incomplete file as the requested WAV.
    if completed.returncode:
        raise SpeechError(failure)


def synthesize(text, output, voice='zh-CN-XiaoxiaoNeural', rate=-5):
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_CHARS or '\0' in text:
        raise SpeechError('SPEECH_TEXT_REQUIRED_MAX_1200_CHARACTERS')
    if not re.fullmatch(r'[A-Za-z]{2,3}-[A-Za-z]{2,4}-[A-Za-z0-9]+Neural', voice):
        raise SpeechError('SPEECH_INVALID_VOICE')
    if not isinstance(rate, int) or not -50 <= rate <= 50:
        raise SpeechError('SPEECH_RATE_MUST_BE_MINUS_50_TO_50_PERCENT')
    output = Path(os.path.abspath(Path(output).expanduser()))
    if output.suffix.lower() != '.wav':
        raise SpeechError('SPEECH_WAV_OUTPUT_REQUIRED')
    if os.path.lexists(output):
        raise SpeechError('SPEECH_OUTPUT_EXISTS')
    uvx, ffmpeg = shutil.which('uvx'), shutil.which('ffmpeg')
    if not uvx or not ffmpeg:
        raise SpeechError('SPEECH_REQUIRES_UVX_AND_FFMPEG')
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix='.wechat-speech-', dir=output.parent) as temporary:
        folder = Path(temporary)
        text_file, media, wav = folder / 'text.txt', folder / 'speech.mp3', folder / 'speech.wav'
        text_file.write_text(text, encoding='utf-8')
        text_file.chmod(0o600)
        run_stage([uvx, '--from', PACKAGE, 'edge-tts', '--voice', voice,
                   f'--rate={rate:+d}%', '--volume=-20%', '--file', str(text_file),
                   '--write-media', str(media)], 90, 'SPEECH_SERVICE_FAILED')
        run_stage([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin',
                   '-i', str(media), '-af', 'loudnorm=I=-22:TP=-6:LRA=7',
                   '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', str(wav)],
                  45, 'SPEECH_CONVERSION_FAILED')
        info = pcm_info(wav)
        wav.chmod(0o600)
        # Publish on the same filesystem only after validation. A concurrent
        # output or symlink must never be overwritten, even after synthesis.
        try:
            os.link(wav, output)
        except FileExistsError as exc:
            raise SpeechError('SPEECH_OUTPUT_EXISTS') from exc
    return {
        'ok': True, 'engine': PACKAGE, 'provider': 'Microsoft Edge online Read Aloud',
        'api_key_required': False, 'voice': voice, 'rate_percent': rate,
        'text_characters': len(text), 'output': str(output), **info,
        'loudness_target_lufs': -22, 'true_peak_target_dbfs': -6,
        'message_send_performed': False, 'call_performed': False,
        'audio_playback_performed': False, 'phone_quality_confirmed': False,
    }


def main(argv):
    parser = argparse.ArgumentParser(prog='wechat.py speech')
    commands = parser.add_subparsers(dest='operation', required=True)
    command = commands.add_parser('synthesize', help='Generate normalized Chinese neural PCM WAV')
    source = command.add_mutually_exclusive_group(required=True)
    source.add_argument('--text')
    source.add_argument('--text-file', type=Path)
    command.add_argument('--output', type=Path, required=True)
    command.add_argument('--voice', default='zh-CN-XiaoxiaoNeural')
    command.add_argument('--rate', type=int, default=-5, help='Percent from -50 to 50')
    args = parser.parse_args(argv)
    try:
        text = args.text
        if args.text_file is not None:
            with args.text_file.expanduser().open('rb') as source_file:
                raw = source_file.read(MAX_CHARS * 4 + 1)
            if len(raw) > MAX_CHARS * 4:
                raise SpeechError('SPEECH_TEXT_REQUIRED_MAX_1200_CHARACTERS')
            try:
                text = raw.decode('utf-8')
            except UnicodeDecodeError as exc:
                raise SpeechError('SPEECH_TEXT_FILE_MUST_BE_UTF8') from exc
        return synthesize(text, args.output, args.voice, args.rate)
    except (SpeechError, OSError) as exc:
        return {'ok': False, 'code': str(exc) if isinstance(exc, SpeechError) else 'SPEECH_LOCAL_ERROR',
                'error_type': type(exc).__name__, 'message_send_performed': False,
                'call_performed': False, 'audio_playback_performed': False}


if __name__ == '__main__':
    result = main(sys.argv[1:])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['ok'] else 1)
