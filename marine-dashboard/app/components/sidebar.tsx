"use client"

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { Home, Upload, Search, Shield, Settings } from 'lucide-react'
import { usePathname } from 'next/navigation'
import React from 'react'

const FloatingDock = () => {
  const [windowWidth, setWindowWidth] = useState(0)
  const pathname = usePathname()

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth)
    handleResize()
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  // Calculate dock width based on the window width, up to a maximum of 300px.
  const dockWidth = Math.min(windowWidth - 32, 300)

  const menuItems = [
    { icon: <Home size={24} />, text: "Dashboard", href: "/" },
    { icon: <Upload size={24} />, text: "Upload", href: "/dashboard/upload" },
    { icon: <Search size={24} />, text: "Search", href: "/search" },
    { icon: <Shield size={24} />, text: "Protect", href: "/protection" },
    { icon: <Settings size={24} />, text: "Settings", href: "/settings" },
  ]

  return (
    <motion.div
      // Center the dock at the bottom of the screen
      className="fixed bottom-4 left-1/2 transform -translate-x-1/2 rounded-full shadow-lg overflow-hidden z-50"
      initial={{ opacity: 0, y: 100 }}
      animate={{ 
        opacity: 1, 
        y: 0,
        width: dockWidth,
      }}
      transition={{ type: "spring", stiffness: 260, damping: 20 }}
    >
      <div 
        className="p-2 flex justify-center items-center gap-2"
        style={{ 
          backgroundColor: 'rgba(0, 138, 144, 0.9)',
          backdropFilter: 'blur(10px)',
        }}
      >
        {menuItems.map((item, index) => (
          <DockItem 
            key={index}
            icon={item.icon}
            text={item.text}
            href={item.href}
            isActive={pathname === item.href}
          />
        ))}
      </div>
    </motion.div>
  )
}

const DockItem = ({ 
  icon, 
  text, 
  href, 
  isActive,
}: { 
  icon: React.ReactNode; 
  text: string; 
  href: string; 
  isActive: boolean;
}) => {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <Link 
      href={href} 
      className="relative group"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <motion.div
        className={`flex flex-col items-center justify-center mx-auto p-2 rounded-full transition-colors duration-200 ${
          isActive ? 'bg-[#006A70]' : 'hover:bg-[#006A70]'
        }`}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
      >
        <AnimatePresence>
          {isHovered && (
            // The label is positioned above the icon using absolute positioning.
            <motion.span
              className="text-white text-xs mb-1 absolute top-[-24px] left-1/2 transform -translate-x-1/2 whitespace-nowrap bg-[#006A70] px-2 py-1 rounded-md"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              {text}
            </motion.span>
          )}
        </AnimatePresence>
        <span className={`text-white ${isActive ? 'opacity-100' : 'opacity-70'}`}>
          {icon}
        </span>
      </motion.div>
    </Link>
  )
}

export default FloatingDock
