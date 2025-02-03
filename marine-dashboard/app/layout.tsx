// app/layout.tsx
import ServiceWorkerRegistration from "../component/ServiceWorkerRegistration";
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        {children}
        <ServiceWorkerRegistration />
      </body>
    </html>
  );
}