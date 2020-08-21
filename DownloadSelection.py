class DownloadSelection:

    def __init__(self, spectrum_ids, specchio_client):
        self.selected_spectra = spectrum_ids
        self.specchio_client = specchio_client

    def 