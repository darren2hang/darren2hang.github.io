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
                </div>
            </div>
        </div>
    );
}