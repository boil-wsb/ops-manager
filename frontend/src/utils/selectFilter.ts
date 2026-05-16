import type { DefaultOptionType } from 'antd/es/select';

export const fuzzyFilterOption = (input: string, option?: DefaultOptionType): boolean => {
  const text = (option?.label ?? option?.children ?? '') as string;
  return text.toLowerCase().includes(input.toLowerCase());
};
