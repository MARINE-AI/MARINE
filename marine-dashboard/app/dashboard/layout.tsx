import Sidebar from "../components/sidebar"

export default function RootLayout({
    children,
  }: {
    children: React.ReactNode
  }) {
    return (
      <html lang="en">
        <head>
          <link rel="icon" href="/favicon.ico" sizes="any" />
        </head>
        <body>
            <Sidebar></Sidebar>
          {children}
        </body>
      </html>
    );
  }