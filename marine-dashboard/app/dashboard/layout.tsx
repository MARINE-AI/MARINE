import "../globals.css"

export default function DashboardLayout({
    children,
  }: {
    children: React.ReactNode
  }) {
    return (
      <div className="min-h-screen bg-gray-50">
        <main className="p-6 max-w-4xl mx-auto">
          {children}
        </main>
      </div>
    );
  }