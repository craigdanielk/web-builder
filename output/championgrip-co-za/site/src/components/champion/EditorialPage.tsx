import Link from "next/link";

export type SourceBlock =
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] }
  | { type: "fields"; items: { label: string; name: string }[] };

export function EditorialPage({
  kicker,
  title,
  lede,
  blocks,
  aside,
}: {
  kicker: string;
  title: string;
  lede?: string;
  blocks: SourceBlock[];
  aside?: { label: string; href: string };
}) {
  return (
    <main className="cg-editorial">
      <p className="cg-kicker">{kicker}</p>
      <h1>{title}</h1>
      {lede ? <p className="cg-lead">{lede}</p> : null}
      <div className="cg-editorial-body">
        {blocks.map((block, index) => {
          if (block.type === "paragraph") {
            return <p key={index}>{block.text}</p>;
          }
          if (block.type === "list") {
            return (
              <ul key={index}>
                {block.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            );
          }
          return (
            <dl key={index} className="cg-fields">
              {block.items.map((field) => (
                <div key={field.name || field.label}>
                  <dt>{field.label || field.name}</dt>
                </div>
              ))}
            </dl>
          );
        })}
      </div>
      {aside ? (
        <p className="cg-fine">
          <Link href={aside.href}>{aside.label}</Link>
        </p>
      ) : null}
    </main>
  );
}
