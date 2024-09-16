class Parachute:
    def __init__(self, surface_area, drag_coefficient, inflation_time, deployment_altitude = 0):
        self.surface_area = surface_area
        self.drag_coefficient = drag_coefficient
        self.deployment_altitude = deployment_altitude
        self.time = 0
        self.inflation_time = inflation_time

    def cross_area(self, dt):
        self.time += dt
        return (self.surface_area/self.inflation_time)*(self.time-dt)