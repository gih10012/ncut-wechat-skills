"""Thin bridge to the independently installed Linux client CLI."""
import argparse
import json
from pathlib import Path
import subprocess

CLI = Path('/usr/local/bin/wechat-linux')


def available():
    return CLI.is_file()


def arguments(argv):
    if not argv:
        raise ValueError('Native operation is required')
    if argv[0] not in ('send', 'send-status'):
        return argv
    parser = argparse.ArgumentParser()
    parser.add_argument('--request-id')
    parser.add_argument('--text')
    parser.add_argument('--recipient', default='filehelper')
    args = parser.parse_args(argv[1:])
    if argv[0] == 'send-status':
        if args.request_id is None:
            from native_send_candidate import REQUEST_ID
            args.request_id = REQUEST_ID
        return ['send-status', '--request-id', args.request_id]
    if args.text is None or args.request_id is None:
        raise ValueError('native send requires --text and --request-id')
    return ['send-text', '--recipient', args.recipient, '--text', args.text,
            '--request-id', args.request_id]


def main(argv):
    # Pass through exactly once; a failed/unknown write never falls back to the
    # old sender. The CLI owns deterministic state and privileged operations.
    result = subprocess.run([str(CLI), *arguments(argv)], check=False)
    return result.returncode


def send_text(text, request_id, recipient, timeout):
    """OneBot's temporary HTTP adapter calls the installed service as owner."""
    try:
        result = subprocess.run([str(CLI), 'send-text', '--recipient', recipient,
                                 '--text', text, '--request-id', request_id],
                                capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        # Only the unprivileged CLI caller is timed out. The service owns its
        # independent backend and debugger and persists the unfinished request.
        return {'status': 'adapter_timeout', 'automatic_retry_allowed': False}
    return json.loads(result.stdout)
