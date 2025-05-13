from Histogram import Histogram
from Function import Function
import uuid
import math

from enum import Enum

class VM_STATUS(Enum):
    OVERLOADED = 1
    COLD_START = 2
    COLD_START_FUNCTION_UNLOADED = 3
    WARM_START = 4
    PENDING_EVICTION = 5

class FUNCTION_TIMESTAMP_TYPE(Enum):
    FUNCTION_START = 1
    FUNCTION_END = 2
class FunctionTimestamp:
    def __init__(self, ts, type):
        self.ts = ts
        self.type = type
    def __str__(self):
        if self.type == FUNCTION_TIMESTAMP_TYPE.FUNCTION_START:
            return "func started at "+ str(self.ts)
        else:
            return "func ended at "+ str(self.ts)

class FunctionInfo:
    def __init__(self, loaded, mem_size):
        self.loaded = loaded
        self.mem_size = mem_size

class PendingVM:
    def __init__(self, config, app_name, ts):
        self.config = config
        self.function_queue = []
        self.app_name = app_name
        self.start_time = ts

        self.functions = set()

    def addFunction(self, func_name, call_ts, runtime, mem_size):
        func_load_time = 0
        if func_name not in self.functions:
            self.functions.add(func_name)
            func_load_time = mem_size / self.config.MEM_LOAD_RATE

        scheduled_time = self.start_time
        if len(self.function_queue) > 0:
            scheduled_time = self.function_queue[-1].getFinishTime()
        scheduled_time += func_load_time
        func = Function(func_name, call_ts, runtime, scheduled_time, mem_size)
        self.function_queue.append(func)

    def getFinishTime(self):
        if len(self.function_queue) == 0:
            return self.start_time
        return self.function_queue[-1].getFinishTime()
    def __str__(self):
        n = len(self.function_queue)
        endtime = self.function_queue[-1].getFinishTime() if n > 0 else -1
        return "PendingVM: "+ self.app_name + " has " +str(n) + " functions with last function finish time "+str(endtime)


