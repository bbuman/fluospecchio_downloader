import tkinter
import tkinter.ttk as ttk
import jpype as jp
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
import time
from tkinter import filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class MyApp(tkinter.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill='both', expand=True, padx=10, pady=10)
        self.menuBar = tkinter.Menu(master)
        master.config(menu=self.menuBar)
        self.fillMenuBar()
        self.createWidgets()
        self.c_path = "C:/Program Files/SPECCHIO/specchio-client.jar"

    def browseFiles(self):
        filename = filedialog.askdirectory(title="Select a File")
        self.folder_path = filename
        # Change label contents
        print(self.folder_path)


    def fillMenuBar(self):
        self.menuFile = tkinter.Menu(self.menuBar, tearoff=False)
        self.menuFile.add_separator()
        self.menuFile.add_command(label="Connect", command=self.connectionDialog)
        self.menuFile.add_separator()
        self.menuFile.add_command(label="Save to", command=self.browseFiles)
        self.menuFile.add_separator()
        self.menuFile.add_command(label="Quit", command=self.quit)
        self.menuFile.add_separator()
        self.menuBar.add_cascade(label="Menu", menu=self.menuFile)


    def createWidgets(self):
        self.tree = ttk.Treeview(self)
        self.tree.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.tree.bind("<ButtonPress-1>", self.onClick)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.vsb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=self.vsb.set)
        self.visualize = tkinter.Button(self)
        self.visualize["text"] = "Visualize"
        self.visualize["command"] = self.visualizeHierarchy
        self.visualize.pack(expand=True, side="right", padx=10, pady=10)

    def onClick(self, event):
        item = self.tree.identify('item', event.x, event.y)
        item_name = self.tree.item(item, "text")
        parent = self.tree.parent(item)
        if parent == '':
            name = item_name
        else:
            name = parent + '-' + item_name
        self.selected_node = self.node_collection.get(name)

    def visualizeHierarchy(self):
        try:
            spectrum_ids = self.specchio_client.getSpectrumIdsForNode(self.selected_node)
        except:
            print("Nothing selected!")
        spaces = self.specchio_client.getSpaces(spectrum_ids, 'Acquisition Time')

        found_ids = spaces[0].getSpectrumIds()  # get them sorted by 'Acquisition Time’

        # Load the spectral data from the database into the space:
        space = self.specchio_client.loadSpace(spaces[0])

        # GET THE SENSOR'S WAVELENGTH SPECIFICATIONS
        wvl = space.getAverageWavelengths()
        # self.frame = tkinter.Frame(self, expand=True, side="right", padx=10, pady=10, width=300, height=300)
        # self.frame.pack()
        vectors = space.getVectors()
        # names = self.specchio_client.getMetaparameterValues(ids, 'File Name')
        timings = self.specchio_client.getMetaparameterValues(found_ids, 'Acquisition Time (UTC)')
        sif = np.zeros((len(wvl), timings.size()))
        t = []
        for i in range(vectors.size()):
            try:
                t.append(dt.datetime.strptime(timings.get(i).toString(), '%Y-%m-%dT%H:%M:%S.%fZ'))
                sif[:, i] = np.array(vectors.get(i))
            except:
                print("no acquisition time found!")

        # ## ---
        figure = plt.Figure(figsize=(6, 5), dpi=100)
        ax = figure.add_subplot(111)
        chart_type = FigureCanvasTkAgg(figure, self)
        chart_type.get_tk_widget().pack()
        for i in range(len(t)):
            ax.plot(wvl, sif[:, i], label=str(t[i]))
        ax.set_title('The Title for your chart')
        rem_vis = tkinter.Button(self)
        rem_vis["text"] = "Clear"
        rem_vis["command"] = plt.clf
        rem_vis.pack(expand=True, side="right", padx=10, pady=10)


    def connectionDialog(self):
        self.frame = tkinter.Toplevel(self, width=200, height=200)
        self.createConnectionDialogWidgets()
        # self.checkConncetionDialog()

    def checkConncetionDialog(self):
        while(len(self.serverName.get()) & len(self.portName.get()) & len(self.pathName.get()) & len(self.datasourceName.get())
              & len(self.usernameName.get()) & len(self.passwordName.get()) == 0):
            self.connect["state"] = tkinter.DISABLED
            time.sleep(1)
        self.connect["state"] = tkinter.ACTIVE

    def createConnectionDialogWidgets(self):
        ## Server
        self.server = tkinter.Label(self.frame)
        self.server.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.server["text"] = "Web Application Server"
        self.entryServer = tkinter.Entry(self.frame)
        self.entryServer.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.serverName = tkinter.StringVar()
        self.serverName.set("")
        self.entryServer["textvariable"] = self.serverName

        ## Port
        self.port = tkinter.Label(self.frame)
        self.port.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.port["text"] = "Port"
        self.entryPort = tkinter.Entry(self.frame)
        self.entryPort.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.portName = tkinter.StringVar()
        self.portName.set("")
        self.entryServer["textvariable"] = self.portName


        ## Application Path
        self.path = tkinter.Label(self.frame)
        self.path.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.path["text"] = "Application Path"
        self.entryPath = tkinter.Entry(self.frame)
        self.entryPath.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.pathName = tkinter.StringVar()
        self.pathName.set("")
        self.entryServer["textvariable"] = self.pathName


        ## Data Source Name
        self.datasource = tkinter.Label(self.frame)
        self.datasource.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.datasource["text"] = "Data Source Name"
        self.entryDatasource = tkinter.Entry(self.frame)
        self.entryDatasource.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.datasourceName = tkinter.StringVar()
        self.datasourceName.set("")
        self.entryServer["textvariable"] = self.datasourceName


        ## Username
        self.username = tkinter.Label(self.frame)
        self.username.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.username["text"] = "Username"
        self.entryUsername = tkinter.Entry(self.frame)
        self.entryUsername.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.usernameName = tkinter.StringVar()
        self.usernameName.set("")
        self.entryServer["textvariable"] = self.usernameName


        ## Password
        self.password = tkinter.Label(self.frame)
        self.password.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.password["text"] = "Password"
        self.entryPassword = tkinter.Entry(self.frame)
        self.entryPassword.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.passwordName = tkinter.StringVar()
        self.passwordName.set("")
        self.entryServer["textvariable"] = self.passwordName


        ## Connect
        self.connect = tkinter.Button(self.frame)
        self.connect.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.connect["text"] = "Connect"
        self.connect["state"] = tkinter.ACTIVE
        self.connect["command"] = self.connectAndDestroy

        ## Cancel
        self.cancel = tkinter.Button(self.frame)
        self.cancel.pack(fill='both', expand=True, side="right", padx=10, pady=10)
        self.cancel["text"] = "Cancel"
        self.cancel["command"] = self.frame.destroy

    def connectAndDestroy(self):
        self.frame.destroy()
        try:
            jp.startJVM(classpath=self.c_path, convertStrings=True)
        except OSError as ose:
            print(str(ose))
        self.SPECCHIO = jp.JPackage('ch').specchio.client
        # 1.3 Create a client factory instance and get a list of all connection details:
        self.cf = self.SPECCHIO.SPECCHIOClientFactory.getInstance()
        # self.db_descriptor_list = self.cf.getAllServerDescriptors()
        # 1.4 Connect to specchio:
        self.db_descriptor = self.SPECCHIO.SPECCHIODatabaseDescriptor(self.serverName.get(),
                                                             self.portName.get(),
                                                             self.pathName.get(),
                                                             self.datasourceName.get(),
                                                             self.usernameName.get(),
                                                             self.passwordName.get())
        # self.specchio_client = self.cf.createClient(self.db_descriptor_list.get(1))  # zero indexed
        self.specchio_client = self.cf.createClient(self.db_descriptor)  # zero indexed
        self.buildTree()

    def buildTree(self):
        self.should_print = False
        # 2. Select campaign:
        self.campaign_node = self.specchio_client.getCampaignNode(13, "Sampling Date", jp.java.lang.Boolean(True))

        # 3. Walk campaign nodes and create list of lists:
        # 3.1 Find depth to data (0 = top-level):
        self.max_depth = self.walk_hierarchy(self.specchio_client, self.campaign_node, 0)
        # 3.2 Build the complete hierarchy
        self.children_list = []
        self.buildHierarchy(self.specchio_client, self.children_list, self.campaign_node, self.max_depth)

        # 4. Build clean list of downloadable days:
        self.days = []
        self.hierarchies = []
        campaign_name = self.campaign_node.getName()
        if self.should_print:
            print("\\ " + self.campaign_node.getName())
        self.len_l0 = len(self.campaign_node.getName()) + 2
        self.level_0 = "/" + self.campaign_node.getName()
        self.buildLevels(self.days, self.hierarchies, self.children_list, self.len_l0, self.level_0, self.max_depth, self.should_print)
        self.node_collection = self.addToTreeAndDict(self.days)

    # def addToTree(self, child, level):
    #     for child in child:
    #         if isinstance(child, list):
    #             self.addToTree(child, level+1)
    #         else:
    #             self.tree.insert('', level, text=child)

    def addToTreeAndDict(self, days):
        node_collection = {}
        for day in days:
            self.tree.insert('', 'end', id=str(day), text=str(day))
            node_collection[str(day)] = day
            for i, node in enumerate(self.specchio_client.getChildrenOfNode(day)):
                self.tree.insert(str(day), i, text=node.getName())
                node_collection[str(day) + '-' + node.getName()] = node
        return node_collection

    def walk_hierarchy(self, specchio_client, node, current_depth):
        depth = current_depth
        children = self.getChildren(specchio_client, node)
        for i, child in enumerate(children):
            if child.getName() == "DN":
                break
            if i < 1:
                depth = self.walk_hierarchy(specchio_client, child, depth)
        return depth + 1

    def getChildren(self, specchio_client, node):
        children = specchio_client.getChildrenOfNode(node)
        return children

    def buildHierarchy(self, specchio_client, children_list, node, depth, should_print=False):
        this_depth = depth - 1
        children = self.getChildren(specchio_client, node)
        current_children = []
        for child in children:
            if (this_depth <= 0):
                if should_print:
                    print("Breaking at lowest hierarchy reached for " + child.getId())
                break
            else:
                current_children.append(child)
                try:
                    self.buildHierarchy(specchio_client, current_children, child, this_depth)
                except:
                    if should_print:
                        print('no more hierarchies')
        children_list.append(current_children)
        return children_list

    def buildLevels(self, days, hierarchies, parent_list, parent_length, current_path, max_depth, should_print = False):
        this_depth = max_depth-1
        child_length = parent_length
        path_to_child = ""
        for child in parent_list:
            if not isinstance(child, list):
                if should_print:
                    distance = ""
                    for i in range(parent_length):
                        distance += "-"
                    print(distance + "\\ " + child.getName())
                    path_to_child = current_path + "/" + child.getName()
                    child_length = parent_length + len(child.getName()) + 2
                if this_depth == 0:
                    days.append(child)
                    hierarchies.append(path_to_child)
            else:
                self.buildLevels(days, hierarchies, child, child_length, path_to_child, this_depth, should_print)

if __name__ == '__main__':
    root = tkinter.Tk()
    app = MyApp(root)
    app.mainloop()