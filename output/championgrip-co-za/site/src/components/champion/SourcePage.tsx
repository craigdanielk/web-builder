import Link from "next/link";
import { notFound } from "next/navigation";
import catalog from "@/content/pages.json";

type Field = { label: string; name: string; required?: boolean; detail?: string };
type Block =
  | { type: "paragraph"; text: string }
  | { type: "heading"; level?: number; text: string }
  | { type: "list"; items: string[] }
  | { type: "table"; caption?: string; columns: string[]; rows: string[][]; empty?: string }
  | { type: "fields"; items: Field[] }
  | { type: "form"; src: string; title?: string }
  | { type: "cta"; label: string; href: string };

type PageRecord = {
  path: string;
  kicker: string;
  title: string;
  lede: string;
  blocks: Block[];
  media: { src: string; alt: string }[];
  source_url: string;
};

const pages = catalog as Record<string, PageRecord>;

export function blogSlugs(): string[] {
  return Object.values(pages)
    .filter((page) => page.path.startsWith("/blog/") && page.path !== "/blog")
    .map((page) => page.path.slice("/blog/".length));
}

function published(url: string): string {
  const match = url.match(/\/(\d{4})\/(\d{2})\/(\d{2})\//);
  return match ? `${match[1]}-${match[2]}-${match[3]}` : "";
}

export function SourcePage({ path }: { path: string }) {
  const page = pages[path];
  if (!page) notFound();
  const posts = Object.values(pages)
    .filter((item) => item.path.startsWith("/blog/") && item.path !== "/blog")
    .sort((a, b) => a.title.localeCompare(b.title));
  const blocks = page.path === "/blog" ? page.blocks.filter((block) => block.type === "paragraph") : page.blocks;
  const images = page.media || [];

  return (
    <main className={`cg-editorial${blocks.some((block) => block.type === "table") ? " is-wide" : ""}`}>
      <p className="cg-kicker">{page.kicker}</p>
      <h1>{page.title}</h1>
      {page.lede ? <p className="cg-lead">{page.lede}</p> : null}
      {images.length ? (
        <div className={`cg-editorial-media-set${images.length > 1 ? " is-multi" : ""}`}>
          {images.map((image) => (
            <figure key={image.src} className="cg-editorial-media">
              <img src={image.src} alt={image.alt || page.title} />
            </figure>
          ))}
        </div>
      ) : null}
      <div className="cg-editorial-body">
        {blocks.map((block, index) => {
          if (block.type === "paragraph") return <p key={index}>{block.text}</p>;
          if (block.type === "heading") return <h2 key={index}>{block.text}</h2>;
          if (block.type === "list") {
            return (
              <ul key={index}>
                {block.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            );
          }
          if (block.type === "table") {
            return (
              <div key={index} className="cg-table-wrap">
                {block.caption ? <h2>{block.caption}</h2> : null}
                <table>
                  <thead>
                    <tr>
                      {block.columns.map((column) => (
                        <th key={column}>{column}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {block.rows.length ? (
                      block.rows.map((row, rowIndex) => (
                        <tr key={rowIndex}>
                          {row.map((cell, cellIndex) => (
                            <td key={cellIndex}>{cell}</td>
                          ))}
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={block.columns.length}>{block.empty || "No Result Found"}</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            );
          }
          if (block.type === "fields") {
            return (
              <dl key={index} className="cg-fields">
                {block.items.map((field) => (
                  <div key={field.name}>
                    <dt>{field.label}</dt>
                    <dd>{field.detail || (field.required ? "Required" : "")}</dd>
                  </div>
                ))}
              </dl>
            );
          }
          if (block.type === "cta") {
            const external = block.href.startsWith("http") || block.href.startsWith("mailto:") || block.href.startsWith("tel:");
            if (external) {
              return (
                <p key={index} className="cg-cta-row">
                  <a className="cg-buy" href={block.href} target={block.href.startsWith("http") ? "_blank" : undefined} rel="noreferrer">
                    {block.label}
                  </a>
                </p>
              );
            }
            return (
              <p key={index} className="cg-cta-row">
                <Link className="cg-buy" href={block.href}>
                  {block.label}
                </Link>
              </p>
            );
          }
          // Never embed legacy Cognito / WordPress forms on this storefront.
          if (block.type === "form") {
            return null;
          }
          return null;
        })}
      </div>
      {page.path === "/blog" ? (
        <div className="cg-blog-list">
          {posts.map((post) => (
            <Link key={post.path} href={post.path}>
              <span>{published(post.source_url)}</span>
              <strong>{post.title}</strong>
              <em>{post.lede}</em>
            </Link>
          ))}
        </div>
      ) : null}
      {page.path === "/find-a-stockist" ? (
        <p className="cg-fine">
          <Link href="/products/champion-grip-spray-120ml-can-elevate-your-bowling-game-with-confidence">Shop online</Link>
          {" · "}
          <Link href="/become-a-stockist">Trade / stockist enquiry</Link>
        </p>
      ) : null}
    </main>
  );
}
