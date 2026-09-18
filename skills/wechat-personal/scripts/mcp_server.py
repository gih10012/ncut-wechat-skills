#!/usr/bin/env python3
"""On-demand stdio MCP over WeChat reads and ClawBot owner-directed sends."""
import json
from pathlib import Path
import subprocess
import sys

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

SCRIPT = Path(__file__).with_name('wechat.py')
server = FastMCP('wechat-personal', instructions=(
    'Read the owner\'s Linux WeChat synced messages or read/send their ClawBot channel. '
    'ClawBot reads and writes have standing owner authorization. Native WeChat writes '
    'require explicit current or applicable advance authorization and are not connected. '
    'These are distinct sources. Optional Android WeCom notifications are only notification text, '
    'not complete personal chats. The full WeCom inbox is not connected. No automatic replies.'))
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
POLL = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=True)
SEND = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True)


def invoke(args):
    try:
        result = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True,
                                text=True, timeout=50)
    except subprocess.TimeoutExpired:
        return {'ok': False, 'code': 'COMMAND_TIMEOUT'}
    try:
        value = json.loads(result.stdout)
    except (ValueError, UnicodeError):
        return {'ok': False, 'code': 'COMMAND_INVALID_RESPONSE', 'exit_code': result.returncode}
    if not isinstance(value, dict):
        return {'ok': False, 'code': 'COMMAND_INVALID_RESPONSE'}
    return value


@server.tool(annotations=READ)
def wechat_conversations(query: str = '', limit: int = 10, unread: bool = False, account: str = 'me') -> dict:
    """Find the owner's locally synced WeChat chats. Returns exact chat IDs; does not mark messages read."""
    args = ['native', 'conversations', '--account', account, '--query', query,
            '--limit', str(max(1, min(limit, 50)))]
    if unread:
        args.append('--unread')
    return invoke(args)


@server.tool(annotations=READ)
def wechat_messages(chat: str, limit: int = 20, account: str = 'me') -> dict:
    """Read a bounded WeChat chat by exact returned chat ID or unique name. Covers this Linux client's synced data."""
    return invoke(['native', 'messages', '--account', account, '--chat', chat,
                   '--limit', str(max(1, min(limit, 50)))])


@server.tool(annotations=POLL)
def clawbot_updates(limit: int = 20, account: str = 'me') -> dict:
    """Poll one ClawBot batch (up to 40 seconds). Advances a private local cursor; does not read personal chats or reply."""
    return invoke(['bot', 'updates', '--account', account, '--limit', str(max(1, min(limit, 100)))])


@server.tool(annotations=READ)
def wecom_notifications(limit: int = 20, account: str = 'me') -> dict:
    """Read locally forwarded Android WeCom notification text only; excludes unnotified chats and historical inbox data."""
    return invoke(['notifications', 'list', '--account', account, '--limit', str(max(1, min(limit, 100)))])


@server.tool(annotations=SEND)
def clawbot_send(text: str, request_id: str, account: str = 'me') -> dict:
    """Send text as ClawBot to its bound owner; standing authorization applies. Reuse request_id to retrieve an attempt without resending. API acceptance does not prove delivery."""
    return invoke(['bot', 'send', '--account', account, '--text=' + text, '--request-id', request_id])


if __name__ == '__main__':
    server.run(transport='stdio')
