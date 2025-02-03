"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import { Home, Upload, Search, Shield, Settings } from "lucide-react"
import { usePathname } from "next/navigation"
import type React from "react"

const FloatingDock = () => {
  const [windowWidth, setWindowWidth] = useState(0)
  const [hoveredItem, setHoveredItem] = useState<string | null>(null)
  const pathname = usePathname()

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth)
    handleResize()
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  const menuItems = [
    { icon: <Home size={24} />, text: "Dashboard", href: "/dashboard" },
    { icon: <Upload size={24} />, text: "Upload", href: "/dashboard/upload" },
    { icon: <Search size={24} />, text: "Data Analysis", href: "/dashboard/dataanalysis" },
    { icon: <Shield size={24} />, text: "Protect", href: "/protection" },
    { icon: <Settings size={24} />, text: "Settings", href: "/settings" },
  ]

  return (
    <div className="fixed bottom-4 w-full flex justify-center px-4 z-50">
      <motion.div
        className="relative w-full max-w-[400px]"
        initial={{ opacity: 0, y: 100 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 260, damping: 20 }}
      >
        <motion.div
          className="p-2 flex justify-center items-center gap-2 rounded-full shadow-lg"
          style={{
            backgroundColor: "rgba(0, 138, 144, 0.2)",
            backdropFilter: "blur(10px)",
          }}
        >
          {menuItems.map((item, index) => (
            <DockItem
              key={index}
              icon={item.icon}
              text={item.text}
              href={item.href}
              isActive={pathname === item.href}
              onHover={setHoveredItem}
              isHovered={hoveredItem === item.text}
            />
          ))}
        </motion.div>
      </motion.div>
    </div>
  )
}

const DockItem = ({
  icon,
  text,
  href,
  isActive,
  onHover,
  isHovered,
}: {
  icon: React.ReactNode
  text: string
  href: string
  isActive: boolean
  onHover: (text: string | null) => void
  isHovered: boolean
}) => {
  return (
    <Link href={href} className="relative group" onMouseEnter={() => onHover(text)} onMouseLeave={() => onHover(null)}>
      <motion.div
        className={`flex flex-col items-center justify-center mx-auto p-2 rounded-full transition-colors duration-200 ${
          isActive ? "bg-[#006A70] text-white" : "text-white/70 hover:bg-[#006A70] hover:text-white"
        }`}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
        style={{
          opacity: isHovered ? 1 : 0.4, // More dull when not hovered
        }}
      >
        {icon}
      </motion.div>
      <AnimatePresence>
        {isHovered && (
          <motion.div
            className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-[#006A70] text-white px-2 py-1 rounded text-xs whitespace-nowrap"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.2 }}
          >
            {text}
          </motion.div>
        )}
      </AnimatePresence>
    </Link>
  )
}

export default FloatingDock

