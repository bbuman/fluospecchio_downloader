import tkinter
import tkinter.ttk as ttk
import jpype as jp
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
import ConnectionManager as cm
import DownloadManager as dm
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
        # self.c_path = "C:/Program Files/SPECCHIO/specchio-client.jar"
        self.c_path = "C:\\Users\\Bastian\\Downloads\\specchio-client\\specchio-client.jar"


    def browseFiles(self):
        filename = filedialog.askdirectory(title="Select a File")
        self.folder_path = filename
        # Change label contents
        # print(self.folder_path)

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
        self.tree.pack(fill='both', expand=True, side="left", padx=10, pady=10)
        self.tree.bind("<ButtonPress-1>", self.onClick)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.vsb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=self.vsb.set)
        self.visualize = tkinter.Button(self)
        self.visualize["text"] = "Visualize"
        self.visualize["command"] = self.visualizeHierarchy
        self.visualize.pack(padx=10, pady=10)
        self.download = tkinter.Button(self)
        self.download["text"] = "Download"
        self.download["command"] = self.downloadData
        self.download.pack(padx=10, pady=10)

    def onClick(self, event):
        item = self.tree.identify('item', event.x, event.y)
        self.selected_item = item
        self.selected_node = self.hierarchy.get(item)

    def downloadData(self):
        try:
            node = self.selected_node
            self.browseFiles()
            self.download_manager = dm.DownloadManager(self.cm.SPECCHIOTYPES, self.cm.specchio_client,
                                                       node, self.selected_item, self.folder_path, self.stop_hierarchy,
                                                       self.tree, self.hierarchy, self.master)
            self.download_manager.startDownload()

        except AttributeError:
            win = tkinter.Toplevel()
            win.wm_title("ERROR")
            l = tkinter.Label(win, text="Failed to Download. Please connect to DB first and then select some data.")
            l.pack()
            b = tkinter.Button(win, text="Okay", command=win.destroy)
            b.pack()

    def visualizeHierarchy(self):
        """
        Download vectors for a certain hierarchy and visualize using matplotlib
        :return:
        """
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
        self.cm = cm.ConnectionManager(self.master, self.c_path, self)

    def buildTree(self):
        # 1. Start with defining lowest hierarchy, this is a hack and not suitable to all specchio implementations!
        self.stop_hierarchy = ["DN", "Radiance", "Reflectance", "SpecFit"]
        # 2. Start with a database node:
        self.db_node = self.cm.specchio_client.getDatabaseNode(jp.JString("Acquisition Time"), jp.JBoolean(True))

        # 3. Downlaod its children (will be campaigns):
        self.campaigns = list(self.cm.specchio_client.getChildrenOfNode(self.db_node))

        # 4. Add all the hierarchies down to the processing levels
        self.hierarchy = {}
        for campaign in self.campaigns:
            self.recursiveTreeBuilder('', 0, self.hierarchy, campaign)

    def recursiveTreeBuilder(self, parent_object, id, node_dict, node_object):
        element_id = self.tree.insert(parent_object, id, text=node_object.getName())
        node_dict[element_id] = node_object
        if node_object.getName() not in self.stop_hierarchy:
            for i, node in enumerate(list(self.cm.specchio_client.getChildrenOfNode(node_object))):
                self.recursiveTreeBuilder(element_id, i, node_dict, node)

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


    def buildHierarchy(self, specchio_client, children_list, node, depth):
        this_depth = depth - 1
        children = self.getChildren(specchio_client, node)
        current_children = []
        for child in children:
            if (this_depth == 0):
                print("Breaking at lowest hierarchy reached for " + child.getId())
                break
            else:
                current_children.append(child)
                try:
                    self.buildHierarchy(specchio_client, current_children, child, this_depth)
                except:
                    print('no more hierarchies')
        children_list.append(current_children)
        return children_list


    def buildLevels(self, days, hierarchies, parent_list, parent_length, current_path, max_depth):
        this_depth = max_depth-1
        child_length = parent_length
        path_to_child = ""
        for child in parent_list:
            if not isinstance(child, list):
                if this_depth == 0:
                    days.append(child)
                    hierarchies.append(path_to_child)
            else:
                self.buildLevels(days, hierarchies, child, child_length, path_to_child, this_depth)


if __name__ == '__main__':
    root = tkinter.Tk()
    app = MyApp(root)
    app.mainloop()