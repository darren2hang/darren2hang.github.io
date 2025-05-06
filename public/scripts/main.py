from LoadBalancer import LoadBalancer, Config
import argparse
import matplotlib.pyplot as plt
import time

mem = []

plot_cold_start = False
plot_mem = False
plot_latency = False
plot_delay = False

def parse_num_traces(value):
    if value.lower() == "all":
        return "all"
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("num_traces must be an integer or 'all'.")
    
def parse_policy_arg(policy):
    # returns 3 bools: use_caching, use_histogram, use_fixed_keep_alive
    if policy == 'histogram_cache':
        return True, True, False
    if policy == 'histogram_only': 
        return False, True, False
    if policy == 'cache_only':
        return True, False, False
    if policy == 'fixed_keep_alive':
        return False, False, True
    raise argparse.ArgumentTypeError("policy must be one of the following values: 'histogram_cache', 'histogram_only', 'cache_only', 'fixed_keep_alive'")

def main():
    parser = argparse.ArgumentParser(description="Process some traces.")
    parser.add_argument(
        "--policy",
        type=parse_policy_arg,
        default="histogram_cache",
        help="Please specify one of the following values: 'histogram_cache', 'histogram_only', 'cache_only', 'fixed_keep_alive'"
    )
    parser.add_argument(
        "--num_traces",
        type=parse_num_traces,
        default=100,
        help="Number of traces (default: 100). Provide an integer or 'all'."
    )
    parser.add_argument(
        "--save_output",
        type=bool,
        default=True,
        help="Boolean stating if we want to write metrics from run to output files"
    )
    parser.add_argument(
        "--input_file",
        type=str,
        # default="/scripts/test_trace_20min.txt",
        default="/scripts/example_trace.txt", 
        # default='/scripts/AzureFunctionsInvocationTraceForTwoWeeksJan2021.txt',
        help="File path to a file with traces you want to simulate"
    )
    parser.add_argument(
        "--eval_description",
        type=str,
        default='Histogram + Cache',
        help="Short Description of Policy to put in Graph Titles"
    )

    args = parser.parse_args()

    filepath = args.input_file
    # filepath = 'AzureFunctionsInvocationTraceForTwoWeeksJan2021.txt'
    # filepath = 'test_trace_20min.txt'
    # filepath = 'test_trace_20min_large_gap.txt'

    lines = []
    with open(filepath, 'r') as file:
        # Discard the first line
        file.readline()
        
        # Process each subsequent line
        for line in file:
            # Split the line by commas
            values = line.strip().split(',')
            # Ensure there are exactly 4 values
            if len(values) == 4:
                # Process the values (you  can modify this part to suit your needs)
                app_name, func_name, end_ts, runtime = values
                # approximate function invocation time with end timestamp - duration of function execution
                lines.append([app_name, func_name, float(end_ts) - float(runtime), float(runtime)])
            else:
                print("Skipping invalid row with incorrect number of values: ", values)

    # sort lines by the start timestamp
    sorted_lines = sorted(lines[:len(lines) if args.num_traces == "all" else min(args.num_traces,len(lines))], key = lambda x: x[2])
    print("Processing ", len(sorted_lines), " traces")
    config = Config()
    # valid parameters:
        # use_caching: True or False
        # keep alive case: use_histogram=False and use_keep_alive=True
        # always on case: use_histogram=False and use_keep_alive=False 
        # histogram case: use_histogram=True and use_keep_alive=False
    use_caching, use_histogram, use_fixed_keep_alive = args.policy
    load_balancer = LoadBalancer(config, use_caching, use_histogram, use_fixed_keep_alive)
    i = 0
    start_time = time.time()
    for line in sorted_lines:
        app_name, func_name, start_ts, runtime = line
        load_balancer.invokeFunction(app_name, func_name, start_ts, runtime)
        i+=1
        if i % 1000 == 0:
            print("finished running ",i," calls")
        if i % 10000 == 0:
            mem = load_balancer.getMemUsage()
            time_index = list(range(len(mem)))
            xy = list(zip(time_index,mem))
            sendToReact(xy)
            # plot_mem_graph(load_balancer, args)
    end_time = time.time()
    print(f"Simulation of {len(sorted_lines)} function calls for {args.eval_description} took {end_time - start_time} seconds")


    # Analysis 
    eval = args.eval_description
    print("Overall cold start percentage: ",load_balancer.getColdStartPercentage())
    print("Max number of vms: ", load_balancer.max_vm_num)
    # print(load_balancer.cold_starts)
    # for i in range(len(sorted_lines)):
    #     print(sorted_lines[i])
    # print(load_balancer.latencies)
    # print(sum(load_balancer.latencies)/len(load_balancer.latencies))
    # print(load_balancer.scheduling_delays)
    # print(sorted_lines[:10])

    app_map = load_balancer.app_cold_starts
    app_cold_starts = []
    for app in app_map.keys():
        num_cold, total = app_map[app]
        app_cold_starts.append(num_cold/total)
    
    mem = load_balancer.getMemUsage()
    time_index = list(range(len(mem)))
    xy = list(zip(time_index,mem))
    sendToReact(xy)

    if args.save_output:
        with open(f"latencies_{eval}.txt", "w") as file:
            file.write(",".join(map(str, load_balancer.latencies))) 

        with open(f"app_cold_start_{eval}.txt", "w") as file:
            file.write(",".join(map(str, app_cold_starts))) 
        
        with open(f"raw_cold_start_{eval}.txt", "w") as file:
            file.write(",".join(map(str, load_balancer.cold_starts))) 
        with open(f"mem_usage_{eval}.txt", "w") as file:
            file.write(",".join(map(str, mem)))

    # plot_cold_start = False
    # plot_mem = True
    # plot_latency = False
    # plot_delay = False

    # plt.grid(True)
    # plot_mem_graph(load_balancer, args)
    if plot_mem:
        # plt.subplot(2, 2, 2)
        plt.plot(mem)  # Adjust bins as needed
        plt.xlabel('Time (sec)')
        plt.ylabel('Mem Usage (MB)')
        plt.title(f'Mem Usage Over Time with {eval} ({args.num_traces} Function Calls)')

    # Plot CDF of app cold start percentage
    if plot_cold_start:
        plt.subplot(2, 2, 1)
        plt.hist(app_cold_starts, bins=40, density=True, histtype='step', cumulative=True, label='CDF')
        # Customize the plot
        plt.xlim(0, 1)
        plt.xlabel('App Cold Start %')
        plt.ylabel('Cumulative Probability')
        plt.title(f'CDF of App Cold Start % with {eval} ({args.num_traces} Function Calls)')
        plt.legend()

    # plot histogram of latencies on log scale
    if plot_latency:
        plt.subplot(2, 2, 3)
        plt.hist(load_balancer.latencies, bins=40)
        plt.yscale("log")
        # Customize the plot
        plt.xlabel('Latency (sec)')
        plt.ylabel('Frequency')
        plt.title(f'Histogram of Latency with {eval} ({args.num_traces} Function Calls)')
        plt.grid(True)

    # plot histogram of scheduling delays on log scale
    if plot_delay:
        plt.subplot(2, 2, 4)
        plt.hist(load_balancer.scheduling_delays, bins=40)
        plt.yscale("log")
        # Customize the plot
        plt.xlabel('Scheduling Delay (sec)')
        plt.ylabel('Frequency')
        plt.title(f'Histogram of Scheduling Delay with {eval} ({args.num_traces} Function Calls)')
        plt.grid(True)

    # plt.tight_layout()
    # plt.show()

# def plot_mem_graph(load_balancer, args):
#     # Plot graph of memory usage over time
#     if plot_mem:
#         # plt.subplot(2, 2, 2)
#         plt.plot(mem)  # Adjust bins as needed
#         plt.xlabel('Time (sec)')
#         plt.ylabel('Mem Usage (MB)')
#         plt.title(f'Mem Usage Over Time with {eval} ({args.num_traces} Function Calls)')



if __name__ == "__main__":
    main()