"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { Upload } from "lucide-react"
import type React from "react"

export default function FileUpload() {
  const [file, setFile] = useState<File | null>(null)
  const [description, setDescription] = useState("")
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

      const descResponse = await fetch("/api/desc", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ id: data.id, description }),
      })

      if (!descResponse.ok) throw new Error("Description upload failed")

      setMessage(`Upload successful! Video ID: ${data.id}`)
    } catch (error) {
      console.error("Upload error:", error)
      setMessage("Upload failed. Please try again.")
    } finally {
      setUploading(false)
      setFile(null)
      setDescription("")
    }
  }

  return (
    <div className="bg-white bg-opacity-10 rounded-lg p-6">
      <h2 className="text-2xl font-bold text-white mb-4">Upload Your Content</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="relative">
          <input type="file" accept="video/*,image/*" onChange={handleFileChange} className="hidden" id="file-upload" />
          <label
            htmlFor="file-upload"
            className="flex items-center justify-center w-full px-4 py-4 border-2 border-dashed border-[#3BF4C7] rounded-lg text-sm font-medium text-white hover:border-white hover:bg-white hover:bg-opacity-10 transition duration-300 ease-in-out cursor-pointer"
          >
            {file ? (
              file.name
            ) : (
              <>
                <Upload className="mr-2" />
                Choose a file to upload
              </>
            )}
          </label>
        </div>

        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Enter file description"
          className="w-full px-3 py-2 text-white bg-white bg-opacity-10 rounded-lg border border-[#3BF4C7] focus:outline-none focus:ring-2 focus:ring-[#3BF4C7]"
          rows={4}
        />

        <motion.button
          type="submit"
          disabled={uploading || !file}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className={`w-full px-4 py-3 text-midnight-blue font-semibold rounded-lg shadow-lg focus:outline-none focus:ring-2 focus:ring-opacity-50 ${
            uploading || !file
              ? "bg-gray-400 cursor-not-allowed"
              : "bg-[#3BF4C7] hover:bg-[#008A90] hover:text-white focus:ring-[#008A90]"
          } transition duration-300 ease-in-out transform`}
        >
          {uploading ? "Uploading..." : "Upload and Protect"}
        </motion.button>
      </form>

      {message && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className={`mt-4 p-3 text-sm rounded-lg ${
            message.includes("successful")
              ? "bg-green-500 bg-opacity-20 text-green-100"
              : "bg-red-500 bg-opacity-20 text-red-100"
          }`}
        >
          {message}
        </motion.div>
      )}
    </div>
  )
}

