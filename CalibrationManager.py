from tkinter import filedialog
import xarray as xr
import numpy as np
import tkinter
from Calibration import Calibration
from Sample import Sample
import re
import os
import pandas as pd

class CalibrationManager:
    def __init__(self, data_path, cal_path, master_frame):
        self.dpath = data_path
        self.cpath = cal_path
        self.cname = os.path.basename(self.cpath)
        self.myframe = master_frame
        ## calibration file:
        p = re.compile('[J][B][-][0-9]{3,}')
        self.box_name = p.findall(self.cname)[0]
        p = re.compile('(((19|20)([2468][048]|[13579][26]|0[48])|2000)[/-]02[/-]29|((19|20)[0-9]{2}[/-](0[4678]|1[02])[/-](0[1-9]|[12][0-9]|30)|(19|20)[0-9]{2}[/-](0[1359]|11)[/-](0[1-9]|[12][0-9]|3[01])|(19|20)[0-9]{2}[/-]02[/-](0[1-9]|1[0-9]|2[0-8])))')
        self.cal_date = p.findall(self.cname)[0][0]
        p = re.compile('NL')
        self.is_nl = True if len(p.findall(self.cname)) > 0 else False
        self.box_name_lab = tkinter.Label(self.myframe, text=self.box_name)
        self.box_name_lab.pack()
        self.box_cal_date_lab = tkinter.Label(self.myframe, text=self.cal_date)
        self.box_cal_date_lab.pack()
        self.box_is_nl_lab = tkinter.Label(self.myframe, text='Non-linearity correction = ' + str(self.is_nl))
        self.box_is_nl_lab.pack()
        self.cal_btn = tkinter.Button(self.myframe, text='Calibrate', command=self.calibrate_now, state='disabled')
        self.cal_btn.pack()
        self.full_files, self.fluo_files = self.list_files()
        self.display_files()

    def list_files(self):
        full_csv = []
        fluo_csv = []
        full_pattern = re.compile('^\w\d{6}')
        fluo_pattern = re.compile('^\d{6}')
        for path, dirs, files in os.walk(self.dpath):
            for filename in files:
                file = os.path.join(path, filename)
                if filename.endswith(".CSV"):
                    if full_pattern.search(filename):  # files for the FULL sensor contain "F"
                        full_csv.append(file)
                    elif fluo_pattern.search(filename):
                        fluo_csv.append(file)  # files for the FLUO sensor

        return full_csv, fluo_csv

    def display_files(self):
        self.full_frame = tkinter.LabelFrame(self.myframe, text='FULL files')
        self.full_frame.pack(side=tkinter.BOTTOM)
        self.fluo_frame = tkinter.LabelFrame(self.myframe, text='FLUO files')
        self.fluo_frame.pack(side = tkinter.BOTTOM)

        self.full_scroll_h = tkinter.Scrollbar(self.full_frame, orient='horizontal')
        self.full_scroll_h.pack(side=tkinter.BOTTOM, fill=tkinter.X)

        self.fluo_scroll_h = tkinter.Scrollbar(self.fluo_frame, orient='horizontal')
        self.fluo_scroll_h.pack(side=tkinter.BOTTOM, fill=tkinter.X)

        self.full_scroll_v = tkinter.Scrollbar(self.full_frame)
        self.full_scroll_v.pack(side=tkinter.RIGHT, fill=tkinter.Y)

        self.fluo_scroll_v = tkinter.Scrollbar(self.fluo_frame)
        self.fluo_scroll_v.pack(side=tkinter.RIGHT, fill=tkinter.Y)

        self.full_text = tkinter.Text(self.full_frame, xscrollcommand=self.full_scroll_h.set, yscrollcommand=self.full_scroll_v.set)
        for file in self.full_files:
            self.full_text.insert(tkinter.END, file+'\n')
        self.full_text.pack(side=tkinter.TOP, fill=tkinter.X)
        self.full_scroll_h.config(command=self.full_text.xview)
        self.full_scroll_v.config(command=self.full_text.yview)

        self.fluo_text = tkinter.Text(self.fluo_frame, xscrollcommand=self.fluo_scroll_h.set,yscrollcommand=self.fluo_scroll_v.set)
        for file in self.fluo_files:
            self.fluo_text.insert(tkinter.END, file + '\n')
        self.fluo_text.pack(side=tkinter.TOP, fill=tkinter.X)
        self.fluo_scroll_h.config(command=self.fluo_text.xview)
        self.fluo_scroll_v.config(command=self.fluo_text.yview)

        self.cal_btn['state'] = 'normal'

    def calibrate_now(self):
        # Remove previously handled:
        self.remove_handled_files(self.dpath + 'files_handled_FULL.csv', self.full_files)
        self.remove_handled_files(self.dpath + 'files_handled_FLUO.csv', self.fluo_files)

        # Read the calibration file:
        self.cal_fluo, self.cal_full = self.parse_calfile(self.cpath)
        # Create a list with files that need to be deleted at the end of the calibration:
        self.files_to_delete = []

        # Choose where to store the data
        self.storepath = filedialog.askdirectory(title="Please choose the storage location.")

        # iterate the full sensor files:
        self.iterate_files(self.full_files, self.cal_full, 'FULL', self.box_name)

        # iterate the fluo sensor files:
        self.iterate_files(self.fluo_files, self.cal_fluo, 'FLUO', self.box_name)

        # Remove intermediate files:
        for file in self.files_to_delete:
            os.remove(file)

        # Popup-window after completion
        popup = tkinter.Toplevel(bg='green')
        popup.wm_title("Success")
        l = tkinter.Label(popup, bg='green', text="Calibration Complete. \n Files can be found under: \n" + self.storepath)
        l.pack()
        b = tkinter.Button(popup, bg='green', text="Okay", command=popup.destroy)
        b.pack()

    def remove_handled_files(self, path, list):
        try:
            with open(path, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    try:
                        list.remove(line)
                    except IndexError as ie:
                        print(str(ie) + ": not handled")
        except FileNotFoundError as fnfe:
            print(str(fnfe))

        return list

    def parse_calfile(self, calfilepath):
        # data structures
        wl = []
        up_coef = []
        dw_coef = []
        nl_coefs = []
        autonull = 1
        wl_F = []
        up_coef_F = []
        dw_coef_F = []
        nl_coefs_F = []
        autonull_F = 1
        # parsing logic
        is_nl = False
        is_nl_F = False
        is_autonull = False
        # parsing
        with open(calfilepath, 'r') as f:
            lines = f.readlines()
            device_id = lines[1].strip().split(";")[6]
            for line in lines[1:]:
                line = line.strip()
                line = line.split(";")

                wl.append(float(line[0]))
                up_coef.append(float(line[1]))
                dw_coef.append(float(line[2]))
                wl_F.append(float(line[3]))
                up_coef_F.append(float(line[4]))
                dw_coef_F.append(float(line[5]))

                if is_nl:
                    try:
                        nl_coefs.append(float(line[6].replace('"', "")))
                    except:
                        print("couldn't parse element")
                elif is_nl_F:
                    try:
                        nl_coefs_F.append(float(line[6].replace('"', "")))
                    except:
                        print("couldn't parse element")
                elif is_autonull:
                    autonull_F = float(line[6].replace('"', ""))
                    is_autonull = False

                if re.search("QE", line[6]):
                    is_nl = True
                elif re.search("FLAME", line[6]):
                    is_nl_F = True
                    is_nl = False
                elif re.search("Autonulling", line[6]):
                    is_autonull = True
                    is_nl_F = False

        wl = np.array(wl)
        up_coef = np.array(up_coef)
        dw_coef = np.array(dw_coef)
        nl_coefs = np.array(nl_coefs)
        wl_F = np.array(wl_F)
        up_coef_F = np.array(up_coef_F)
        dw_coef_F = np.array(dw_coef_F)
        nl_coefs_F = np.array(nl_coefs_F)

        cal_fluo = Calibration(wl, up_coef, dw_coef, nl_coefs, autonull, device_id, 'FLUO')
        cal_full = Calibration(wl_F, up_coef_F, dw_coef_F, nl_coefs_F, autonull_F, device_id, 'FULL')

        return cal_fluo, cal_full

    def iterate_files(self, file_list, cal_file, sensor, campaign_name):

        for i in range(0, len(file_list)):

            samples = self.parse_rawdata(file_list[i])
            wr_ds, veg_ds = self.calibrate_samples(samples, cal_file)
            filename_accessor = '_' + str(i)
            filename_time = pd.datetime.now()
            format = "%y%m%d_%H%M%S"

            name = self.storepath + '//' + sensor + '_' + 'WR' + '_' + filename_accessor + '_' + filename_time.strftime(format) + '.nc'
            wr_ds.to_netcdf(name)
            self.files_to_delete.append(name)

            name = self.storepath + '//' + sensor + '_' + 'VEG' + '_' + filename_accessor + '_' + filename_time.strftime(format) + '.nc'
            veg_ds.to_netcdf(name)
            self.files_to_delete.append(name)

        wr_ds = xr.open_mfdataset((self.storepath + '//' + sensor + '_' + 'WR' + '*.nc'), combine='nested', concat_dim='time')
        self.save_mf_to_disk(wr_ds, self.storepath, sensor, 'WR', campaign_name)
        wr_ds.close()
        veg_ds = xr.open_mfdataset((self.storepath + '//' + sensor + '_' + 'WR' + '*.nc'), combine='nested', concat_dim='time')
        self.save_mf_to_disk(veg_ds, self.storepath, sensor, 'VEG', campaign_name)
        veg_ds.close()

    def parse_rawdata(self, file):
        samples = []
        with open(file, 'r') as f:
            lines = f.readlines()
            sample_indices = self.figure_out_sample_indices(lines)  # only parsing complete samples (6 rows, metadata + wr1, wr2, veg, dc_wr, dc_veg)
            for i in sample_indices:
                # Metadata
                # print("i = " + str(i))
                metadata = lines[i + 0]
                metadata = metadata.strip()  # we strip the line from the next line indicators to remove empty rows
                metadata = metadata.split(";")  # we want to split the line based on the specified separator ";
                try:
                    sample_nr = int(metadata[0])
                except ValueError as ve:
                    # print(str(ve) + " Sample number not found")
                    continue
                # '2018-05-01 11:29:58'
                date = metadata[1]
                date = '20' + date[0:2] + '-' + date[2:4] + '-' + date[4:6]
                time = metadata[2]
                time = time[0:2] + ':' + time[2:4] + ':' + time[4:6]
                # Other info
                indexes = self.find_metadata_indexes(metadata)
                it_wr = int(metadata[indexes['it_wr']])
                it_veg = int(metadata[indexes['it_veg']])
                device_id = metadata[indexes['device_id']]
                device_id = device_id.split(" ")[2]
                # WR1
                wr_1 = self.read_data_line(lines[i + 1])
                # VEG
                veg = self.read_data_line(lines[i + 2])
                # WR2
                wr_2 = self.read_data_line(lines[i + 3])
                # DC_WR
                dc_wr = self.read_data_line(lines[i + 4])
                # DC_VEG
                dc_veg = self.read_data_line(lines[i + 5])
                if not (len(wr_1) == len(wr_2) == len(veg) == len(dc_wr) == len(dc_veg)):
                    # print('Not all measurements contain the same number of channels!')
                    continue
                this_sample = Sample(wr_1, wr_2, veg, dc_wr, dc_veg, it_wr, it_veg, sample_nr, date, time,
                                     device_id)
                samples.append(this_sample)

        return samples

    def figure_out_sample_indices(self, lines):
        indices = []
        for i, line in enumerate(lines):
            try:
                if re.search("IT_WR", line) and re.search("DC_VEG", lines[i + 5]):
                    indices.append(i)
            except IndexError as ie:
                print(str(ie) + ": incomplete sample")
        return indices

    def find_metadata_indexes(self, metadata):
        indexes = {
            'it_wr': 0,
            'it_veg': 0,
            'device_id': 0
        }
        for i, element in enumerate(metadata):
            if re.search("IT_WR", element):
                indexes['it_wr'] = i + 1
            elif re.search("IT_VEG", element):
                indexes['it_veg'] = i + 1
            elif re.search("FloX", element):
                indexes['device_id'] = i

        return indexes

    def read_data_line(self, line):
        dat = line.strip()
        dat = dat.split(";")
        dat = dat[1:1025]
        dat_np = np.zeros((len(dat)))
        for i in range(len(dat)):
            try:
                dat_np[i] = dat[i]
            except ValueError as ve:
                print(str(ve) + " Problem encountered when reading measurement!")
        return dat_np

    def calibrate_samples(self, samples, calibration):
        time_veg = []
        time_wr = []
        wr = []
        veg = []
        wl = calibration.wl

        for sample in samples:
            try:
                t = pd.to_datetime(sample.date + ' ' + sample.time)
            except:
                t = pd.to_datetime('1991-01-01 00:00:00')
            time_veg.append(t)
            time_wr.append(t)
            time_wr.append(t)
            # print(str(t))
            wr1_cal = self.calibrate(sample.wr_1, sample.dc_wr, sample.it_wr, calibration.up_coef, calibration.nl_coefs,
                                calibration.autonull)
            wr2_cal = self.calibrate(sample.wr_2, sample.dc_wr, sample.it_wr, calibration.up_coef, calibration.nl_coefs,
                                calibration.autonull)
            veg_cal = self.calibrate(sample.veg, sample.dc_veg, sample.it_veg, calibration.dw_coef, calibration.nl_coefs,
                                calibration.autonull)
            wr.append(wr1_cal)
            wr.append(wr2_cal)
            veg.append(veg_cal)

        time_veg = np.array(time_veg)
        time_wr = np.array(time_wr)
        wr = np.array(wr)
        veg = np.array(veg)
        wl = np.array(wl)

        wr_dataset = self.create_xarray(wr, [time_wr, wl], ['time', 'wavelength'], 'wr')
        veg_dataset = self.create_xarray(veg, [time_veg, wl], ['time', 'wavelength'], 'veg')

        return wr_dataset, veg_dataset

    def calibrate(self, signal, dark_current, integration_time, gain, nl_coefs, autonull_factor):
        if not list(nl_coefs):
            dn_subtracted = signal - dark_current
            dn = dn_subtracted / integration_time * 1000
            calibrated = dn * gain
        else:
            # Autonulling
            dc_an = dark_current * autonull_factor
            signal_an = signal * autonull_factor
            # DC Subtraction
            sig = signal_an - dc_an
            # Nonlinearity
            signal_nl = (nl_coefs[7] * (sig ** 7)) + (nl_coefs[6] * (sig ** 6)) + (nl_coefs[5] * (sig ** 5)) + (
                    nl_coefs[4] * (sig ** 4)) + (nl_coefs[3] * (sig ** 3)) + (nl_coefs[2] * (sig ** 2)) + (
                                nl_coefs[1] * sig) + nl_coefs[0]
            signal_nl = sig / signal_nl
            calibrated = (signal_nl / integration_time) * 1000 * gain

        return calibrated

    def create_xarray(self, data, coordinates, dimensions, data_name):
        ds = xr.DataArray(data, coords=coordinates, dims=dimensions, name=data_name)
        ds = ds.to_dataset()
        ds['wavelength'].attrs["units"] = "nm"
        ds['wavelength'].attrs["long_name"] = "Wavelength"
        ds['time'].attrs['long_name'] = "Time"
        ds[data_name].attrs["units"] = "$W^{1}m^{-2}nm^{-1}sr^{-1}$"
        ds[data_name].attrs["long_name"] = "Radiance (" + data_name + ")."
        ds.attrs["Comment"] = "Created by the python fluospecchio application calibration process, www.rsws.ch"

        return ds

    def save_mf_to_disk(self, ds, outdir, sensor, mtype, campaign_name):
        grouping_factor = "time.season"
        nr_months = (len(ds.groupby('time.month').groups))
        nr_seasons = (len(ds.groupby('time.season').groups))
        nr_years = (len(ds.groupby('time.year').groups))
        if nr_years > 1:
            grouping_factor = "time.year"
        elif nr_months < 6:
            grouping_factor = "time.month"

        folder_name = outdir + '\\' + sensor + "\\" + mtype + "\\"
        os.makedirs(folder_name, exist_ok=True)
        grouping_name = grouping_factor.split(".")[1]
        iternums, datasets = zip(*ds.groupby(grouping_factor))
        paths = [folder_name + campaign_name + "_" + sensor + "_" + mtype + "_" + grouping_name + "_" + str(it) + ".nc" for
                 it in iternums]
        xr.save_mfdataset(datasets, paths)
