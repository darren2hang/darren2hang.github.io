from VM import VM, VM_STATUS
from Histogram import Histogram

class Config:
    def __init__(
            self,
            CV_THRESHOLD=2,
            VM_THRESHOLD=10,
            HISTOGRAM_MAX_SIZE=240,
            VM_START_TIME=2.5, # seconds
            VM_DELETE_TIME=2, # seconds
            VM_MEM_SIZE=300, # in MB
            FUNCTION_LOAD_TIME=0.1, # in seconds
            FUNCTION_UNLOAD_TIME=0.1, # in seconds
            FUNCTION_MEM_SIZE=170, # in MB
            VM_CACHE_SIZE=64,
            HEAD_PERCENTILE=5,
            TAIL_PERCENTILE=99,
            FIXED_KEEP_ALIVE=10 # in minutes
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

class LoadBalancer:
    def __init__(self, config, use_caching=True, use_histogram=True, use_fixed_keep_alive=False):
        self.vm_map = {}
        self.histogram_map = {}
        self.current_ts = 0
        self.num_cold_starts = 0
        self.num_warm_starts = 0
        self.memory_usage = []
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

    def invokeFunction(self, app_name, func_name, ts, runtime):
        self.speedForward(ts)
        if app_name not in self.vm_map:
            new_vm = self.createVM(app_name, ts)
            if new_vm is None:
                # handle this later
                return False
            self.vm_map[app_name] = [new_vm]
            self.app_cold_starts[app_name] = [0,0]
        scheduled = False
        i = 0
        while not scheduled:
            if i >= len(self.vm_map[app_name]):
                new_vm = self.createVM(app_name, ts)
                if new_vm is None:
                    # handle this later
                    return False
                self.vm_map[app_name].append(new_vm)

            vm_instance = self.vm_map[app_name][i]
            # print()
            # print("----------------------------------------")
            # print("vm map: ",self.vm_map)
            # print("load balancer invoking: ", ts)
            vm_status = vm_instance.invokeFunction(app_name, func_name, ts, runtime)
            if vm_status != VM_STATUS.OVERLOADED:
                scheduled = True
                if vm_status == VM_STATUS.COLD_START:
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
                i += 1

    def createVM(self, new_app_name, ts):
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
            evicted_vm = vms[0]
            for vm in self.vm_map[evicted_vm.app_name]:
                if vm.id == evicted_vm.id:
                    self.vm_map[evicted_vm.app_name].remove(vm)
                    self.num_vm -= 1
            
        self.num_vm += 1
        if self.num_vm > self.max_vm_num:
            self.max_vm_num = self.num_vm
        histogram = Histogram(self.config)
        if new_app_name in self.histogram_map and new_app_name in self.vm_map and len(self.vm_map[new_app_name]) == 0:
            histogram = self.histogram_map[new_app_name]
        if new_app_name in self.vm_map and len(self.vm_map[new_app_name]) == 0:
            self.histogram_map[new_app_name] = histogram
        return VM(new_app_name, ts + self.config.VM_START_TIME, histogram, self.config, self.use_histogram, self.use_fixed_keep_alive)
    
    def speedForward(self, ts):
        self.current_ts = ts
        mem_usages = []
        # TODO: need to test if the deleting and aggregate of memories works correctly
        for app_name in self.vm_map.keys():
            delete_arr = []
            for vm in self.vm_map[app_name]:
                mem_usage, delete = vm.speedForward(ts, self.latencies, self.scheduling_delays)
                mem_usages.append(mem_usage)
                delete_arr.append(delete)
                if delete:
                    self.num_vm -= 1
            self.vm_map[app_name] = [vm for i, vm in enumerate(self.vm_map[app_name]) if not delete_arr[i]]
        
        self.memory_usage.extend([sum(values) for values in zip(*mem_usages)])


    def getColdStartPercentage(self):
        n = self.num_cold_starts + self.num_warm_starts
        if n == 0:  
            return 1
        return self.num_cold_starts / n
    
    def getMemUsage(self):
        return self.memory_usage