import "./globals.css";
import { Orbitron } from "next/font/google"
const orbitron = Orbitron({ subsets: ["latin"] })
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
      <body className={orbitron.className}>
        {children}
      </body>
    </html>
  );
}