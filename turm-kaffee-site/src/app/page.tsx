import Section01Nav from "@/components/sections/01-nav";
import Section02Hero from "@/components/sections/02-hero";
import Section03About from "@/components/sections/03-about";
import Section04HowItWorks from "@/components/sections/04-how_it_works";
import Section05ProductShowcase from "@/components/sections/05-product_showcase";
import Section06Pricing from "@/components/sections/06-pricing";
import Section07Testimonials from "@/components/sections/07-testimonials";
import Section08Newsletter from "@/components/sections/08-newsletter";
import Section09Footer from "@/components/sections/09-footer";

export default function Home() {
  return (
    <main className="min-h-screen">
      <Section01Nav />
      <Section02Hero />
      <Section03About />
      <Section04HowItWorks />
      <Section05ProductShowcase />
      <Section06Pricing />
      <Section07Testimonials />
      <Section08Newsletter />
      <Section09Footer />
    </main>
  );
}
