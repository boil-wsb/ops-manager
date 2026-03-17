import type { ThemeConfig } from 'antd';
import { theme } from 'antd';

export const lightTheme: ThemeConfig = {
  token: {
    colorPrimary: '#1890ff',
    colorBgContainer: '#ffffff',
    colorBgLayout: '#f5f5f5',
    colorText: 'rgba(0, 0, 0, 0.88)',
    colorTextSecondary: 'rgba(0, 0, 0, 0.65)',
    colorBorder: '#d9d9d9',
    colorBorderSecondary: '#f0f0f0',
  },
  components: {
    Card: {
      colorBgContainer: '#ffffff',
    },
    Table: {
      colorBgContainer: '#ffffff',
      headerBg: '#fafafa',
    },
    Menu: {
      darkItemBg: '#001529',
      darkItemSelectedBg: '#1890ff',
    },
    Layout: {
      headerBg: '#ffffff',
      siderBg: '#001529',
      bodyBg: '#f5f5f5',
    },
  },
};

export const darkTheme: ThemeConfig = {
  token: {
    colorPrimary: '#177ddc',
    colorBgContainer: '#141414',
    colorBgLayout: '#000000',
    colorText: 'rgba(255, 255, 255, 0.85)',
    colorTextSecondary: 'rgba(255, 255, 255, 0.65)',
    colorBorder: '#434343',
    colorBorderSecondary: '#303030',
  },
  algorithm: theme.darkAlgorithm,
  components: {
    Card: {
      colorBgContainer: '#1f1f1f',
    },
    Table: {
      colorBgContainer: '#1f1f1f',
      headerBg: '#2a2a2a',
      rowHoverBg: '#2a2a2a',
    },
    Menu: {
      darkItemBg: '#001529',
      darkItemSelectedBg: '#177ddc',
    },
    Layout: {
      headerBg: '#1f1f1f',
      siderBg: '#001529',
      bodyBg: '#000000',
    },
    Input: {
      colorBgContainer: '#1f1f1f',
    },
    Select: {
      colorBgContainer: '#1f1f1f',
    },
    Modal: {
      colorBgElevated: '#1f1f1f',
    },
    Drawer: {
      colorBgElevated: '#1f1f1f',
    },
    Dropdown: {
      colorBgElevated: '#1f1f1f',
    },
  },
};

export const cssVarTheme = {
  light: {
    '--bg-color': '#f5f5f5',
    '--bg-card': '#ffffff',
    '--text-primary': 'rgba(0, 0, 0, 0.88)',
    '--text-secondary': 'rgba(0, 0, 0, 0.65)',
    '--border-color': '#d9d9d9',
    '--shadow-sm': '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02)',
    '--shadow-md': '0 6px 16px 0 rgba(0, 0, 0, 0.08), 0 3px 6px -4px rgba(0, 0, 0, 0.12), 0 9px 28px 8px rgba(0, 0, 0, 0.05)',
    '--radius-sm': '4px',
    '--radius-md': '6px',
    '--radius-lg': '8px',
  },
  dark: {
    '--bg-color': '#141414',
    '--bg-card': '#1f1f1f',
    '--text-primary': 'rgba(255, 255, 255, 0.85)',
    '--text-secondary': 'rgba(255, 255, 255, 0.65)',
    '--border-color': '#434343',
    '--shadow-sm': '0 1px 2px 0 rgba(0, 0, 0, 0.3), 0 1px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px 0 rgba(0, 0, 0, 0.3)',
    '--shadow-md': '0 6px 16px 0 rgba(0, 0, 0, 0.5), 0 3px 6px -4px rgba(0, 0, 0, 0.6), 0 9px 28px 8px rgba(0, 0, 0, 0.4)',
    '--radius-sm': '4px',
    '--radius-md': '6px',
    '--radius-lg': '8px',
  },
};
