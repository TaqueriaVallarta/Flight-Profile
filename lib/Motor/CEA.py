from rocketcea.cea_obj import CEA_Obj, add_new_fuel, add_new_oxidizer, add_new_propellant

from math import sqrt
chamber_pressure = 425
ideal_OF_ratio = 6.5
def V_eq():
    pc_ov_pe = chamber_pressure/exit_pressure
    eps = ispObj.get_eps_at_PcOvPe(chamber_pressure, ideal_OF_ratio, pc_ov_pe)
    def equivalent_exit_velocity(ambient_pressure, OF_ratio, contratction_ratio):
        Isp = ispObj.estimate_Ambient_Isp(chamber_pressure, MR=OF_ratio, eps=eps, Pamb=ambient_pressure)
        v_eq = Isp*9.81
        return v_eq
