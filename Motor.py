class Motor:
    def __init__(self, wet_mass, burn_time, mean_thrust):
        self.wet_mass = wet_mass
        self.burn_time = burn_time
        self.mean_thrust = mean_thrust

    def mass(self,time):
        if time <= self.burn_time:
            return self.wet_mass-(self.wet_mass/self.burn_time)*time
        else:
            return 0

    def thrust(self,time):
        if time <= self.burn_time:
            return self.mean_thrust
        else:
            return 0
