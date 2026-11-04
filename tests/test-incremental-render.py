#!/usr/bin/env python3
"""Exercise real PTY navigation, scrolling and redraw invalidation."""
import importlib.util
import os
from pathlib import Path
import re
import signal
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('responsive', Path(__file__).with_name('test-responsive.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class Screen:
    def __init__(self, rows, cols):
        self.rows, self.cols = rows, cols
        self.cells = [[' '] * cols for _ in range(rows)]
        self.y = self.x = 0

    def feed(self, data):
        text = data.decode(errors='replace')
        i = 0
        while i < len(text):
            if text[i] == '\x1b':
                match = re.match(r'\x1b\[([0-9;?]*)([@-~])', text[i:])
                if match:
                    args, cmd = match.groups()
                    if cmd == 'J' and args == '2':
                        self.cells = [[' '] * self.cols for _ in range(self.rows)]
                    elif cmd in ('H', 'f') and not args.startswith('?'):
                        values = args.split(';') if args else []
                        self.y = int(values[0] or 1)-1 if values else 0
                        self.x = int(values[1] or 1)-1 if len(values)>1 else 0
                    i += len(match[0]); continue
                i += 2; continue
            c = text[i]
            if c == '\r': self.x = 0
            elif c == '\n': self.y += 1
            elif ord(c) >= 32:
                width = r.character_width(c)
                if width and 0 <= self.y < self.rows and 0 <= self.x < self.cols:
                    self.cells[self.y][self.x] = c
                self.x += width
            i += 1


class IncrementalTests(unittest.TestCase):
    def exercise(self, rows, cols):
        with tempfile.TemporaryDirectory() as home:
            pid, fd = r.spawn_console(rows, cols, home)
            screen = Screen(rows, cols)
            try:
                initial = r.collect_frame(fd, b'Navigate')
                self.assertIn(r.CLEAR, initial)
                screen.feed(initial)
                # Include scroll-window changes and wrap from last back to first.
                for index in range(18):
                    os.write(fd, b'\x1b[B')
                    delta = r.collect(fd, .45)
                    self.assertTrue(delta, (rows, cols, index))
                    self.assertNotIn(r.CLEAR, delta)
                    self.assertNotIn(b'SYSTEM STATUS', delta)
                    self.assertNotIn(b'LOCATION', delta)
                    r.assert_within_terminal(delta, rows, cols)
                    screen.feed(delta)
                before = [line[:] for line in screen.cells]
                os.kill(pid, signal.SIGWINCH)
                full = r.collect_frame(fd, b'Navigate')
                self.assertIn(r.CLEAR, full)
                screen.feed(full)
                # Compare menu and context. The right status panel can sample
                # changing system data only when the complete screen redraws.
                limit = cols if cols < 100 else 80
                self.assertEqual([x[:limit] for x in before], [x[:limit] for x in screen.cells])
                os.write(fd, b'x')
                self.assertEqual(r.collect(fd, .25), b'')
                os.write(fd, b'\x1b[A')
                up = r.collect(fd, .45)
                self.assertNotIn(r.CLEAR, up)
                self.assertTrue(up)
                os.write(fd, b'\x1b')
                dialog = r.collect_frame(fd, b'EXIT KENOFORGE')
                self.assertIn(r.CLEAR, dialog)
                os.write(fd, b'\x1b')
                returned = r.collect_frame(fd, b'Navigate')
                self.assertIn(r.CLEAR, returned)
                os.write(fd, b'\r')
                switched = r.collect_frame(fd, b'Navigate')
                self.assertIn(r.CLEAR, switched)
                self.assertIn(b'PYTHON CENTER', switched)
                os.write(fd, b'\x1b[B')
                delta = r.collect(fd, .45)
                self.assertTrue(delta)
                self.assertNotIn(r.CLEAR, delta)
                os.write(fd, b'\x1b')
                back = r.collect_frame(fd, b'Navigate')
                self.assertIn(r.CLEAR, back)
                self.assertIn(b'CONTROL CENTER', back)
                log = Path(home) / 'KenoForge/Logs/render-errors.log'
                self.assertEqual(log.read_text(), '')
            finally:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
                os.close(fd)

    def test_wide_full_layout(self):
        self.exercise(44, 173)

    def test_compact_scrolling_layout(self):
        self.exercise(10, 55)


if __name__ == '__main__':
    unittest.main()
