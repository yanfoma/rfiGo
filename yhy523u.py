#!/usr/bin/python

import datetime
import os, sys, struct, serial

# Command header
HEADER = '\xAA\xBB'
# \x00\x00 according to API reference but only works with YHY632
# \xFF\xFF works for both.
RESERVED = '\xFF\xFF'

# Serial commands
CMD_SET_BAUDRATE = 0x0101
CMD_SET_NODE_NUMBER = 0x0102
CMD_READ_NODE_NUMBER = 0x0103
CMD_READ_FW_VERSION = 0x0104
CMD_BEEP = 0x0106
CMD_LED = 0x0107
CMD_RFU = 0x0108 # Unused according to API reference
CMD_WORKING_STATUS = 0x0108 # Unused according to API reference
CMD_ANTENNA_POWER = 0x010C
# Request a type of card
#     data = 0x52: request all Type A card In field,
#     data = 0x26: request idle card
CMD_MIFARE_REQUEST = 0x0201
CMD_MIFARE_ANTICOLISION = 0x0202 # 0x04 -> <NUL> (00)     [4cd90080]-cardnumber
CMD_MIFARE_SELECT = 0x0203 # [4cd90080] -> 0008
CMD_MIFARE_HALT = 0x0204
CMD_MIFARE_AUTH2 = 0x0207 # 60[sector*4][key]
CMD_MIFARE_READ_BLOCK = 0x0208 #[block_number]
CMD_MIFARE_WRITE_BLOCK = 0x0209
CMD_MIFARE_INITVAL = 0x020A
CMD_MIFARE_READ_BALANCE = 0x020B
CMD_MIFARE_DECREMENT = 0x020C
CMD_MIFARE_INCREMENT = 0x020D
CMD_MIFARE_UL_SELECT = 0x0212

# Default keys
DEFAULT_KEYS = (
    '\x00\x00\x00\x00\x00\x00',
    '\xa0\xa1\xa2\xa3\xa4\xa5',
    '\xb0\xb1\xb2\xb3\xb4\xb5',
    '\x4d\x3a\x99\xc3\x51\xdd',
    '\x1a\x98\x2c\x7e\x45\x9a',
    '\xFF'*6,
    '\xd3\xf7\xd3\xf7\xd3\xf7',
    '\xaa\xbb\xcc\xdd\xee\xff'
)

# Error codes
ERR_BAUD_RATE = 1
ERR_PORT_OR_DISCONNECT = 2
ERR_GENERAL = 10
ERR_UNDEFINED = 11
ERR_COMMAND_PARAMETER = 12
ERR_NO_CARD = 13
ERR_REQUEST_FAILURE = 20
ERR_RESET_FAILURE = 21
ERR_AUTHENTICATE_FAILURE = 22
ERR_READ_BLOCK_FAILURE = 23
ERR_WRITE_BLOCK_FAILURE = 24
ERR_READ_ADDRESS_FAILURE = 25
ERR_WRITE_ADDRESS_FAILURE = 26

# Mifare types
TYPE_MIFARE_UL = 0x4400
TYPE_MIFARE_1K = 0x0400
TYPE_MIFARE_4K = 0x0200
TYPE_MIFARE_DESFIRE = 0x4403
TYPE_MIFARE_PRO = 0x0800


