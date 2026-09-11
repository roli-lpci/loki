import { useCallback, useState } from 'react';
export function useConfirmDelete({ onDelete } = {}) {
  const [pendingId, setPendingId] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const requestDelete = useCallback((id) => setPendingId(id), []);
  const cancel = useCallback(() => { if (!isDeleting) setPendingId(null); }, [isDeleting]);
  const confirm = useCallback(async () => {
    if (pendingId == null || !onDelete) return;
    setIsDeleting(true);
    try { await onDelete(pendingId); setPendingId(null); } finally { setIsDeleting(false); }
  }, [pendingId, onDelete]);
  return { pendingId, isOpen: pendingId != null, isDeleting, requestDelete, cancel, confirm };
}
