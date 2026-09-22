import { blogSlugs, SourcePage } from "@/components/champion/SourcePage";

export function generateStaticParams() {
  return blogSlugs().map((slug) => ({ slug }));
}

export default async function BlogPostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <SourcePage path={`/blog/${slug}`} />;
}
