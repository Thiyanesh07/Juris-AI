import type { Metadata } from 'next';
import { Instrument_Sans, JetBrains_Mono, DM_Serif_Display } from 'next/font/google';
import './globals.css';
import { AuthContextProvider } from '@/context/AuthContext';

const instrumentSans = Instrument_Sans({
  subsets: ['latin'],
  variable: '--font-instrument-sans',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains-mono',
});

const dmSerifDisplay = DM_Serif_Display({
  weight: '400',
  subsets: ['latin'],
  variable: '--font-dm-serif',
});

export const metadata: Metadata = {
  title: 'Juris AI — Admin Portal',
  description: 'Juris AI system administration, knowledge graph indexing, and operations infrastructure.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${instrumentSans.variable} ${jetbrainsMono.variable} ${dmSerifDisplay.variable}`}
    >
      <body suppressHydrationWarning className="bg-[#E7EDF4] text-[#17253A] font-sans antialiased min-h-screen">
        <AuthContextProvider>
          {children}
        </AuthContextProvider>
      </body>
    </html>
  );
}
