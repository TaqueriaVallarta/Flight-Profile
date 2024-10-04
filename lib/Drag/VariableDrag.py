from lib.Drag.DragSetup import DragSetup

class DragForce: 
    def __init__(self, DragCoeff, prevelocity, predrag, crossArea, density):
        prevelocity = 1.9
        predrag = 10
        DragCoeff = DcoeffCalc
        crossArea = self.crossArea
        density = self.density

def DcoeffCalc(DragCoeff, prevelocity, predrag, crossArea, density):
        DragCoeff = ((density*(prevelocity^2)*crossArea)/(2*predrag))
        return DragCoeff

print(DcoeffCalc)
