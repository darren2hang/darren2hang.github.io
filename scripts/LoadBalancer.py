from VM import VM, VM_STATUS
from Histogram import Histogram
from enum import Enum
import numpy as np

class Config:
    def __init__(
            self,
            CV_THRESHOLD=2,
            VM_THRESHOLD= 0.5,# this is a measure of cpu active time / vm_load_window time, it used to be number of functions and was a value of 10,
            HISTOGRAM_MAX_SIZE=240,
            VM_START_TIME=2.5, # seconds
            VM_DELETE_TIME=2, # seconds
            VM_MEM_SIZE=300, # in MB
            FUNCTION_LOAD_TIME=0.1, # in seconds
            FUNCTION_UNLOAD_TIME=0.1, # in seconds
            FUNCTION_MEM_SIZE=170, # in MB
            VM_CACHE_SIZE=512,
            HEAD_PERCENTILE=5,
            TAIL_PERCENTILE=99,
            FIXED_KEEP_ALIVE=10, # in minutes
            VM_LOAD_WINDOW=5, # in seconds
            MEM_LOAD_RATE=2000, # MB/s that VM loads function into memory
            ):
        self.CV_THRESHOLD = CV_THRESHOLD
        self.VM_THRESHOLD = VM_THRESHOLD
        self.HISTOGRAM_MAX_SIZE = HISTOGRAM_MAX_SIZE
        self.VM_START_TIME = VM_START_TIME
        self.VM_DELETE_TIME = VM_DELETE_TIME
        self.VM_MEM_SIZE = VM_MEM_SIZE
        self.FUNCTION_LOAD_TIME = FUNCTION_LOAD_TIME
        self.FUNCTION_UNLOAD_TIME = FUNCTION_UNLOAD_TIME
        self.FUNCTION_MEM_SIZE = FUNCTION_MEM_SIZE
        self.VM_CACHE_SIZE = VM_CACHE_SIZE
        self.HEAD_PERCENTILE = HEAD_PERCENTILE
        self.TAIL_PERCENTILE = TAIL_PERCENTILE
        self.FIXED_KEEP_ALIVE = FIXED_KEEP_ALIVE
        self.VM_LOAD_WINDOW = VM_LOAD_WINDOW
        self.MEM_LOAD_RATE = MEM_LOAD_RATE

class COLD_START_TYPE(Enum):
    NO_VM = 1
    FUNCTION_UNLOADED = 2
    WARM_START = 3

