import tkinter
import tkinter.ttk as ttk
import jpype as jp
import numpy as np
import datetime as dt
import ConnectionManager as cm
import DownloadManager as dm
from tkinter import filedialog

class MyApp(tkinter.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.pack(fill='both', expand=True, padx=10, pady=10)
        self.menuBar = tkinter.Menu(master)
        master.config(menu=self.menuBar)
        self.fillMenuBar()
        self.createWidgets()
        self.restricted_view = False

    def browseFiles(self):
        filename = filedialog.askdirectory(title="Select a File")
        self.folder_path = filename

    def fillMenuBar(self):
        self.menuFile = tkinter.Menu(self.menuBar, tearoff=False)
        self.menuFile.add_separator()
        self.menuFile.add_command(label="Connect", command=self.connectionDialog)
        self.menuFile.add_separator()
        self.menuFile.add_command(label="Quit", command=self.quit)
        self.menuFile.add_separator()
        self.menuBar.add_cascade(label="Menu", menu=self.menuFile)

    def createWidgets(self):
        self.download = tkinter.Button(self)
        self.download["text"] = "Download"
        self.download["command"] = self.downloadData
        self.download.pack(padx=10, pady=10)

    def createTree(self):
        self.tree = ttk.Treeview(self)
        self.tree.pack(fill='both', expand=True, side="left", padx=10, pady=10)
        self.tree.bind("<ButtonRelease-1>", self.onClick)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.vsb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=self.vsb.set)

    def onClick(self, event):
        self.selected_nodes = []
        self.selected_items = self.tree.selection()

        for item in self.selected_items:
            if self.hierarchy.get(item).getName() not in self.stop_hierarchy:
                if len(self.tree.get_children(item)) == 0:
                    for i, node in enumerate(list(self.cm.specchio_client.getChildrenOfNode(self.hierarchy.get(item)))):
                        element_id = self.tree.insert(item, i, text=node.getName())
                        self.hierarchy[element_id] = node
            self.selected_nodes.append(self.hierarchy.get(item))
            print(self.hierarchy.get(item))

    def downloadData(self):
        try:
            nodes = self.selected_nodes
            self.browseFiles()
            self.download_manager = dm.DownloadManager(self.cm.SPECCHIOTYPES, self.cm.specchio_client,
                                                       nodes, self.selected_items, self.folder_path, self.stop_hierarchy,
                                                       self.tree, self.hierarchy, self.master)

        except AttributeError as ae:
            win = tkinter.Toplevel()
            win.wm_title("ERROR")
            err_txt = "Failed to Download. Error = " + str(ae)
            l = tkinter.Label(win, text= err_txt)
            l.pack()
            b = tkinter.Button(win, text="Okay", command=win.destroy)
            b.pack()

    def findSpecchioClient(self):
        filename = filedialog.askopenfilename(title="Please Navigate to the Specchio Client")
        self.c_path = filename

    def findRawData(self):
        filename = filedialog.askdirectory(title="Please Navigate to the raw data.")
        self.raw_data_path = filename

    def findCalibrationFile(self):
        filename = filedialog.askopenfilename(title="Please Navigate to the calibration file you want to use")
        if not filename.lower().endswith('.csv'):
            self.calibration_path = 'empty'
        else:
            self.calibration_path = filename

    def connectionDialog(self):
        try: 
            self.tree.destroy()
            self.vsb.destroy()
        except:
            print("can't destroy")
        self.findSpecchioClient()
        if not len(self.c_path) == 0:
            self.createTree()
            self.cm = cm.ConnectionManager(self.master, self.c_path, self)
        
    def buildTree(self):
        # 1. Start with defining lowest hierarchy, this is a hack and not suitable to all specchio implementations!
        self.stop_hierarchy = ["DN", "Radiance", "Reflectance", "SpecFit"]
        # 2. Start with a database node:

        self.db_node = self.cm.specchio_client.getDatabaseNode(jp.JString("Acquisition Time"), jp.JBoolean(self.restricted_view))

        # 3. Downlaod its children (will be campaigns):
        self.campaigns = list(self.cm.specchio_client.getChildrenOfNode(self.db_node))

        # 4. container for the hierarchies
        self.hierarchy = {}

        # 5. Add campaigns to the hierarchy browser:
        for campaign in self.campaigns:
            element_id = self.tree.insert('', 0, text=campaign.getName())
            self.hierarchy[element_id] = campaign

        # for campaign in self.campaigns:
        #     self.recursiveTreeBuilder('', 0, self.hierarchy, campaign)
    
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
    root.geometry("500x1000")
    app = MyApp(root)
    app.mainloop()