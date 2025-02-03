import FileUpload from "../../components/fileupload"
import Sidebar from "../../components/sidebar"

export default function UploadPage() {
  return (
    <div className="flex min-h-screen bg-gradient-to-br from-[#001F29] to-[#003543]">
      <Sidebar />
      <main className="flex-1 p-8 ml-24 mr-12 relative">
        <FileUpload />
      </main>
    </div>
  )
}
