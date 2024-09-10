import DragSetup
from DragSetup import Atmosphere, DragSetup, drag_force
from Motor import Motor


# Self-Explanatory
def inches_to_meters(inches):
    return (inches * 2.54) / 100


class Rocket:
    def __init__(self, drag_setup: DragSetup, motor: Motor, dry_mass, initial_height_asl=0):
        self.drag_setup = drag_setup  # drag setup class
        self.motor = motor  # motor class
        self.dry_mass = dry_mass  # dry mass in kg
        self.initial_height_asl = initial_height_asl  # Initial Height in m ASL
        self.height_agl = 0  # height above ground level
        self.height_asl = initial_height_asl  # height above ground level
        self.velocity = 0
        self.gravity = self.drag_setup.atmosphere.g

    def mass(self, time):
        return self.dry_mass+self.motor.mass(time)

    def acceleration(self, height, velocity, time):
        drag = self.drag_setup.calculate_drag_force(velocity, height)
        thrust = self.motor.thrust(time)
        weight = -self.gravity*self.mass(time)
        force = drag+thrust+weight
        return force/self.mass(time)


# initializes all the values
def initialize():
    fin_thickness = inches_to_meters(.5)
    fin_height = inches_to_meters(12)
    drag_coef = .5

    # Initializes with 8" body tube
    drag_setup = DragSetup(fin_thickness, fin_height, drag_coef)

    wet_mass = 20  # Kilograms
    burn_time = 20  # Seconds
    mean_thrust = 4000  # Newtons
    motor = Motor(wet_mass, burn_time, mean_thrust)

    dry_mass = 80  # Kilograms
    return Rocket(drag_setup, motor, dry_mass)


# rk4 program, takes in the values and acceleration as a function
def rk4_step(height, velocity, acceleration, dt, t):
    """
    Perform a single step of the RK4 method.

    Args:
    height: float - Initial position.
    velocity: float - Initial velocity.
    acceleration: function - Function to compute acceleration a(height, velocity, t).
    dt: float - Time step size.
    t: float - Current time.

    Returns:
    tuple - (new position, new velocity)
    """
    # k1 values for position and velocity
    k1x = velocity
    k1v = acceleration(height, velocity, t)

    # k2 values for position and velocity
    k2x = velocity + 0.5 * dt * k1v
    k2v = acceleration(height + 0.5 * dt * k1x, velocity + 0.5 * dt * k1v, t + 0.5 * dt)

    # k3 values for position and velocity
    k3x = velocity + 0.5 * dt * k2v
    k3v = acceleration(height + 0.5 * dt * k2x, velocity + 0.5 * dt * k2v, t + 0.5 * dt)

    # k4 values for position and velocity
    k4x = velocity + dt * k3v
    k4v = acceleration(height + dt * k3x, velocity + dt * k3v, t + dt)

    # Compute new position and velocity
    new_x = height + (dt / 6) * (k1x + 2 * k2x + 2 * k3x + k4x)
    new_v = velocity + (dt / 6) * (k1v + 2 * k2v + 2 * k3v + k4v)

    return new_x, new_v


if __name__ == '__main__':
    print("Height", ",", "Velocity", ",",
          "Acceleration", ",",
          "Time", ",", "Mass", ",",
          "Drag Force")
    rocket = initialize()
    current_time = 0
    time_step = .1
    while rocket.height_agl >= 0:
        rocket.height_asl, rocket.velocity = rk4_step(rocket.height_asl, rocket.velocity,
                                                      rocket.acceleration, time_step, current_time)
        rocket.height_agl = rocket.height_asl - rocket.initial_height_asl

        print(rocket.height_agl,",", rocket.velocity, ",", rocket.acceleration(rocket.height_agl,rocket.velocity,current_time), ",",
              current_time, ",", rocket.mass(current_time), ",", rocket.drag_setup.calculate_drag_force(rocket.velocity, rocket.height_agl))

        current_time += time_step

