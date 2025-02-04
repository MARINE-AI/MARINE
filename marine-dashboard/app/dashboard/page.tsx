"use client"

import { useState, useEffect } from "react"
import { useSession } from "next-auth/react"
import { Upload, FileVideo, AlertTriangle, Check, ChevronRight, Search, Frown, Clock } from "lucide-react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

// Define a comprehensive type for video uploads
interface VideoUpload {
  id: number;
  title: string;
  status: "clean" | "flagged";
  uploadDate: string;
  duration: string;
  analysisDetails?: {
    contentId: string;
    similarityPercentage: number;
    flaggedSection?: string;
  };
}

export default function Dashboard() {
  const { data: session } = useSession()
  const [uploads, setUploads] = useState<VideoUpload[]>([])
  const [searchTerm, setSearchTerm] = useState("")
  const [selectedUpload, setSelectedUpload] = useState<VideoUpload | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchUploads = async () => {
      // Only fetch if user is logged in
      if (!session?.user?.email) {
        setIsLoading(false)
        return
      }

      try {
        setIsLoading(true)
        const res = await fetch(
          `http://localhost:8080/dashboard/videos?user_email=${encodeURIComponent(session.user.email)}`,
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            }
          }
        )

        if (!res.ok) {
          throw new Error('Failed to fetch uploads')
        }

        const data: VideoUpload[] = await res.json()
        setUploads(data || [])  // Ensure data is an array even if null
        setError(null)
      } catch (err) {
        console.error('Error fetching uploads:', err)
        setError(err instanceof Error ? err.message : 'An unknown error occurred')
        setUploads([])
      } finally {
        setIsLoading(false)
      }
    }

    fetchUploads()
  }, [session])

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return "Good morning"
    if (hour < 18) return "Good afternoon"
    return "Good evening"
  }

  const filteredUploads = uploads ? uploads.filter((upload) => 
    upload.title.toLowerCase().includes(searchTerm.toLowerCase())
  ) : []

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#003f42] flex items-center justify-center">
        <div className="text-[#00d1c1] text-2xl">Loading your uploads...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#003f42] p-6">
      <div className="max-w-7xl mx-auto">
        {/* Greeting Section */}
        <div className="bg-[#005f63] rounded-lg p-6 mb-6 shadow-lg border border-[#00d1c1]/30">
          <h1 className="text-3xl font-bold text-[#00d1c1] mb-2">
            {getGreeting()}, {session?.user?.name?.split(" ")[0] || "User"}!
          </h1>
          <p className="text-lg text-[#00b8d4]">Welcome to your Marine Dashboard</p>
        </div>

        {/* Upload and Search Section */}
        <div className="flex justify-between items-center mb-6">
          <Link href="/dashboard/upload">
            <Button className="bg-[#00b8d4] text-white hover:bg-[#00a9b0] transition-colors duration-300">
              <Upload className="mr-2 h-4 w-4" /> Upload New Content
            </Button>
          </Link>
          <div className="relative w-64">
            <Input
              type="text"
              placeholder="Search uploads..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 bg-[#005f63] text-white border-[#00d1c1] focus:ring-2 focus:ring-[#00b8d4] placeholder-[#00a9b0]"
            />
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#00d1c1]" />
          </div>
        </div>

        {/* Error Handling */}
        {error && (
          <Card className="bg-[#005f63] border-red-500 text-center p-6">
            <CardContent>
              <AlertTriangle className="mx-auto text-red-500 h-16 w-16 mb-4" />
              <h2 className="text-2xl font-bold text-white mb-2">Error Fetching Uploads</h2>
              <p className="text-[#00a9b0] mb-4">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Uploads Section with Scrollable Area */}
        <div className="h-[calc(100vh-300px)] overflow-y-auto">
          {uploads.length === 0 && !error ? (
            // No Uploads State
            <Card className="bg-[#005f63] border-[#00d1c1] text-center p-6">
              <CardContent>
                <Frown className="mx-auto text-[#00d1c1] h-16 w-16 mb-4" />
                <h2 className="text-2xl font-bold text-[#00b8d4] mb-2">No uploads yet</h2>
                <p className="text-[#00a9b0] mb-4">Start by uploading your first piece of content!</p>
                <Link href="/dashboard/upload">
                  <Button className="bg-[#00b8d4] text-white hover:bg-[#00a9b0] transition-colors duration-300">
                    <Upload className="mr-2 h-4 w-4" /> Upload New Content
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ) : filteredUploads.length === 0 ? (
            // No Search Results State
            <Card className="bg-[#005f63] border-[#00d1c1] text-center p-6">
              <CardContent>
                <Search className="mx-auto text-[#00d1c1] h-16 w-16 mb-4" />
                <h2 className="text-2xl font-bold text-[#00b8d4] mb-2">No results found</h2>
                <p className="text-[#00a9b0]">Try adjusting your search term</p>
              </CardContent>
            </Card>
          ) : (
            // Uploads Grid
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredUploads.map((upload) => (
                <Card
                  key={upload.id}
                  className="bg-[#005f63] border-[#00d1c1]/50 hover:bg-[#006d72] transition-all duration-300"
                >
                  <CardHeader className="pb-2">
                    <CardTitle className="text-[#00d1c1] text-lg flex items-center">
                      <FileVideo className="mr-2 text-[#00b8d4]" />
                      {upload.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pb-2">
                    <div className="flex justify-between items-center mb-2">
                      <Badge
                        variant={upload.status === "clean" ? "default" : "destructive"}
                        className={`${
                          upload.status === "clean" ? "bg-[#00d1c1] hover:bg-[#00b8d4]" : "bg-red-500 hover:bg-red-600"
                        } text-[#003f42]`}
                      >
                        {upload.status === "clean" ? (
                          <>
                            <Check className="mr-1 h-3 w-3" /> Clean
                          </>
                        ) : (
                          <>
                            <AlertTriangle className="mr-1 h-3 w-3" /> Flagged
                          </>
                        )}
                      </Badge>
                      <span className="text-[#00a9b0] text-sm flex items-center">
                        <Clock className="mr-1 h-3 w-3" /> {upload.duration}
                      </span>
                    </div>
                    <CardDescription className="text-[#00b8d4] text-xs">Uploaded on {upload.uploadDate}</CardDescription>
                  </CardContent>
                  <CardFooter>
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button
                          variant="outline"
                          className="w-full text-[#00d1c1] border-[#00d1c1] hover:bg-[#00a9b0] hover:text-[#003f42] transition-colors duration-300"
                          onClick={() => setSelectedUpload(upload)}
                        >
                          View Details <ChevronRight className="ml-2 h-4 w-4" />
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="bg-[#005f63] border-[#00d1c1]">
                        <DialogHeader>
                          <DialogTitle className="text-[#00d1c1]">{selectedUpload?.title}</DialogTitle>
                          <DialogDescription className="text-[#00b8d4]">
                            Uploaded on {selectedUpload?.uploadDate}
                          </DialogDescription>
                        </DialogHeader>
                        <div className="text-[#00a9b0]">
                          <p className="mb-2">Status: {selectedUpload?.status}</p>
                          <p className="mb-2">Duration: {selectedUpload?.duration}</p>
                          {selectedUpload?.status === "flagged" && selectedUpload.analysisDetails && (
                            <div>
                              <p className="font-semibold mb-1 text-[#00d1c1]">Content Analysis Results:</p>
                              <ul className="list-disc pl-5 text-[#00b8d4]">
                                <li>{selectedUpload.analysisDetails.similarityPercentage}% similarity with content ID: {selectedUpload.analysisDetails.contentId}</li>
                                {selectedUpload.analysisDetails.flaggedSection && (
                                  <li>Flagged section: {selectedUpload.analysisDetails.flaggedSection}</li>
                                )}
                              </ul>
                            </div>
                          )}
                        </div>
                      </DialogContent>
                    </Dialog>
                  </CardFooter>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}