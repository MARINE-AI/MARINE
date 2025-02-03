"use client"

import { useState } from "react"

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState("")

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    setUploading(true)
    setMessage("")

    try {
      const formData = new FormData()
      formData.append("file", file)

      const response = await fetch("http://localhost:8080/upload", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) throw new Error("Upload failed")

      const data = await response.json()
      setMessage(`Upload successful! Video ID: ${data.id}`)
    } catch (error) {
      console.error("Upload error:", error)
      setMessage("Upload failed. Please try again.")
    } finally {
      setUploading(false)
      setFile(null)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        <h2 className="text-3xl font-bold text-center mb-8 text-gray-800">Upload Your Video</h2>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="relative">
            <input type="file" accept="video/*" onChange={handleFileChange} className="hidden" id="file-upload" />
            <label
              htmlFor="file-upload"
              className="flex items-center justify-center w-full px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:border-blue-500 hover:bg-blue-50 transition duration-150 ease-in-out cursor-pointer"
            >
              {file ? file.name : "Choose a video file"}
            </label>
          </div>

          <button
            type="submit"
            disabled={uploading || !file}
            className={`w-full px-4 py-3 text-white font-semibold rounded-lg shadow-md focus:outline-none focus:ring-2 focus:ring-opacity-75 ${
              uploading || !file
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700 focus:ring-blue-400"
            } transition duration-200 ease-in-out transform hover:scale-105`}
          >
            {uploading ? (
              <span className="flex items-center justify-center">
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Uploading...
              </span>
            ) : (
              "Upload Video"
            )}
          </button>
        </form>

        {message && (
          <div
            className={`mt-6 p-4 text-sm rounded-lg ${
              message.includes("successful") ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
            }`}
          >
            {message}
          </div>
        )}
      </div>
    </div>
  )
}

