import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Projects from "./pages/Projects";
import ColdStartHome from "./pages/reducing-cold-starts/ColdStartHome";
import ColdStartApp from "./pages/reducing-cold-starts/ColdStartApp";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/home" element={<Home />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/reducing-cold-starts" element={<ColdStartHome />} />
        <Route path="/projects/reducing-cold-starts/simulation" element={<ColdStartApp />} />
      </Routes>
    </Router>
  );
}

export default App;