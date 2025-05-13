/// <reference lib="webworker" />

export { };
import { loadPyodide, PyodideInterface } from 'pyodide';

let pyodide: PyodideInterface;

// Declare global function for loadPyodide
// declare global {
//     var loadPyodide: (config?: { indexURL: string }) => Promise<any>;
//   }

self.onmessage = async (event) => {
  const {
    type,
    input_file,
    policy,
    keepAliveTime,
    cacheSize,
    cvThreshold,
    vmThreshold,
    cpuRateWindow,
    maxHist,
    headPer,
    tailPer,
    vmStart,
    vmEnd,
    vmMem,
    memLoadRate,
  } = event.data;

  if (type === 'init') {
    pyodide = await loadPyodide({
      indexURL: "https://cdn.jsdelivr.net/pyodide/v0.27.5/full/",
    });
    // pyodide = await loadPyodide();

    // Wrap the JS function in a Python-compatible proxy
    const sendToReact = (data: any) => {
      // console.log("in sendToReact")
      // console.log(data)
      const jsObj = data.toJs({ deep: true });
      // console.log(jsObj)
      self.postMessage({ type: 'data', payload: jsObj });
    };

    const sendFinalDataToReact = (data: any) => {
      // console.log("in sendToReact")
      // console.log(data)
      const jsObj = data.toJs({ deep: true });
      // console.log(jsObj)
      self.postMessage({
        type: 'final_data', payload: {
          memData: jsObj[0][1], // only send mem data, don't send time index
          latencyData: jsObj[1],
          coldStartData: jsObj[2],
          coldStartRate: jsObj[3]
        }
      });
    };

    pyodide.globals.set("sendToReact", pyodide.toPy(sendToReact));
    pyodide.globals.set("sendFinalDataToReact", pyodide.toPy(sendFinalDataToReact));

    self.postMessage({ type: 'ready' });
  }

  if (type === "run") {
    try {
      console.log("Starting process to run python code")
      const files = [
        "main.py",
        "Function.py",
        "Histogram.py",
        "LoadBalancer.py",
        "VM.py",
        "example_trace.txt",
        "test_trace_20min.txt",
        // "AzureFunctionsInvocationTraceForTwoWeeksJan2021.txt"
      ]

      // Create a directory inside Pyodide's virtual FS
      const fs = (pyodide.FS as any)
      if (!fs.analyzePath("/scripts").exists) {
        fs.mkdir("/scripts");
      }

      // Load each file
      for (const filename of files) {
        const response = await fetch(`/scripts/${filename}`);
        const code = await response.text();
        pyodide.FS.writeFile(`/scripts/${filename}`, code);
      }
      // create input file from react text input
      pyodide.FS.writeFile(`/scripts/input_file.txt`, input_file);

      console.log(pyodide.FS.readdir('/scripts'));

      // Add /scripts to Python module search path
      await pyodide.runPythonAsync(`
          import sys
          sys.path.append('/scripts')
        `);

      // download packages
      const packages = [
        'numpy',
        'matplotlib',
      ]
      await Promise.all(
        packages.map((packageName: string) => pyodide.loadPackage(packageName))
      )

      console.log("Executing python script")
      // handle python command line arguments

      // note: we need to pass all values as strings even if they are numbers
      const args = [
        "main.py",
        "--num_traces", "all",
        "--policy", policy,
        "--keep_alive_time", keepAliveTime,
        "--cache_size", cacheSize,
        "--cv_threshold", cvThreshold,
        "--vm_threshold", vmThreshold,
        "--cpu_rate_window", cpuRateWindow,
        "--max_hist", maxHist,
        "--head_percentile", headPer,
        "--tail_percentile", tailPer,
        "--vm_start", vmStart,
        "--vm_end", vmEnd,
        "--vm_mem", vmMem,
        "--mem_load_rate", memLoadRate
      ];
      const argString = JSON.stringify(args);
      // execute python script
      await pyodide.runPythonAsync(`
          import sys, json
          sys.argv = json.loads('${argString}')
  
          exec(open('/scripts/main.py').read())  
        `)
      self.postMessage({ type: "done" })
    } catch (err) {
      console.log("Error: " + (err as Error).message)
      self.postMessage({ type: "error", error: "Error: " + (err as Error).message });
    }
  }
};

