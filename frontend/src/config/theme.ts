import type { ThemeConfig } from 'antd';
import { theme } from 'antd';

export const lightTheme: ThemeConfig = {
  token: {
    colorPrimary: '#1890ff',
    colorBgContainer: '#f0f3fa',
    colorBgLayout: '#e8ecf4',
    colorText: 'rgba(20, 25, 50, 0.88)',
    colorTextSecondary: 'rgba(20, 25, 50, 0.65)',
    colorBorder: '#c8cee0',
    colorBorderSecondary: '#d8dde8',
  },
  algorithm: theme.defaultAlgorithm,
  components: {
    Card: {
      colorBgContainer: '#f0f3fa',
    },
    Table: {
      colorBgContainer: '#f0f3fa',
      headerBg: '#e8ecf4',
      rowHoverBg: '#e4e8f2',
    },
    Menu: {
      darkItemBg: '#2a3050',
      darkItemSelectedBg: '#1890ff',
    },
    Layout: {
      headerBg: '#f0f3fa',
      siderBg: '#2a3050',
      bodyBg: '#e8ecf4',
    },
    Input: {
      colorBgContainer: '#f5f7fc',
    },
    Select: {
      colorBgContainer: '#f5f7fc',
    },
    Modal: {
      colorBgElevated: '#f0f3fa',
    },
    Drawer: {
      colorBgElevated: '#f0f3fa',
    },
    Dropdown: {
      colorBgElevated: '#f0f3fa',
    },
    Statistic: {
      colorText: 'rgba(20, 25, 50, 0.88)',
    },
    Tabs: {
      colorBgContainer: '#f0f3fa',
      inkBarColor: '#1890ff',
    },
  },
};

export const darkTheme: ThemeConfig = {
  token: {
    colorPrimary: '#177ddc',
    colorBgContainer: '#1a1a2e',
    colorBgLayout: '#0e0e1a',
    colorText: 'rgba(255, 255, 255, 0.88)',
    colorTextSecondary: 'rgba(255, 255, 255, 0.65)',
    colorBorder: '#2a2a4a',
    colorBorderSecondary: '#222240',
  },
  algorithm: theme.darkAlgorithm,
  components: {
    Card: {
      colorBgContainer: '#1e1e36',
    },
    Table: {
      colorBgContainer: '#1a1a2e',
      headerBg: '#22223a',
      rowHoverBg: '#22223a',
    },
    Menu: {
      darkItemBg: '#1e1e2d',
      darkItemSelectedBg: '#177ddc',
    },
    Layout: {
      headerBg: '#1a1a2e',
      siderBg: '#1e1e2d',
      bodyBg: '#0e0e1a',
    },
    Input: {
      colorBgContainer: '#22223a',
    },
    Select: {
      colorBgContainer: '#22223a',
    },
    Modal: {
      colorBgElevated: '#1e1e36',
    },
    Drawer: {
      colorBgElevated: '#1e1e36',
    },
    Dropdown: {
      colorBgElevated: '#1e1e36',
    },
    Statistic: {
      colorText: 'rgba(255, 255, 255, 0.88)',
    },
    Tabs: {
      colorBgContainer: '#1a1a2e',
      inkBarColor: '#177ddc',
    },
  },
};

export const cssVarTheme = {
  light: {
    '--bg-color': '#e8ecf4',
    '--bg-card': '#f0f3fa',
    '--text-primary': 'rgba(20, 25, 50, 0.88)',
    '--text-secondary': 'rgba(20, 25, 50, 0.65)',
    '--border-color': '#c8cee0',
    '--shadow-sm': '0 1px 2px 0 rgba(30, 40, 80, 0.06), 0 1px 6px -1px rgba(30, 40, 80, 0.04)',
    '--shadow-md': '0 6px 16px 0 rgba(30, 40, 80, 0.08), 0 3px 6px -4px rgba(30, 40, 80, 0.1)',
    '--radius-sm': '4px',
    '--radius-md': '6px',
    '--radius-lg': '8px',
  },
  dark: {
    '--bg-color': '#0e0e1a',
    '--bg-card': '#1a1a2e',
    '--text-primary': 'rgba(255, 255, 255, 0.88)',
    '--text-secondary': 'rgba(255, 255, 255, 0.65)',
    '--border-color': '#2a2a4a',
    '--shadow-sm': '0 1px 2px 0 rgba(0, 0, 0, 0.3), 0 1px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px 0 rgba(0, 0, 0, 0.3)',
    '--shadow-md': '0 6px 16px 0 rgba(0, 0, 0, 0.5), 0 3px 6px -4px rgba(0, 0, 0, 0.6), 0 9px 28px 8px rgba(0, 0, 0, 0.4)',
    '--radius-sm': '4px',
    '--radius-md': '6px',
    '--radius-lg': '8px',
  },
};
