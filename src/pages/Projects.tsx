import { Link } from "react-router-dom";


export default function Projects() {
    return (
        <div>
            <header>
                <Link to="/">Home</Link>
                <Link to="/projects" className="selected">Projects</Link>
            </header>
            <div className="main_page">
                <h1>Projects</h1>
                <div className="content">
                    <Link to="/projects/reducing-cold-starts">Addressing Cold Starts in Serverless Applications Simulation</Link>
                    <p><a href="https://playnet.uclaacm.com/">UCLA Playnet</a> made in collaboration with UCLA ACM TeachLA</p>
                </div>
            </div>
        </div>
    );
}