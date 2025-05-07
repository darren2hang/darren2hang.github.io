import { Link } from "react-router-dom";

export default function Home() {
    return (
        <div>
            <header>
                <Link to="/" className="selected">Home</Link>
                <Link to="/projects">Projects</Link>
            </header>
            <div className="main_page">
                <h1>Hi! I'm Darren Zhang</h1>
                <div className="content">
                    I'm a aspiring software engineer interested in distributed systems, LLMs, security, and building anything cool with code.
                </div>
            </div>
        </div>
    );
}