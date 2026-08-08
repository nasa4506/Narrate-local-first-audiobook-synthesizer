import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Narrate — Local Audiobook Studio",
  description:
    "Turn any book into an audiobook locally. Paste chapters, narrate them in parallel on your GPU with Kokoro-82M, and download studio-quality WAV files.",
  keywords: ["audiobook", "TTS", "text-to-speech", "Kokoro", "voice synthesis"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
