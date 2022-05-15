import sys
import time
import threading
import os

from PySide2.QtGui import QGuiApplication, QIcon
from PySide2.QtQml import QQmlApplicationEngine
from PySide2.QtCore import QObject, Slot, Signal

from datetime import datetime
import serial

# Define our backend object, which we will pass to the engine object
class Backend(QObject):
    recordsPerFile = 5000        # Set max number of records that will be written to each file here
    currentStatus = ""
    status = Signal(str)

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

    def readSerial(self):
        with serial.Serial('COM4', 115200, timeout=1) as ser:
            print("Port opened, looking for device...")
            while (True):
                stillReading    = True
                curTime         = datetime.now().strftime("%H-%M-%S")
                sequenceNum     = 0
                fileCounter     = 0
                bytesMessage    = ser.readline().decode()[:-2]     # read a '\n' terminated line, removing the \n
                file            = 0
                sequence        = 0
                whiteline       = 0

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
                                file.write(bytesMessage + "\r\n")
                                file.write(sequence + "\r\n")
                                if os.name == 'nt':
                                    whiteline = ser.readline().decode("unicode_escape")[:-2]
                                else:
                                    whiteline = ser.readline().decode()[:-2] 

                                if whiteline == "":     # Every third line should be a blankspace
                                    file.write("\n")
                                else:
                                    print(whiteline)
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
    engine.load('main.qml')
    engine.quit.connect(app.quit)

    # Get QML File context
    backend = Backend()
    engine.rootObjects()[0].setProperty('backend', backend)
    backend.update_records(recordsPerFile)

    backend.update_status("Awaiting Connection")
    thread = threading.Thread(target=backend.readSerial, args=())
    thread.start()
    sys.exit(app.exec_())
