import React, { useState } from "react";
import "./UploadFileComponent.css";

import JSZip from "jszip";

interface UploadFileComponentProps {
    setDownloading: React.Dispatch<React.SetStateAction<boolean>>;
    setTextInput: React.Dispatch<React.SetStateAction<string>>;
    setFilename: React.Dispatch<React.SetStateAction<string | null>>;
}

const UploadFileComponent: React.FC<UploadFileComponentProps> = ({ setDownloading, setTextInput, setFilename }) => {
    const [showPopup, setShowPopup] = useState(false);

    const handleFileChange = (event: any) => {
        const file = event.target.files?.[0];
        if (!file) return;
        setFilename(file.name);

        const reader = new FileReader();
        reader.onload = (e: any) => {
            const result = e.target.result;
            if (typeof result === "string") {
                setTextInput(result); // full multiline string
            }
        };
        reader.readAsText(file);
        setShowPopup(false);
    };

    const downloadAndExtractAzureTrace = async () => {
        try {
            // setDownloadingAzure(true);
            setDownloading(true)
            const response = await fetch("https://raw.githubusercontent.com/darren2hang/public-microsoft-azure-trace/main/AzureFunctionsInvocationTraceForTwoWeeksJan2021.zip");
            const arrayBuffer = await response.arrayBuffer();
            console.log("successfully downloaded zip file")

            // Step 2: Load the ZIP file using JSZip
            const zip = await JSZip.loadAsync(arrayBuffer);

            // Step 3: Get the file list (in this case, it's assumed there's only one file)
            const fileName = Object.keys(zip.files)[0]; // Get the first file's name
            const file = zip.files[fileName]; // Get the file object

            // Step 4: Extract the file's content (assuming it's a text file)
            const fileData = await file.async("text"); // Extract as text

            const newlineIndex = fileData.indexOf("\n");
            const restOfText = fileData.slice(newlineIndex + 1);
            // Step 5: Save the text content to the state
            setFilename("AzureFunctionsInvocationTraceForTwoWeeksJan2021.txt")
            setTextInput(restOfText);
        } catch (err) {
            console.error("Error reading RAR:", err);
            alert("Unable to load and extract the RAR file.");
        }
        //   setUsingAzure(true);
        //   setDownloadingAzure(false);
        setDownloading(false);
    };

    return (
        <div>
            <button onClick={() => setShowPopup(true)} className="use-file-button">
                Use File
            </button>

            {showPopup && (
                <div className="popup-overlay">
                    <div className="popup-content">
                        <h3>Select File Option</h3>
                        <button
                            className="popup-button"
                            onClick={() => {
                                setShowPopup(false);
                                downloadAndExtractAzureTrace();
                            }}
                        >
                            Use Azure Trace
                        </button>

                        <div className="file-input-wrapper">
                            Or upload file:
                            <label htmlFor="file-upload" className="file-upload-label">
                                <input
                                    id="file-upload"
                                    type="file"
                                    onChange={handleFileChange}
                                />
                                Choose File
                            </label>
                        </div>

                        <button
                            className="popup-close-button"
                            onClick={() => setShowPopup(false)}
                        >
                            Close
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default UploadFileComponent;
