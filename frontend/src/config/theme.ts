import type { ThemeConfig } from 'antd';
import { theme } from 'antd';

export const lightTheme: ThemeConfig = {
  token: {
    colorPrimary: '#1890ff',
    colorBgContainer: '#1a1a2e',
    colorBgLayout: '#121220',
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
      darkItemSelectedBg: '#1890ff',
    },
    Layout: {
      headerBg: '#1a1a2e',
      siderBg: '#1e1e2d',
      bodyBg: '#121220',
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
      inkBarColor: '#1890ff',
    },
    Tag: {
      colorBgContainer: 'transparent',
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
    Tag: {
      colorBgContainer: 'transparent',
    },
  },
};

export const cssVarTheme = {
  light: {
    '--bg-color': '#121220',
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
