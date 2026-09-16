from pathlib import Path
import hashlib
import sqlite3
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import native_messages as messages


class MessageTests(unittest.TestCase):
    def database(self, keys, relative):
        conn = sqlite3.connect(':memory:'); conn.row_factory = sqlite3.Row
        if relative == 'contact/contact.db':
            conn.executescript("CREATE TABLE contact(username,remark,nick_name); INSERT INTO contact VALUES('group@chatroom','','Test group'),('sender','','Alice');")
        elif relative == 'session/session.db':
            conn.executescript("CREATE TABLE SessionTable(username,unread_count,summary,last_timestamp,last_msg_type,is_hidden,sort_timestamp); INSERT INTO SessionTable VALUES('group@chatroom',2,'new',200,1,0,200);")
        else:
            table = 'Msg_'+hashlib.md5(b'group@chatroom').hexdigest()
            conn.executescript('CREATE TABLE Name2Id(user_name); INSERT INTO Name2Id VALUES("sender"); '
                              'CREATE TABLE "'+table+'"(local_id,server_id,local_type,create_time,sort_seq,message_content,compress_content,real_sender_id);')
            conn.executemany('INSERT INTO "'+table+'" VALUES(?,?,?,?,?,?,?,?)',
                             [(1, 9007199254740993, 1, 100, 1, 'sender:\nold', '', 1),
                              (2, 9007199254740994, 1, 200, 2, 'sender:\nnew', '', 1)])
        return conn, {'database': relative, 'wal_committed_frames': 1}

    def test_scoped_history_preserves_ids_sender_and_time_filters(self):
        keys = {'files': {'message/message_0.db': 'fake'}}
        with patch.object(messages, 'open_database', side_effect=self.database):
            value = messages.messages(keys, 'Test group', limit=1, before=200)
        self.assertEqual(len(value['items']), 1)
        self.assertEqual(value['items'][0]['text'], 'old')
        self.assertEqual(value['items'][0]['server_id'], '9007199254740993')
        self.assertEqual(value['items'][0]['sender'], 'Alice')
        self.assertFalse(value['marks_read'])

    def test_ambiguous_name_never_selects_first_chat(self):
        rows = [{'username': 'one'}, {'username': 'two'}]
        with patch.object(messages, 'session_rows', return_value=(rows, {})):
            with self.assertRaisesRegex(ValueError, 'CHAT_NOT_UNIQUE'):
                messages.resolve_chat({}, 'Same name', {'one': 'Same name', 'two': 'Same name'})

    def test_shared_article_and_media_do_not_dump_xml_or_claim_ocr(self):
        value = messages.message_body({'local_type': 49, 'message_content':
                '<msg><appmsg><title>Article</title><url>https://mp.weixin.qq.com/s/example</url><des>Intro</des></appmsg></msg>',
                'compress_content': ''}, 100)
        self.assertEqual(value['text'], 'Article')
        self.assertTrue(value['url'].startswith('https://mp.weixin.qq.com/'))
        self.assertEqual(messages.message_body({'local_type': 3, 'message_content': '<img/>', 'compress_content': ''}, 100)['text'], '[图片]')


if __name__ == '__main__':
    unittest.main()
