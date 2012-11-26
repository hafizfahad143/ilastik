from lazyflow.graph import OperatorWrapper

class OperatorSubView(object):
    """
    An adapter class that makes a specific lane of a multi-image operator look like a single image operator.
    """
    
    def __init__(self, op, index):
        self.__op = op
        self.__index = index
        self.__slots = {}
        self.__slots.update(op.inputs)
        self.__slots.update(op.outputs)
        
    def __getattribute__(self, name):
        try:
            # If we have this attr, return it.
            return object.__getattribute__(self, name)
        except:
            # If it's a slot, return that.
            if name in self.__slots.keys():
                slot = self.__slots[name]
                if slot.level >= 1:
                    return slot[self.__index]
                else:
                    return slot

            # Special case for OperatorWrappers: Get the member from the appropriate inner operator.
            if isinstance(self.__op, OperatorWrapper):
                return getattr(self.__op.innerOperators[self.__index], name)

            # Get the member from the operator directly.
            return getattr(self.__op, name)

if __name__ == "__main__":
    from lazyflow.graph import Graph, Operator, InputSlot, OutputSlot

    class OpSum(Operator):
        InputA = InputSlot()
        InputB = InputSlot()
    
        Output = OutputSlot()
        
        def __init__(self, *args, **kwargs):
            super(OpSum, self).__init__(*args, **kwargs)
            self.hello = "Heya heya"
    
        def setupOutputs(self):
            assert self.InputA.meta.shape == self.InputB.meta.shape, "Can't add images of different shapes!"
            self.Output.meta.assignFrom(self.InputA.meta)
    
        def execute(self, slot, subindex, roi, result):
            a = self.InputA.get(roi).wait()
            b = self.InputB.get(roi).wait()
            result[...] = a+b
            return result
    
        def propagateDirty(self, dirtySlot, subindex, roi):
            self.Output.setDirty(roi)
    
    class OpMultiThreshold(Operator):
        ThresholdLevel = InputSlot()
        Inputs = InputSlot(level=1)
        Outputs = OutputSlot(level=1)
    
        def __init__(self, *args, **kwargs):
            super(OpMultiThreshold, self).__init__(*args, **kwargs)
            self.hello = "Heya"
    
        def setupOutputs(self):
            self.Outputs.resize( len(self.Inputs) )
            for i in range( len(self.Inputs) ):
                self.Outputs[i].meta.assignFrom(self.Inputs[i].meta)
                self.Outputs[i].meta.dtype = numpy.uint8
    
        def execute(self, slot, subindex, roi, result):
            assert len(subindex) == 1
            index = subindex[0]
            thresholdLevel = self.ThresholdLevel.value
            inputData = self.Inputs[index].get(roi).wait()
            result[...] = inputData > thresholdLevel
            return result
    
        def propagateDirty(self, dirtySlot, subindex, roi):
            self.Outputs[subindex].setDirty(roi)


    graph = Graph()
    opWrappedSum = OperatorWrapper( OpSum, graph=graph )
    opWrappedSum.InputA.resize(3)
        
    subView0 = OperatorSubView(opWrappedSum, 0)
    assert subView0.InputA == opWrappedSum.InputA[0]
    assert subView0.InputB == opWrappedSum.InputB[0]
    assert subView0.Output == opWrappedSum.Output[0]
    assert subView0.hello == opWrappedSum.innerOperators[0].hello
    
    subView1 = OperatorSubView(opWrappedSum, 1)
    assert subView1.InputA == opWrappedSum.InputA[1]
    assert subView1.InputB == opWrappedSum.InputB[1]
    assert subView1.Output == opWrappedSum.Output[1]
    assert subView1.hello == opWrappedSum.innerOperators[1].hello
    
    opMultiThreshold = OpMultiThreshold(graph=graph)
    opMultiThreshold.Inputs.resize(3)
    opMultiThreshold.Outputs.resize(3)
    
    subThresholdView = OperatorSubView( opMultiThreshold, 1 )
    
    assert subThresholdView.Inputs == opMultiThreshold.Inputs[1]
    assert subThresholdView.Outputs == opMultiThreshold.Outputs[1]
    assert subThresholdView.hello == opMultiThreshold.hello

