class Motor:
    def __init__(self, wet_mass, burn_time, impulse):
        self.wet_mass = wet_mass
        self.burn_time = burn_time
        self.impulse = impulse

    # Uses constant mass flow rate
    def mass(self, time):
        if time <= self.burn_time:
            return self.wet_mass - ((self.wet_mass / self.burn_time) * time)
        else:
            return 0

    # todo: make thrust somewhat normal (may add thrust curve?)
    def thrust(self, time):
        if time <= self.burn_time:
            return self.impulse / self.burn_time
        else:
            return 0
