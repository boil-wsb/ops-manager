const toSnakeCase = (str: string): string => {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
};

const toCamelCase = (str: string): string => {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
};

const transformKeys = <T extends Record<string, unknown>>(
  obj: T,
  transformer: (key: string) => string
): Record<string, unknown> => {
  if (obj === null || typeof obj !== 'object') {
    return obj as unknown as Record<string, unknown>;
  }

  if (Array.isArray(obj)) {
    return obj.map((item) =>
      transformKeys(item as Record<string, unknown>, transformer)
    ) as unknown as Record<string, unknown>;
  }

  const result: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(obj)) {
    const newKey = transformer(key);

    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      result[newKey] = transformKeys(value as Record<string, unknown>, transformer);
    } else if (Array.isArray(value)) {
      result[newKey] = value.map((item) =>
        typeof item === 'object' && item !== null
          ? transformKeys(item as Record<string, unknown>, transformer)
          : item
      );
    } else {
      result[newKey] = value;
    }
  }

  return result;
};

export const toSnakeCaseObj = <T extends Record<string, unknown>>(obj: T): Record<string, unknown> => {
  return transformKeys(obj, toSnakeCase);
};

export const toCamelCaseObj = <T extends Record<string, unknown>>(obj: T): Record<string, unknown> => {
  return transformKeys(obj, toCamelCase);
};
