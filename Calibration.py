class Calibration:

    def __init__(self, wl, up_coef, dw_coef, nl_coefs, autonull, device_id, cal_type):
        self.wl = wl
        self.up_coef = up_coef
        self.dw_coef = dw_coef
        self.nl_coefs = nl_coefs
        self.autonull = autonull
        self.device_id = device_id
        self.cal_type = cal_type
