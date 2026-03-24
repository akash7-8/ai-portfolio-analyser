"use client";

import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  FileCheck,
  AlertCircle,
  Download,
  X,
} from "lucide-react";
import {
  parsePortfolioCSV,
  sampleCSVContent,
  type PortfolioAsset,
} from "@/lib/portfolioUtils";

interface CSVUploaderProps {
  onParsed: (assets: PortfolioAsset[]) => void;
}

export default function CSVUploader({ onParsed }: CSVUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      setError(null);
      setSuccess(false);

      if (!file.name.endsWith(".csv")) {
        setError("Please upload a .csv file.");
        setFileName(null);
        return;
      }

      setFileName(file.name);

      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        const result = parsePortfolioCSV(text);
        if (result.success) {
          setSuccess(true);
          setError(null);
          onParsed(result.data);
        } else {
          setError(result.error || "Invalid CSV format.");
          setSuccess(false);
        }
      };
      reader.onerror = () => {
        setError("Failed to read file.");
      };
      reader.readAsText(file);
    },
    [onParsed]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const clearFile = useCallback(() => {
    setFileName(null);
    setSuccess(false);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  const downloadSample = useCallback(() => {
    const blob = new Blob([sampleCSVContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sample_portfolio.csv";
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  return (
    <div className="flex flex-col gap-4">
      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => inputRef.current?.click()}
        className={`relative flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-10 cursor-pointer transition-all duration-300 ${
          isDragging
            ? "border-accent-teal bg-accent-teal/[0.06] scale-[1.01]"
            : success
              ? "border-positive/40 bg-positive/[0.04]"
              : error
                ? "border-negative/40 bg-negative/[0.04]"
                : "border-white/[0.1] bg-white/[0.02] hover:border-white/[0.2] hover:bg-white/[0.04]"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          onChange={handleInputChange}
          className="hidden"
        />

        <AnimatePresence mode="wait">
          {success ? (
            <motion.div
              key="success"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="flex flex-col items-center gap-2"
            >
              <div className="w-12 h-12 rounded-2xl bg-positive/10 flex items-center justify-center">
                <FileCheck size={22} className="text-positive" />
              </div>
              <p className="text-sm font-medium text-positive">
                File uploaded successfully
              </p>
              <div className="flex items-center gap-2 text-xs text-text-secondary">
                <span>{fileName}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    clearFile();
                  }}
                  className="p-0.5 rounded hover:bg-white/[0.1] transition-colors"
                >
                  <X size={12} />
                </button>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="upload"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-2"
            >
              <div
                className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-colors ${
                  isDragging
                    ? "bg-accent-teal/20"
                    : "bg-white/[0.04]"
                }`}
              >
                <Upload
                  size={22}
                  className={
                    isDragging ? "text-accent-teal" : "text-text-muted"
                  }
                />
              </div>
              <p className="text-sm text-text-secondary">
                <span className="font-medium text-text-primary">
                  Drop your CSV here
                </span>{" "}
                or click to browse
              </p>
              <p className="text-xs text-text-muted">
                CSV with Ticker and Quantity columns
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Error message */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -5, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -5, height: 0 }}
            className="flex items-center gap-2 text-xs text-negative px-3 py-2 rounded-xl bg-negative/[0.06] border border-negative/20"
          >
            <AlertCircle size={14} className="flex-shrink-0" />
            <span>{error}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Download sample */}
      <button
        onClick={downloadSample}
        className="flex items-center gap-2 text-xs text-text-muted hover:text-accent-teal transition-colors self-start"
      >
        <Download size={12} />
        Download sample CSV
      </button>
    </div>
  );
}
