import LogWriter as lw
import xarray as xr
import numpy as np
import tkinter
import tkinter.ttk as ttk
import datetime as dt
import re
import os


class DownloadManager:

    def __init__(self, types, specchio_client, nodes, items, download_path, stop_hierarchy, tree, hierarchy, master_frame):
        self.types = types
        self.selected_nodes = nodes
        self.selected_items = items
        self.specchio_client = specchio_client
        self.dw_path = download_path
        self.stop_hierarchy = stop_hierarchy
        self.tree = tree
        self.hierarchy = hierarchy
        self.log_writer = lw.LogWriter(self.dw_path)
        self.master_frame = master_frame

    def startDownload(self):
        # Downloadable hierarchies are:
        self.download_hierarchy = {}
        for name in self.stop_hierarchy:
            self.download_hierarchy[name] = []
        # # Write start information
        # for node in self.selected_nodes:
        #     if isinstance(node, self.types.campaign_node):
        #         self.log_writer.writeLog("INFO", "Starting download for the following camapign: " + node.getName())
        #     else:
        #         self.log_writer.writeLog("INFO", "Starting download for the following hierarchy: " + node.getName())
        # Fill download hierarchy information
        for item in self.selected_items:
            self.createDownloadHierarchy(item, self.download_hierarchy)

        self.win = tkinter.Toplevel()
        self.win.wm_title("Info")
        # Frame
        self.select_levels = tkinter.LabelFrame(self.win)
        self.select_levels["text"] = "Please chose"
        self.select_levels.pack()
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

        okbtn = tkinter.Button(self.win)
        okbtn.pack()
        okbtn["text"] = "OK"
        okbtn["state"] = tkinter.ACTIVE
        okbtn["command"] = self.destroy_and_download

    def handle_selection(self):
        self.chosen_levels.clear()
        for i, var in enumerate(self.vars):
            if var.get():
                self.chosen_levels.append(self.checks[i]["text"])

    def destroy_and_download(self):
        self.win.destroy()
        for name in self.chosen_levels:
            self.download(self.download_hierarchy.get(name), name)

    def createDownloadHierarchy(self, tree_item, download_dict):
        for child in self.tree.get_children(tree_item):
            child_name = self.hierarchy.get(child).getName()
            try:
                download_dict[child_name].append(self.hierarchy.get(child))
            except:
                self.createDownloadHierarchy(child, download_dict)

    def download(self, node_list, level_identifier):
        win = tkinter.Toplevel()
        win.wm_title("Info")
        l = tkinter.Label(win, text="Downloading the following processing level: " + level_identifier)
        l.pack()
        prog = ttk.Progressbar(win)
        prog.pack()
        self.log_writer.writeLog("INFO", "Downloading the following processing level: " + level_identifier)

        sensor_dict = {'FULL': {}, 'FLUO': {}}
        level_identifier = level_identifier

        # target = {'name': [], 'time': [], 'signal': [], 'id': [], 'metadata': [], 'temp_files': []}
        # reference = {'name': [], 'time': [], 'signal': [], 'id': [], 'metadata': [], 'temp_files': []}

        if level_identifier == "DN" or level_identifier == "Radiance":
            sensor_dict.get("FULL")['target'] = []
            sensor_dict.get("FLUO")['target'] = []
            sensor_dict.get("FULL")['reference'] = []
            sensor_dict.get("FLUO")['reference'] = []
        else:
            sensor_dict.get("FULL")['target'] = []
            sensor_dict.get("FLUO")['target'] = []

        for i, node in enumerate(node_list):
            self.log_writer.writeLog("INFO", "Downloading the following node: " + str(node.getId()))
            # update progress bar
            prog['value'] = (float(i) / len(node_list)) * 100
            self.master_frame.update_idletasks()

            # get spectrum_ids
            spectrum_ids = self.specchio_client.getSpectrumIdsForNode(node)

            # get the spaces corresponding to these spectra\n",
            spaces = self.specchio_client.getSpaces(spectrum_ids, 'Acquisition Time')

            for space in spaces:
                # Get the spectrum ids belonging to this space
                space_ids = space.getSpectrumIds()
                # load the space
                this_space = self.specchio_client.loadSpace(space)
                space_wvl = this_space.getAverageWavelengths()

                if(space_wvl[0] < 400):
                    sensor_identifier = "FULL"
                else:
                    sensor_identifier = "FLUO"

                target = {'name': [], 'time': [], 'signal': [], 'id': [], 'metadata': [], 'temp_files': []}
                reference = {'name': [], 'time': [], 'signal': [], 'id': [], 'metadata': [], 'temp_files': []}

                # Download the data:
                vectors = this_space.getVectors()
                names = self.specchio_client.getMetaparameterValues(space_ids, 'File Name')
                timings = self.specchio_client.getMetaparameterValues(space_ids, 'Acquisition Time (UTC)')

                for i in range(vectors.size()):
                    try:
                        t = dt.datetime.strptime(timings.get(i).toString(), '%Y-%m-%dT%H:%M:%S.%fZ')
                    except:
                        continue
                    vector = np.array(vectors.get(i))
                    name = names.get(i)
                    # Used to split up the data into incoming and reflected \n",
                    is_target = False
                    if(re.search("VEG*", name)):
                        is_target = True

                    if (is_target):
                        # sensor_dict.get(sensor_identifier).get('target').get("signal").append(vector)
                        # sensor_dict.get(sensor_identifier).get('target').get("time").append(t)
                        target["signal"].append(vector)
                        target["time"].append(t)
                        # target["name"].append(name)
                    else:
                        # sensor_dict.get(sensor_identifier).get('reference').get("signal").append(vector)
                        # sensor_dict.get(sensor_identifier).get('reference').get("time").append(t)
                        reference["signal"].append(vector)
                        reference["time"].append(t)
                        # reference["name"].append(name)

                # Create Xarray dataset:
                file_name = self.dw_path + "/" + level_identifier + '_' + sensor_identifier + '_' + str(node.getId()) + '_target.nc'
                ds_target = self.to_xarray(target.get('signal'),
                                           target.get('time'),
                                           space_wvl, 'target', level_identifier)
                # sensor_dict.get(sensor_identifier).get('target').get('temp_files').append(file_name)
                sensor_dict.get(sensor_identifier).get('target').append(file_name)
                ds_target.to_netcdf(file_name)
                ds_target.close()

                if level_identifier == "DN" or level_identifier == "Radiance":
                    file_name = self.dw_path + "/" + level_identifier + '_' + sensor_identifier + '_' + str(node.getId()) + '_reference.nc'
                    ds_reference = self.to_xarray(reference.get('signal'),
                                           reference.get('time'),
                                           space_wvl, 'reference', level_identifier)
                    sensor_dict.get(sensor_identifier).get('reference').append(file_name)
                    ds_reference.to_netcdf(file_name)
                    ds_reference.close()

        for sensor in sensor_dict:
            for mtype in sensor_dict.get(sensor):
                if len(sensor_dict.get(sensor).get(mtype)) > 0:
                    filename = self.dw_path + "/" + level_identifier + '_' + sensor + '_' + mtype
                    self.combine_datasets(sensor_dict.get(sensor).get(mtype), filename)

        win.destroy()

    def to_xarray(self, signal, time, wvl, variable_name, processing_level):
        dataset = xr.DataArray(signal, coords=[time, wvl], dims=['time', 'wavelength'], name=variable_name)
        dataset["wavelength"].attrs["units"] = "nm"
        dataset["wavelength"].attrs["long_name"] = "Wavelength"
        if processing_level == "DN":
            dataset.attrs["units"] = "Digital Number"
            dataset.attrs["long_name"] = variable_name
        elif processing_level == "Radiance":
            dataset.attrs["units"] = "$W^{1}m^{-2}nm^{-1}sr^{-1}$"
            dataset.attrs["long_name"] = variable_name
        elif processing_level == "Reflectance":
            dataset.attrs["units"] = "a.u."
            dataset.attrs["long_name"] = "Reflectance"
        else:
            dataset.attrs["units"] = "$mW^{1}m^{-2}nm^{-1}sr^{-1}$"
            dataset.attrs["long_name"] = "F"

        return dataset

    def combine_datasets(self, file_list, filename):
        dataset = xr.open_mfdataset(file_list, combine='nested', concat_dim='time')
        grouping_factor = "time.season"
        n_months = len(dataset.groupby('time.month').groups)
        n_years = len(dataset.groupby('time.year').groups)
        if n_years > 1:
            grouping_factor = "time.year"
        elif n_months < 6:
            grouping_factor = "time.month"
        self.save_to_disk(dataset, grouping_factor, filename)
        dataset.close()
        self.clean_temporary_files(file_list)

    def clean_temporary_files(self, temp_files):
        [os.remove(file) for file in temp_files]

    def save_to_disk(self, dataset,  grouping_factor, filename):
        iternums, datasets = zip(*dataset.groupby(grouping_factor))
        filenames = [filename + '_' + str(it) + '.nc' for it in iternums]
        xr.save_mfdataset(datasets, filenames)