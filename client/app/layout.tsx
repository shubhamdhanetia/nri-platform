import "./globals.css";
import GoogleProvider from "../providers/google-provider";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "NRI Platform",
  description: "Connect with the NRI community wherever home is.",
};

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