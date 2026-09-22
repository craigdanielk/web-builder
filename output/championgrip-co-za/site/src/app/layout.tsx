import type { Metadata } from "next";
import { Open_Sans, Raleway } from "next/font/google";
import "./globals.css";
import { CartProvider } from "@/lib/shopify/cart-context";
import { CartDrawer } from "@/lib/shopify/CartDrawer";
import { SiteFooter, SiteHeader } from "@/components/champion/SiteChrome";

const raleway = Raleway({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-raleway" });
const openSans = Open_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-open-sans" });

export const metadata: Metadata = {
  title: "Champion Grip",
  description: "The world's first aerosol bowls grip enhancer. 120ml. R85.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${raleway.variable} ${openSans.variable} antialiased`}>
        <CartProvider>
          <SiteHeader />
          {children}
          <CartDrawer />
          <SiteFooter />
        </CartProvider>
      </body>
    </html>
  );
}
