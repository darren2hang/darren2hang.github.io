import { useEffect, useState, useRef } from "react";
import Plot from 'react-plotly.js';

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
  // const [output, setOutput] = useState<string>("");
  const [data, setData] = useState<number[]>([]);
  const workerRef = useRef<Worker>(null);
  const [status, setStatus] = useState("Loading...");

  useEffect(() => {
    const worker = new Worker(new URL("./PyodideWorker.ts", import.meta.url), {
      type: "module",
    });

    workerRef.current = worker;

    worker.onmessage = (event) => {
      const { type, payload, error } = event.data;

      if (type === "ready") {
        setStatus("Ready to run Python!");
      }

      if (type === "data") {
        console.log("App.tsx received data")
        console.log(payload)
        setData(payload);
      }

      if (type === "done") {
        setStatus("Simulation complete.");
      }

      if (type === "error") {
        setStatus(`Error: ${error}`);
      }
    };

    worker.postMessage({ type: "init" });

    return () => worker.terminate();
  }, []);

  const runPython = () => {
    setData([]);
    setStatus("Running...");
    workerRef.current?.postMessage({ type: "run" });
  };


  // // Register the JS callback that Python will call
  // useEffect(() => {
  //   (window as any).onDataChunk = (proxyData: any) => {
  //     console.log("React received data chunk")
  //     // console.log(proxyData)
  //     var array: number [];
  //     if (proxyData.toJs) {
  //       console.log("converting proxy")
  //       array = proxyData.toJs({copy: true}); // full JS copy
  //       proxyData.destroy(); // ✨ important: free proxy
  //     } else {
  //       array = proxyData;
  //     }
  //     // console.log(array)
  //     const dataArr = [...array]
  //     setData(dataArr);
  //   };
  // }, []);

  // useEffect(() => {
  //   const loadPyodideScript = async () => {
  //     // Load the script from CDN
  //     const script = document.createElement("script");
  //     script.src = "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js";
  //     script.onload = async () => {
  //       const py = await window.loadPyodide();
  //       setPyodide(py);
  //     };
  //     script.onerror = () => {
  //       console.error("Failed to load Pyodide script.");
  //     };
  //     document.body.appendChild(script);
  //   };

  //   loadPyodideScript();
  // }, []);


  // const runPython = async () => {
  //   if (!pyodide) return;

  //   try {
  //     console.log("Starting process to run python code")
  //     const files = [
  //       "main.py",
  //       "Function.py",
  //       "Histogram.py",
  //       "LoadBalancer.py",
  //       "VM.py",
  //       "example_trace.txt",
  //       "test_trace_20min.txt",
  //       "AzureFunctionsInvocationTraceForTwoWeeksJan2021.txt"
  //     ]

  //     // Create a directory inside Pyodide's virtual FS
  //     if (!pyodide.FS.analyzePath("/scripts").exists) {
  //       pyodide.FS.mkdir("/scripts");
  //     }

  //     // Load each file
  //     for (const filename of files) {
  //       const response = await fetch(`/scripts/${filename}`);
  //       const code = await response.text();
  //       pyodide.FS.writeFile(`/scripts/${filename}`, code);
  //     }

  //     console.log(pyodide.FS.readdir('/scripts'));

  //     // Add /scripts to Python module search path
  //     await pyodide.runPythonAsync(`
  //       import sys
  //       sys.path.append('/scripts')
  //     `);
      
  //     // download packages
  //     const packages = [
  //       'numpy',
  //       'matplotlib',
  //     ]
  //     await Promise.all(
  //       packages.map((packageName: string) => pyodide.loadPackage(packageName))
  //     )
     
  //     console.log("Executing python script")
  //     // handle python command line arguments
  //     const args = ["main.py", "--num_traces", "all"];
  //     const argString = JSON.stringify(args);
  //     // execute python script
  //     await pyodide.runPythonAsync(`
  //       import sys, json
  //       sys.argv = json.loads('${argString}')

  //       exec(open('/scripts/main.py').read())  
  //     `)
  //     // const response = await fetch("python-scripts/main.py");
  //     // const code = await response.text();
  //     // await pyodide.runPythonAsync(code);

  //     // const mem_data = pyodide.globals.get("mem");
  //     // console.log(mem_data)
  //     // setData(mem_data);
  //     setOutput("finished running main.py")
  //   } catch(err) {
  //     console.log("Error: "+(err as Error).message)
  //     setOutput("Error: "+(err as Error).message);
  //   }

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
  // };

  return (
    <div style={{ padding: "2rem" }}>
      <h1>React + Pyodide (TypeScript)</h1>
      <button onClick={runPython}>Run Python</button>
      <p>{status}</p>

      {data.length > 0 && (
        <Plot
          data={[
            {
              y: data,
              type: 'scattergl',
              mode: 'lines',
              line: { color: 'blue' },
            },
          ]}
          layout={{ width: 800, height: 400, title: 'Memory Usage Over Time' }}
        />
        // <table border={1} cellPadding={10} style={{ marginTop: "1rem" }}>
        //   <thead>
        //     <tr>
        //       {Object.keys(data[0]).map((key) => (
        //         <th key={key}>{key}</th>
        //       ))}
        //     </tr>
        //   </thead>
        //   <tbody>
        //     {data.map((row, i) => (
        //       <tr key={i}>
        //           <td key={i+"row"}>{row}</td>
        //       </tr>
        //     ))}
        //   </tbody>
        // </table>
      )}
    </div>
  );
}

export default App;
