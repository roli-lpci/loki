import { useCallback, useState } from 'react';
export function useToast() {
  const [toast, setToast] = useState(null);
  const showToast = useCallback((message, type = 'info') => setToast({ message, type }), []);
  return { toast, showToast, hideToast: () => setToast(null), clearToast: () => setToast(null) };
}
