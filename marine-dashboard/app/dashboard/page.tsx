"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import Sidebar from "../components/sidebar"
import { Upload, Database, Shield, Fingerprint } from "lucide-react"
import type React from "react" // Added import for React

export default function Dashboard() {
  const [dataAnalysisStatus, setDataAnalysisStatus] = useState<"pending" | "success">("pending")

  useEffect(() => {
    const timer = setTimeout(() => {
      setDataAnalysisStatus("success")
    }, 3000)

    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="flex bg-black min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6 ml-16 flex items-center justify-center">
        <div className="grid grid-cols-2 gap-8 max-w-6xl w-full">
          <DashboardBox
            title="Upload Your Video"
            icon={<Upload className="w-10 h-10" />}
            content="Upload your video along with descriptive data. Our advanced algorithms will process and protect your content across the web."
          />
          <DashboardBox
            title="Data Analysis"
            icon={<Database className="w-10 h-10" />}
            content="We're currently scraping thousands of sites to analyze and protect your content. Our AI-powered system processes terabytes of data to ensure comprehensive coverage."
            status={dataAnalysisStatus}
          />
          <DashboardBox
            title="Protection Results"
            icon={<Shield className="w-10 h-10" />}
            content="Our system has identified multiple instances of your content being used without authorization. View detailed reports and take action to protect your intellectual property."
          />
          <DashboardBox
            title="Advanced Protection"
            icon={<Fingerprint className="w-10 h-10" />}
            content="We use cutting-edge techniques like pHash and video fingerprinting to ensure the highest level of content protection. Your videos are safe with our multi-layered security approach."
          />
        </div>
      </main>
    </div>
  )
}

interface DashboardBoxProps {
  title: string
  icon: React.ReactNode
  content: string
  status?: "pending" | "success"
}

const DashboardBox: React.FC<DashboardBoxProps> = ({ title, icon, content, status }) => {
  return (
    <motion.div
      className="border border-white p-8 rounded-lg relative overflow-hidden group"
      whileHover={{ scale: 1.05 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
    >
      <motion.div
        className="absolute inset-0 pointer-events-none"
        animate={{
          boxShadow: "0 0 20px 2px rgba(255, 255, 255, 0.3), 0 0 6px 1px rgba(255, 255, 255, 0.3) inset",
        }}
        transition={{ duration: 0.2 }}
      />
      <div className="flex items-center mb-4">
        {icon}
        <h2 className="text-white text-2xl font-bold ml-3">{title}</h2>
      </div>
      <p className="text-gray-300 text-lg">{content}</p>
      {status && (
        <div className="absolute bottom-3 right-3">
          <span className={`px-3 py-1 rounded-full text-sm ${status === "pending" ? "bg-yellow-500" : "bg-green-500"}`}>
            {status}
          </span>
        </div>
      )}
    </motion.div>
  )
}

