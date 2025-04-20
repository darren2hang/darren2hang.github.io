import { useEffect, useState } from "react";

// Pyodide types aren’t built-in, so we can loosely type it
type PyodideInterface = {
  runPythonAsync: (code: string) => Promise<any>;
  loadPackage: (packageName: string) => Promise<any>;
  globals: any;
  FS: any;
};

declare global {
  interface Window {
    loadPyodide: () => Promise<any>;
  }
}

function App() {
  const [pyodide, setPyodide] = useState<PyodideInterface | null>(null);
  const [output, setOutput] = useState<string>("");
  const [data, setData] = useState<Array<number>>([]);

  useEffect(() => {
    const loadPyodideScript = async () => {
      // Load the script from CDN
      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js";
      script.onload = async () => {
        const py = await window.loadPyodide();
        setPyodide(py);
      };
      script.onerror = () => {
        console.error("Failed to load Pyodide script.");
      };
      document.body.appendChild(script);
    };

    loadPyodideScript();
  }, []);


  const runPython = async () => {
    if (!pyodide) return;

    try {
      const files = [
        "main.py",
        "Function.py",
        "Histogram.py",
        "LoadBalancer.py",
        "VM.py",
        "example_trace.txt"
      ]

      // Create a directory inside Pyodide's virtual FS
      if (!pyodide.FS.analyzePath("/scripts").exists) {
        pyodide.FS.mkdir("/scripts");
      }

      // Load each file
      for (const filename of files) {
        const response = await fetch(`/scripts/${filename}`);
        const code = await response.text();
        pyodide.FS.writeFile(`/scripts/${filename}`, code);
      }

      console.log(pyodide.FS.readdir('/scripts'));

      // Add /scripts to Python module search path
      await pyodide.runPythonAsync(`
        import sys
        sys.path.append('/scripts')
      `);
      
      // download packages
      const packages = [
        'numpy',
        'matplotlib'
      ]
      await Promise.all(
        packages.map((packageName: string) => pyodide.loadPackage(packageName))
      )
     
      // execute python script
      await pyodide.runPythonAsync(`
        exec(open('/scripts/main.py').read())  
      `)
      // const response = await fetch("python-scripts/main.py");
      // const code = await response.text();
      // await pyodide.runPythonAsync(code);
      const mem_data = pyodide.globals.get("mem");
      setData(mem_data);
      setOutput("finished running main.py")
    } catch(err) {
      console.log("Error: "+(err as Error).message)
      setOutput("Error: "+(err as Error).message);
    }

    // await pyodide.runPythonAsync(`
    //   import json
    //   data = [
    //       {"name": "Alice", "score": 90},
    //       {"name": "Bob", "score": 85},
    //       {"name": "Charlie", "score": 92}
    //   ]
    //   json_data = json.dumps(data)
    // `);

    // const json = pyodide.globals.get("json_data");
    // const parsed: Array<string> = JSON.parse(json);
    // setData(parsed);
    // setOutput("Python code executed!");
  };

  return (
    <div style={{ padding: "2rem" }}>
      <h1>React + Pyodide (TypeScript)</h1>
      <button onClick={runPython}>Run Python</button>
      <p>{output}</p>

      {data.length > 0 && (
        <table border={1} cellPadding={10} style={{ marginTop: "1rem" }}>
          <thead>
            <tr>
              {Object.keys(data[0]).map((key) => (
                <th key={key}>{key}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i}>
                  <td key={i+"row"}>{row}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default App;
