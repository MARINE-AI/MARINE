 
import FloatingTopBar from "@/app/components/header"

export default function Home() {
  return (
    <div className="flex bg-midnight-blue min-h-screen">
      
      <FloatingTopBar />
      <main className="flex-1 p-8 ml-24 mt-20">
        <h1 className="text-4xl font-bold text-white mb-8">Welcome to Marines</h1>
        <p className="text-xl text-gray-300 mb-8">
          Protect your digital content with our advanced copyright protection and content tracking service.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <ServiceCard
            title="Smart Search"
            description="Scan the internet to identify unauthorized use of your copyrighted content using our advanced algorithms."
            icon="🔍"
          />
          <ServiceCard
            title="Video Fingerprinting"
            description="Embed unique hashes in your videos for easy tracking and identification across the web."
            icon="👆"
          />
          <ServiceCard
            title="pHashing"
            description="Use perceptual hashing to detect similar images and videos, even if they've been slightly modified."
            icon="🧮"
          />
          <ServiceCard
            title="FAISS Integration"
            description="Leverage Facebook AI Similarity Search for fast and efficient content matching at scale."
            icon="🚀"
          />
        </div>
        <div id="about-us" className="mt-12">
          <h2 className="text-2xl font-bold text-white mb-4">About Us</h2>
          <p className="text-gray-300">
            Marines is a cutting-edge SaaS platform dedicated to protecting your digital content and intellectual
            property. Our team of experts combines advanced technology with years of experience to provide you with the
            best content protection solutions.
          </p>
        </div>
        <div id="protection" className="mt-12">
          <h2 className="text-2xl font-bold text-white mb-4">Protection</h2>
          <p className="text-gray-300">
            Our comprehensive protection suite includes real-time monitoring, content fingerprinting, and AI-powered
            detection systems. We ensure that your content remains secure across the internet, giving you peace of mind
            and control over your digital assets.
          </p>
        </div>
        <div id="benefits" className="mt-12">
          <h2 className="text-2xl font-bold text-white mb-4">Benefits We Offer</h2>
          <ul className="list-disc list-inside text-gray-300 space-y-2">
            <li>24/7 content monitoring and protection</li>
            <li>Advanced AI-powered detection algorithms</li>
            <li>Customizable alerts and notifications</li>
            <li>Comprehensive analytics and reporting</li>
            <li>Dedicated customer support</li>
            <li>Scalable solutions for businesses of all sizes</li>
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

