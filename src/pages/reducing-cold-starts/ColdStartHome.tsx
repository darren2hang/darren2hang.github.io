import { Link } from "react-router-dom";

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
                    <div>
                        <p>
                            The fixed keep alive policy will keep a VM around for a fixed time, ex. 10 minutes, after a function finishes executing.
                            The hope is that after a function is called, it will be called again shortly after. This policy is not adaptive to different function workloads.
                        </p>
                    </div>
                    <h3>Histogram Policy</h3>
                    <div>
                        <p>
                            This policy comes from <a href="https://www.usenix.org/conference/atc20/presentation/shahrad">Microsoft Research</a> and uses a histogram of inter-arrival times between function calls.
                            The histogram is used to estimate the amount of time inbetween function calls. The key insight is that when we are waiting for the next function call, we can unload the function code and any library code from memory.
                            This can reduce the total memory. If we can predict the correct time before the next function call, we can also reload the function code and library code back into memory right before the next function call.
                        </p>
                    </div>
                    <h3>Caching Policy</h3>
                    <div>
                        <p>
                            This approach comes from <a href="https://dl.acm.org/doi/10.1145/3445814.3446757">Indiana University</a> and views predicting the next function call as a caching problem. A dedicated VM for a function is equivalent to having a piece of data in the cache. A cold start where we have to allocate and load a VM is equivalent to fetch data from disk.
                            Thus, we can set a limit on the number of VMs we want around and then use a cache eviction policy to determine which VMs to keep and evict. This will keep a set of "hot" VMs that are most likely to be called next.
                        </p>
                    </div>
                    <h3>Hybrid Histogram + Cache Policy</h3>
                    <div>
                        <p>
                            This policy adds the cache policy to the histogram policy. The cache policy is used as a limit on the max number of VMs. Otherwise, the histogram policy will behave as normal, loading and unloading function code from memory within a VM.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}