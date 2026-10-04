import "./globals.css";
import GoogleProvider from "../providers/google-provider";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <GoogleProvider>
          {children}
        </GoogleProvider>
      </body>
    </html>
  );
}