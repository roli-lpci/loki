import { useEffect, useState } from 'react';
export function useBelowBreakpoint(breakpoint) {
  const getValue = () => typeof window !== 'undefined' && window.innerWidth < breakpoint;
  const [below, setBelow] = useState(getValue);
  useEffect(() => {
    const update = () => setBelow(getValue());
    window.addEventListener('resize', update);
    update();
    return () => window.removeEventListener('resize', update);
  }, [breakpoint]);
  return below;
}
