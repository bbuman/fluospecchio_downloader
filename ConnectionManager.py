import tkinter
import jpype as jp
import DownloadClient as dc


class ConnectionManager:

    def __init__(self, parent_frame, c_path, download_client):
        self.parent_frame = parent_frame
        self.c_path = c_path
        self.frame = tkinter.Toplevel(self.parent_frame, width=200, height=200)
        self.createConnectionDialogWidgets()
        self.dc = download_client

    def connectionDialog(self):
        self.frame = tkinter.Toplevel(self.parent_frame, width=200, height=200)
        self.createConnectionDialogWidgets()

    def createConnectionDialogWidgets(self):
        self.connection_frame = tkinter.Frame(self.frame)
        self.connection_frame.pack()
        self.label_frames = tkinter.Frame(self.connection_frame)
        self.label_frames.pack(side=tkinter.LEFT)
        self.entry_frames = tkinter.Frame(self.connection_frame)
        self.entry_frames.pack(side=tkinter.RIGHT)

        ## Server
        self.server = tkinter.Label(self.label_frames)
        self.server.pack(padx=5, pady=5)
        self.server["text"] = "Web Application Server"
        self.entryServer = tkinter.Entry(self.entry_frames)
        self.entryServer.pack(padx=5, pady=5)
        self.serverName = tkinter.StringVar()
        self.serverName.set("")
        self.entryServer["textvariable"] = self.serverName

        ## Port
        self.port = tkinter.Label(self.label_frames)
        self.port.pack(padx=5, pady=5)
        self.port["text"] = "Port"
        self.entryPort = tkinter.Entry(self.entry_frames)
        self.entryPort.pack(padx=5, pady=5)
        self.portName = tkinter.StringVar()
        self.portName.set("")
        self.entryPort["textvariable"] = self.portName

        ## Application Path
        self.path = tkinter.Label(self.label_frames)
        self.path.pack(padx=5, pady=5)
        self.path["text"] = "Application Path"
        self.entryPath = tkinter.Entry(self.entry_frames)
        self.entryPath.pack(padx=5, pady=5)
        self.pathName = tkinter.StringVar()
        self.pathName.set("")
        self.entryPath["textvariable"] = self.pathName

        ## Data Source Name
        self.datasource = tkinter.Label(self.label_frames)
        self.datasource.pack(padx=5, pady=5)
        self.datasource["text"] = "Data Source Name"
        self.entryDatasource = tkinter.Entry(self.entry_frames)
        self.entryDatasource.pack(padx=5, pady=5)
        self.datasourceName = tkinter.StringVar()
        self.datasourceName.set("")
        self.entryDatasource["textvariable"] = self.datasourceName

        ## Username
        self.username = tkinter.Label(self.label_frames)
        self.username.pack(padx=5, pady=5)
        self.username["text"] = "Username"
        self.entryUsername = tkinter.Entry(self.entry_frames)
        self.entryUsername.pack(padx=5, pady=5)
        self.usernameName = tkinter.StringVar()
        self.usernameName.set("")
        self.entryUsername["textvariable"] = self.usernameName

        ## Password
        self.password = tkinter.Label(self.label_frames)
        self.password.pack(padx=5, pady=5)
        self.password["text"] = "Password"
        self.entryPassword = tkinter.Entry(self.entry_frames)
        self.entryPassword.pack(padx=5, pady=5)
        self.passwordName = tkinter.StringVar()
        self.passwordName.set("")
        self.entryPassword["textvariable"] = self.passwordName

        ## Connect
        self.connect = tkinter.Button(self.label_frames)
        self.connect.pack(padx=5, pady=5)
        self.connect["text"] = "Connect"
        self.connect["state"] = tkinter.ACTIVE
        self.connect["command"] = self.connectAndDestroy

        ## Cancel
        self.cancel = tkinter.Button(self.entry_frames)
        self.cancel.pack(padx=5, pady=5)
        self.cancel["text"] = "Cancel"
        self.cancel["command"] = self.frame.destroy

    def connectAndDestroy(self):
        """
        connect to the server
        :return:
        """
        self.frame.destroy()
        try:
            jp.startJVM(classpath=self.c_path, convertStrings=True)
        except OSError as ose:
            print(str(ose))
        self.SPECCHIO = jp.JPackage('ch').specchio.client
        self.SPECCHIOTYPES = jp.JPackage('ch').specchio.types
        # 1.3 Create a client factory instance and get a list of all connection details:
        self.cf = self.SPECCHIO.SPECCHIOClientFactory.getInstance()

        ### --- custom login credentials - not yet working:
        # self.db_descriptor = self.SPECCHIO.SPECCHIODatabaseDescriptor(jp.JString(self.serverName.get()),
        #                                                      jp.JInt(int(self.portName.get())),
        #                                                      jp.JString(self.pathName.get()),
        #                                                      jp.JString(self.datasourceName.get()),
        #                                                      jp.JString(self.usernameName.get()),
        #                                                      jp.JString(self.passwordName.get()))
        # self.specchio_client = self.cf.createClient(self.db_descriptor)  # zero indexed

        ### --- fixed login credentials
        self.db_descriptor_list = self.cf.getAllServerDescriptors()
        # self.specchio_client = self.cf.createClient(self.db_descriptor_list.get(1))  # zero indexed
        self.specchio_client = self.cf.createClient(self.db_descriptor_list.get(0))  # zero indexed
        self.dc.buildTree()