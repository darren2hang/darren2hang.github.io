import { useEffect, useState, useRef } from "react";
import Plot from 'react-plotly.js';
import { LTTB } from 'downsample';
import { Link } from "react-router-dom";
import "./ColdStartApp.css"
import Select from "react-select";
import CreatableSelect from "react-select/creatable";

type OptionType = { value: string; label: string };

function ColdStartApp() {
  // const [output, setOutput] = useState<string>("");
  const [xData, setXData] = useState<number[]>([]);
  const [yData, setYData] = useState<number[]>([]);
  const [textInput, setTextInput] = useState<string>(
    `app,func,end_timestamp,duration,memory(optional)
a,1,1200,0.1
a,1,2400,0.1
a,1,3600,0.1
a,1,4800,0.1
a,1,6000,0.1
a,1,7200,0.1
a,1,8400,0.1
a,1,9600,0.1
a,1,10800,0.1
a,1,12000,0.1
a,1,13200,0.1
a,1,14400,0.1
a,1,15600,0.1
a,1,16800,0.1
a,1,18000,0.1
a,1,19200,0.1
a,1,20400,0.1
a,1,21600,0.1
a,1,22800,0.1
a,1,24000,0.1
a,1,25200,0.1
a,1,26400,0.1
a,1,27600,0.1
a,1,28800,0.1
a,1,140000,0.1
a,1,145000,0.1`);
  const workerRef = useRef<Worker>(null);
  const [status, setStatus] = useState("Loading...");

  const [cacheOptions, setCacheOptions] = useState([
    { value: "8", label: "8" },
    { value: "16", label: "16" },
    { value: "32", label: "32" },
    { value: "64", label: "64" },
    { value: "128", label: "128" },
    { value: "256", label: "256" }
  ]);

  const [cacheSize, setCacheSize] = useState<OptionType | null>(null);

  const policies = [
    { value: "fixed_keep_alive", label: "Keep Alive" },
    { value: "histogram_only", label: "Histogram Only" },
    { value: "cache_only", label: "Cache Only" },
    { value: "histogram_cache", label: "Hybrid Histogram + Cache" }
  ]

  const [policy, setPolicy] = useState<OptionType | null>(null);

  const [keepAliveOptions, setKeepAliveOptions] = useState([
    { value: "10", label: "10" },
    { value: "20", label: "20" },
  ]);

  const [keepAliveTime, setKeepAliveTime] = useState<OptionType | null>(null);

  useEffect(() => {
    const worker = new Worker(new URL("./PyodideWorker.mts", import.meta.url), {
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
        // console.log(payload)
        // console.log("payload x")
        // console.log(payload.length)
        const n = Math.floor(payload.length / 30);
        const downsampled = Array.from(LTTB(payload, n)); // Downsample to 1000 points
        const downsampledX = downsampled.map((d: any) => d[0]);
        const downsampledY = downsampled.map((d: any) => d[1]);
        setXData(downsampledX);
        setYData(downsampledY);
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
    setXData([]);
    setYData([]);
    setStatus("Running...");
    workerRef.current?.postMessage({
      type: "run",
      input_file: textInput,
      policy: policy == null ? "histogram_cache" : policy.value,
      // keepAliveTime: parseInt(keepAliveTime?.value),
      // cacheSize: parseInt(cacheSize?.value)
    });
  };

  const handleCreateNumOptions = (inputValue: string, setOptions: React.Dispatch<React.SetStateAction<{
    value: string;
    label: string;
  }[]>>, setVal: React.Dispatch<React.SetStateAction<OptionType | null>>) => {
    inputValue = inputValue.replace(/^0+(?=\d)/, '');
    if (!/^\d+$/.test(inputValue)) {
      alert("Please enter a valid number.");
      return;
    }

    const newOption = { value: inputValue, label: inputValue };
    setOptions((prev) => [...prev, newOption]);
    setVal(newOption);
  };

  const handleCreateDecimalOptions = (inputValue: string, setOptions: React.Dispatch<React.SetStateAction<{
    value: string;
    label: string;
  }[]>>, setVal: React.Dispatch<React.SetStateAction<OptionType | null>>) => {
    inputValue = inputValue.replace(/^0+(?=\d)/, '');
    if (!/^\d+(\.\d+)?$/.test(inputValue)) {
      alert("Please enter a valid number.");
      return;
    }

    const newOption = { value: inputValue, label: inputValue };
    setOptions((prev) => [...prev, newOption]);
    setVal(newOption);
  };

  const allInputsFilledOut = () => {
    if (policy == null) {
      return false;
    }
    
    if (policy.value == "fixed_keep_alive" && keepAliveTime == null) {
      return false;
    }

    if ((policy.value == "cache_only" || policy.value == "histogram_cache") && cacheSize == null) {
      return false;
    }
    return true;
  }

  return (
    <div>
      <header>
        <Link to="/projects/reducing-cold-starts">About</Link>
        <Link to="/projects/reducing-cold-starts/simulation" className="selected">Simulation</Link>
      </header>
      <div className="main_page">
        <h1>React + Pyodide (TypeScript)</h1>
        <div className="simulation-page">
          <div className="simulation-inputs">
            <div className="simulation-configs">
              <div className="config-dropdown">
                Policy for Mitigating Cold Starts
                <Select
                  id="Policy"
                  isClearable
                  options={policies}
                  value={policy}
                  onChange={setPolicy}
                />
              </div>
              {policy?.value == "fixed_keep_alive" &&
                <div className="config-dropdown">
                  Keep Alive Time (minutes)
                  <CreatableSelect
                    id="keepAliveSelect"
                    isClearable
                    options={keepAliveOptions}
                    value={keepAliveTime}
                    onChange={setKeepAliveTime}
                    onCreateOption={val => handleCreateDecimalOptions(val, setKeepAliveOptions, setKeepAliveTime)}
                    placeholder="Specify how many minutes to keep a VM around after function execution"
                  />
                </div>
              }
              {(policy?.value == "histogram_cache" || policy?.value == "cache_only") &&
                <div className="config-dropdown">
                  Number of VMs/Cache Size
                  <CreatableSelect
                    id="cacheSizeSelect"
                    isClearable
                    options={cacheOptions}
                    value={cacheSize}
                    onChange={setCacheSize}
                    onCreateOption={val => handleCreateNumOptions(val, setCacheOptions, setCacheSize)}
                    placeholder="Specify the max number of VMs"
                  />
                </div>
              }
            </div>
            <button onClick={runPython} disabled={!allInputsFilledOut()}>Run Python</button>
            <p>{status}</p>
            <textarea
              value={textInput}
              onChange={e => setTextInput(e.target.value)}
            />
          </div>
          <div className="simulation-results">
            {(true || xData.length > 0) && (
              <Plot
                data={[
                  {
                    x: xData,
                    y: yData,
                    type: 'scattergl',
                    mode: 'lines',
                    line: { color: 'blue' },
                  },
                ]}
                layout={{ autosize: true, title: 'Memory Usage Over Time' }}
              />
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

export default ColdStartApp;
