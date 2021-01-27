import LogWriter as lw
import xarray as xr
import numpy as np
import tkinter
import tkinter.ttk as ttk
import datetime as dt
import re
import os
import _thread


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
        self.all_meta = ['Integration Time', 'Optical Compartment Humidity', 'Optical Compartment Temperature',
                            'PCB Humidity', 'PCB Temperature', 'Spectrometer Frame Temperature', 'Irradiance Instability', 
                            'Saturation Count', 'f_SpecFit_A', 'f_SpecFit_B', 'f_int', 'f_max_FR', 'f_max_FR_wvl', 
                            'f_max_R', 'f_max_R_wvl']
        self.all_meta_level = {'DN': self.all_meta[0:7], 'Radiance': self.all_meta[0:8],
                               'Reflectance': self.all_meta[0:8], 'SpecFit': self.all_meta}


    def startDownload(self):
        # Downloadable hierarchies are:
        self.download_hierarchy = {}
        for name in self.stop_hierarchy:
            self.download_hierarchy[name] = []
        # Fill download hierarchy information
        for item in self.selected_items:
            self.createDownloadHierarchy(item, self.download_hierarchy)

        self.win = tkinter.Toplevel()
        self.win.wm_title("Info")

        # Frame
        self.select_meta = tkinter.LabelFrame(self.win)
        self.select_meta["text"] = "Please chose metadata"
        self.select_meta.pack(side="right", padx=5, pady=5, expand=True)
        self.chosen_meta = []
        self.meta_vars = []
        self.meta_checks = []
        for mp in self.all_meta:
            var = tkinter.BooleanVar()
            var.set(False)
            check = tkinter.Checkbutton(self.select_meta)
            check["text"] = mp
            check["command"] = self.handle_meta_selection
            check["variable"] = var
            check.pack(anchor="w")
            self.meta_checks.append(check)
            self.meta_vars.append(var)

        # Frame
        self.select_levels = tkinter.LabelFrame(self.win)
        self.select_levels["text"] = "Please chose processing level(s)"
        self.select_levels.pack(side="right", padx=5, pady=5, expand=True)
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
        okbtn.pack(side="bottom", padx=5, pady=5, expand=True)
        okbtn["text"] = "OK"
        okbtn["state"] = tkinter.ACTIVE
        okbtn["command"] = self.destroy_and_download

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
        if len(self.chosen_levels) > 1:
            for name in self.chosen_levels:
                self.download(self.download_hierarchy.get(name), name)
        else:
            _thread.start_new_thread(self.download, (self.download_hierarchy.get(self.chosen_levels[0]), self.chosen_levels[0]))

    def createDownloadHierarchy(self, tree_item, download_dict):
        for child in self.tree.get_children(tree_item):
            child_name = self.hierarchy.get(child).getName()
            try:
                if self.hierarchy.get(child) not in download_dict[child_name]:
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

        if level_identifier == "DN" or level_identifier == "Radiance":
            sensor_dict.get("FULL")['target'] = {'pickle_names': [], 'xarray_names': []}
            sensor_dict.get("FLUO")['target'] = {'pickle_names': [], 'xarray_names': []}
            sensor_dict.get("FULL")['reference'] = {'pickle_names': [], 'xarray_names': []}
            sensor_dict.get("FLUO")['reference'] = {'pickle_names': [], 'xarray_names': []}
        else:
            sensor_dict.get("FULL")['target'] = {'pickle_names': [], 'xarray_names': []}
            sensor_dict.get("FLUO")['target'] = {'pickle_names': [], 'xarray_names': []}

        for i, node in enumerate(node_list):
            parent = self.specchio_client.getHierarchyParentId(node.getId())
            parent_name = self.specchio_client.getHierarchyName(parent)
            self.log_writer.writeLog("INFO", "Downloading the following node: " + str(parent_name)) # this does not make sense because the node id is not visible to the user!
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

                target = {'name': [], 'time': [], 'signal': [], 'id': [], 'temp_files': [], 'metadata': {}}
                reference = {'name': [], 'time': [], 'signal': [], 'id': [], 'temp_files': [], 'metadata': {}}

                # Download the data:
                vectors = this_space.getVectors()
                names = self.specchio_client.getMetaparameterValues(space_ids, 'File Name')
                timings = self.specchio_client.getMetaparameterValues(space_ids, 'Acquisition Time (UTC)')

                # Download metadata:
                metadata = {}
                for mp in self.chosen_meta:
                    if mp in self.all_meta_level.get(level_identifier):
                        metadata[mp] = self.specchio_client.getMetaparameterValues(space_ids, mp)
                        target.get("metadata")[mp] = []
                        reference.get("metadata")[mp] = []

                for j in range(vectors.size()):
                    try:
                        t = dt.datetime.strptime(timings.get(j).toString(), '%Y-%m-%dT%H:%M:%S.%fZ')
                    except:
                        continue
                    vector = np.array(vectors.get(j))
                    name = names.get(j)

                    # Used to split up the data into incoming and reflected \n",
                    is_target = False
                    if(re.search("VEG*", name)):
                        is_target = True

                    if (is_target):
                        target["signal"].append(vector)
                        target["time"].append(t)
                        target["name"].append(name)
                        for key in metadata:
                            if metadata.get(key).get(j) == None:
                                target.get("metadata")[key].append(np.nan)
                            elif float(metadata.get(key).get(j)) == -999.0:
                                target.get("metadata")[key].append(np.nan)
                            else:
                                target.get("metadata")[key].append(metadata.get(key).get(j))
                                # print(metadata.get(key).get(j))

                    else:
                        reference["signal"].append(vector)
                        reference["time"].append(t)
                        reference["name"].append(name)
                        for key in metadata:
                            reference.get("metadata")[key].append(metadata.get(key).get(j))

                # Always add the filename as metadata element
                target.get("metadata")['File Name'] = target["name"]
                reference.get("metadata")['File Name'] = reference["name"]

                # Create Xarray dataset:
                file_name = self.dw_path + "/" + level_identifier + '_' + sensor_identifier + '_' + str(parent_name) + '_target.nc'
                ds_target = self.to_xarray(target.get('signal'),
                                           target.get('time'),
                                           target.get('metadata'),
                                           space_wvl, 'target', level_identifier)
                sensor_dict.get(sensor_identifier).get('target').get('xarray_names').append(file_name)
                ds_target.to_netcdf(file_name)
                ds_target.close()

                if level_identifier == "DN" or level_identifier == "Radiance":
                    file_name = self.dw_path + "/" + level_identifier + '_' + sensor_identifier + '_' + str(parent_name) + '_reference.nc'
                    ds_reference = self.to_xarray(reference.get('signal'),
                                           reference.get('time'),
                                           reference.get('metadata'),
                                           space_wvl, 'reference', level_identifier)
                    sensor_dict.get(sensor_identifier).get('reference').get('xarray_names').append(file_name)
                    ds_reference.to_netcdf(file_name)
                    ds_reference.close()

        for sensor in sensor_dict:
            for mtype in sensor_dict.get(sensor):
                filename = self.dw_path + "/" + level_identifier + '_' + sensor + '_' + mtype
                if len(sensor_dict.get(sensor).get(mtype).get('xarray_names')) > 0:
                    self.combine_datasets(sensor_dict.get(sensor).get(mtype).get('xarray_names'), filename)

        win.destroy()

    def to_xarray(self, signal, time, metadata, wvl, variable_name, processing_level):
        dataset = xr.DataArray(signal, coords=[time, wvl], dims=['time', 'wavelength'], name=variable_name)
        dataset["wavelength"].attrs["units"] = "nm"
        dataset["wavelength"].attrs["long_name"] = "Wavelength"
        dataset = dataset.to_dataset()
        for metaparameter in metadata:
            dataset[metaparameter] = (['time'], metadata.get(metaparameter))
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
        for file in temp_files:
            try:
                os.remove(file)
            except:
                print("File not found.")

    def save_to_disk(self, dataset,  grouping_factor, filename):
        iternums, datasets = zip(*dataset.groupby(grouping_factor))
        filenames = [filename + '_' + str(it) + '.nc' for it in iternums]
        xr.save_mfdataset(datasets, filenames)