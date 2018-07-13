#!/usr/bin/python3
"""Usage: can_we_talk.py [-hv] [-b <bustype>] [-c <channel>]

Options:
    -h --help                            Display this information
    -v --version                         Display version information
    -b --bustype <bustype>               CAN bus type [default: socketcan_native]
                                         (for more see https://python-can.readthedocs.io/en/2.1.0/interfaces.html)
    -c <channel>, --channel <channel>    Specify CAN channel, [default: can0]
"""

# This is the module required for everything CAN bus. It is not default on most systems though
# and needs to be installed with something like `pip install python-can`
import can
# This is a requirement for this tool's command line argument handling.
from docopt import docopt
# This module exposes everything we need to set wait and timeout intervals.
import time


class OBD(object):
    """
    Utility Class for unpacking OBD-II response data.
    """
    _obd_standards_dictionary = {
        1: "OBD-II as defined by the [California Air Resources Board|CARB]",
        2: "OBD as defined by the [United States Environmental Protection Agency|EPA]",
        3: "OBD and OBD-II",
        4: "OBD-I",
        5: "Not OBD compliant",
        6: "EOBD (Europe)",
        7: "EOBD and OBD-II",
        8: "EOBD and OBD",
        9: "EOBD, OBD and OBD II",
        10: "JOBD (Japan)",
        11: "JOBD and OBD II",
        12: "JOBD and EOBD",
        13: "JOBD, EOBD, and OBD II",
        14: "Not OBD compliant",
        15: "Not OBD compliant",
        16: "Not OBD compliant",
        17: "Engine Manufacturer Diagnostics (EMD)",
        18: "Engine Manufacturer Diagnostics Enhanced (EMD+)",
        19: "Heavy Duty On-Board Diagnostics (Child/Partial) (HD OBD-C)",
        20: "Heavy Duty On-Board Diagnostics (HD OBD)",
        21: "World Wide Harmonized OBD (WWH OBD)",
        22: "Not OBD compliant",
        23: "Heavy Duty Euro OBD Stage I without NOx control (HD EOBD-I)",
        24: "Heavy Duty Euro OBD Stage I with NOx control (HD EOBD-I N)",
        25: "Heavy Duty Euro OBD Stage II without NOx control (HD EOBD-II)",
        26: "Heavy Duty Euro OBD Stage II with NOx control (HD EOBD-II N)",
        27: "Not OBD compliant",
        28: "Brazil OBD Phase 1 (OBDBr-1)",
        29: "Brazil OBD Phase 2 (OBDBr-2)",
        30: "Korean OBD (KOBD)",
        31: "India OBD I (IOBD I)",
        32: "India OBD II (IOBD II)",
        33: "Heavy Duty Euro OBD Stage VI (HD EOBD-IV)", }

    @staticmethod
    def get_A(data):
        """
        Formulas defined for 'A':
        https://en.wikipedia.org/wiki/OBD-II_PIDs#Standard_PIDs
        """
        return data[3]

    @staticmethod
    def get_B(data):
        """
        Formulas defined for 'B':
        https://en.wikipedia.org/wiki/OBD-II_PIDs#Standard_PIDs
        """
        return data[4]

    @staticmethod
    def get_C(data):
        """
        Formulas defined for 'C':
        https://en.wikipedia.org/wiki/OBD-II_PIDs#Standard_PIDs
        """
        return data[5]

    @staticmethod
    def get_D(data):
        """
        Formulas defined for 'D':
        https://en.wikipedia.org/wiki/OBD-II_PIDs#Standard_PIDs
        """
        return data[6]

    @staticmethod
    def get_obd_standard(reply):
        """
        Standards bit encoding:
        https://en.wikipedia.org/wiki/OBD-II_PIDs#Mode_1_PID_1C
        """
        key = OBD.get_A(reply.data)

        if (key < 1) or (key > 33):
            return "Not OBD compliant"

        return OBD._obd_standards_dictionary[key]

    @staticmethod
    def get_fuel_tank_level(reply):
        """
        Formula for fuel tank level:
        https://en.wikipedia.org/wiki/OBD-II_PIDs#Standard_PIDs
        """
        return OBD.get_A(reply.data) * 100.0 / 255.0

    @staticmethod
    def get_seconds_since_start(reply):
        """
        Formula for seconds since engine start:
        https://en.wikipedia.org/wiki/OBD-II_PIDs#Standard_PIDs
        """
        return (256 * OBD.get_A(reply.data)) + OBD.get_B(reply.data)


class CanBus(object):
    """
    CanBus class for to connecting to, and communicating on your vehicle's OBD-II CAN bus.
    """

    def __init__(
            self,
            bustype='socketcan_native',
            channel='can0',
            bitrate=500000):
        """
        Connect to CAN bus on instantiation.
        """

        try:
            self.bus = can.interface.Bus(
                bustype=bustype,
                channel=channel,
                bitrate=int(bitrate))
        except:
            raise Exception(
                'unable to connect to CAN bus, check that hardware '
                'is connected and that socketcan is active')

        self.query_id = 0x7DF
        self.reply_id = 0x7E8

    def reading_sleep(self, duration=1.0):
        """
        Used in place of `time.sleep()`. Enables "waiting" for some interval while maintaining
        confidence that once we start unpacking at the car's replys again that data hasn't gone
        stale.
        """

        end = time.time() + duration

        while time.time() < end:
            self.get_response()

    def get_wait_time(self, timeout):
        """
        Returns ammout of time after 'now' specified by timeout.
        """
        return time.time() + timeout

    def query(self, pid, timeout=1.0):
        """
        Send a frame on OBD-II CAN bus.
        """
        query_frame = [0x02, 0x01, pid, 0x55, 0x55, 0x55, 0x55, 0x55]

        msg = can.Message(
            arbitration_id=self.query_id,
            data=query_frame, extended_id=False)
        self.bus.send(msg, timeout=timeout)

    def get_response(
            self,
            timeout=1.0):
        """
        Return first qualifying reply received.
        """
        wait = self.get_wait_time(timeout)

        while True:
            msg = self.bus.recv(timeout)
            if msg is not None:
                if msg.arbitration_id == self.reply_id:
                    return msg

            if time.time() > wait:
                return None


def main(args):
    """
    Query the OBD-II CAN bus and print unpacked reply when reads are successful.

    Parameter ID (pid) values can be referenced at
    https://en.wikipedia.org/wiki/OBD-II_PIDs#Standard_PIDs.
    """

    if args['--version']:
        print('can_we_talk 0.1.0')
        return

    bus = CanBus(
        bustype=args['--bustype'],
        channel=args['--channel'])

    pid = 0x1C  # conforming OBD-II standard

    bus.query(pid)
    reply = bus.get_response()

    if reply is None:
        print('unable to read OBD standard this vehicle conforms to')
    else:
        standard = OBD.get_obd_standard(reply)
        print('OBD standard this vehicle conforms to:', standard)

    pid = 0x2F  # fuel tank level

    bus.query(pid)
    reply = bus.get_response()

    if reply is None:
        print('unable to read fuel tank level')
    else:
        percent = OBD.get_fuel_tank_level(reply)
        print('Fuel tank level: %s' % percent, 'percent')

    pid = 0x1F  # seconds since engine start

    bus.query(pid)
    reply = bus.get_response()

    if reply is None:
        print('unable to read run time since engine start')
    else:
        seconds = OBD.get_seconds_since_start(reply)
        print('run time since engine start:', seconds, 'seconds')


if __name__ == "__main__":
    """
    The program's entry point if run as an executable.
    """

    main(docopt(__doc__))
