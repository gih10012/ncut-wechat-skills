import importlib.util
import math
from pathlib import Path
import stat
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import wave


path = Path(__file__).resolve().parents[1] / 'scripts/speech.py'
spec = importlib.util.spec_from_file_location('wechat_speech', path)
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)


def wav(path, amplitude=8192, rate=16000, channels=1):
    samples = [int(amplitude * math.sin(2 * math.pi * 440 * index / rate))
               for index in range(rate)]
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(channels)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(struct.pack('<' + 'h' * len(samples), *samples))


class SpeechTests(unittest.TestCase):
    def test_pcm_validation_rejects_overdriven_silent_and_wrong_format(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'audio.wav'
            for settings in [dict(amplitude=32000), dict(amplitude=0), dict(rate=8000), dict(channels=2)]:
                wav(path, **settings)
                with self.assertRaises(speech.SpeechError):
                    speech.pcm_info(path)
            wav(path)
            info = speech.pcm_info(path)
            self.assertEqual(info['duration_seconds'], 1)
            self.assertAlmostEqual(info['peak_dbfs'], -12.041, places=2)
            self.assertEqual(info['clipped_samples'], 0)

    def test_truncated_pcm_is_not_published_as_valid(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'audio.wav'
            wav(path)
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaisesRegex(speech.SpeechError, 'TRUNCATED'):
                speech.pcm_info(path)

    def test_existing_file_and_dangling_symlink_do_not_contact_provider(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(speech, 'run_stage') as run:
            path = Path(temporary) / 'output.wav'
            path.write_bytes(b'keep')
            with self.assertRaisesRegex(speech.SpeechError, 'OUTPUT_EXISTS'):
                speech.synthesize('通知', path)
            self.assertEqual(path.read_bytes(), b'keep')
            path.unlink()
            path.symlink_to(Path(temporary) / 'absent.wav')
            with self.assertRaisesRegex(speech.SpeechError, 'OUTPUT_EXISTS'):
                speech.synthesize('通知', path)
            run.assert_not_called()

    def test_failed_cloud_request_keeps_output_absent_and_diagnostics_private(self):
        failed = subprocess.CompletedProcess([], 1, b'', b'private notification text')
        with tempfile.TemporaryDirectory() as temporary, patch.object(speech.shutil, 'which', return_value='/fake'), patch.object(speech.subprocess, 'run', return_value=failed):
            path = Path(temporary) / 'output.wav'
            result = speech.main(['synthesize', '--text', 'private notification text', '--output', str(path)])
            self.assertFalse(result['ok'])
            self.assertNotIn('private notification text', str(result))
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_success_publishes_private_validated_wav_and_removes_intermediates(self):
        def completed(command, timeout, failure):
            if command[-1].endswith('.wav'):
                wav(command[-1])
        with tempfile.TemporaryDirectory() as temporary, patch.object(speech.shutil, 'which', return_value='/fake'), patch.object(speech, 'run_stage', side_effect=completed):
            path = Path(temporary) / 'output.wav'
            result = speech.synthesize('通知', path)
            self.assertTrue(result['ok'])
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(result['sha256'], speech.pcm_info(path)['sha256'])
            self.assertFalse(result['audio_playback_performed'])
            self.assertFalse(result['call_performed'])
            self.assertEqual(list(Path(temporary).iterdir()), [path])

    def test_output_created_during_synthesis_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'output.wav'
            def completed(command, timeout, failure):
                if command[-1].endswith('.wav'):
                    wav(command[-1])
                    path.write_bytes(b'concurrent output')
            with patch.object(speech.shutil, 'which', return_value='/fake'), patch.object(speech, 'run_stage', side_effect=completed):
                with self.assertRaisesRegex(speech.SpeechError, 'OUTPUT_EXISTS'):
                    speech.synthesize('通知', path)
            self.assertEqual(path.read_bytes(), b'concurrent output')
            self.assertEqual(list(Path(temporary).iterdir()), [path])


if __name__ == '__main__':
    unittest.main()
