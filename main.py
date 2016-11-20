from yhy523u import YHY523U
import struct

def to_hex(cmd):
    """Return the hexadecimal version of a serial command.

    Keyword arguments:
    cmd -- the serial command

    """
    return ' '.join([hex(ord(c))[2:].zfill(2) for c in cmd])




def action_choice():
    block = 1

    print "Select your action"
    print "1. Display the current amount"
    print "2. Add in the card"
    print "3. Remove from the card"



    try:

        choice = input()
    except NameError:
        print "Enter only one digit character"
        return

    if  choice == 1:

        #while 1:
            try:
                card_type, serial = device.select()
                device.init_balance(7, '\xff' * 6, block, 100)
                print "Card type:", card_type, "- Serial number:", to_hex(serial)
                print "Balance:",struct.unpack("4b", device.read_balance(7, '\xff' * 6, block))[0]

                #device.write_block(7, '\xff' * 6, 1, 50)
                #device.increase_balance(7, '\xff' * 6, 1, 2)
                device.beep(10)
            except Exception as e:
                pass

    elif choice == 2:
            print "Adding money ...."
            value=input()
            print "Enter amount:",value
            card_type, serial = device.select()
            print "Card type:", card_type, "- Serial number:", to_hex(serial)
            device.increase_balance(7, '\xff' * 6, block, value)
            print "Balance:", struct.unpack("4b", device.read_balance(7, '\xff' * 6, block))[0]

           # if  (struct.unpack("4b", device.read_balance(7, '\xff' * 6, block))[0] == 126)
              #   block+=1

    elif choice == 3:
            print "Removing money ...."
            bal_remov=input()
            card_type, serial = device.select()
            print "Card type:", card_type, "- Serial number:", to_hex(serial)
            device.decrease_balance(7, '\xff' * 6, block, bal_remov)
            print "Balance:", struct.unpack("4b", device.read_balance(7, '\xff' * 6, block))[0]
    else:
        action_choice()



if __name__ == '__main__':

    # Creating the device
    device = YHY523U()
    # Lighting of the blue LED
    # Beeping during 10 ms
    device.beep(10)
    # Lighting of both LEDs
    device.set_led('both')
    # Welcome message
    print "Welcome to Warifa Console ..."
    while 1:
        action_choice()

    # Printing the version of the firmware
    #print device.get_fw_version()

    # Trying to dump the card with different hex keys A
    #device.dump('\xA0\xA1\xA2\xA3\xA4\xA5')
    #device.dump('\x8f\xd0\xa4\xf2\x56\xe9')
    # Trying to dump the card with \xFF\xFF\xFF\xFF\xFF\xFF
    #device.dump()

    # Trying to dump the card ACs with \xFF\xFF\xFF\xFF\xFF\xFF
    #device.dump_access_conditions()

    # Printing card type and serial id
    #card_type, serial = device.select()
    #print "Card type:", card_type, "- Serial number:", to_hex(serial)

    # Printing the dump of the blocks 0 and 1 of the sector 0
    # with the key A \xFF\xFF\xFF\xFF\xFF\xFF
    #device.select()
    #print to_hex(device.read_sector(0,'\xff'*6, (0,1)))
    # Reading sector: 2, blocks: 0, 1
    #device.select()
    #print to_hex(device.read_sector(2, '\xA0\xA1\xA2\xA3\xA4\xA5', (0,1,)))

    # Looping reading cards
    #import time
    #while 1:
    #    try:
    #        card_type, serial = device.select()
    #        print "Card type:", card_type, "- Serial number:", to_hex(serial)
    #    except KeyboardInterrupt:
    #        raise KeyboardInterrupt
    #    except:
    #        pass
    #    time.sleep(0.1)

    # Read-write-read-write-read
    # Reading sector: 4, blocks: 2, 3
    #device.select()
    #print to_hex(device.read_sector(4, '\xA0\xA1\xA2\xA3\xA4\xA5', (2, 3)))
    #device.write_block(4, '\xA0\xA1\xA2\xA3\xA4\xA5', 2, '\x01\x23\x45\x67'*4)
    #print to_hex(device.read_sector(4, '\xA0\xA1\xA2\xA3\xA4\xA5', (2, 3)))
    #device.write_block(4, '\xA0\xA1\xA2\xA3\xA4\xA5', 2, '\x00'*16)
    #print to_hex(device.read_sector(4, '\xA0\xA1\xA2\xA3\xA4\xA5', (2, 3)))

    # Read-write-read-write-read-write-read
    # Playing with a balance on sector: 7, block: 1
    #device.select()
    #print "Balance:", struct.unpack("4b", device.read_balance(7, '\xff'*6, 1))
    #device.init_balance(7, '\xff'*6, 1, 42)
    #print "Balance:", struct.unpack("4b", device.read_balance(7, '\xff'*6, 1))
    #device.decrease_balance(7, '\xff'*6, 1, 3)
    #print "Balance:", struct.unpack("4b", device.read_balance(7, '\xff'*6, 1))
    #device.increase_balance(7, '\xff'*6, 1, 2)
    #print "Balance:", struct.unpack("4b", device.read_balance(7, '\xff'*6, 1))

    # Testing a set of default keys
    #device.test_keys()

    # Other tests
    #print device.send_receive(CMD_WORKING_STATUS, '\x01\x23')

#exitonclick()