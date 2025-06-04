import { useEffect, useState, useRef } from "react";
import Plot from 'react-plotly.js';
import { LTTB, DataPoint } from 'downsample';
import { Link } from "react-router-dom";
import "./ColdStartApp.css"
import Select from "react-select";
import CreatableSelect from "react-select/creatable";

import spinnerImg from "../../assets/spinner.png";

import UploadFileComponent from "./UploadFileComponent";

type OptionType = { value: string; label: string };

function ColdStartApp() {
  // const [output, setOutput] = useState<string>("");
  const [xData, setXData] = useState<number[]>([]);
  const [yData, setYData] = useState<number[]>([]);
  const [textInput, setTextInput] = useState<string>(
    `a,1,1200,0.1
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

  const [downloadingAzure, setDownloadingAzure] = useState(false);

  const [memData, setMemData] = useState(null);
  const [latencyData, setLatencyData] = useState(null);
  const [coldStartData, setColdStartData] = useState(null);
  const [coldStartRate, setColdStartRate] = useState(null);

  const [filename, setFilename] = useState<string | null>(null);

  const [showConfig, setShowConfig] = useState(false);

  const [cvThreshold, setCvThreshold] = useState(2.0);
  const [vmThreshold, setVmThreshold] = useState(0.5);
  const [cpuRateWindow, setCpuRateWindow] = useState(5.0);
  const [maxHist, setMaxHist] = useState(240);
  const [headPer, setHeadPer] = useState(5);
  const [tailPer, setTailPer] = useState(99);
  const [vmStart, setVmStart] = useState(2.5);
  const [vmEnd, setVmEnd] = useState(2.0);
  const [vmMem, setVmMem] = useState(300.0);
  const [memLoadRate, setMemLoadRate] = useState(2000.0);

  const [keepAliveError, setKeepAliveError] = useState("");
  const [cacheSizeError, setCacheSizeError] = useState("");

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
        // console.log("App.tsx received data")
        // console.log(payload)
        // console.log("payload x")
        // console.log(payload.length)
        const n = Math.floor(payload[0].length / 30);
        // console.log(payload)
        const dataInPairForm = []
        for (let i = 0; i < payload[0].length; i++) {
          const p = [payload[0][i], payload[1][i]] as DataPoint;
          dataInPairForm.push(p);
        }
        // console.log(dataInPairForm)
        const downsampled = Array.from(LTTB(dataInPairForm, n)); // Downsample to 1000 points
        const downsampledX = downsampled.map((d: any) => d[0]);
        const downsampledY = downsampled.map((d: any) => d[1]);
        console.log(downsampled)
        setXData(downsampledX);
        setYData(downsampledY);
      }

      if (type == "final_data") {
        setMemData(payload.memData);
        setLatencyData(payload.latencyData);
        setColdStartData(payload.coldStartData);
        setColdStartRate(payload.coldStartRate);
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
    setColdStartRate(null);
    setColdStartData(null);
    setMemData(null);
    setLatencyData(null);
    workerRef.current?.postMessage({
      type: "run",
      input_file: textInput,
      policy: policy == null ? "histogram_cache" : policy.value,
      keepAliveTime: keepAliveTime != null ? keepAliveTime?.value : "10",
      cacheSize: cacheSize != null ? cacheSize?.value : "256",
      cvThreshold: String(cvThreshold),
      vmThreshold: String(vmThreshold),
      cpuRateWindow: String(cpuRateWindow),
      maxHist: String(maxHist),
      headPer: String(headPer),
      tailPer: String(tailPer),
      vmStart: String(vmStart),
      vmEnd: String(vmEnd),
      vmMem: String(vmMem),
      memLoadRate: String(memLoadRate),
    });
  };

  const handleCreateNumOptions = (inputValue: string, setOptions: React.Dispatch<React.SetStateAction<{
    value: string;
    label: string;
  }[]>>, setVal: React.Dispatch<React.SetStateAction<OptionType | null>>) => {
    inputValue = inputValue.replace(/^0+(?=\d)/, '');
    if (!/^\d+$/.test(inputValue)) {
      setCacheSizeError("Please enter a valid non-negative number.")
      setVal(null);
      return;
    }
    setCacheSizeError("");
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
      setKeepAliveError("Please enter a valid non-negative number.")
      setVal(null);
      return;
    }
    setKeepAliveError("");
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

  const handleDownload = (content: any, name: string) => {
    // const content = data.join("\n"); // or JSON.stringify(data, null, 2)
    const blob = new Blob([JSON.stringify(content)], { type: "text/plain;charset=utf-8" });

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name + Date.now() + ".txt"; // you can change file name/extension
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const overMaxLineCount = (text: string): boolean => {
    let count = 0;
    for (let i = 0; i < text.length; i++) {
      if (text[i] === '\n') count++;
      if (count > 2000) {
        return true;
      }
    }
    return false;
  };

  const getTextOverflowMsg = (): string => {
    let msg = "";
    if (filename == null) {
      msg += "Please upload as file instead";
    } else {
      msg += filename + " successfully loaded";
    }
    msg += "\n\nTrace too large to be displayed (display limit of 2000 lines)"
    return msg;
  }

  return (
    <div>
      <header>
        <Link to="/projects/reducing-cold-starts">About</Link>
        <Link to="/projects/reducing-cold-starts/simulation" className="selected">Simulation</Link>
      </header>
      <div className="main_page">
        <h1>Serverless Functions Simulation</h1>
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
                    onChange={v => {
                      setKeepAliveTime(v);
                      setKeepAliveError("");
                    }}
                    onCreateOption={val => handleCreateDecimalOptions(val, setKeepAliveOptions, setKeepAliveTime)}
                    placeholder="Specify how many minutes to keep a VM around after function execution"
                  />
                  {keepAliveError && <div style={{ color: "red", marginTop: 4 }}>{keepAliveError}</div>}
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
                    onChange={v => {
                      setCacheSize(v);
                      setCacheSizeError("");
                    }}
                    onCreateOption={val => handleCreateNumOptions(val, setCacheOptions, setCacheSize)}
                    placeholder="Specify the max number of VMs"
                  />
                  {cacheSizeError && <div style={{ color: "red", marginTop: 4 }}>{cacheSizeError}</div>}
                </div>
              }
              <div className="moreConfigWrapper">
                <button onClick={() => setShowConfig(true)}>More Configs</button>
                {showConfig &&
                  <div className="popup-overlay">
                    <div className="popup-content">
                      <div className="config-input">
                        <label htmlFor="cvInput">CV Threshold for Histogram</label>
                        <input id="cvInput" type="number" value={cvThreshold}
                          onChange={e => setCvThreshold(Math.abs(parseFloat(e.target.value)))} />
                      </div>
                      <div className="config-input">
                        <label htmlFor="vmThreshold">VM CPU Utilization Rate Autoscale Threshold</label>
                        <input id="vmThreshold" type="number" value={vmThreshold}
                          onChange={e => setVmThreshold(Math.abs(parseFloat(e.target.value)))} />
                      </div>
                      <div className="config-input">
                        <label htmlFor="cpuWindow">Window to calculate VM CPU Usage (sec)</label>
                        <input id="cpuWindow" type="number" value={cpuRateWindow}
                          onChange={e => setCpuRateWindow(Math.abs(parseFloat(e.target.value)))} />
                      </div>
                      <div className="config-input">
                        <label htmlFor="maxHist">Max Size of Histogram (minutes)</label>
                        <input id="maxHist" type="number" value={maxHist}
                          onChange={e => setMaxHist(Math.abs(parseInt(e.target.value)))} />
                      </div>
                      <div className="config-input">
                        <label htmlFor="headPer">Head Percentile for Histogram</label>
                        <input id="headPer" type="number" value={headPer}
                          onChange={e => setHeadPer(Math.abs(parseInt(e.target.value)))} />
                      </div>
                      <div className="config-input">
                        <label htmlFor="tailPer">Tail Percentile for Histogram</label>
                        <input id="tailPer" type="number" value={tailPer}
                          onChange={e => setTailPer(Math.abs(parseInt(e.target.value)))} />
                      </div>
                      <div className="config-input">
                        <label htmlFor="vmStart">Time to Start a VM (sec)</label>
                        <input id="vmStart" type="number" value={vmStart}
                          onChange={e => setVmStart(Math.abs(parseFloat(e.target.value)))} />
                      </div>
                      <div className="config-input">
                        <label htmlFor="vmEnd">Time to Delete a VM (sec)</label>
                        <input id="vmEnd" type="number" value={vmEnd}
                          onChange={e => setVmEnd(Math.abs(parseFloat(e.target.value)))} />
                      </div>
                      <div className="config-input">
                        <label htmlFor="vmMem">Memory Overhead of a VM (MB)</label>
                        <input id="vmMem" type="number" value={vmMem}
                          onChange={e => setVmMem(Math.abs(parseFloat(e.target.value)))} />
                      </div>
                      <div className="config-input">
                        <label htmlFor="memRate">Memory Load Rate for Functions (MB/s)</label>
                        <input id="memRate" type="number" value={memLoadRate}
                          onChange={e => setMemLoadRate(Math.abs(parseFloat(e.target.value)))} />
                      </div>
                      <button
                        className="popup-close-button"
                        onClick={() => setShowConfig(false)}
                      >
                        Close
                      </button>
                    </div>
                  </div>
                }
              </div>
            </div>
            <button onClick={runPython} disabled={!allInputsFilledOut() || downloadingAzure || status == "Running..."}>Run Python</button>
            <p>
              {status}
              <br />
              {coldStartRate && ("Cold start rate: " + coldStartRate)}
            </p>
            <div id="inputTraceWrapper">
              <div id="inputTraceHeader">
                <label htmlFor="inputTraces">app, func, end_timestamp(s), duration(s), <span  id="optional">(optional: memory in MB)</span></label>
                {/* <button id="azureDownloadButton" onClick={downloadAndExtractAzureTrace}>Use Data From Azure Trace</button> */}
                <UploadFileComponent
                  setDownloading={setDownloadingAzure}
                  setTextInput={setTextInput}
                  setFilename={setFilename}
                />
              </div>
              <div id="textAreaWrapper">
                <textarea
                  id="inputTraces"
                  value={!overMaxLineCount(textInput) ? textInput : getTextOverflowMsg()}
                  onChange={e => setTextInput(e.target.value)}
                  disabled={downloadingAzure || overMaxLineCount(textInput)}
                />
                {downloadingAzure &&
                  <div id="spinner-wrapper">
                    <p>Downloading Azure Trace...</p>
                    <img src={spinnerImg} className="loader" />
                  </div>}
              </div>
            </div>
          </div>
          <div className="simulation-results">
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
              layout={{
                autosize: true,
                title: { text: 'Memory Usage Over Time' },
                xaxis: {
                  title: { text: 'Time (sec)' }
                },
                yaxis: {
                  title: { text: 'Memory Usage (MB)' }
                }
              }}
              style={{ width: '100%' }}
            />
            <div id="downloadContainer">
              <button
                id="memDownload"
                disabled={status != "Simulation complete."}
                onClick={() => handleDownload(memData, "memory_usage")}>
                Download Memory Usage
              </button>
              <button
                id="latencyDownload"
                disabled={status != "Simulation complete."}
                onClick={() => handleDownload(latencyData, "latency_data")}
              >Download Latencies</button>
              <button
                id="coldStartDownload"
                disabled={status != "Simulation complete."}
                onClick={() => handleDownload(coldStartData, "cold_start_data")}
              >Download Cold Starts</button>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

export default ColdStartApp;
