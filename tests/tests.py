#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function, division

import unittest

import sys
import os
import time
import threading

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

import core




# class RaiseExceptionInThreadTest(unittest.TestCase):

#     def setUp(self):
#         # Mock threading.Thread to just run a function in the main thread:
#         class MockThread(object):
#             used = False
#             def __init__(self, target, args):
#                 self.target = target
#                 self.args = args
#             def start(self):
#                 MockThread.used = True
#                 self.target(*self.args)
#         self.mock_thread = MockThread
#         self.orig_thread = threading.Thread
#         threading.Thread = MockThread

#     def test_can_raise_exception_in_thread(self):
#         class TestError(Exception):
#             pass
#         try:
#             raise TestError('test')
#         except Exception:
#             exc_info = sys.exc_info()
#             with self.assertRaises(TestError):
#                 raise_exception_in_thread(exc_info)
#             self.assertTrue(self.mock_thread.used)

#     def tearDown(self):
#         # Restore threading.Thread to what it should be
#         threading.Thread = self.orig_thread


class  ReprTest(unittest.TestCase):
    """test the string representation of objects"""

    def setUp(self):
        self.shot = core.Shot('parent_name')
        self.pseudoclock = core.Pseudoclock('pseudoclock', self.shot)
        self.clocked_device = core.ClockedDevice('clocked_device', self.pseudoclock, 'flag 1')
        self.output = core.Output('output', self.pseudoclock, 'a01')
        self.instruction = core.instruction('')


    def test_all_classes_have_name_test(self):
        for name in dir(core):
            if isinstance(getattr(core, name), type):
                self.assertTrue(hasattr(self, f"test_repr_{name}"), name)

    # def test_repr_Child(self):

    #     child = core.Child('name', )

    # def test_fakse(self):
    #     assert False


if __name__ == '__main__':
    try:
        unittest.main(verbosity=1)
    except SystemExit:
        pass