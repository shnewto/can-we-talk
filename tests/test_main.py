"""
Tests to verify that `can_we_talk`'s main function runs to completion (no exceptions) regardless of
whether reading from the CAN bus succeeds or fails.
"""

import can_we_talk
from docopt import docopt
from mock import MagicMock
from can import Message


class MockMsg(object):
    """
    Arbitrary can.Message object. Used for 'successful' `can.recv` calls.
    """

    def __init__(self, data=[0, 0, 0, 0, 0, 0, 0, 0]):
        self.data = data


def setup():
    """
    Mocks generic across `test_main` functions.
    """
    can_we_talk.can.interface = MagicMock()
    can_we_talk.can.send = MagicMock()
    can_we_talk.CanBus.get_wait_time = MagicMock(return_value=0)


def test_main_successes():
    """
    Test that successful `can.recv` calls don't correspond to any exceptions thrown.
    """
    setup()
    can_we_talk.can.recv = MagicMock(return_value=MockMsg())
    can_we_talk.main(docopt(can_we_talk.__doc__, argv=[]))


def test_main_failures():
    """
    Test that failed `can.recv` calls don't correspond to any exceptions thrown.
    """
    setup()
    can_we_talk.can.recv = MagicMock(return_value=None)
    can_we_talk.main(docopt(can_we_talk.__doc__, argv=[]))
