import FloatingTopBar from "@/app/components/header"

export default function Home() {
  return (
    <div className="flex bg-midnight-blue min-h-screen">
      <FloatingTopBar />
      <main className="flex-1 p-8 ml-24 mt-20">
        <h1 className="text-4xl font-bold text-white mb-8">Protect Your Content from Pirates</h1>
        <p className="text-xl text-gray-300 mb-8">
          Stop thieves from stealing your videos. We hunt down pirated copies so you don’t have to.
        </p>
        
        {/* What It Does */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <ServiceCard
            title="Find Stolen Videos Anywhere"
            description="Even if they’re edited, cropped, or re-uploaded. We detect 85%+ matches."
            icon="🔍"
          />
          <ServiceCard
            title="Instant Alerts"
            description="Get notified immediately with links to pirated content."
            icon="🚨"
          />
          <ServiceCard
            title="Take Back Control"
            description="Download ready-to-use reports for takedowns or legal action."
            icon="⚖️"
          />
        </div>

        {/* How It Works */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-12">
          <ServiceCard
            title="1. Upload Your Video"
            description="Securely share your original content (like your private Netflix, but better!)."
            icon="📤"
          />
          <ServiceCard
            title="2. We Play Detective"
            description="We scan YouTube, social media, torrents, and shady corners of the web."
            icon="🕵️"
          />
          <ServiceCard
            title="3. AI Does the Work"
            description="Our AI compares every frame, audio clip, and watermark."
            icon="🤖"
          />
          <ServiceCard
            title="4. You Take Action"
            description="Get proof to shut down pirates—fast."
            icon="✅"
          />
        </div>

        {/* Why Use This? */}
        <div id="about-us" className="mt-12">
          <h2 className="text-2xl font-bold text-white mb-4">Why You’ll Love This</h2>
          <p className="text-gray-300">
            Pirates cost creators billions yearly. Instead of wasting hours searching, <strong>let us do the dirty work</strong>. 
            Focus on creating—we’ll handle the policing.
          </p>
        </div>

        {/* Who It’s For */}
        <div id="protection" className="mt-12">
          <h2 className="text-2xl font-bold text-white mb-4">Who Needs This?</h2>
          <p className="text-gray-300">
            Perfect for <strong>creators</strong> (YouTubers, filmmakers, educators), <strong>businesses</strong> protecting 
            training videos/demos, and <strong>teams</strong> fighting piracy legally.
          </p>
        </div>

        {/* Final Call */}
        <div id="benefits" className="mt-12">
          <h2 className="text-2xl font-bold text-white mb-4">Your Time &amp; Money, Protected</h2>
          <ul className="list-disc list-inside text-gray-300 space-y-2">
            <li>No more manual searches—automate the hunt</li>
            <li>Stop losing revenue to copycats</li>
            <li>Protect your brand’s reputation</li>
            <li>24/7 monitoring, zero effort</li>
          </ul>
        </div>
      </main>
    </div>
  )
}

const ServiceCard = ({ title, description, icon }: { title: string; description: string; icon: string }) => (
  <div className="bg-white bg-opacity-10 rounded-lg p-6 hover:bg-opacity-20 transition-colors duration-200">
    <div className="text-4xl mb-4">{icon}</div>
    <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
    <p className="text-gray-300">{description}</p>
  </div>
)