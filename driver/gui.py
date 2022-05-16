import sys
import time
import threading
import os
import glob
import serial

from PySide2.QtGui import QGuiApplication, QIcon
from PySide2.QtQml import QQmlApplicationEngine
from PySide2.QtCore import QObject, Slot, Signal

from datetime import datetime


# Define our backend object, which we will pass to the engine object
class Backend(QObject):
    recordsPerFile = 4000        # Set max number of records that will be written to each file here
    currentStatus = ""
    status = Signal(str)
    quick  = True

    def __init__(self):
        super().__init__()

        self.destination_folder = ""

    # This function is sending data to the frontend (uses the status signal)
    def update_status(self, msg):
        # Pass the current status message to QML.
        self.currentStatus = msg
        self.status.emit(msg)
    
    #This function sets the max records per file based on user input
    def update_records(self,n):
        self.recordsPerFile = n

    # This function is getting data from frontend
    @Slot(str)
    def getFileLocation(self, location):
        print("User selected: " + location[7:])
        self.destination_folder = location[7:]
    
    def serial_ports(self):
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

    def readStarter(self):
        open_ports = []
        count = 0

        while not open_ports:
            open_ports = self.serial_ports()
            time.sleep(.1)
            count += 1
            self.update_status("Looking for MGRUE device...")
            if count == 50:
                print("No MGRUE device found")
                self.update_status("Error: no MGRUE device found")
                time.sleep(10)
                count = 0

        self.update_status("Awaiting command from device...")
        while True:
            self.quickReadSerial(open_ports[0])

    def quickReadSerial(self, port):
        with serial.Serial(port, 921600, timeout=1) as ser:
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

                if bytesMessage == 'connect' and self.destination_folder != "":
                    ser.write(b'handshake\n')
                    self.update_status("Device Connected")
                    
                    if os.name == 'nt':
                        file = open(self.destination_folder[1:] + "/" + curTime + "_file" + str(fileCounter) + ".fn", "a", encoding="utf-8", errors='ignore')
                    else:
                        file = open(self.destination_folder + "/" + curTime + "_file" + str(fileCounter) + ".fn", "w", encoding="utf-8", errors='ignore')
                    self.update_status("Data transfer in progress....")
                    while (self.currentStatus != "Data transfer complete! Awaiting new action..."):
                        while (self.currentStatus != "Data transfer complete! Awaiting new action..."):
                            bytesMessage = ser.read(ser.in_waiting).decode("utf-8", errors='replace')
                            
                            if self.currentStatus == "Paused.":
                                if 'kill' in bytesMessage:
                                    self.update_status("Transfer was stopped early. Awaiting new command...")
                                    file.close()
                                    return
                                else:
                                    self.update_status("Data transfer in progress....")
                            lines = bytesMessage.split('\n')
                            if leftover:
                                lines[0] = leftover + lines[0]
                                leftover = ""

                            print("Bytes in waiting %s" %(ser.in_waiting), end="\r")
                            for line in lines[:-1]:
                                if 'done' in line:
                                    self.update_status("Data transfer complete! Awaiting new action...")
                                    file.close()
                                    return
                                if 'pause' in line:       # Pauses the transfer for a baud rate change
                                    self.update_status("Paused.")
                                    lines.remove(line)
                                elif 'kill' in line:
                                    self.update_status("Transfer was stopped early. Awaiting new command...")
                                    file.close()
                                    return
                                else:
                                    file.write(line + "\r\n")
                                    count += 1
                                    if count % 3 == 0 and count / 3 == self.recordsPerFile:
                                        fileCounter += 1
                                        if os.name == 'nt':
                                            file.close()
                                            file = open(self.destination_folder[1:] + "/" + curTime + "_file" + str(fileCounter) + ".fn", "a", encoding="utf-8", errors='ignore')
                                        else:
                                            file.close()
                                            file = open(self.destination_folder + "/" + curTime + "_file" + str(fileCounter) + ".fn", "w", encoding="utf-8", errors='ignore')
                                        count = 0
                            
                            leftover = lines[-1]

                            if 'done' in leftover:
                                self.update_status("Data transfer complete! Awaiting new action...")
                                file.close()
                                return
                            
                        # if self.currentStatus == "Paused.":
                        #     bytesMessage = ser.readline().decode("utf-8", errors='replace')
                        #     if bytesMessage:
                        #         self.update_status("Data transfer in progress....")
                        #         file.write(bytesMessage)

                    

    def readSerial(self):
        open_ports = self.serial_ports()
        with serial.Serial(open_ports[0], 115200, timeout=1) as ser:
            print("Port %s opened, looking for device..." %(open_ports[0]))
            while (True):
                stillReading    = True
                curTime         = datetime.now().strftime("%H-%M-%S")
                sequenceNum     = 0
                fileCounter     = 0
                bytesMessage    = ser.readline().decode()[:-2]     # read a '\n' terminated line, removing the \n
                file            = 0
                sequence        = 0
                whiteline       = 0
                count           = 0

                if bytesMessage == 'connect' and self.destination_folder != "":
                    ser.write(b'handshake\n')
                    self.update_status("Device Connected")
                    
                    if os.name == 'nt':
                        file = open(self.destination_folder[1:] + "/" + curTime + "_file" + str(fileCounter) + ".fn", "w", encoding="unicode_escape")
                    else:
                        file = open(self.destination_folder + "/" + curTime + "_file" + str(fileCounter) + ".fn", "w", encoding="utf-8")

                    while (stillReading or self.currentStatus == "Paused."):       # Run while file is still being read or the reading is paused.
                        if os.name == 'nt':
                            bytesMessage = ser.readline().decode("unicode_escape")[:-2]     # This should either be the start of a record, a new_rate command, or EOF
                        else:
                            bytesMessage = ser.readline().decode()[:-2]     

                        if bytesMessage == 'pause':       # Pauses the transfer for a baud rate change
                            self.update_status("Paused.")
                        elif bytesMessage != "" and bytesMessage[0] == '>':     # Ensures that the first piece of data of a record is the metadata
                            self.update_status("Data transfer in progress....")
                            
                            if os.name == 'nt':
                                sequence = ser.readline().decode("unicode_escape")[:-2]
                            else:
                                sequence = ser.readline().decode()[:-2]   # If your still getting the crashing error in Ubuntu then switch to only using unicode_escape
                            
                            if sequence != "" and sequence[0] != '>':       # Ensures that next piece of data is DNA sequence
                                print("Reading Line #%s" %(count))
                                file.write(bytesMessage + "\r\n")
                                file.write(sequence + "\r\n")
                                if os.name == 'nt':
                                    whiteline = ser.readline().decode("unicode_escape")[:-2]
                                else:
                                    whiteline = ser.readline().decode()[:-2] 

                                if whiteline == "":     # Every third line should be a blankspace
                                    file.write("\n")
                                    count += 3
                                else:
                                    print(whiteline.decode())
                                    self.update_status("Error, line should have been a whiteline...")
                                    return
                                
                                sequenceNum += 1        # A record has successfully been written, increment SequenceNum
                                if sequenceNum == self.recordsPerFile:     # When backend.recordsPerFile records have been written, close file and start another one
                                    file.close()
                                    fileCounter += 1
                                    if os.name == 'nt':
                                        file = open(self.destination_folder[1:] + "/" + curTime + "_file" + str(fileCounter) + ".fn", "w")
                                    else:
                                        file = open(self.destination_folder + "/" + curTime + "_file" + str(fileCounter) + ".fn", "w")

                                    sequenceNum = 0
                            else:
                                print(sequence)
                                self.update_status("Error, line should have been a dna sequence...")
                                return
                        elif bytesMessage != "":        # If data is not a command, new record then it must be bad.
                            self.update_status("Error, Received bad line: " + bytesMessage)
                            return
                        elif bytesMessage == "" and self.currentStatus == "Data transfer in progress....":     # If no data is received when not paused must be EOF
                            stillReading = False
                            file.close()
                            self.update_status("Data transfer complete! Awaiting new action...")
                            time.sleep(1)
                            self.update_status("Awaiting Connection")

                elif bytesMessage == 'connect' and self.destination_folder == "":
                    self.update_status("Error, must set folder before sending data.")
                                

                        
                #time.sleep(.01)


def init(recordsPerFile):
    app = QGuiApplication(sys.argv)

    # Added to avoid runtime warnings
    app.setOrganizationName("UB CSE-453")
    app.setOrganizationDomain("engineering.buffalo")
    app.setApplicationName("mGRUE Driver")
    app.setWindowIcon(QIcon("images/icon.png"))
    engine = QQmlApplicationEngine()

    # Load QML file
    engine.load(os.path.dirname(os.path.abspath(__file__)) + '/main.qml')
    engine.quit.connect(app.quit)

    # Get QML File context
    backend = Backend()
    engine.rootObjects()[0].setProperty('backend', backend)
    backend.update_records(recordsPerFile)

    backend.update_status("Awaiting Connection")
    #thread = threading.Thread(target=backend.readSerial, args=())
    thread = threading.Thread(target=backend.readStarter, args=())
    thread.start()
    sys.exit(app.exec_())