class LoadBalancer:
    def __init__(self, config, use_caching=True, use_histogram=True, use_fixed_keep_alive=False):
        self.vm_map = {}
        self.histogram_map = {}
        self.current_ts = 0
        self.num_cold_starts = 0
        self.num_warm_starts = 0
        self.memory_usage = [[], []]
        self.config = config
        self.use_caching = use_caching
        self.use_histogram = use_histogram
        self.use_fixed_keep_alive = use_fixed_keep_alive
        self.num_vm = 0
        self.max_vm_num = 0
        self.cold_starts = []
        self.app_cold_starts = {}
        self.latencies = []
        self.scheduling_delays = []
        self.cold_start_types = []
        self.num_func_completed = 0

        self.sorted_vms = []

    def invokeFunction(self, app_name, func_name, ts, runtime, mem_size):
        self.speedForward(ts)
        cold_start_type = COLD_START_TYPE.WARM_START
        if app_name not in self.app_cold_starts:
            self.app_cold_starts[app_name] = [0,0]
        if app_name not in self.vm_map or len(self.vm_map[app_name]) == 0: # must evict to get a new VM for unallocated function
            new_vm = self.createVM(app_name, ts)
            cold_start_type = COLD_START_TYPE.NO_VM
            if new_vm is None:
                # handle this later
                # strong evict
                vm_to_evict = None
                # self.sorted_vms[0]
                for vm in self.sorted_vms:
                    if not vm.pending_eviction or vm.pending_vms[-1].app_name == app_name:
                        vm_to_evict = vm
                if vm_to_evict is None:
                    vm_to_evict = self.sorted_vms[0]

                if not vm_to_evict.pending_eviction:
                    self.vm_map[vm_to_evict.app_name].remove(vm_to_evict)
                    self.vm_map[app_name] = [vm_to_evict]
                vm_status, finish_time = vm_to_evict.migrateVM(app_name, func_name, ts, runtime, mem_size)
                self.cold_start_types.append(COLD_START_TYPE.NO_VM)
                self.num_cold_starts += 1
                self.cold_starts.append(True)
                num_cold, total = self.app_cold_starts[app_name]
                self.app_cold_starts[app_name] = [num_cold+1, total+1]

                return finish_time
            self.vm_map[app_name] = [new_vm]
        # else:
        #     cold_start_type = COLD_START_TYPE.FUNCTION_UNLOADED

        scheduled = False
        i = 0
        finish_time = -1
        least_load = -1
        least_overloaded_vm = None
        while not scheduled:
            # cold_start_type = COLD_START_TYPE.FUNCTION_UNLOADED
            if i >= len(self.vm_map[app_name]): # autoscaling
                new_vm = self.createVM(app_name, ts)
                cold_start_type = COLD_START_TYPE.NO_VM
                if new_vm is None:
                    # self.vm_map[app_name][i-1]
                    # cold_start = COLD_START_TYPE.FUNCTION_UNLOADED
                    if least_overloaded_vm.pending_eviction:
                        vm_status, finish_time = least_overloaded_vm.migrateVM(app_name, func_name, ts, runtime, mem_size)
                        cold_start = COLD_START_TYPE.NO_VM
                    else:
                        vm_status, finish_time = least_overloaded_vm.invokeFunction(app_name, func_name, ts, runtime, mem_size, overload=True)
                        # print("function not in memory")
                        cold_start = COLD_START_TYPE.FUNCTION_UNLOADED
                    if vm_status == VM_STATUS.COLD_START or vm_status == VM_STATUS.COLD_START_FUNCTION_UNLOADED:
                        self.cold_start_types.append(cold_start)
                        self.num_cold_starts += 1
                        self.cold_starts.append(True)
                        num_cold, total = self.app_cold_starts[app_name]
                        self.app_cold_starts[app_name] = [num_cold+1, total+1]
                    else:
                        self.num_warm_starts += 1
                        self.cold_starts.append(False)
                        num_cold, total = self.app_cold_starts[app_name]
                        self.app_cold_starts[app_name] = [num_cold, total+1]
                    return finish_time
                else:
                    # self.cold_start_types.append(COLD_START_TYPE.NO_VM)
                    cold_start_type = COLD_START_TYPE.NO_VM
                    self.vm_map[app_name].append(new_vm)

            vm_instance = self.vm_map[app_name][i]
            # print()
            # print("----------------------------------------")
            # print("vm map: ",self.vm_map)
            # print("load balancer invoking: ", ts)
            if vm_instance.pending_eviction:
                vm_status, finish_time = vm_instance.migrateVM(app_name, func_name,ts, runtime, mem_size)
            else:
                vm_status, finish_time = vm_instance.invokeFunction(app_name, func_name, ts, runtime, mem_size)
            if vm_status != VM_STATUS.OVERLOADED:
                scheduled = True
                if vm_status == VM_STATUS.COLD_START or vm_status == VM_STATUS.COLD_START_FUNCTION_UNLOADED:
                    if vm_status == VM_STATUS.COLD_START:
                        cold_start_type = COLD_START_TYPE.NO_VM
                    elif vm_status == VM_STATUS.COLD_START_FUNCTION_UNLOADED:
                        cold_start_type = COLD_START_TYPE.FUNCTION_UNLOADED
                    else:
                        print("in else: ",cold_start_type)
                    self.cold_start_types.append(cold_start_type)
                    self.num_cold_starts += 1
                    self.cold_starts.append(True)
                    num_cold, total = self.app_cold_starts[app_name]
                    self.app_cold_starts[app_name] = [num_cold+1, total+1]
                else:
                    self.num_warm_starts += 1
                    self.cold_starts.append(False)
                    num_cold, total = self.app_cold_starts[app_name]
                    self.app_cold_starts[app_name] = [num_cold, total+1]
            else:
                vm_load = vm_instance.getVMLoad()
                if least_load == -1 or vm_load < least_load:
                    least_load = vm_load
                    least_overloaded_vm = vm_instance
                i += 1
        return finish_time

    def createVM(self, new_app_name, ts):
        # only evicts in a VM is not running anything
        # handle eviction
        if self.use_caching and self.num_vm + 1 > self.config.VM_CACHE_SIZE:
            vms = []
            for app_name in self.vm_map.keys():
                if app_name != new_app_name:
                    for vm in self.vm_map[app_name]:
                        vms.append(vm)
            if len(vms) == 0:
                return None
            vms.sort(key=lambda vm: vm.getPriority())
            self.sorted_vms = vms
            evicted_vm = None
            for vm in vms:
                if len(vm.function_queue) == 0 and not vm.pending_eviction:
                    evicted_vm = vm
            if evicted_vm == None:
                # print("Tried evicting but all VMs are busy, can't evict")
                return None
            for vm in self.vm_map[evicted_vm.app_name]:
                if vm.id == evicted_vm.id:
                    self.vm_map[evicted_vm.app_name].remove(vm)
                    self.num_vm -= 1
            
        self.num_vm += 1
        if self.num_vm > self.max_vm_num:
            self.max_vm_num = self.num_vm
        histogram = self.createHistogram(new_app_name)
        # histogram = Histogram(self.config)
        # if new_app_name in self.histogram_map and new_app_name in self.vm_map and len(self.vm_map[new_app_name]) == 0:
        #     histogram = self.histogram_map[new_app_name]
        # if new_app_name in self.vm_map and len(self.vm_map[new_app_name]) == 0:
        #     self.histogram_map[new_app_name] = histogram
        return VM(new_app_name, ts + self.config.VM_START_TIME, histogram, self.config, self.use_histogram, self.use_fixed_keep_alive)
    
    def createHistogram(self, new_app_name):
        # Either creates a new histogram or uses a pre-existing histogram
        histogram = Histogram(self.config)
        if new_app_name in self.histogram_map and new_app_name in self.vm_map and len(self.vm_map[new_app_name]) == 0:
            histogram = self.histogram_map[new_app_name]
        if new_app_name in self.vm_map and len(self.vm_map[new_app_name]) == 0:
            self.histogram_map[new_app_name] = histogram
        return histogram
    
    def speedForward(self, ts):
        self.current_ts = ts
        mem_usages = []
        # TODO: need to test if the deleting and aggregate of memories works correctly
        for app_name in self.vm_map.keys():
            delete_arr = []
            for vm in self.vm_map[app_name]:
                mem_usage, delete, num_func_completed = vm.speedForward(ts, self.latencies, self.scheduling_delays)
                mem_usages.append(mem_usage)
                delete_arr.append(delete)
                self.num_func_completed += num_func_completed
                if delete:
                    self.num_vm -= 1
            self.vm_map[app_name] = [vm for i, vm in enumerate(self.vm_map[app_name]) if not delete_arr[i]]
        
        if len(mem_usages) != 0:
            # Extend memory_usage[0] with the longest mem_usages[i][0]
            longest_0 = max(mem_usages, key=lambda x: len(x[0]))[0]
            self.memory_usage[0].extend(longest_0)

            # Pad mem_usages[i][1] with zeros to match max length, then sum
            max_len = max(len(mem_use[1]) for mem_use in mem_usages)

            padded_1s = [np.pad(mem_use[1], (0, max_len - len(mem_use[1])), constant_values=0) for mem_use in mem_usages]
            sum_mem = np.sum(padded_1s, axis=0).tolist()
            self.memory_usage[1].extend(sum_mem)


    def getColdStartPercentage(self):
        n = self.num_cold_starts + self.num_warm_starts
        if n == 0:  
            return 1
        return self.num_cold_starts / n
    
    def getMemUsage(self):
        return self.memory_usage