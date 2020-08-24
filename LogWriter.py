import datetime as dt

class LogWriter:

    def __init__(self, path_to_logfile):
        self.path = path_to_logfile
        self.types = ["ERROR", "WARNING", "INFO"]
        self.createLogFile()


    def createLogFile(self):
        self.log_name = self.path + "/" + "download_log_" + dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".txt"
        self.log = open(self.log_name, "w")


    def writeLog(self, error_type, message):
        if error_type == "ERROR":
            self.log.write(self.getTimeStamp() + ": - ERROR - " + message + ".\n")
        elif error_type == "WARNING":
            self.log.write(self.getTimeStamp() + ": - WARNING - " + message + ".\n")
        elif error_type == "INFO":
            self.log.write(self.getTimeStamp() + ": - INFO - " + message + ".\n")
        else:
            self.log.write(self.getTimeStamp() + ": - " + error_type + " - " + message + ".\n")
        self.log.flush()

    def writeUpdate(self, message):
        self.log.write(self.log.write(self.getTimeStamp() + ": " + message))
        self.log.flush()

    def getTimeStamp(self):
        return dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")