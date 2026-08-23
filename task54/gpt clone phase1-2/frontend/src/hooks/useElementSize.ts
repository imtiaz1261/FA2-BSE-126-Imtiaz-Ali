import { useEffect, useRef, useState } from "react";

/** Tracks an element's rendered size — used to size react-window's
 * VariableSizeList to its flex-grown container without a fixed height. */
export function useElementSize<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => {
      const box = entry.contentBoxSize?.[0];
      if (box) {
        setSize({ width: box.inlineSize, height: box.blockSize });
      } else {
        setSize({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, ...size };
}
