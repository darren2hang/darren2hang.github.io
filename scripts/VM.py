from Histogram import Histogram
from Function import Function
import uuid
import math

from enum import Enum

class VM_STATUS(Enum):
    OVERLOADED = 1
    COLD_START = 2
    WARM_START = 3

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
    

    def invokeFunction(self, app_name, func_name, ts, runtime):
        if len(self.function_queue) > self.config.VM_THRESHOLD:
            return VM_STATUS.OVERLOADED
        self.frequency += 1
        self.clock = ts
        delay = 0
        # print(self.functions)
        if func_name not in self.functions:
            self.functions[func_name] = 1
            self.size += self.config.FUNCTION_MEM_SIZE
            delay += self.config.FUNCTION_LOAD_TIME
            return_status = VM_STATUS.COLD_START
        # print("invoke at: ", ts,", keep alive end ts: ", self.keepalive_end_ts)
        # print("delay: ",delay)
        if ((self.keepalive_end_ts > ts and delay == 0) or
            (not self.use_histogram and not self.use_fixed_keep_alive and delay == 0)): # always on case doesn't use the keepalive_end_ts variable
            return_status = VM_STATUS.WARM_START
        else:
            return_status = VM_STATUS.COLD_START
            num_loaded = self.loadFunctions()
            delay += self.config.FUNCTION_LOAD_TIME * num_loaded
            self.prewarm_end_ts = ts

        if self.use_histogram and self.prev_ts != -1:
            self.histogram.add_value((ts - self.prev_ts) / 60)
        self.prev_ts = ts

        if len(self.function_queue) == 0:
            # VM might still be loading so we need to use timestamp of VM
            self.function_queue.append(Function(func_name, ts, runtime, self.current_ts+delay))
        else:
            # function won't run until previous functions finish
            self.function_queue.append(Function(func_name, ts, runtime, self.function_queue[len(self.function_queue)-1].getFinishTime()))
        
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
        
        return return_status

    def loadFunctions(self):
    # this function returns how many functions were loaded
        not_loaded_funcs = 0
        for func in self.functions.keys():
            if self.functions[func] == 0:
                self.functions[func] = 1
                not_loaded_funcs += 1
        self.size += self.config.FUNCTION_MEM_SIZE * not_loaded_funcs
        return not_loaded_funcs
    
    def unloadFunctions(self):
        num_unloaded = 0
        for func in self.functions.keys():
            if self.functions[func] == 1:
                self.functions[func] = 0
                num_unloaded += 1
        self.size -= self.config.FUNCTION_MEM_SIZE * num_unloaded
        return num_unloaded
    
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
        if ts < self.current_ts:
            return [], False
        mem_usage = []
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
            latencies.append(func.getLatency())
            scheduling_delays.append(func.getDelay())
            new_ts = func.getFinishTime()
            # if len(self.function_queue) == 0:
            #     self.prewarm_end_ts = new_ts + self.histogram.getHeadPercentile(self.config.HEAD_PERCENTILE)
        self.addMemForTimeFrame(mem_usage, self.current_ts, new_ts)
        # for i in range(math.ceiling(self.current_ts), math.floor(new_ts)+1):
        #     mem_usage.append(self.size)
        self.current_ts = new_ts
        # if new_ts < ts:
        #     if 
        # print("finished processing functions. remaining functions: ", len(self.function_queue), ", current ts: ",self.current_ts, ", ts: ", ts, ", keep alive end ts: ", self.keepalive_end_ts, " pre warm end ts: ", self.prewarm_end_ts)
        while self.current_ts < ts:
            if len(self.function_queue) == 0:
                # print("speed forward invoked at: ",ts, ", keep alive end: ", self.keepalive_end_ts, ", current ts: ",self.current_ts)
                # print("no functions in queue: ", self.app_name)
            # we have no functions in the queue
                # 3 cases: fixed keep alive, no histogram, histogram
                # fixed keep alive
                if not self.use_histogram and self.use_fixed_keep_alive:
                    if self.current_ts >= self.keepalive_end_ts:
                        delete = True
                        self.addMemForTimeFrame(mem_usage, self.current_ts, ts, use_zero=True)
                        return mem_usage, delete
                    else:
                        self.addMemForTimeFrame(mem_usage, self.current_ts, min(ts, self.keepalive_end_ts))
                        self.current_ts = min(ts, self.keepalive_end_ts)
                        if self.current_ts == self.keepalive_end_ts:
                            delete = True

                # no histogram
                if not self.use_histogram and not self.use_fixed_keep_alive:
                    self.addMemForTimeFrame(mem_usage, self.current_ts, ts)
                    self.current_ts = ts
                    return mem_usage, False
                
                # use histogram
                if self.use_histogram and not self.use_fixed_keep_alive:  
                    if self.current_ts >= self.keepalive_end_ts:
                        # prewarm_time = self.histogram.getHeadPercentile(self.config.HEAD_PERCENTILE) if self.histogram.get_cv() > self.config.CV_THRESHOLD else 0
                        prewarm_time = self.getPreWarmTime()
                        # print("prewarm time: ", prewarm_time)
                        if prewarm_time > 0:
                            delay = self.unloadFunctions() * self.config.FUNCTION_UNLOAD_TIME
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
                                delay = self.loadFunctions() * self.config.FUNCTION_UNLOAD_TIME
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

        if self.use_histogram and self.prev_ts != -1 and ts - self.prev_ts > 60 * self.config.HISTOGRAM_MAX_SIZE:
            delete = True
        # print("finished speed forward ts: ", self.current_ts, ", keep alive end ts: ", self.keepalive_end_ts)
        return mem_usage, delete
    
    def addMemForTimeFrame(self, mem_arr, start_time, end_time, use_zero=False):
        if start_time == end_time:
            return
        for i in range(math.ceil(start_time), math.floor(end_time)+1):
            mem_arr.append(self.size if not use_zero else 0)
    
    def getPriority(self):
        return self.clock + self.frequency * self.cost / self.size