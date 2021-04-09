import LogWriter as lw
import xarray as xr
import numpy as np
import tkinter
import tkinter.ttk as ttk
import datetime as dt
import netCDF4 as nc4
import datetime as dt
from cftime import num2date, date2num
import re
import os
import _thread
# Default fill values:
# {'S1': '\x00',
#  'i1': -127,
#  'u1': 255,
#  'i2': -32767,
#  'u2': 65535,
#  'i4': -2147483647,
#  'u4': 4294967295,
#  'i8': -9223372036854775806,
#  'u8': 18446744073709551614,
#  'f4': 9.969209968386869e+36,
#  'f8': 9.969209968386869e+36}

class DownloadManager:

    def __init__(self, types, specchio_client, nodes, items, download_path, stop_hierarchy, tree, hierarchy, master_frame):
        self.types = types
        self.selected_nodes = nodes
        self.selected_items = items 
        self.specchio_client = specchio_client # reference to the specchio client instance (java application)
        self.dw_path = download_path # the selected download location (file system path to location)
        self.stop_hierarchy = stop_hierarchy
        self.tree = tree
        self.hierarchy = hierarchy
        self.log_writer = lw.LogWriter(self.dw_path)
        self.master_frame = master_frame
        # A selection of hard-coded currently available QI or Metadata parameters
        self.meta = ['Integration Time', 'Optical Compartment Humidity', 'Optical Compartment Temperature',
                         'PCB Humidity', 'PCB Temperature', 'Spectrometer Frame Temperature', 'Irradiance Instability', 
                         'Saturation Count', 'f_SpecFit_A', 'f_SpecFit_B', 'f_int', 'f_max_FR', 'f_max_FR_wvl', 
                         'f_max_R', 'f_max_R_wvl']
        # Based on this specify which metadata elements are available for each processing level
        self.level_meta = {'DN': self.meta[0:7], 'Radiance': self.meta[0:8],
                               'Reflectance': self.meta[0:8], 'SpecFit': self.meta}
        self.download_selection()
        self.setup_GUI()

    def setup_GUI(self):
        # Top level frame 
        self.win = tkinter.Toplevel()
        self.win.wm_title("Data Download")

        # Selection frame
        self.sel_frame = tkinter.Frame(self.win)
        self.sel_frame.pack()

        # Processing level selection frame
        self.select_levels = tkinter.LabelFrame(self.sel_frame)
        self.select_levels["text"] = "Please chose processing level(s)"
        self.select_levels.pack(side="left", padx=5, pady=5, expand=True)
        self.chosen_levels =  []
        self.vars = []
        self.checks = []
        for key in self.download_hierarchy:
            var = tkinter.BooleanVar()
            var.set(False)
            check = tkinter.Checkbutton(self.select_levels)
            check["text"] = key
            check["command"] = self.handle_selection
            check["variable"] = var
            check.pack(anchor="w")
            self.checks.append(check)
            self.vars.append(var)

        # Metadata selection frame
        self.select_meta = tkinter.LabelFrame(self.sel_frame)
        self.select_meta["text"] = "Please chose metadata"
        self.select_meta.pack(side="right", padx=5, pady=5, expand=True)
        self.chosen_meta = []
        self.meta_vars = []
        self.meta_checks = []
        for mp in self.meta:
            var = tkinter.BooleanVar()
            var.set(False)
            check = tkinter.Checkbutton(self.select_meta)
            check["text"] = mp
            check["command"] = self.handle_meta_selection
            check["variable"] = var
            check.pack(anchor="w")
            self.meta_checks.append(check)
            self.meta_vars.append(var)

        # OK (download now) button
        self.ok_frame = tkinter.Frame(self.win)
        self.ok_frame.pack()
        okbtn = tkinter.Button(self.ok_frame)
        okbtn.pack(padx=5, pady=5, expand=True)
        okbtn["text"] = "OK"
        okbtn["state"] = tkinter.ACTIVE
        okbtn["command"] = self.destroy_and_download

    def download_selection(self):
        # Downloadable hierarchies are:
        self.download_hierarchy = {}
        for name in self.stop_hierarchy:
            self.download_hierarchy[name] = []
        # Fill download hierarchy information
        for item in self.selected_items:
            self.createDownloadHierarchy(item, self.download_hierarchy)

    def handle_selection(self):
        self.chosen_levels.clear()
        for i, var in enumerate(self.vars):
            if var.get():
                self.chosen_levels.append(self.checks[i]["text"])

    def handle_meta_selection(self):
        self.chosen_meta.clear()
        for i, var in enumerate(self.meta_vars):
            if var.get():
                self.chosen_meta.append(self.meta_checks[i]["text"])

    def destroy_and_download(self):
        self.win.destroy()
        # 1.  Find the name of the selected campaign:
        # stop = False
        # cur_id = self.download_hierarchy.get(self.chosen_levels[0])[0].getId()
        # while not stop:
        #     p_id = self.specchio_client.getHierarchyParentId(cur_id)
        #     if p_id == cur_id:
        #         stop = True
        #     cur_id = p_id
        
        # campaign_name = self.specchio_client.getHierarchyName(cur_id)
        campaign_name = "dataset"
        # 2. Prepare the file 
        self.prepare_netcdf(self.chosen_levels, campaign_name)
        # 3. Download the processing levels 
        for name in self.chosen_levels:
            # _thread.start_new_thread(self.download_window, (name,))
            # self.download_window(name)
            # _thread.start_new_thread(self.download_processing_level, (self.download_hierarchy.get(name), name))
            self.download_processing_level(self.download_hierarchy.get(name), name)

        self.rootgrp.close()
            

    def createDownloadHierarchy(self, tree_item, download_dict):
        for child in self.tree.get_children(tree_item):
            child_name = self.hierarchy.get(child).getName()
            try:
                if self.hierarchy.get(child) not in download_dict[child_name]:
                    download_dict[child_name].append(self.hierarchy.get(child))
            except:
                self.createDownloadHierarchy(child, download_dict)

    def download_window(self, level_identifier):
        """Creat a top level window with progress bar and other info
        Keyword arguments:
        level_identifier: string, representing the processing level
        """
        # Download info frame
        self.progress_win = tkinter.Toplevel()
        self.progress_win.wm_title("Downloading now...")
        self.l = tkinter.Label(self.progress_win, text="The following processing level: " + level_identifier + " is being downloaded.")
        self.l.pack()
        self.prog = ttk.Progressbar(self.progress_win, orient='horizontal', mode='indeterminate', length=280)
        self.prog.pack()

    def prepare_netcdf(self, chosen_levels, campaign_name):
        """Prepare an empty netCDF4 file for the data. The name of the file is based on time and campaign.
        Keyword arguments:
        chosen_levels: list of strings, A list containing all the chosen processing levels. 
        campaign_name: string, the name of the current campaign.
        """
        now = dt.datetime.now()
        file_name = "/" + campaign_name + "_" + now.strftime(format="%Y_%m_%d_%H_%M") + ".nc"
        self.rootgrp = nc4.Dataset(self.dw_path + file_name, "w", format="NETCDF4")
        for level in chosen_levels:
            # 1. Creating the groups
            self.rootgrp.createGroup(level)
            # 1.1 FLUO
            self.rootgrp.createGroup(level+"/FLUO")
            self.rootgrp.createGroup(level+"/FLUO/Downwelling")
            self.rootgrp.createGroup(level+"/FLUO/Upwelling")
            # 1.2 FULL
            self.rootgrp.createGroup(level+"/FULL")
            self.rootgrp.createGroup(level+"/FULL/Downwelling")
            self.rootgrp.createGroup(level+"/FULL/Upwelling")

            # 2. Creating the dimensions (wavelength, time)
            # 2.1 FLUO
            self.rootgrp[level+"/FLUO/Downwelling"].createDimension("wavelength", 1024) # get correct length from data
            self.rootgrp[level+"/FLUO/Downwelling"].createDimension("time", None) # we don't know the correct length at runtime
            self.rootgrp[level+"/FLUO/Upwelling"].createDimension("wavelength", 1024) 
            self.rootgrp[level+"/FLUO/Upwelling"].createDimension("time", None)
            # 2.2 FULL
            self.rootgrp[level+"/FULL/Downwelling"].createDimension("wavelength", 1024) 
            self.rootgrp[level+"/FULL/Downwelling"].createDimension("time", None) 
            self.rootgrp[level+"/FULL/Upwelling"].createDimension("wavelength", 1024) 
            self.rootgrp[level+"/FULL/Upwelling"].createDimension("time", None) 

            # 3. Create variables for coordinates
            # 3.1 FLUO
            self.rootgrp[level+"/FLUO/Downwelling"].createVariable("wavelength","f8",("wavelength",)) # f8 = 64-bit floating point
            self.rootgrp[level+"/FLUO/Downwelling"]["wavelength"].units = "nm"
            self.rootgrp[level+"/FLUO/Downwelling"].createVariable("time", "f8", ("time",))
            self.rootgrp[level+"/FLUO/Downwelling"]["time"].units = "seconds since 1970-01-01 00:00:00"
            self.rootgrp[level+"/FLUO/Downwelling"]["time"].calendar = "standard"
            self.rootgrp[level+"/FLUO/Upwelling"].createVariable("wavelength","f8",("wavelength",))
            self.rootgrp[level+"/FLUO/Upwelling"]["wavelength"].units = "nm"
            self.rootgrp[level+"/FLUO/Upwelling"].createVariable("time", "f8", ("time",))
            self.rootgrp[level+"/FLUO/Upwelling"]["time"].units = "seconds since 1970-01-01 00:00:00"
            self.rootgrp[level+"/FLUO/Upwelling"]["time"].calendar = "standard"
            # 3.2 FULL
            self.rootgrp[level+"/FULL/Downwelling"].createVariable("wavelength","f8",("wavelength",)) 
            self.rootgrp[level+"/FULL/Downwelling"]["wavelength"].units = "nm"
            self.rootgrp[level+"/FULL/Downwelling"].createVariable("time", "f8", ("time",))
            self.rootgrp[level+"/FULL/Downwelling"]["time"].units = "seconds since 1970-01-01 00:00:00"
            self.rootgrp[level+"/FULL/Downwelling"]["time"].calendar = "standard"
            self.rootgrp[level+"/FULL/Upwelling"].createVariable("wavelength","f8",("wavelength",))
            self.rootgrp[level+"/FULL/Upwelling"]["wavelength"].units = "nm"
            self.rootgrp[level+"/FULL/Upwelling"].createVariable("time", "f8", ("time",))
            self.rootgrp[level+"/FULL/Upwelling"]["time"].units = "seconds since 1970-01-01 00:00:00"
            self.rootgrp[level+"/FULL/Upwelling"]["time"].calendar = "standard"

            # 4. Create variables for the measurements
            # 4.1 define data type and unit type
            if level == "DN":
                utype = "DN"
            elif level == "Radiance" or "SpecFit":
                utype = "W/m2/nm/sr"
            else:
                utype = "a.u."
            # 4.2 FLUO
            self.rootgrp[level+"/FLUO/Downwelling"].createVariable("downwelling", "f8", ("wavelength", "time",)) 
            self.rootgrp[level+"/FLUO/Downwelling"]["downwelling"].units = utype
            self.rootgrp[level+"/FLUO/Upwelling"].createVariable("upwelling", "f8", ("wavelength", "time",)) 
            self.rootgrp[level+"/FLUO/Upwelling"]["upwelling"].units = utype
            # 4.3 FULL
            self.rootgrp[level+"/FULL/Downwelling"].createVariable("downwelling", "f8", ("wavelength", "time",)) 
            self.rootgrp[level+"/FULL/Downwelling"]["downwelling"].units = utype
            self.rootgrp[level+"/FULL/Upwelling"].createVariable("upwelling", "f8", ("wavelength", "time",)) 
            self.rootgrp[level+"/FULL/Upwelling"]["upwelling"].units = utype

            # 5. Create variables for the file name, they align with the time dimension - currently not working
            # 5.1 FLUO
            # self.rootgrp[level+"/FLUO/Downwelling"].createVariable("file_name", "vlen", ("time",)) 
            # self.rootgrp[level+"/FLUO/Upwelling"].createVariable("file_name", "vlen", ("time",)) 
            # # 5.2 FULL
            # self.rootgrp[level+"/FULL/Downwelling"].createVariable("file_name", "vlen", ("time",)) 
            # self.rootgrp[level+"/FULL/Upwelling"].createVariable("file_name", "vlen", ("time",)) 

            # 6. Create variables for other metadata elements, they also align with the time dimension
            # we could save on disk space by using u4 datatype, but currently no time to think about the consequences
            for mp in self.chosen_meta:
                if mp in self.level_meta.get(level):
                    # 6.1 FLUO
                    self.rootgrp[level+"/FLUO/Downwelling"].createVariable(mp, "f8", ("time",)) 
                    self.rootgrp[level+"/FLUO/Upwelling"].createVariable(mp, "f8", ("time",)) 
                    # 6.2 FULL
                    self.rootgrp[level+"/FULL/Downwelling"].createVariable(mp, "f8", ("time",)) 
                    self.rootgrp[level+"/FULL/Upwelling"].createVariable(mp, "f8", ("time",)) 

        self.log_writer.writeLog("INFO", "NetCDF4 file created.")
               
    def download_processing_level(self, node_list, level_identifier):
        """Download all data belonging to a certain processing level and store in the prepared netCDF4 file. 
        Keyword arguments:
        node_list: list, containing all selected nodes (java type)
        level_identifier: string, identifies the current processing level, one of DN, Radiance, Reflectance, SpecFit
        """
        # Write 
        self.log_writer.writeLog("INFO", "Downloading the following processing level: " + level_identifier)
        
        for i, node in enumerate(node_list):
            # 1. Find the name of the hierarchy 
            parent = self.specchio_client.getHierarchyParentId(node.getId())
            parent_name = self.specchio_client.getHierarchyName(parent)
            self.log_writer.writeLog("INFO", "Downloading the following node: " + str(parent_name))

            # 2. Get spectrum_ids for this node
            spectrum_ids = self.specchio_client.getSpectrumIdsForNode(node)

            # 3. Get the spaces corresponding to these spectra
            spaces = self.specchio_client.getSpaces(spectrum_ids, 'Acquisition Time')

            # 4. Download the space
            for space in spaces:
                # 4.1 Get the spectrum ids belonging to this space
                space_ids = space.getSpectrumIds()
                # 4.2 Load the space
                this_space = self.specchio_client.loadSpace(space)
                # 4.3 Get the wavelength information
                space_wvl = np.array(this_space.getAverageWavelengths())
                # 4.4 Check which sensor this space belongs to (FLUO or FULL)
                if(space_wvl[0] < 400):
                    sensor_identifier = "FULL"
                else:
                    sensor_identifier = "FLUO"
                # 4.5 Download the measurement
                vectors = this_space.getVectors()
                # 4.6 Download metadata: Acquisition Time UTC and File Name
                names = self.specchio_client.getMetaparameterValues(space_ids, 'File Name')
                timings = self.specchio_client.getMetaparameterValues(space_ids, 'Acquisition Time (UTC)')
                # 4.7 Download selected metadata
                metadata = {}
                for mp in self.chosen_meta:
                    if mp in self.level_meta.get(level_identifier):
                        metadata[mp] = self.specchio_client.getMetaparameterValues(space_ids, mp)

                # 4.8 Process the downloaded info
                dw_count = 0
                up_count = 0
                for j in range(vectors.size()):
                    # 4.8.1 Try to parse the timing information. Skip this element if no time stamp is available
                    try:
                        t = dt.datetime.strptime(timings.get(j).toString(), "%Y-%m-%dT%H:%M:%S.%fZ")
                    except:
                        continue
                    # 4.8.2 Convert vector to numpy array
                    vector = np.array(vectors.get(j))
                    # 4.8.3 Get the name of this measurement
                    name = names.get(j)
                    # 4.8.4 Check if upwelling or downwelling:
                    is_upwelling = False
                    direction = "Downwelling"
                    var_name = "downwelling"
                    dw_count += 1
                    if(re.search("VEG*", name)):
                        is_upwelling = True
                        direction = "Upwelling"
                        var_name = "upwelling"
                        up_count +=1
                    # 4.8.5 If first run, then add wavelength data to the wavelength dimension
                    if i == 0 and (dw_count == 1 or up_count == 1):
                        self.rootgrp[level_identifier + "/" + sensor_identifier + "/" + direction]["wavelength"][:] = space_wvl[:]
                    # 4.8.6 Add timestamp to time dimension
                    # Convert timestamp to numeric, based on specified unit and calendar (see point 3 in prepare_netcdf)
                    cur_index = self.rootgrp[level_identifier + "/" + sensor_identifier + "/" + direction]["time"].shape[0]
                    t_num = date2num(t, units=self.rootgrp[level_identifier + "/" + sensor_identifier + "/" + direction]["time"].units, calendar=self.rootgrp[level_identifier + "/" + sensor_identifier + "/" + direction]["time"].calendar)
                    self.rootgrp[level_identifier + "/" + sensor_identifier + "/" + direction]["time"][cur_index] = t_num
                    # 4.8.7 Insert measurement to netcdf
                    self.rootgrp[level_identifier + "/" + sensor_identifier + "/" + direction][var_name][:,cur_index] = vector[:]
                    # 4.8.8 Insert file name to netcdf - currently not working (see point 5 in prepare_netcdf)
                    # self.rootgrp[level_identifier + "/" + sensor_identifier + "/" + direction]["file_name"][cur_index] = name
                    # 4.8.9 Insert other metaparameters
                    for key in metadata:
                        if metadata.get(key).get(j) == None:
                            self.rootgrp[level_identifier + "/" + sensor_identifier + "/" + direction][key][cur_index] = 9.969209968386869e+36
                        elif float(metadata.get(key).get(j)) == -999.0:
                            self.rootgrp[level_identifier + "/" + sensor_identifier + "/" + direction][key][cur_index] = 9.969209968386869e+36
                        else:
                            self.rootgrp[level_identifier + "/" + sensor_identifier + "/" + direction][key][cur_index] = metadata.get(key).get(j)