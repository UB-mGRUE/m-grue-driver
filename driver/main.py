import argparse
import logging
import os
import sys
import time
import glob
from datetime import datetime
import serial


def valid_path(path):
    if path == './output':
        if not os.path.isdir(path):
            os.mkdir('output')
            return path
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid directory")

def valid_file(path):
    if path == '':
        raise argparse.ArgumentTypeError(f"Path cannot be empty")
    if path == './output':
        if not os.path.isdir(path):
            os.mkdir('output')
            return path
    if os.path.isfile(path):
        if path.endswith('.fn'):
            return path
        else:
            raise argparse.ArgumentTypeError(f"{path} is not a valid file type")
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid file")

def serial_ports():
        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 2) for i in range(255)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='mGRUE-driver', description='Initialize the mGRUE Host Device Driver')
    parser.version = '1.0'
    parser.add_argument('mode',
                        choices=['gui', 'cli', 'transfer'],
                        default='cli',
                        help='option to use program through a GUI or via Command Line')
    parser.add_argument('-l',
                        '--location',
                        type=valid_path,
                        nargs='?',
                        default='./output',
                        help="destination for the records recieved by the mGRUE application. Default ./output")
    parser.add_argument('-f',
                        '--file',
                        type=valid_file,
                        nargs='?',
                        help="data file to replace the file that is sent to the driver")
    parser.add_argument('-r',
                        '--records',
                        type=int,
                        nargs='?',
                        default=4000,
                        help='the number of records per file. Default 4000.')
    args = parser.parse_args()

    if args.location == '' or args.file == '':
        print('ERROR: Please specify a valid location and file')
        sys.exit(1)
    recordsPerFile = args.records
    destinationFolder = args.location
    

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    if(args.mode == 'gui'):
        import gui
        gui.init(recordsPerFile)
    elif(args.mode == 'transfer'):
        open_ports = []
        count = 0
        logging.info(f"Looking for mGRUE device...")

        while not open_ports:
            open_ports = serial_ports()
            time.sleep(.1)
            count += 1
            if count == 50:
                logging.warning(f"no mGRUE device found")
                time.sleep(10)
                count = 0
                logging.info(f"Looking for mGRUE device...")


        currentStatus = "Port opened, found mGRUE device"
        logging.info(f"{currentStatus}")   
        with serial.Serial(open_ports[0], 921600, timeout=1) as ser:
            while (True):
                stillReading    = True
                curTime         = datetime.now().strftime("%H-%M-%S")
                sequenceNum     = 0
                fileCounter     = 0
                bytesMessage    = ser.readline().decode("utf-8", errors='replace')[:-1]     # read a '\n' terminated line, removing the \n
                file            = 0
                sequence        = 0
                whiteline       = 0
                count           = 0
                leftover        = 0
                lines           = []

                if bytesMessage == 'connect':
                    ser.write(b'transfer\n')
                    currentStatus = "Device Connected"
                    logging.info(f"{currentStatus}")
                    with open(args.file, "r") as f:
                        for line in f.readlines():
                            #print(line[:-1])
                            ser.write((line).encode("utf-8"))
                    ser.write(b"done\n")          
                    currentStatus = "Transfer Complete"
                    logging.info(f"{currentStatus}")
                    exit()
    else:
        open_ports = []
        count = 0
        logging.info(f"Looking for mGRUE device...")

        while not open_ports:
            open_ports = serial_ports()
            time.sleep(.1)
            count += 1
            if count == 50:
                logging.warning(f"no mGRUE device found")
                time.sleep(10)
                count = 0
                logging.info(f"Looking for mGRUE device...")
                
        logging.info(f"File Destination Path -> {destinationFolder}")

        currentStatus = "Port opened, found mGRUE device"
        logging.info(f"{currentStatus}")

        with serial.Serial(open_ports[0], 921600, timeout=1) as ser:
            while (True):
                stillReading    = True
                curTime         = datetime.now().strftime("%H-%M-%S")
                sequenceNum     = 0
                fileCounter     = 0
                bytesMessage    = ser.readline().decode("utf-8", errors='replace')[:-1]     # read a '\n' terminated line, removing the \n
                file            = 0
                sequence        = 0
                whiteline       = 0
                count           = 0
                leftover        = 0
                lines           = []

                if bytesMessage == 'connect' and destinationFolder != "":
                    ser.write(b'handshake\n')
                    currentStatus = "Device Connected"
                    logging.info(f"{currentStatus}")
                    
                    if os.name == 'nt':
                        file = open(destinationFolder + "/" + curTime + "_file" + str(fileCounter) + ".fn", "a", encoding="utf-8", errors='ignore')
                    else:
                        file = open(destinationFolder + "/" + curTime + "_file" + str(fileCounter) + ".fn", "w", encoding="utf-8", errors='ignore')
                    currentStatus = "Data transfer in progress...."
                    logging.info(f"{currentStatus}")
                    while (currentStatus != "Data transfer complete! Awaiting new action..." and \
                            currentStatus != "Transfer was stopped early. Awaiting new command..."):
                        while (currentStatus != "Data transfer complete! Awaiting new action..." and \
                                currentStatus != "Transfer was stopped early. Awaiting new command..."):
                            bytesMessage = ser.read(ser.in_waiting).decode("utf-8", errors='replace')
                            if currentStatus == "Paused.":
                                currentStatus = "Data transfer in progress...."
                            lines = bytesMessage.split('\n')
                            if leftover:
                                lines[0] = leftover + lines[0]
                                leftover = ""

                            # print("INFO: Bytes in waiting: %s" %(ser.in_waiting), end="\r")
                            if ser.in_waiting > 0:
                                logging.debug("Bytes in waiting %s." %(ser.in_waiting))
                            for line in lines[:-1]:
                                if 'done' in line:
                                    currentStatus = "Data transfer complete! Awaiting new action..."
                                    logging.info(f"{currentStatus}")
                                    file.close()         # I have no idea why on god's green earth this breaks here but not in the gui. 
                                if 'pause' in line:       # Pauses the transfer for a baud rate change
                                    currentStatus = "Paused."
                                    logging.info(f"{currentStatus}")
                                    lines.remove(line)
                                elif 'kill' in line:
                                    currentStatus = "Transfer was stopped early. Awaiting new command..."
                                    logging.info(f"{currentStatus}")
                                    file.close()
                                else:
                                    try:
                                        file.write(line + "\r\n")
                                        count += 1
                                        if count % 3 == 0 and count / 3 == recordsPerFile:
                                            fileCounter += 1
                                            if os.name == 'nt':
                                                file.close()
                                                file = open(destinationFolder + "/" + curTime + "_file" + str(fileCounter) + ".fn", "a", encoding="utf-8", errors='ignore')
                                            else:
                                                file.close()
                                                file = open(destinationFolder + "/" + curTime + "_file" + str(fileCounter) + ".fn", "w", encoding="utf-8", errors='ignore')
                                            count = 0
                                    except:
                                        pass
                                    
                            
                            leftover = lines[-1]

                            if 'done' in leftover:
                                currentStatus = "Data transfer complete! Awaiting new action..."
                                logging.info(f"{currentStatus}")
                                file.close()
