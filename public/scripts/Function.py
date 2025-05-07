# class to hold information about a function invocation while it is in the queue
class Function:
    def __init__(self,
            func_name,
            invoke_time,
            runtime,
            scheduled_time,
            mem_size    
        ):
        self.func_name = func_name
        self.invoke_time = invoke_time
        self.runtime = runtime
        self.scheduled_time = scheduled_time # this represents when the function will actually start running
        self.mem_size = mem_size

    def getFinishTime(self):
        return self.scheduled_time + self.runtime
    
    def getLatency(self):
        # print(self.scheduled_time,", ",self.runtime, ", ", self.invoke_time, " = ", self.scheduled_time + self.runtime - self.invoke_time)
        return self.scheduled_time + self.runtime - self.invoke_time
    
    def getDelay(self):
        return self.scheduled_time - self.invoke_time
        # if self.runtime == 0:
        #     return 0
        # return(self.scheduled_time - self.invoke_time) / self.runtime