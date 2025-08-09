// CodeHighlighter.tsx
import { useEffect } from "react";
import Prism from "prismjs";
import "prismjs/themes/prism-tomorrow.css"; // classic theme

interface CodeHighlighterProps {
  code: string;
  language: string;
}

export default function CodeHighlighter({ code, language }: CodeHighlighterProps) {
  useEffect(() => {
    Prism.highlightAll(); // highlight on first render
  }, [code]);

  return (
    <pre className={`language-${language}`}>
      <code>{code.trim()}</code>
    </pre>
  );
}
