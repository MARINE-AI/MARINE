"use client"

import { useState, useRef, useEffect } from "react"
import Link from "next/link"
import { motion } from "framer-motion"

const FloatingTopBar = () => {
  const [hoveredItem, setHoveredItem] = useState<string | null>(null)
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const topBarRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (topBarRef.current) {
        const rect = topBarRef.current.getBoundingClientRect()
        setMousePosition({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top,
        })
      }
    }

    topBarRef.current?.addEventListener("mousemove", handleMouseMove)

    return () => {
      topBarRef.current?.removeEventListener("mousemove", handleMouseMove)
    }
  }, [])

  return (
    <motion.div
      ref={topBarRef}
      className="fixed top-4 left-[14.28%] right-[14.28%] bg-[#460000] shadow-lg overflow-hidden"
      initial={{ opacity: 0, y: -50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      style={{ clipPath: "inset(0)" }}
    >
      <nav className="flex justify-between items-center px-6 py-3 relative">
        <motion.div
          className="absolute bg-black rounded-full w-16 h-16 pointer-events-none"
          animate={{
            x: mousePosition.x - 32,
            y: mousePosition.y - 32,
          }}
          transition={{ type: "spring", stiffness: 500, damping: 28 }}
          style={{ opacity: 0.2 }}
        />
        <Link href="/" className="text-white text-2xl font-extrabold" style={{ fontFamily: "Orbitron, sans-serif" }}>
          MARINES
        </Link>
        <div className="flex space-x-6">
          {["About Us", "Protection", "Benefits"].map((item) => (
            <motion.div
              key={item}
              onHoverStart={() => setHoveredItem(item)}
              onHoverEnd={() => setHoveredItem(null)}
              className="relative"
            >
              <Link
                href={`#${item.toLowerCase().replace(" ", "-")}`}
                className="text-white hover:text-gray-200 transition-colors duration-200"
              >
                {item}
              </Link>
              {hoveredItem === item && (
                <motion.div
                  className="absolute inset-0 bg-black"
                  layoutId="hover"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 0.3 }}
                  transition={{ duration: 0.2 }}
                />
              )}
            </motion.div>
          ))}
        </div>
        <Link
          href="/auth/signin"
          className="bg-white text-[#460000] px-4 py-2 hover:bg-gray-200 transition-colors duration-200"
        >
          Log In
        </Link>
      </nav>
    </motion.div>
  )
}

export default FloatingTopBar

