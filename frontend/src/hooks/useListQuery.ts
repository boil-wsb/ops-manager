import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

interface PaginationState {
  current: number;
  pageSize: number;
}

interface UseListQueryOptions<TParams> {
  queryFn: (params: TParams & { skip: number; limit: number }) => Promise<{ total: number; items: any[] }>;
  queryKey: string;
  initialFilter?: Partial<TParams>;
}

interface UseListQueryReturn<T, TParams> {
  data: { total: number; items: T[] } | undefined;
  isLoading: boolean;
  pagination: PaginationState;
  setPagination: (pagination: PaginationState) => void;
  filter: TParams;
  setFilter: (filter: TParams) => void;
}

function useListQuery<T, TParams extends Record<string, any>>(
  options: UseListQueryOptions<TParams>
): UseListQueryReturn<T, TParams> {
  const { queryFn, queryKey, initialFilter } = options;

  const [pagination, setPagination] = useState<PaginationState>({
    current: 1,
    pageSize: 20,
  });

  const [filter, setFilter] = useState<TParams>((initialFilter as TParams) || ({} as TParams));

  const skip = (pagination.current - 1) * pagination.pageSize;
  const limit = pagination.pageSize;

  const { data, isLoading } = useQuery({
    queryKey: [queryKey, pagination, filter],
    queryFn: () =>
      queryFn({
        ...filter,
        skip,
        limit,
      }),
  });

  return {
    data,
    isLoading,
    pagination,
    setPagination,
    filter,
    setFilter,
  };
}

export { useListQuery };
export type { PaginationState, UseListQueryOptions, UseListQueryReturn };
