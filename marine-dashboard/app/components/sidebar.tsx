"use client"

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { Home, Upload, Search, Shield, Settings } from 'lucide-react'
import React from 'react'; // Added import for React

const Sidebar = () => {
  const [isHovered, setIsHovered] = useState(false)
  const [windowHeight, setWindowHeight] = useState(0)

  useEffect(() => {
    const handleResize = () => setWindowHeight(window.innerHeight)
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const sidebarHeight = windowHeight * 0.5
  const topOffset = windowHeight * 0.25

  return (
    <motion.div
      className="fixed left-4 rounded-2xl shadow-lg overflow-hidden z-4232"
      initial={{ opacity: 0.6, width: 64 }}
      animate={{ 
        opacity: isHovered ? 1 : 0.6, 
        width: isHovered ? 256 : 64,
        height: sidebarHeight,
        top: topOffset
      }}
      style={{ 
        backgroundColor: isHovered ? '#008A90' : 'rgba(0, 138, 144, 0.7)',
        transition: 'background-color 0.3s ease-in-out'
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="p-4 h-full flex flex-col">
        <h1 className="text-2xl font-bold mb-8 text-white">
          {isHovered ? 'Marines' : 'M'}
        </h1>
        <nav className="flex-grow">
          <ul className="space-y-4">
            <SidebarItem icon={<Home />} text="Dashboard" href="/" />
            <SidebarItem icon={<Upload />} text="Upload" href="/dashboard/upload" />
            <SidebarItem icon={<Search />} text="Search" href="/search" />
            <SidebarItem icon={<Shield />} text="Protect" href="/protection" />
            <SidebarItem icon={<Settings />} text="Settings" href="/settings" />
          </ul>
        </nav>
      </div>
    </motion.div>
  )
}

const SidebarItem = ({ icon, text, href }: { icon: React.ReactNode; text: string; href: string }) => {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <li
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <Link href={href} className="flex items-center space-x-4 text-white hover:bg-[#006A70] rounded-lg p-2 transition-colors duration-200">
        {icon}
        {isHovered && <span>{text}</span>}
      </Link>
    </li>
  )
}

export default Sidebar