class YHY523U:
    """Driver for Ehuoyan's YHY523U module"""

    def __init__(self, port='COM3', baudrate=115200):
        #/dev/ttyUSB0 for linux and unix
        try:
            self.port = port
            self.baudrate = baudrate
            self.ser = serial.Serial(self.port, baudrate=self.baudrate)
            print "The module is connected"
        except serial.SerialException:
            print "Connect the module first"

    def build_command(self, cmd, data):
        """Build a serial command.

        Keyword arguments:
        cmd -- the serial command
        data -- the argument of the command

        """
        length = 2 + 2 + 1 + len(data)

        body_raw = RESERVED + struct.pack('<H', cmd) + data
        body = ''
        for b in body_raw:
            body += b
            if b == '\xAA':
                body += '\x00'

        body_int = map(ord, body)
        checksum = reduce(lambda x,y:  x^y, body_int)

        return HEADER + struct.pack('<H', length) + body + struct.pack('B', checksum)

    def get_n_bytes(self, n, handle_AA=False):
        """Read n bytes from the device.

        Keyword arguments:
        n -- the number of bytes to read
        handle_AA -- True to handle \xAA byte differently, False otherwise

        """
        buffer = ''
        while 1:
            received = self.ser.read()
            if handle_AA:
                if received.find('\xAA\x00') >= 0:
                    received = received.replace('\xAA\x00','\xAA')
                if received[0] == '\x00' and buffer[-1] == '\xAA':
                    received = received[1:]
            buffer += received

            if len(buffer) >= n:
                return buffer

    def send_command(self, cmd, data):
        """Send a serial command to the device.

        Keyword arguments:
        cmd -- the serial command
        data -- the argument of the command

        """
        buffer = self.build_command(cmd, data)
        self.ser.write(buffer)
        self.ser.flush()

    def receive_data(self):
        """Receive data from the device."""
        buffer = ''

        # Receive junk bytes
        prev_byte = '\x00'
        while 1:
            cur_byte = self.ser.read(1)
            if prev_byte + cur_byte == HEADER:
                # Header found, breaking
                break
            prev_byte = cur_byte

        length = struct.unpack('<H', self.get_n_bytes(2))[0]
        packet = self.get_n_bytes(length, True)

        reserved, command = struct.unpack('<HH', packet[:4])
        data = packet[4:-1]
        checksum = ord(packet[-1])

        packet_int = map(ord, packet[:-1])
        checksum_calc = reduce(lambda x,y: x^y, packet_int)
        if data[0] == '\x00':
            if checksum != checksum_calc:
                raise Exception, "bad checksum"
        return command, data

    def send_receive(self, cmd, data):
        """Send a serial command to the device and receive the answer.

        Keyword arguments:
        cmd -- the serial command
        data -- the argument of the command

        """
        self.send_command(cmd, data)
        cmd_received, data_received = self.receive_data()
        if cmd_received != cmd:
            raise Exception, "the command in answer is bad!"
        else:
            return ord(data_received[0]), data_received[1:]

    def select(self):
        """Select a Mifare card. (Needed before any reading/writing operation)
        Return the type and the serial of a Mifare card.

        """
        status, card_type = self.send_receive(CMD_MIFARE_REQUEST, '\x52')
        if status != 0:
            raise Exception, "No card found"

        status, serial = self.send_receive(CMD_MIFARE_ANTICOLISION, '\x04')
        if status != 0:
            raise Exception, "Error in anticollision"

        card_type = struct.unpack('>H', card_type)[0]
        if card_type == TYPE_MIFARE_UL:
            status, serial = self.send_receive(CMD_MIFARE_UL_SELECT, '')
        else:
            self.send_receive(CMD_MIFARE_SELECT, serial)
        return card_type, serial

    def halt(self):
        """Halt the device."""
        status, data = self.send_receive(CMD_MIFARE_HALT, '')
        return status, data

    def read_sector(self, sector=0, keyA='\xff'*6, blocks=(0,1,2,)):
        """Read a sector of a Mifare card.

        Keyword arguments:
        sector -- the sector index (default: 0)
        keyA -- the key A
        blocks -- the blocks to read in the sector

        """
        self.send_receive(CMD_MIFARE_AUTH2, '\x60' + chr(sector * 4) + keyA)
        results = ''
        for block in blocks:
            status, data = self.send_receive(CMD_MIFARE_READ_BLOCK, chr(sector * 4 + block))
            if status != 0:
                raise Exception, "errorcode: %d" % status
            results += data
        return results

    def write_block(self, sector=0, keyA='\xff'*6, block=0, data='\x00'*16):
        """Write in a block of a Mifare card.

        Keyword arguments:
        sector -- the sector index (default: 0)
        keyA -- the key A
        block -- the block to write on in the sector (default: 0)
        data -- the data string to be written

        """
        self.send_receive(CMD_MIFARE_AUTH2, '\x60' + chr(sector * 4) + keyA)
        status, result = self.send_receive(CMD_MIFARE_WRITE_BLOCK, chr(sector * 4 + block) + data)
        if status != 0:
            raise Exception, "errorcode: %d" % status
        return result

    def dump(self, keyA='\xff'*6):
        """Dump a Mifare card.

        Keyword arguments:
        keyA -- the key A

        """
        self.select()
        for sector in xrange(0, 16):
            print "sector %d" % sector
            try:
                print to_hex(self.read_sector(sector, keyA))
            except:
                pass

    def dump_access_conditions(self, keyA='\xff'*6):
        """Dump the access conditions (AC) of a Mifare card.

        Keyword arguments:
        sector -- the sector index (default: 0)
        keyA -- the key A

        """
        self.select()
        for sector in xrange(0, 16):
            try:
                ac = buffer(self.read_sector(sector, keyA, (3,)), 6, 3)
                print "ACs for sector %d:" % sector, to_hex(ac)
            except:
                print "Unable to read ACs for sector %d" % sector

    def get_fw_version(self):
        """Return the firmware version of the device."""
        status, data = self.send_receive(CMD_READ_FW_VERSION, '')
        return data

    def get_node_number(self):
        """Return the node number of the device."""
        status, data = self.send_receive(CMD_READ_NODE_NUMBER, '')
        return data

    def set_node_number(self, number):
        """Set the node number of the device.

        Keyword arguments:
        number -- the node number

        """
        status, data = self.send_receive(CMD_SET_NODE_NUMBER, struct.pack('<H', number))
        return data

    def beep(self, delay=10):
        """Make the device beeping.

        Keyword arguments:
        delay -- the beep duration in milliseconds (default: 10)

        """
        status, data = self.send_receive(CMD_BEEP, chr(delay))
        if status == 0:
            return 1
        else:
            return 0

    def set_led(self, led='off'):
        """Light the LED of the device.

        Keyword arguments:
        led -- the LED to be lighted, can be: 'red', 'blue', 'both' or 'off' (default: 'off')

        """
        if led == 'red':
            data = '\x01'
        elif led == 'blue':
            data = '\x02'
        elif led == 'both':
            data = '\x03'
        else:
            data = '\x00'
        return self.send_receive(CMD_LED, data)[0] == 0

    def set_baudrate(self, rate=19200):
        """Set the baud rate of the device.

        Keyword arguments:
        rate -- the baud rate (default: 19200)

        """
        if rate == 19200:
            data = '\x03'
        elif rate == 28800:
            data = '\x04'
        elif rate == 38400:
            data = '\x05'
        elif rate == 57600:
            data = '\x06'
        elif rate == 115200:
            data = '\x07'
        else:
            data = '\x01'
        return self.send_receive(CMD_SET_BAUDRATE, data)[0] == 0

    def init_balance(self, sector=0, keyA='\xff'*6, block=0, amount=1):
        """Init a balance in a Mifare card.

        Keyword arguments:
        sector -- the sector index (default: 0)
        keyA -- the key A
        block -- the block to write on in the sector (default: 0)
        amount -- the initial amount of the balance (default: 1)

        """
        self.send_receive(CMD_MIFARE_AUTH2, '\x60' + chr(sector * 4) + keyA)
        status, result = self.send_receive(CMD_MIFARE_INITVAL, chr(sector * 4 + block) + struct.pack("I", amount))
        if status != 0:
            raise Exception, "errorcode: %d" % status
        return result

    def read_balance(self, sector=0, keyA='\xff'*6, block=0):
        """Read a balance.

        Keyword arguments:
        sector -- the sector index (default: 0)
        keyA -- the key A
        block -- the block to read in the sector (default: 0)

        """
        self.send_receive(CMD_MIFARE_AUTH2, '\x60' + chr(sector * 4) + keyA)
        status, result = self.send_receive(CMD_MIFARE_READ_BALANCE, chr(sector * 4 + block))
        if status != 0:
            raise Exception, "errorcode: %d" % status
        return result

    def decrease_balance(self, sector=0, keyA='\xff'*6, block=0, amount=1):
        """Decrease a balance of amount.

        Keyword arguments:
        sector -- the sector index (default: 0)
        keyA -- the key A
        block -- the block to write on in the sector (default: 0)
        amount -- the decrement amount (default: 1)

        """
        self.send_receive(CMD_MIFARE_AUTH2, '\x60' + chr(sector * 4) + keyA)
        status, result = self.send_receive(CMD_MIFARE_DECREMENT, chr(sector * 4 + block) + struct.pack("I", amount))
        if status != 0:
            raise Exception, "errorcode: %d" % status
        return result

    def increase_balance(self, sector=0, keyA='\xff'*6, block=0, amount=1):
        """Increase a balance of amount.

        Keyword arguments:
        sector -- the sector index (default: 0)
        keyA -- the key A
        block -- the block to write on in the sector (default: 0)
        amount -- the increment amount (default: 1)

        """
        self.send_receive(CMD_MIFARE_AUTH2, '\x60' + chr(sector * 4) + keyA)
        status, result = self.send_receive(CMD_MIFARE_INCREMENT, chr(sector * 4 + block) + struct.pack("I", amount))
        if status != 0:
            raise Exception, "errorcode: %d" % status
        return result

    def test_keys(self, sector=0, keys=DEFAULT_KEYS):
        """Test an array of potential keys to find the right one.

        Keyword arguments:
        sector -- the sector index (default: 0)
        keys -- the keys to be tested (default: DEFAULT_KEYS)

        """
        for key in keys:
            self.select()
            status, data = self.send_receive(CMD_MIFARE_AUTH2, '\x60' + chr(sector * 4) + key)
            if status == 0:
                print "Key A found:", to_hex(key)
                break
            else:
                print "Invalid key A:", to_hex(key)

        for key in keys:
            self.select()
            status, data = self.send_receive(CMD_MIFARE_AUTH2, '\x61' + chr(sector * 4) + key)
            if status == 0:
                print "Key B found:", to_hex(key)
                break
            else:
                print "Invalid key B:", to_hex(key)
