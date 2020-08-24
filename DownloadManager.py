import LogWriter as lw
import xarray as xr
import numpy as np
import tkinter
import tkinter.ttk as ttk
import datetime as dt
import re


class DownloadManager:

    def __init__(self, types, specchio_client, node, item, download_path, stop_hierarchy, tree, hierarchy, master_frame):
        self.types = types
        self.selected_node = node
        self.selected_item = item
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
            self.download_hierarchy[name]=[]
        # Write start information
        if isinstance(self.selected_node, self.types.campaign_node):
            self.log_writer.writeLog("INFO", "Starting download for the following camapign: " + self.selected_node.getName())
        else:
            self.log_writer.writeLog("INFO", "Starting download for the following hierarchy: " + self.selected_node.getName())
        # Fill download hierarchy information
        self.createDownloadHierarchy(self.selected_item, self.download_hierarchy)
        for key in self.download_hierarchy:
            self.download(self.download_hierarchy.get(key), key)

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

        temporary_target_files = []
        temporary_reference_files = []

        level_identifier = level_identifier

        for i, node in enumerate(node_list):
            self.log_writer.writeLog("INFO", "Downloading the following node: " + node.getName())
            # update progress bar
            prog['value'] = (float(i) / len(node_list)) * 100
            self.master_frame.update_idletasks()

            # get spectrum_ids
            spectrum_ids = self.specchio_client.getSpectrumIdsForNode(node)

            # get the spaces corresponding to these spectra\n",
            spaces = self.specchio_client.getSpaces(spectrum_ids, 'Acquisition Time')

            for space in spaces:

                target = {'name': [], 'time': [], 'signal': [], 'id': [], 'metadata': []}
                reference = {'name': [], 'time': [], 'signal': [], 'id': [], 'metadata': []}


                # Get the spectrum ids belonging to this space
                space_ids = space.getSpectrumIds()
                # load the space
                this_space = self.specchio_client.loadSpace(space)
                space_wvl = this_space.getAverageWavelengths()

                if(space_wvl[0] < 400):
                    sensor_identifier = "FULL"
                else:
                    sensor_identifier = "FLUO"

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
                        target["signal"].append(vector)
                        # target["name"].append(name)
                        target["time"].append(t)
                    else:
                        reference["signal"].append(vector)
                        # reference["name"].append(name)
                        reference["time"].append(t)

                # Create Xarray dataset:
                file_name = self.dw_path + "/" + level_identifier + '_' + sensor_identifier + '_target.nc'
                ds_target = self.to_xarray(target["signal"], target["time"], space_wvl, 'target')
                temporary_target_files.append(file_name)
                ds_target.to_netcdf(file_name)

                file_name = self.dw_path + "/" + level_identifier + '_' + sensor_identifier + '_reference.nc'
                ds_reference = self.to_xarray(reference["signal"], reference["time"], space_wvl, 'reference')
                temporary_reference_files.append(file_name)
                ds_reference.to_netcdf(file_name)

        filename = self.dw_path + "/" + level_identifier + '_' + sensor_identifier + '_target'
        self.combine_datasets(temporary_target_files, filename)
        filename = self.dw_path + "/" + level_identifier + '_' + sensor_identifier + '_reference'
        self.combine_datasets(temporary_reference_files)

        win.destroy()

    def to_xarray(self, signal, time, wvl, variable_name):
        dataset = xr.DataArray(signal, coords=[time, wvl], dims=['time','wavelength'], name=variable_name)
        dataset["wavelength"].attrs["units"] = "nm"
        dataset["wavelength"].attrs["long_name"] = "Wavelength"
        dataset[variable_name].attrs["units"] = "$W^{1}m^{-2}nm^{-1}sr^{-1}$"
        dataset[variable_name].attrs["long_name"] = variable_name
        return dataset

    def combine_datasets(self, file_list, filename):
        dataset = xr.open_mfdataset(file_list, combine = 'nested', concat_dim = 'time')
        grouping_factor = "time.season"
        n_months = len(dataset.groupby('time.month').groups)
        n_seasons = len(dataset.groupby('time.season').groups)
        n_years = len(dataset.groupby('time.year').groups)
        if n_years > 1:
            grouping_factor = "time.year"
        elif n_months < 6:
            grouping_factor = "time.month"
        self.save_to_disk(dataset, grouping_factor, filename)

    def save_to_disk(self, dataset,  grouping_factor, filename):
        iternums, datasets = zip(*dataset.groupby(grouping_factor))
        filenames = [filename + '_' + str(it) + '.nc' for it in iternums]
        xr.save_mfdataset(datasets, filenames)