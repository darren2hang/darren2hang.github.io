import { Link } from "react-router-dom";
import cacheImg from "../../assets/cache_example.png"
import histImg from "../../assets/histogram_example.png"
import keepAliveImg from "../../assets/keep_alive_example.png"
import "./ColdStartApp.css"

export default function ColdStartHome() {
    return (
        <div>
            <header>
                <Link to="/projects/reducing-cold-starts" className="selected">About</Link>
                <Link to="/projects/reducing-cold-starts/simulation">Simulation</Link>
            </header>
            <div className="main_page">
                <h1>About: Cold Starts in Serverless Applications</h1>
                <div className="content">
                    <p>
                        Serverless applications are hosted on serverless cloud platforms.
                        Users uploaded a function to cloud providers instead of reserving a VM.
                        The provider will run the function when it is triggered instead of having a server on 24/7 dedicated to the server.
                    </p>

                    <p>
                        This allows the user to save costs because they don't need to pay for a server 100% of the time and only need to pay for when their function is being ran.
                    </p>

                    <p>
                        However, this type of paradigm leads to an issue known as cold starts. When a function is triggered, the cloud provider may need to allocate a VM and schedule the function on the VM. This can incur additionally latency.
                    </p>

                    <p>
                        Many policies exist to mitigate cold starts. Most policies involve keeping dedicated VMs around and trying to predict the next function invocation. The goal is that the policy decides the correct VM to keep around, so that the next function invocation occurs when the dedicated VM is still on.
                    </p>

                    <p>This simulation supports 4 different cold start mitigation policies.</p>

                    <h3>Fixed Keep Alive Policy</h3>
                    <div className="horizontal-image-wrapper">
                        <div className="text-wrapper">
                        <p>
                            The fixed keep alive policy will keep a VM around for a fixed time, ex. 10 minutes, after a function finishes executing.
                            The hope is that after a function is called, it will be called again shortly after. This policy is not adaptive to different function workloads.
                        </p>
                        <p>
                            The figure on the right shows the memory usage of the fixed keep alive policy using a 10 minute keep alive period evaluated on a function workload where 1 function is invoked every 20 minutes.
                            The red lines are the function invocation times and red indicates it is a cold start. As we see, the keep alive time is not long enough, and the VM is deleted by the time the next function call occurs.
                        </p>
                        </div>
                        <img src={keepAliveImg}/>
                    </div>
                    <h3>Histogram Policy</h3>
                    <div className="horizontal-image-wrapper">
                        <div className="text-wrapper">
                        <p>
                            This policy comes from <a href="https://www.usenix.org/conference/atc20/presentation/shahrad">Microsoft Research</a> and uses a histogram of inter-arrival times between function calls.
                            The histogram is used to estimate the amount of time inbetween function calls. The key insight is that when we are waiting for the next function call, we can unload the function code and any library code from memory.
                            This can reduce the total memory. If we can predict the correct time before the next function call, we can also reload the function code and library code back into memory right before the next function call.
                        </p>
                        <p>
                            The figure on the right shows the memory usage of the histogram policy evaluated on a function workload with a reoccuring function every 20 minutes.
                            The vertical lines indicate function invocations, with red indicating cold start and green indicating warm start.
                            The histogram requires a couple function calls before learning the pattern. Looking at the final 3 function invocations, 
                            we can see that the function is unloaded from memory after function execution and loaded back into memory just before the next function call, resulting in a warm start.
                        </p>
                        </div>
                        <img src={histImg} />
                    </div>
                    <h3>Caching Policy</h3>
                    <div className="horizontal-image-wrapper">
                    <div className="text-wrapper">
                        <p>
                            This approach comes from <a href="https://dl.acm.org/doi/10.1145/3445814.3446757">Indiana University</a> and views predicting the next function call as a caching problem. A dedicated VM for a function is equivalent to having a piece of data in the cache. A cold start where we have to allocate and load a VM is equivalent to fetch data from disk.
                            Thus, we can set a limit on the number of VMs we want around and then use a cache eviction policy to determine which VMs to keep and evict. This will keep a set of "hot" VMs that are most likely to be called next.
                        </p>
                        <p>
                            The figure on the right shows the memory usage of the cache policy evaluated on a workload where a function is invoked every 20 minutes. 
                            Since there is only 1 function, 1 VM is only ever needed and no VM evictions occur. Thus, the memory usage is constant as the VM is fully loaded until evicted. We get all warm starts after the initial cold start.
                        </p>
                        </div>
                        <img src={cacheImg}/>
                    </div>
                    <h3>Hybrid Histogram + Cache Policy</h3>
                    <div>
                        <p>
                            This policy adds the cache policy to the histogram policy. The cache policy is used as a limit on the max number of VMs. Otherwise, the histogram policy will behave as normal, loading and unloading function code from memory within a VM.
                        </p>
                        <p>
                            For a one function workload, the hybrid policy would behave the exact same as the histogram only policy as there would be no evictions.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}