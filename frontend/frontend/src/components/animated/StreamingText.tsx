"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

interface StreamingTextProps {
  content: string;
  speed?: number; // ms per word/char
  cursor?: boolean;
  className?: string;
  onComplete?: () => void;
}

export function StreamingText({
  content,
  speed = 30,
  cursor = true,
  className = "",
  onComplete
}: StreamingTextProps) {
  const [displayedText, setDisplayedText] = useState("");
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    let index = 0;
    setDisplayedText("");
    setIsComplete(false);

    const interval = setInterval(() => {
      if (index < content.length) {
        setDisplayedText((prev) => prev + content.charAt(index));
        index++;
      } else {
        clearInterval(interval);
        setIsComplete(true);
        if (onComplete) onComplete();
      }
    }, speed);

    return () => clearInterval(interval);
  }, [content, speed, onComplete]);

  return (
    <span className={className}>
      {displayedText}
      {cursor && !isComplete && (
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ repeat: Infinity, duration: 0.8 }}
          className="inline-block w-1.5 h-[1em] ml-0.5 bg-current align-middle"
        />
      )}
    </span>
  );
}
