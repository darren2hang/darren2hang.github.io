import math
import numpy as np
# import random

class Histogram:
    def __init__(self, config=None):
        # self.histogram_max_size = config.HISTOGRAM_MAX_SIZE
        self.arr = np.array([0]*240)
        self.weldford = WeldfordAlgo()
        self.count = 0
    
    def add_value(self, inter_arrival_time):
        # inter_arrival_time is in minutes
        self.count += 1
        i = math.floor(inter_arrival_time)
        self.arr[i] += 1
        self.weldford.update(self.arr[i]-1, self.arr[i])

    def get_cv(self):
        # code to check the true CV value
        # mean = np.sum(self.arr)/ 240
        # m2 = np.sum(np.square(self.arr - mean))
        # cv = (m2 / 239) **0.5 / mean
        # print("true: ",cv)
        return self.weldford.get_cv()

    def getHeadPercentile(self, p):
        # returns in unit of minutes
        # TODO: need to test if this function works correctly
        i = 0
        sum = 0
        goal = math.floor(p /100 * self.count)
        while sum < goal and i < len(self.arr):
            sum += self.arr[i]
            i += 1
        return max(0, min((i-1) * 0.9, 240))
    
    def getTailPercentile(self, p):
        # returns in unit of minutes
        # TODO: need to test if this function works correctly
        i = 0
        sum = 0
        goal = math.ceil(p /100 * self.count)
        while sum < goal and i < len(self.arr):
            sum += self.arr[i]
            i += 1
        return max(0, min((i) * 1.1, 240))



class WeldfordAlgo:
    def __init__(self):
        self.n = 240
        self.mean = 0.0
        self.m2 = 0.0  # Sum of squared deviations
  
    def update(self, old_bin, new_bin):
        diff_old = old_bin - self.mean
        self.mean += 1 / self.n
        diff_new = new_bin - self.mean
        # approximate estimate of new sum of squares
        # works pretty well
        self.m2 += diff_new **2 - diff_old**2

    def get_cv(self):
        if self.n < 2:
            return 0  # CV is undefined for n < 2
        std_dev = (self.m2 / (self.n - 1)) ** 0.5
        if self.mean == 0:
            return 0
        return std_dev / self.mean
    


# code to test how accurate the approximated CV value is

# values1 = [0,1,2,211,1,2,1,2,3,4,5,6,6,1,2,3,4,5,6,9]
# for i in range(2000000):
#     random_double = random.uniform(0, 239)
#     values1.append(random_double)

# mean = 120  # Centered around 120
# std_dev = 10  # Adjust standard deviation as needed
# size = 2000000  # Number of values

# # Generate normal distribution
# values = np.random.normal(loc=mean, scale=std_dev, size=size)

# # Clip values to stay within [0, 239]
# values = np.clip(values, 0, 239)

# values1.extend(values)

# values = [20] * 1000
# h = Histogram(240)
# for i in values:
#     h.add_value(i)

# print(h.get_cv())