class VM:
    def __init__(self, app_name, ts, histogram, config, use_histogram, use_fixed_keep_alive):
        self.id = uuid.uuid4()
        self.app_name = app_name
        self.functions = {}
        if use_histogram:
            self.histogram = Histogram(config) if histogram is None else histogram
        else:
            self.histogram = None
        self.function_queue = []
        self.config = config

        self.use_histogram = use_histogram
        self.use_fixed_keep_alive = use_fixed_keep_alive

        ## Values used for calculated Priority for Eviction
        # clock: timestamp of last function use
        # frequency: # of times function has been invoked
        # reset to 0 if the container is evicted (or when all containers for this app are evicted)
        # probably aggregate this across all the functions on this machine
        # cost: cold start time of function
        # size: memory usage of container
        self.clock = 0
        self.frequency = 0
        self.cost = config.VM_START_TIME+config.FUNCTION_LOAD_TIME
        self.size = config.VM_MEM_SIZE

        self.prewarming = False
        self.keepalive = False
        self.prewarm_end_ts = 0
        self.keepalive_end_ts = -1000
        self.current_ts = ts

        self.prev_ts = -1

        # Pending VM stuff
        self.pending_vms = []
        self.pending_eviction = False
        # self.new_app_name = ""
        # self.new_function_queue = []
        self.new_start_time = -1

        self.active_times = []
    
    def migrateVM(self, new_app_name, new_func_name, ts, runtime, mem_size):
        self.clock = ts
        self.frequency += 1

        self.pending_eviction = True
        self.new_app_name = new_app_name
        if len(self.pending_vms) == 0:
            self.new_start_time = self.function_queue[-1].getFinishTime()+self.config.VM_DELETE_TIME + self.config.VM_START_TIME

            p_vm = PendingVM(self.config, new_app_name, self.new_start_time)
            p_vm.addFunction(new_func_name, ts, runtime, mem_size)
            self.pending_vms.append(p_vm)
            # return VM_STATUS.COLD_START, p_vm.function_queue[-1].getFinishTime()
        elif new_app_name == self.pending_vms[-1].app_name:
            self.pending_vms[-1].addFunction(new_func_name, ts, runtime, mem_size)
            # return VM_STATUS.COLD_START, self.pending_vms[-1].getFinishTime()
        else:
            new_pvm = PendingVM(self.config, new_app_name, self.pending_vms[-1].getFinishTime() + self.config.VM_DELETE_TIME+self.config.VM_START_TIME)
            new_pvm.addFunction(new_func_name, ts, runtime, mem_size)
            self.pending_vms.append(new_pvm)
        return VM_STATUS.COLD_START, self.pending_vms[-1].getFinishTime()
        # func_sched_time = self.new_start_time
        # if len(self.new_function_queue) > 0:
        #     func_sched_time = self.new_function_queue[-1].getFinishTime()
        # self.new_function_queue.append(Function(
        #     new_func_name,
        #     ts,
        #     runtime,
        #     func_sched_time
        # ))
        # return VM_STATUS.COLD_START, self.new_function_queue[-1].getFinishTime()

    def invokeFunction(self, app_name, func_name, ts, runtime, mem_size, overload=False):
        # print("Current vm load at ",self.current_ts,": ", self.getActiveTime())
        # returns VM status and timestamp of last expected function execution
        if self.pending_eviction:
            return VM_STATUS.PENDING_EVICTION, -1
        # if len(self.function_queue) > self.config.VM_THRESHOLD and not overload:
        #     return VM_STATUS.OVERLOADED, -1
        if self.getVMLoad() > self.config.VM_THRESHOLD and not overload:
            return VM_STATUS.OVERLOADED, -1
        self.frequency += 1
        self.clock = ts
        delay = 0
        # print(self.functions)
        if func_name not in self.functions:
            self.functions[func_name] = FunctionInfo(True, mem_size)
            # self.size += self.config.FUNCTION_MEM_SIZE
            # delay += self.config.FUNCTION_LOAD_TIME
            self.size += mem_size
            delay += mem_size / self.config.MEM_LOAD_RATE
            return_status = VM_STATUS.COLD_START_FUNCTION_UNLOADED
        # print("invoke at: ", ts,", keep alive end ts: ", self.keepalive_end_ts)
        # print("delay: ",delay)
        if ((self.keepalive_end_ts > ts and delay == 0) or
            (not self.use_histogram and not self.use_fixed_keep_alive and delay == 0)): # always on case doesn't use the keepalive_end_ts variable
            return_status = VM_STATUS.WARM_START
        else:
            return_status = VM_STATUS.COLD_START_FUNCTION_UNLOADED
            function_load_delay = self.loadFunctions()
            delay += function_load_delay
            self.prewarm_end_ts = ts
        
        if ts < self.current_ts:
            return_status = VM_STATUS.COLD_START

        if self.use_histogram and self.prev_ts != -1:
            self.histogram.add_value((ts - self.prev_ts) / 60)
        self.prev_ts = ts

        if len(self.function_queue) == 0:
            # VM might still be loading so we need to use timestamp of VM
            self.function_queue.append(Function(func_name, ts, runtime, self.current_ts+delay, mem_size))
        else:
            # function won't run until previous functions finish
            self.function_queue.append(Function(func_name, ts, runtime, self.function_queue[len(self.function_queue)-1].getFinishTime(), mem_size))
        
        expected_function_execution_finish = self.function_queue[len(self.function_queue)-1].getFinishTime()
        if self.use_fixed_keep_alive:
            self.keepalive_end_ts = expected_function_execution_finish + self.getKeepAliveTime()
            # print("keep alive time: ", self.getKeepAliveTime())
            self.prewarm_end_ts = expected_function_execution_finish
        else:
            self.keepalive_end_ts = expected_function_execution_finish
            # print("pre warm time: ", self.getPreWarmTime())
            self.prewarm_end_ts = expected_function_execution_finish + self.getPreWarmTime()
        # if self.histogram.get_cv() > self.config.CV_THRESHOLD:
        #     self.keepalive_end_ts = expected_function_execution_finish + self.histogram.getTailPercentile(self.config.TAIL_PERCENTILE)
        #     self.keepalive = True
        # else:
        #     self.keepalive_end_ts = expected_function_execution_finish + self.config.HISTOGRAM_MAX_SIZE * 60
        #     self.keepalive = True
        
        finish_time = self.function_queue[len(self.function_queue)-1].getFinishTime()
        self.clock = finish_time
        return return_status, finish_time

    def loadFunctions(self):
    # this function returns the time taken to load all the functions
        # not_loaded_funcs = 0
        load_delay_time = 0
        for func in self.functions.keys():
            funcObj = self.functions[func]
            if not funcObj.loaded:
                funcObj.loaded = True
                # not_loaded_funcs += 1
                self.size += funcObj.mem_size
                load_delay_time += funcObj.mem_size / self.config.MEM_LOAD_RATE
        # self.size += self.config.FUNCTION_MEM_SIZE * not_loaded_funcs
        return load_delay_time
    
    def unloadFunctions(self):
        # num_unloaded = 0
        function_unload_time = 0
        for func in self.functions.keys():
            funcObj = self.functions[func]
            if funcObj.loaded:
                funcObj.loaded = False
                # num_unloaded += 1
                self.size -= funcObj.mem_size
                function_unload_time += funcObj.mem_size / self.config.MEM_LOAD_RATE
        # self.size -= self.config.FUNCTION_MEM_SIZE * num_unloaded
        return function_unload_time
    
    def getKeepAliveTime(self):
        if not self.use_histogram and self.use_fixed_keep_alive:
            return self.config.FIXED_KEEP_ALIVE * 60
        if not self.use_histogram: # some random value, this won't be used in theory
            return self.config.HISTOGRAM_MAX_SIZE * 60
        if self.histogram.get_cv() > self.config.CV_THRESHOLD:
            return self.histogram.getTailPercentile(self.config.TAIL_PERCENTILE) * 60
        else:
            return self.config.HISTOGRAM_MAX_SIZE * 60
        
    def getPreWarmTime(self):
        if not self.use_histogram:
            return 0
        if self.histogram.get_cv() > self.config.CV_THRESHOLD:
            return self.histogram.getHeadPercentile(self.config.HEAD_PERCENTILE) * 60
        else: 
            return 0
    
    def speedForward(self, ts, latencies, scheduling_delays):
        # new_ts = self.current_ts
        mem_arr = [[], []]
        delete = False
        total_func_comp = 0
        new_vm = True
        while new_vm and self.current_ts < ts:
            new_mem, delete, num_func_completed, new_vm = self.speedForwardHelper(ts, latencies, scheduling_delays)
            mem_arr[0].extend(new_mem[0])
            mem_arr[1].extend(new_mem[1])
            total_func_comp += num_func_completed
        
        return mem_arr, delete, total_func_comp
        


    def speedForwardHelper(self, ts, latencies, scheduling_delays):
        # print("vm has this many pending vms: ",len(self.pending_vms))
        num_func_completed = 0
        if ts < self.current_ts:
            return [], False, num_func_completed
        mem_usage = [[], []]
        delete = False
        # print("in speedforward, current time: ", self.current_ts, ", ts: ", ts)

        # if len(self.function_queue) > 0:
        #     # process functions in the queue
        #     new_ts = self.current_ts
        #     while len(self.function_queue) > 0 and self.function_queue[0].getFinishTime() < ts:
        #         func = self.function_queue.pop(0)
        #         self.latencies.append(func.getLatency())
        #         new_ts = func.getFinishTime()
        #         # if len(self.function_queue) == 0:
        #         #     self.prewarm_end_ts = new_ts + self.histogram.getHeadPercentile(self.config.HEAD_PERCENTILE)
        #     self.addMemForTimeFrame(mem_usage, self.current_ts, new_ts)
        #     # for i in range(math.ceiling(self.current_ts), math.floor(new_ts)+1):
        #     #     mem_usage.append(self.size)
        #     self.current_ts = new_ts
        # else:

        # process all the functions in the queue
        new_ts = self.current_ts
        while len(self.function_queue) > 0 and self.function_queue[0].getFinishTime() < ts:
            func = self.function_queue.pop(0)
            # this is to handle pending VM memory, the function start times should already account for this delay
            # so we don't need to add any delay to the function scheduled time
            if func.func_name not in self.functions or not self.functions[func.func_name].loaded:
                self.size += func.mem_size
                self.functions[func.func_name] = FunctionInfo(True, func.mem_size)
                # self.functions[func.func_name].loaded = True
            func_start = func.scheduled_time
            if func_start > self.current_ts:
                self.active_times.append(FunctionTimestamp(func_start, FUNCTION_TIMESTAMP_TYPE.FUNCTION_START))
            num_func_completed += 1
            latencies.append(func.getLatency())
            scheduling_delays.append(func.getDelay())
            new_ts = func.getFinishTime()
            self.addMemForTimeFrame(mem_usage, self.current_ts, new_ts)
            self.current_ts = new_ts
            self.active_times.append(FunctionTimestamp(new_ts, FUNCTION_TIMESTAMP_TYPE.FUNCTION_END))
            if len(self.function_queue) > 0 and self.current_ts >= self.function_queue[0].scheduled_time and self.current_ts < self.function_queue[0].getFinishTime():
                self.active_times.append(FunctionTimestamp(self.function_queue[0].scheduled_time, FUNCTION_TIMESTAMP_TYPE.FUNCTION_START))


            # if len(self.function_queue) == 0:
            #     self.prewarm_end_ts = new_ts + self.histogram.getHeadPercentile(self.config.HEAD_PERCENTILE)
        # self.addMemForTimeFrame(mem_usage, self.current_ts, new_ts)
        
        # for i in range(math.ceiling(self.current_ts), math.floor(new_ts)+1):
        #     mem_usage.append(self.size)
        self.current_ts = new_ts
        # if new_ts < ts:
        #     if 
        # print("finished processing functions. remaining functions: ", len(self.function_queue), ", current ts: ",self.current_ts, ", ts: ", ts, ", keep alive end ts: ", self.keepalive_end_ts, " pre warm end ts: ", self.prewarm_end_ts)
        while self.current_ts < ts:
            if len(self.function_queue) == 0:

                if self.pending_eviction:
                    new_vm = self.pending_vms[0]
                    self.pending_vms.remove(new_vm)

                    self.app_name = new_vm.app_name
                    self.function_queue = new_vm.function_queue

                    if len(self.pending_vms) == 0:
                        self.pending_eviction = False
                    # new_start_ts = self.current_ts + self.config.VM_DELETE_TIME + self.config.VM_START_TIME
                    self.functions.clear()
                    # for func in self.function_queue:
                    #     self.functions[func.func_name] = 1

                    # load_funcs_delay_time = self.loadFunctions() * self.config.FUNCTION_LOAD_TIME
                    # new_start_ts += load_funcs_delay_time
                    # self.function_queue[0].scheduled_time = new_start_ts
                    # for i in range(1, len(self.function_queue)):
                    #     self.function_queue[i].scheduled_time = self.function_queue[i-1].getFinishTime()

                    vm_start_ts = new_vm.start_time
                    self.addMemForTimeFrame(mem_usage, self.current_ts, min(ts, vm_start_ts), use_zero=True)
                    next_ts = min(ts, vm_start_ts)
                    self.current_ts = next_ts
                    # we're done with current vm, allow other loop to run again with pending VM
                    return mem_usage, False, num_func_completed, True

                    # if next_ts == ts: # speedForward is over, but we aren't at the start time yet
                    #     # end this call and make sure future calls to speedForward don't start prematurely
                    #     # self.current_ts = vm_start_ts
                    #     return mem_usage, False, num_func_completed, next_ts
                    # else: # we are now the new VM and we can start executing
                    #     return mem_usage, False, num_func_completed, next_ts
                        # new_mem, deleteNewVM, new_vm_func_completed = self.speedForward(ts, latencies, scheduling_delays)
                        # print("new mem: ")
                        # print(new_mem)
                        # print("mem usage:")
                        # print(mem_usage)
                        # mem_usage.extend(new_mem)
                        # if delete or deleteNewVM:
                        #     delete = True
                        # return mem_usage, delete, new_vm_func_completed + num_func_completed



                # print("speed forward invoked at: ",ts, ", keep alive end: ", self.keepalive_end_ts, ", current ts: ",self.current_ts)
                # print("no functions in queue: ", self.app_name)
            # we have no functions in the queue
                # 3 cases: fixed keep alive, no histogram, histogram
                # fixed keep alive
                if not self.use_histogram and self.use_fixed_keep_alive:
                    if self.current_ts >= self.keepalive_end_ts:
                        delete = True
                        self.addMemForTimeFrame(mem_usage, self.current_ts, ts, use_zero=True)
                        self.current_ts = ts
                        return mem_usage, delete, num_func_completed, False
                    else:
                        self.addMemForTimeFrame(mem_usage, self.current_ts, min(ts, self.keepalive_end_ts))
                        self.current_ts = min(ts, self.keepalive_end_ts)
                        if self.current_ts == self.keepalive_end_ts:
                            delete = True

                # no histogram
                if not self.use_histogram and not self.use_fixed_keep_alive:
                    self.addMemForTimeFrame(mem_usage, self.current_ts, ts)
                    self.current_ts = ts
                    return mem_usage, False, num_func_completed, False
                
                # use histogram
                if self.use_histogram and not self.use_fixed_keep_alive:  
                    if self.current_ts >= self.keepalive_end_ts:
                        # prewarm_time = self.histogram.getHeadPercentile(self.config.HEAD_PERCENTILE) if self.histogram.get_cv() > self.config.CV_THRESHOLD else 0
                        prewarm_time = self.getPreWarmTime()
                        # print("prewarm time: ", prewarm_time)
                        if prewarm_time > 0:
                            delay = self.unloadFunctions() 
                            self.prewarm_end_ts = self.keepalive_end_ts + prewarm_time + delay
                        else:
                            self.prewarm_end_ts = self.keepalive_end_ts
                        self.addMemForTimeFrame(mem_usage, self.current_ts, min(self.prewarm_end_ts, ts))
                        self.current_ts = min(self.prewarm_end_ts, ts)
                        keepalive_time = self.getKeepAliveTime()
                        # print("keep alive time: ", keepalive_time)
                        if self.current_ts >= self.prewarm_end_ts:
                            # keepalive_time = self.histogram.getTailPercentile(self.config.TAIL_PERCENTILE) * 60 if self.histogram.get_cv() > self.config.CV_THRESHOLD else self.config.HISTOGRAM_MAX_SIZE * 60
                            keepalive_time = self.getKeepAliveTime()
                            if keepalive_time > 0:
                                delay = self.loadFunctions()
                                self.keepalive_end_ts = self.prewarm_end_ts + keepalive_time + delay
                            else:
                                self.keepalive_end_ts = self.current_ts
                        # handle case where pre warm and keep alive are both 0
                        # just keep function unloaded the whole time
                        if prewarm_time == 0 and keepalive_time == 0:
                            self.unloadFunctions()
                            self.addMemForTimeFrame(mem_usage, self.current_ts, ts)
                            self.current_ts = ts
                        # print("current ts: ",self.current_ts)
                    else:
                        self.addMemForTimeFrame(mem_usage, self.current_ts, min(self.keepalive_end_ts, ts))
                        self.current_ts = min(self.keepalive_end_ts, ts)

            else:
            # we still have functions to execute, but we didn't execute them because they finish after ts
                # for i in range(math.ceiling(self.current_ts), math.floor(ts)+1):
                #     mem_usage.append(self.size)
                self.addMemForTimeFrame(mem_usage, self.current_ts, ts)
                self.current_ts = ts

        if self.use_histogram and self.prev_ts != -1 and ts - self.prev_ts > 60 * self.config.HISTOGRAM_MAX_SIZE and len(self.function_queue) == 0:
            delete = True
        # print("finished speed forward ts: ", self.current_ts, ", keep alive end ts: ", self.keepalive_end_ts)
        return mem_usage, delete, num_func_completed, False
    
    def addMemForTimeFrame(self, mem_arr, start_time, end_time, use_zero=False):
        if start_time >= end_time:
            return
        for i in range(math.ceil(start_time), math.floor(end_time)+1):
            mem_arr[0].append(i)
            mem_arr[1].append(self.size if not use_zero else 0)
    
    def getPriority(self):
        return self.clock + self.frequency * self.cost / self.size
    
    def getVMLoad(self):
        # return len(self.function_queue)
        return self.getActiveTime()
    
    def getActiveTime(self):
        if len(self.active_times) == 0:
            return 0
        
        active_time = 0
        # print("Active times arr: ------------------------------")
        # for a in self.active_times:
        #     print(str(a))
        # print("---------------------------------------------------------------")
        current_state = None
        current_time = self.current_ts
        i = len(self.active_times) - 1
        while i > -1 and self.active_times[i].ts > self.current_ts - self.config.VM_LOAD_WINDOW:
            prev_change = self.active_times[i]
            current_state = prev_change.type
            if prev_change.type == FUNCTION_TIMESTAMP_TYPE.FUNCTION_START:
                active_time += current_time - prev_change.ts
                current_time = prev_change.ts
            else: # FUNCTION_END
                current_time = prev_change.ts
            i -= 1
        
        extra_time = 0
        if self.current_ts - self.config.VM_LOAD_WINDOW < current_time:
            extra_time = current_time - (self.current_ts - self.config.VM_LOAD_WINDOW)
        
        if current_state == FUNCTION_TIMESTAMP_TYPE.FUNCTION_END:
            active_time += extra_time
        elif current_state is None and self.active_times[-1].type == FUNCTION_TIMESTAMP_TYPE.FUNCTION_START:
                active_time += extra_time
        # other two cases:
        # current state is None but previous timestamp is a end means we are not executing anything
        # current stat is start, which means time before it is not running
        # print("In getActiveTime at ",self.current_ts," : active_time ",active_time)
        return active_time / self.config.VM_LOAD_WINDOW

    def __str__(self):
        n = len(self.function_queue)
        endtime = self.function_queue[-1].getFinishTime() if n > 0 else -1
        string_rep = "VM: "+self.app_name+" function queue with length " + str(n) + " with end time "+ str(endtime) + " with pending vms: "
        for pv in self.pending_vms:
            string_rep += str(pv) + ", "
        return string_rep