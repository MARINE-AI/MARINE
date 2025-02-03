"use client"

import { signIn, useSession } from "next-auth/react"
import { useRouter } from "next/navigation"
import { Button } from "@/app/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/app/components/ui/card"
import { ChromeIcon } from "lucide-react"
import { useEffect } from "react"

export default function SignInPage() {
  const { data: session } = useSession()
  const router = useRouter()

  useEffect(() => {
    if (session) {
      router.push("/dashboard")
    }
  }, [session, router])

  const handleSignIn = () => {
    signIn("google", { callbackUrl: "/dashboard" })
  }

  return (
    <div className="flex bg-[#0f172a] min-h-screen">
      <main className="flex-1 p-8 ml-24 mt-20 flex items-center justify-center">
        <Card className="w-full max-w-md bg-white/10 text-white border-gray-700">
          <CardHeader className="space-y-1 flex flex-col items-center">
            <div className="text-4xl font-bold mb-4">Marine</div>
            <CardTitle className="text-2xl font-bold text-center">Welcome Back</CardTitle>
            <CardDescription className="text-center text-gray-300">
              Sign in to protect your digital content with our advanced copyright protection and content tracking
              service.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              variant="outline"
              className="w-full flex items-center justify-center space-x-2 bg-white/10 hover:bg-white/20 transition-colors duration-200 text-white border-gray-600"
              onClick={handleSignIn}
            >
              <ChromeIcon size={20} />
              <span>Sign in with Google</span>
            </Button>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}

