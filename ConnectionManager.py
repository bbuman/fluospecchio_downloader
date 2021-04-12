import tkinter
import jpype as jp

class ConnectionManager:

    def __init__(self, parent_frame, c_path, download_client):
        self.parent_frame = parent_frame
        self.c_path = c_path
        self.frame = tkinter.Toplevel(self.parent_frame, width=200, height=200)
        self.initialize_client()
        self.list_db_connections()
        self.create_connection_window()
        if self.db_descriptors.size() > 0:
            db_descriptor = self.db_descriptors.get(0)
            self.set_info(db_descriptor.getProtocol(), db_descriptor.getServer(), db_descriptor.getPort(), 
            db_descriptor.getPath(), db_descriptor.getDataSourceName(), db_descriptor.getDisplayUser(), 
            db_descriptor.getPassword())
        else:
            self.set_info("", "", "", "", "", "", "")

        self.dc = download_client

    def create_connection_window(self):
        """ Create the window that allows to enter or select a connection to a web application server. 
        """
        self.connection_frame = tkinter.Frame(self.frame)
        self.connection_frame.pack()
        self.list_frame = tkinter.Frame(self.connection_frame)
        self.list_frame.pack(side=tkinter.TOP)
        self.label_frame = tkinter.Frame(self.connection_frame)
        self.label_frame.pack(side=tkinter.LEFT)
        self.entry_frame = tkinter.Frame(self.connection_frame)
        self.entry_frame.pack(side=tkinter.RIGHT)

        ## Available connections
        # 1. create the dropdown and first entry 
        self.tkvarq = tkinter.StringVar(self.list_frame) 
        self.tkvarq.set(self.db_descriptors_str[0])
        # 2. create the menu dropdown item and populate the items
        self.connections_menu = tkinter.OptionMenu(self.list_frame, self.tkvarq, *self.db_descriptors_str, command=self.OptionMenu_SelectionEvent)
        self.connections_menu.pack()

        ## Protocol
        self.protocol_label = tkinter.Label(self.label_frame)
        self.protocol_label['text'] = "Protocol"
        self.protocol_label.pack(padx=5, pady=5)
        self.button_frame = tkinter.Frame(self.entry_frame)
        self.button_frame.pack(padx=5, pady=5)
        self.chose_protocols = ['http', 'https']
        self.sel_protocol = tkinter.StringVar()

        for protocol in self.chose_protocols:
            b = tkinter.Radiobutton(self.button_frame)
            b['text'] = protocol
            b['value'] = protocol
            b['variable'] = self.sel_protocol
            b.pack(anchor="w", side='right')

        ## Server
        self.server = tkinter.Label(self.label_frame)
        self.server.pack(padx=5, pady=5)
        self.server["text"] = "Web Application Server"
        self.entryServer = tkinter.Entry(self.entry_frame)
        self.entryServer.pack(padx=5, pady=5)
        self.serverName = tkinter.StringVar()
        self.entryServer["textvariable"] = self.serverName

        ## Port
        self.port = tkinter.Label(self.label_frame)
        self.port.pack(padx=5, pady=5)
        self.port["text"] = "Port"
        self.entryPort = tkinter.Entry(self.entry_frame)
        self.entryPort.pack(padx=5, pady=5)
        self.portName = tkinter.StringVar()
        self.entryPort["textvariable"] = self.portName

        ## Application Path
        self.path = tkinter.Label(self.label_frame)
        self.path.pack(padx=5, pady=5)
        self.path["text"] = "Application Path"
        self.entryPath = tkinter.Entry(self.entry_frame)
        self.entryPath.pack(padx=5, pady=5)
        self.pathName = tkinter.StringVar()
        self.entryPath["textvariable"] = self.pathName

        ## Data Source Name
        self.datasource = tkinter.Label(self.label_frame)
        self.datasource.pack(padx=5, pady=5)
        self.datasource["text"] = "Data Source Name"
        self.entryDatasource = tkinter.Entry(self.entry_frame)
        self.entryDatasource.pack(padx=5, pady=5)
        self.datasourceName = tkinter.StringVar()
        self.entryDatasource["textvariable"] = self.datasourceName

        ## Username
        self.username = tkinter.Label(self.label_frame)
        self.username.pack(padx=5, pady=5)
        self.username["text"] = "Username"
        self.entryUsername = tkinter.Entry(self.entry_frame)
        self.entryUsername.pack(padx=5, pady=5)
        self.usernameName = tkinter.StringVar()
        self.entryUsername["textvariable"] = self.usernameName

        ## Password
        self.password = tkinter.Label(self.label_frame)
        self.password.pack(padx=5, pady=5)
        self.password["text"] = "Password"
        self.entryPassword = tkinter.Entry(self.entry_frame)
        self.entryPassword.pack(padx=5, pady=5)
        self.passwordName = tkinter.StringVar()
        self.entryPassword["textvariable"] = self.passwordName

        ## Connect
        self.connect = tkinter.Button(self.label_frame)
        self.connect.pack(padx=5, pady=5)
        self.connect["text"] = "Connect"
        self.connect["state"] = tkinter.ACTIVE
        self.connect["command"] = self.client_connect

        ## Cancel
        self.cancel = tkinter.Button(self.entry_frame)
        self.cancel.pack(padx=5, pady=5)
        self.cancel["text"] = "Cancel"
        self.cancel["command"] = self.frame.destroy

    def set_info(self, protocol, server, port, path, jdbc, user, password):
        """ Set the info to be displayed in the text fields depending on user action
        Keyword arguments:
        protocol: "http" or "https"
        server: ip address of the server
        port: the port number
        path: the path to the web application (e.g. /specchio_service)
        user: the user name
        password: the password 
        datasource: the jdbc connection (e.g. jdbc/specchio)

        Returns:
        """
        self.sel_protocol.set(protocol)
        self.serverName.set(server)
        self.portName.set(port)
        self.pathName.set(path)
        self.datasourceName.set(jdbc)
        self.usernameName.set(user)
        self.passwordName.set(password)

    def OptionMenu_SelectionEvent(self, event): 
        """ Listen on selection changes in the dropdown menu
        """
        con_str = self.tkvarq.get()[0] # connection string from dropdown menu
        db_descriptor = self.db_descriptors.get(int(con_str))
        self.set_info(db_descriptor.getProtocol(), db_descriptor.getServer(), db_descriptor.getPort(), 
            db_descriptor.getPath(), db_descriptor.getDataSourceName(), db_descriptor.getDisplayUser(), 
            db_descriptor.getPassword())      

    def initialize_client(self):
        """Initialize the JVM and the specchio-client application
        """
        try:
            jp.startJVM(classpath=self.c_path, convertStrings=True)
        except OSError as ose:
            print(str(ose))
        self.SPECCHIO = jp.JPackage('ch').specchio.client
        self.SPECCHIOTYPES = jp.JPackage('ch').specchio.types
        # 1.3 Create a client factory instance and get a list of all connection details:
        self.cf = self.SPECCHIO.SPECCHIOClientFactory.getInstance()

    def list_db_connections(self):
        """ Clears the descriptors and reloads them, then creates a list of available connections.
        """
        self.db_descriptors = self.cf.getAllServerDescriptors()
        print(self.db_descriptors)
        self.db_descriptors_str = []
        for i in range(self.db_descriptors.size()):
            cur_str = self.db_descriptors.get(i).toString()
            self.db_descriptors_str.append(str(i) + "-" + cur_str)
    
    def create_db_connection(self, protocol, server, port, path, user, password, datasource):
        """Create a new WebAppDescriptor for the connection to a server.

        Keyword arguments:
        protocol: "http" or "https"
        server: ip address of the server
        port: the port number
        path: the path to the web application (e.g. /specchio_service)
        user: the user name
        password: the password 
        datasource: the jdbc connection (e.g. jdbc/specchio)

        Returns:
        db_descriptor: the descriptor object used for the connection
        """

        # SPECCHIOWebAppDescriptor(java.lang.String protocol, java.lang.String server, int port, 
        # java.lang.String path, java.lang.String user, java.lang.String password, java.lang.String dataSourceName, 
        # boolean uses_default_trust_store, java.lang.String preferenceNodeName)
        db_descriptor = self.SPECCHIO.SPECCHIOWebAppDescriptor(
                                                              jp.JString(protocol),     # http or https
                                                              jp.JString(server),       # server
                                                              jp.JInt(int(port)),       # port (int)
                                                              jp.JString(path),         # path
                                                              jp.JString(user),         # user
                                                              jp.JString(password),     # password
                                                              jp.JString(datasource),   # datasource
                                                              jp.JBoolean(False),       # trust_store
                                                              jp.JString('1')
                                                              )
        return db_descriptor

    def client_connect(self):
        """Connect to the server defined in the GUI
        Keyword arguments:
        Returns: 
        """
        connection = self.create_db_connection(self.sel_protocol.get(), self.serverName.get(), self.portName.get(), self.pathName.get(), self.usernameName.get(), self.passwordName.get(), self.datasourceName.get())
        self.specchio_client = self.cf.createClient(connection) 
        
        self.frame.destroy()
        self.dc.buildTree()