class Parachute:
    def __init__(self, surface_area, drag_coefficient, inflation_time, deployment_altitude=0):
        self.surface_area = surface_area
        self.start_surface_area = 0
        self.drag_coefficient = drag_coefficient
        self.deployment_altitude = deployment_altitude
        self.inflation_time = inflation_time
        self.DeployTime = 0
        self.DeployStatus = False

    def cross_area(self, time):
        if time - self.DeployTime > self.inflation_time:
            return self.surface_area, .5
        else:
            return (self.start_surface_area + ((self.surface_area - self.start_surface_area) / self.inflation_time) *
                    (time - self.DeployTime)), .025
