import { useState } from 'react';
import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';
import { App } from 'antd';

interface UseFormModalOptions<T> {
  createFn: (data: Partial<T>) => Promise<T>;
  updateFn: (id: number, data: Partial<T>) => Promise<T>;
  queryKey: string;
}

interface UseFormModalReturn<T> {
  open: boolean;
  setOpen: (open: boolean) => void;
  editingItem: T | null;
  setEditingItem: (item: T | null) => void;
  createMutation: UseMutationResult<T, Error, Partial<T>>;
  updateMutation: UseMutationResult<T, Error, { id: number; data: Partial<T> }>;
  handleOpen: (item?: T) => void;
  handleClose: () => void;
}

function useFormModal<T extends { id?: number }>(options: UseFormModalOptions<T>): UseFormModalReturn<T> {
  const { createFn, updateFn, queryKey } = options;
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<T | null>(null);

  const createMutation = useMutation({
    mutationFn: createFn,
    onSuccess: () => {
      message.success('创建成功');
      queryClient.invalidateQueries({ queryKey: [queryKey] });
      setOpen(false);
      setEditingItem(null);
    },
    onError: (error: Error) => {
      message.error(error.message || '创建失败');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<T> }) => updateFn(id, data),
    onSuccess: () => {
      message.success('更新成功');
      queryClient.invalidateQueries({ queryKey: [queryKey] });
      setOpen(false);
      setEditingItem(null);
    },
    onError: (error: Error) => {
      message.error(error.message || '更新失败');
    },
  });

  const handleOpen = (item?: T) => {
    setEditingItem(item || null);
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setEditingItem(null);
  };

  return {
    open,
    setOpen,
    editingItem,
    setEditingItem,
    createMutation,
    updateMutation,
    handleOpen,
    handleClose,
  };
}

export { useFormModal };
export type { UseFormModalOptions, UseFormModalReturn };
