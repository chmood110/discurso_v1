import { cn } from "@/lib/cn";

/**
 * PaperLayout
 *
 * The "printed document" surface that hosts the generated speech.
 *  · White background, dark slate text (the entire palette inverts inside).
 *  · A 6px sky stripe sits on top — defined in globals.css via .speech-paper.
 *  · Drop-shadow sized to make it feel like a physical sheet floating
 *    above the navy canvas.
 *
 * Use it as the outermost wrapper of a Speech result; it keeps the responsive
 * padding and rounded corners consistent.
 */

interface Props {
  children: React.ReactNode;
  className?: string;
}

export function PaperLayout({ children, className }: Props) {
  return (
    <div
      className={cn(
        "speech-paper rounded-sm p-12 md:p-20",
        "min-h-[800px]",
        className
      )}
    >
      {children}
    </div>
  );
}
