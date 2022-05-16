import argparse
import logging
import os
import sys
import time
import threading


from datetime import datetime
import serial
import gui



def valid_path(path):
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid directory")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='mGRUE-driver', description='Initialize the mGRUE Host Device Driver')
    parser.version = '1.0'
    parser.add_argument('mode',
                        choices=['gui', 'cli'],
                        help='option to use program through a GUI or via Command Line')
    parser.add_argument('directory',
                        type=valid_path,
                        help="destination for the records recieved by the mGRUE application")
    parser.add_argument('-r',
                        '--records',
                        type=int,
                        nargs='?',
                        default=500,
                        help='the number of records per file. Default 500')
    args = parser.parse_args()

    recordsPerFile = args.records
    destinationFolder = args.directory

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    if(args.mode == 'gui'):
        gui.init(recordsPerFile)

    else:
        logging.info(f"File Destination Path: {destinationFolder}")
        currentStatus = "Port opened, looking for device..."
        logging.info(f"Status: {currentStatus}")

        with serial.Serial('COM1', 115200, timeout=1) as ser:
            while (True):
                stillReading    = True
                curTime         = datetime.now().strftime("%H-%M-%S")
                sequenceNum     = 0
                fileCounter     = 0
                bytesMessage    = ser.readline().decode()[:-2]     # read a '\n' terminated line, removing the \n
                file            = 0
                sequence        = 0
                whiteline       = 0

                if bytesMessage == 'connect' and destinationFolder != "":
                    ser.write(b'handshake\n')
                    currentStatus = "Device Connected"
                    logging.info(f"Status: {currentStatus}")
                    
                    if os.name == 'nt':
                        file = open(destinationFolder + "/" + curTime + "_file" + str(fileCounter) + ".fn", "w", encoding="unicode_escape")
                    else:
                        file = open(destinationFolder + "/" + curTime + "_file" + str(fileCounter) + ".fn", "w", encoding="utf-8")

                    while (stillReading or currentStatus == "Paused."):       # Run while file is still being read or the reading is paused.
                        if os.name == 'nt':
                            bytesMessage = ser.readline().decode("unicode_escape")[:-2]     # This should either be the start of a record, a new_rate command, or EOF
                        else:
                            bytesMessage = ser.readline().decode()[:-2]

                        if bytesMessage == 'pause':       # Pauses the transfer for a baud rate change
                            currentStatus = "Paused."
                            logging.info(f"Status: {currentStatus}")
                            
                        elif bytesMessage != "" and bytesMessage[0] == '>':     # Ensures that the first piece of data of a record is the metadata
                            currentStatus = "Data transfer in progress...."
                            logging.info(f"Status: {currentStatus}")

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
                                    currentStatus ="Error, line should have been a whiteline..."
                                    logging.error(f"{currentStatus}")
                                    sys.exit()
                                
                                sequenceNum += 1        # A record has successfully been written, increment SequenceNum
                                if sequenceNum == recordsPerFile:     # When backend.recordsPerFile records have been written, close file and start another one
                                    file.close()
                                    fileCounter += 1
                                    if os.name == 'nt':
                                        file = open(destinationFolder+ "/" + curTime + "_file" + str(fileCounter) + ".fn", "w")
                                    else:
                                        file = open(destinationFolder + "/" + curTime + "_file" + str(fileCounter) + ".fn", "w")

                                    sequenceNum = 0
                            else:
                                print(sequence)
                                currentStatus = "Error, line should have been a dna sequence..."
                                logging.error(f"{currentStatus}")
                                sys.exit()
                        elif bytesMessage != "":        # If data is not a command, new record then it must be bad.
                            currentStatus = "Error, Received bad line: " + bytesMessage
                            logging.error(f"{currentStatus}")
                            sys.exit()
                        elif bytesMessage == "" and currentStatus == "Data transfer in progress....":     # If no data is received when not paused must be EOF
                            stillReading = False
                            file.close()
                            currentStatus = "Data transfer complete! Awaiting new action..."
                            logging.info(f"Status: {currentStatus}")
                            time.sleep(1)
                            currentStatus = "Awaiting Connection"
                            logging.info(f"Status: {currentStatus}")

                elif bytesMessage == 'connect' and destinationFolder == "":
                    currentStatus = "Error, must set folder before sending data."
                    logging.error(f"{currentStatus}")
                                

                        
                #time.sleep(.01)
